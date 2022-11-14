import asyncio
import hashlib
import json
import logging

import plyvel
from jsonschema.exceptions import ValidationError
from jsonschema.validators import validate

import config
import messages
import peers
import schemas
import transaction_validation
from org.webpki.json.Canonicalize import canonicalize


class ProtocolError(Exception):
    pass


class Connection:
    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter, incoming: bool) -> None:
        self._reader: asyncio.StreamReader = reader
        self._writer: asyncio.StreamWriter = writer
        self.incoming: bool = incoming
        self.peer_name: str = "{}:{}".format(
            *writer.get_extra_info("peername"))
        logging.info(
            f"Established connection {'from' if incoming else 'to'} {self.peer_name}")

    async def close(self) -> None:
        logging.info(
            f"Closing the connection {'from' if self.incoming else 'to'} {self.peer_name}")
        try:
            self._writer.close()
            await self._writer.wait_closed()
        except ConnectionError as e:
            logging.debug(e)

    async def write_message(self, message: dict) -> None:
        data = canonicalize(message) + b"\n"
        logging.debug(f"Sending {data!r} to {self.peer_name}")
        self._writer.write(data)
        await self._writer.drain()

    async def read_message(self) -> dict:
        data = await self._reader.readuntil()
        logging.debug(f"Received {data!r} from {self.peer_name}")
        return json.loads(data)


class Node:
    def __init__(self, listen_addr: str, storage_path: str) -> None:
        self._server = None
        self._listen_addr: str = listen_addr
        self._peers: peers.Peers = peers.Peers(storage_path)
        self._connections: set[Connection] = set()
        self._client_conn_sem: asyncio.Semaphore = asyncio.Semaphore(
            config.CLIENT_CONNECTIONS)
        self._background_tasks: set = set()
        self._db: plyvel.DB = plyvel.DB(storage_path, create_if_missing=True)

    async def start_server(self):
        self._server = await asyncio.start_server(self.handle_connection, *self._listen_addr.rsplit(":", 1),
                                                  limit=config.BUFFER_SIZE)

        addrs = ", ".join(str(sock.getsockname())
                          for sock in self._server.sockets)
        logging.info(f"Serving on {addrs}")

    async def serve(self) -> None:
        try:
            async with self._server:
                await self._server.serve_forever()
        finally:
            await self.shutdown()

    async def shutdown(self):
        self._db.close()
        if self._server:
            self._server.close()
        for background_task in self._background_tasks:
            background_task.cancel()
        await asyncio.gather(*self._background_tasks)

    def peer_discovery(self) -> None:
        for peer in self._peers:
            task = asyncio.create_task(self.connect(peer))
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)

    def broadcast(self, message: dict) -> None:
        for connection in self._connections:
            task = asyncio.create_task(connection.write_message(message))
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)

    async def connect(self, peer: str) -> None:
        async with self._client_conn_sem:
            if peer in {c.peer_name for c in self._connections}:
                logging.info(f"Already connected to {peer}")
                return
            try:
                logging.info(f"Connecting to {peer}")
                reader, writer = await asyncio.open_connection(*peer.rsplit(":", 1), limit=config.BUFFER_SIZE)
            except OSError as e:
                logging.error(f"Failed connecting to {peer}: {e}")
                return
            await self.handle_connection(reader, writer, False)

    async def handle_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter,
                                incoming=True) -> None:
        conn = Connection(reader, writer, incoming)
        try:
            await conn.write_message(messages.HELLO)
            await conn.write_message(messages.GET_PEERS)
            # Handshake
            message = await conn.read_message()
            validate(message, schemas.HELLO)
            if message["type"] != "hello":
                raise ProtocolError(
                    f"Received message {message} prior to 'hello'")
            self._connections.add(conn)
            logging.info(f"Completed handshake with {conn.peer_name}")
            # Request-response loop
            while True:
                request = await conn.read_message()
                logging.info(
                    f"Received message {request} from {conn.peer_name}")
                if response := self.handle_message(request):
                    await conn.write_message(response)
        except (EOFError, ConnectionError) as e:
            logging.debug(e)
        except ValueError as e:  # JSONDecodeError, UnicodeDecodeError
            logging.error(
                f"Unable to parse message from {conn.peer_name}: {e}")
            response = {
                "type": "error",
                "error": "Failed to parse incoming message as JSON"
            }
            await conn.write_message(response)
        except ValidationError as e:
            logging.error(
                f"Unable to validate message from {conn.peer_name}: {e}")
            response = {
                "type": "error",
                "error": f"Failed to validate incoming message: {e.message}"
            }
            await conn.write_message(response)
        except ProtocolError as e:
            logging.error(
                f"Unable to handle message from {conn.peer_name}: {e}")
            response = {
                "type": "error",
                "error": str(e)
            }
            await conn.write_message(response)
        finally:
            await conn.close()
            self._connections.discard(conn)

    def handle_message(self, message: dict) -> dict | None:
        validate(message, schemas.MESSAGE)
        match message["type"]:
            case "getpeers":
                return {
                    "type": "peers",
                    "peers": [peer for peer in self._peers]
                }
            case "peers":
                self._peers.add_all(message["peers"])
                self._peers.dump()
            case "object":
                object_ = message["object"]
                canonical_object = canonicalize(object_)
                object_id = hashlib.sha256(canonical_object)
                if self._db.get(object_id.digest()) is None:

                    if object_["type"] == "transaction":
                        try:
                            transaction_validation.validate_transaction(
                                object_, self._db)
                        except transaction_validation.InvalidTransaction as e:
                            logging.warning("Received invalid tx")
                            raise ProtocolError(str(e))

                    self._db.put(object_id.digest(), canonical_object)
                    logging.info(
                        f"Saved object: {object_} with object ID: {object_id.hexdigest()}")
                    self.broadcast({
                        "type": "ihaveobject",
                        "objectid": object_id.hexdigest()
                    })
                else:
                    logging.info(
                        f"Object: {object_} ignored, already in the database")
            case "ihaveobject":
                object_id = message["objectid"]
                if self._db.get(bytes.fromhex(object_id)) is None:
                    return {
                        "type": "getobject",
                        "objectid": object_id
                    }
                else:
                    logging.info(
                        f"Object with object ID: {object_id} is already in the database")
            case "getobject":
                object_id = message["objectid"]
                if object_ := self._db.get(bytes.fromhex(object_id)):
                    return {
                        "type": "object",
                        "object": json.loads(object_)
                    }
                else:
                    logging.info(
                        f"Object with object ID: {object_id} is not in the database")

            case "hello":
                raise ProtocolError(
                    "Received a second 'hello' message, even though handshake is completed")


async def main():
    await node.start_server()
    node.peer_discovery()
    await node.serve()


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    node = Node(config.LISTEN_ADDR, config.STORAGE_PATH)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
