import asyncio
import ipaddress
import json
import logging

from jsonschema.exceptions import ValidationError
from jsonschema.validators import validate

import config
import messages
import schemas
import storage
from org.webpki.json.Canonicalize import canonicalize

import plyvel
import hashlib


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
    def __init__(self, listen_addr: str, storage_path: str, database_path: str) -> None:
        self._server = None
        self._listen_addr: str = listen_addr
        self._storage: storage.Storage = storage.Storage(storage_path)
        self._connections: set[Connection] = set()
        self._client_conn_sem: asyncio.Semaphore = asyncio.Semaphore(
            config.CLIENT_CONNECTIONS)
        self._background_tasks: set = set()
        self._db: plyvel.DB = plyvel.DB(database_path, create_if_missing=True)

    async def start_server(self):
        self._server = await asyncio.start_server(self.handle_connection, *self._listen_addr.rsplit(":", 1))

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
        for peer in self._storage:
            task = asyncio.create_task(self.connect(peer))
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)

    async def gossiping(self, objectID: str) -> None:
        for connection in self._connections:
            message = {"type": "ihaveobject","objectid": objectID}
            await connection.write_message(message)

    async def connect(self, peer: str) -> None:
        async with self._client_conn_sem:
            if peer in {c.peer_name for c in self._connections}:
                logging.info(f"Already connected to {peer}")
                return
            try:
                logging.info(f"Connecting to {peer}")
                reader, writer = await asyncio.open_connection(*peer.rsplit(":", 1))
            except OSError as e:
                logging.error(f"Failed connecting to {peer}: {e}")
                return
            await self.handle_connection(reader, writer, False)

    async def handle_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter,
                                incoming=True) -> None:
        conn = Connection(reader, writer, incoming)
        self._connections.add(conn)
        await conn.write_message(messages.HELLO)
        await conn.write_message(messages.GET_PEERS)
        try:
            # Handshake
            message = await conn.read_message()
            validate(message, schemas.HELLO)
            if message["type"] != "hello":
                raise ProtocolError(
                    f"Received message {message} prior to 'hello'")
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
                "error": f"Failed to parse incoming message as JSON"
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
            self._connections.remove(conn)

    def handle_message(self, message: dict) -> dict | None:
        validate(message, schemas.MESSAGE)
        match message["type"]:
            case "getpeers":
                return {
                    "type": "peers",
                    "peers": [peer for peer in self._storage]
                }
            case "peers":
                valid_peers = []
                for peer in message["peers"]:
                    peer = peer.strip()
                    host, port = peer.rsplit(":", 1)
                    try:
                        ip = ipaddress.ip_address(host)
                        if ip.is_global:
                            valid_peers.append(peer)
                        else:
                            logging.warning(
                                f"Peer IP is not global: {peer}")
                    except ValueError:
                        logging.warning(f"Invalid peer: {peer}")
                self._storage.add_all(valid_peers)
                self._storage.dump()
            case "object":
                object = message["object"]
                bytesObject = json.dumps(object).encode('utf-8')
                logging.info(
                    f"Object: {bytesObject.decode('utf-8')}")
                objectID = hashlib.sha256(bytesObject).hexdigest()
                if self._db.get(objectID.encode()) is None:
                    self._db.put(objectID.encode(), bytesObject)
                    logging.info(
                    f"Saved object: {object} with object ID: {objectID}")
                    # TODO: gossiping
                else: 
                    logging.info(
                    f"Object: {object} ignored, already in the database")#
            case "ihaveobject":
                objectID = message["objectid"]
                if self._db.get(objectID.encode()) is None:
                    return {
                    "type": "getobject",
                    "objectid": objectID
                    }
                else: 
                    logging.info(
                    f"Object with object ID: {objectID} is already in the database")
            case "getobject":
                objectID = message["objectid"]
                if object := self._db.get(objectID.encode()):
                    logging.info(
                    f"Object: {object.decode('utf-8')}")
                    return {
                    "type": "object",
                    "object": object.decode('utf-8')
                    }
                else: 
                    logging.info(
                    f"Object with object ID: {objectID} is not in the database")
            case "hello":
                raise ProtocolError(
                    "Received a second 'hello' message, even though handshake is completed")


async def main():
    await node.start_server()
    node.peer_discovery()
    await node.serve()


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    node = Node(config.LISTEN_ADDR, config.STORAGE_PATH, config.DATABASE_PATH)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
