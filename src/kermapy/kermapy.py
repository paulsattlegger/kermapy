import asyncio
import ipaddress
import json
import logging
from json import JSONDecodeError

from jsonschema.exceptions import ValidationError
from jsonschema.validators import validate

import config
import messages
import schemas
import storage
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

    async def handle(self, node: "Node") -> None:
        await self.write_message(messages.HELLO)
        await self.write_message(messages.GET_PEERS)
        try:
            # Handshake
            message = await self.read_message()
            validate(message, schemas.HELLO)
            if message["type"] != "hello":
                raise ProtocolError(
                    f"Received message {message} prior to 'hello'")
            logging.info(f"Completed handshake with {self.peer_name}")
            # Request-response loop
            while True:
                request = await self.read_message()
                logging.info(
                    f"Received message {message} from {self.peer_name}")
                if response := node.handle_message(request):
                    await self.write_message(response)
        except JSONDecodeError as e:
            logging.error(
                f"Unable to parse message {e.doc} from {self.peer_name}: {e}")
            response = {
                "type": "error",
                "error": f"Failed to parse incoming message as JSON: {e.doc!r}"
            }
            await self.write_message(response)
        except ValidationError as e:
            logging.error(
                f"Unable to validate message from {self.peer_name}: {e}")
            response = {
                "type": "error",
                "error": f"Failed to validate incoming message: {e.message}"
            }
            await self.write_message(response)
        except ProtocolError as e:
            logging.error(
                f"Unable to handle message from {self.peer_name}: {e}")
            response = {
                "type": "error",
                "error": str(e)
            }
            await self.write_message(response)
        await self.close()

    async def close(self) -> None:
        logging.info(
            f"Closing the connection {'from' if self.incoming else 'to'} {self.peer_name}")
        self._writer.close()
        await self._writer.wait_closed()

    async def write_message(self, message: dict) -> None:
        data = canonicalize(message) + b"\n"
        logging.debug(f"Sending {data!r} to {self.peer_name}")
        self._writer.write(data)
        await self._writer.drain()

    async def read_message(self) -> dict:
        data = await self._reader.readline()
        logging.debug(f"Received {data!r} from {self.peer_name}")
        return json.loads(data)


class Node:
    def __init__(self, listen_addr: str, storage_path: str, connect_to_saved_peers: bool = True) -> None:
        self._listen_addr: str = listen_addr
        self._connect_to_saved_peers = connect_to_saved_peers
        self._storage: storage.Storage = storage.Storage(storage_path)
        self._connections: set[Connection] = set()
        self._client_conn_sem: asyncio.Semaphore = asyncio.Semaphore(
            config.CLIENT_CONNECTIONS)
        self._background_tasks: set = set()

    async def serve(self) -> None:
        if self._connect_to_saved_peers:
            for peer in self._storage:
                task = asyncio.create_task(self.connect(peer))
                self._background_tasks.add(task)
                task.add_done_callback(self._background_tasks.discard)

        server = await asyncio.start_server(self.handle_connection, *self._listen_addr.rsplit(":", 1))

        addrs = ", ".join(str(sock.getsockname()) for sock in server.sockets)
        logging.info(f"Serving on {addrs}")

        try:
            async with server:
                await server.serve_forever()
        except asyncio.CancelledError:
            logging.warn("[serve] Received cancellation")

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
        connection = Connection(reader, writer, incoming)
        self._connections.add(connection)
        try:
            await connection.handle(self)
        except asyncio.CancelledError:
            logging.warning("[handle_connection] Received cancellation")
        except OSError as e:
            logging.error(e)
        self._connections.remove(connection)

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
                    stripped = str(peer).strip()
                    ip_port = stripped.split(":")
                    try:
                        ip = ipaddress.ip_address(ip_port[0])
                        port = int(ip_port[1])

                        if ip.is_global and port == 18018:
                            valid_peers.append(str(ip) + ":" + str(port))
                        else:
                            logging.warn(
                                "Peer IP is not global or port incorrect: " + stripped)

                    except ValueError:
                        logging.warn("Invalid peer: " + stripped)

                self._storage.add_all(valid_peers)
                self._storage.dump()
                for peer in valid_peers:
                    task = asyncio.create_task(self.connect(peer))
                    self._background_tasks.add(task)
                    task.add_done_callback(self._background_tasks.discard)
            case "hello":
                raise ProtocolError(
                    "Received a second 'hello' message, even though handshake is completed")


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    node = Node(config.LISTEN_ADDR, config.STORAGE_PATH)
    asyncio.run(node.serve())
