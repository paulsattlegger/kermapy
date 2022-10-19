import asyncio
import json
import logging
from json import JSONDecodeError

from jsonschema.exceptions import ValidationError
from jsonschema.validators import validate

import messages
import schemas
from config import LISTEN_ADDR, CLIENT_WORKERS, PEERS
from exceptions import ProtocolError
from org.webpki.json.Canonicalize import canonicalize
from peers import Peers


class Connection:
    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter, incoming: bool) -> None:
        self._reader: asyncio.StreamReader = reader
        self._writer: asyncio.StreamWriter = writer
        self.incoming: bool = incoming
        self.peer_name: str = "{}:{}".format(*writer.get_extra_info("peername"))
        logging.info(f"Established connection {'from' if incoming else 'to'} {self.peer_name}")

    async def run(self) -> None:
        await self.write_message(messages.HELLO)
        await self.write_message(messages.GET_PEERS)
        try:
            # Handshake
            message = await self.read_message()
            validate(message, schemas.MESSAGE)
            if message["type"] != "hello":
                raise ProtocolError(f"Received message {message} prior to 'hello'")
            logging.info(f"Completed handshake with {self.peer_name}")
            # Request-response loop
            while True:
                request = await self.read_message()
                validate(request, schemas.MESSAGE)
                logging.info(f"Received message {message} from {self.peer_name}")
                if response := await handle_message(request):
                    await self.write_message(response)
        except JSONDecodeError as e:
            logging.error(f"Unable to parse message {e.doc} from {self.peer_name}: {e}")
            response = {
                "type": "error",
                "error": f"Failed to parse incoming message as JSON: {e.doc}"
            }
            await self.write_message(response)
        except ValidationError as e:
            logging.error(f"Unable to validate message from {self.peer_name}: {e}")
            response = {
                "type": "error",
                "error": f"Failed to validate incoming message: {e.message}"
            }
            await self.write_message(response)
        except ProtocolError as e:
            logging.error(f"Unable to handle message from {self.peer_name}: {e}")
            response = {
                "type": "error",
                "error": str(e)
            }
            await self.write_message(response)
        self.close()

    def close(self) -> None:
        logging.info(f"Closing the connection {'from' if self.incoming else 'to'} {self.peer_name}")
        self._writer.close()

    async def write_message(self, message: dict) -> None:
        data = canonicalize(message) + b"\n"
        logging.debug(f"Sending {data!r} to {self.peer_name}")
        self._writer.write(data)
        await self._writer.drain()

    async def read_message(self) -> dict:
        data = await self._reader.readline()
        logging.debug(f"Received {data!r} from {self.peer_name}")
        return json.loads(data)


async def handle_message(message: dict) -> dict:
    if message["type"] == "getpeers":
        return {
            "type": "peers",
            "peers": [peer for peer in peers]
        }
    elif message["type"] == "peers":
        await peers.add_all(message["peers"])
        peers.dump()
    elif message["type"] == "hello":
        raise ProtocolError("Received a second 'hello' message, even though handshake is completed")


async def handle_connection(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
    connection = Connection(reader, writer, True)
    try:
        await connection.run()
    except OSError as e:
        logging.error(e)


async def serve():
    server = await asyncio.start_server(handle_connection, *LISTEN_ADDR.rsplit(":", 1))

    addrs = ", ".join(str(sock.getsockname()) for sock in server.sockets)
    logging.info(f"Serving on {addrs}")

    async with server:
        await server.serve_forever()


async def connect():
    """
    Peer discovery policy:
      - Connect to up to CLIENT_WORKERS (default: 8) peers concurrently
      - Keep connection with up to CLIENT_WORKERS, i.e., if a connection is terminated issue a new one (to another addr)
      - Store all learned nodes in a dict (synchronized to PEERS file)
    """
    while peer := await peers.get():
        try:
            logging.info(f"Connecting to {peer}")
            reader, writer = await asyncio.open_connection(*peer.rsplit(":", 1))
        except OSError as e:
            logging.error(f"Failed connecting to {peer}: {e}")
            continue
        connection = Connection(reader, writer, False)
        try:
            await connection.run()
        except OSError as e:
            logging.error(e)


async def main():
    await asyncio.gather(serve(), *[connect() for _ in range(CLIENT_WORKERS)])


if __name__ == "__main__":
    peers: Peers = Peers(PEERS)
    logging.basicConfig(level=logging.DEBUG)
    asyncio.run(main())
