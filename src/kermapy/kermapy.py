import asyncio
import json
import logging
from json import JSONDecodeError

from jsonschema.exceptions import ValidationError
from jsonschema.validators import validate

import messages
import schemas
from config import LISTEN_ADDR, PEER_DISCOVERY_INTERVAL, CLIENT_WORKERS
from exceptions import ProtocolError
from org.webpki.json.Canonicalize import canonicalize
from peers import peers_dict, peers_queue, add_peers


async def write_message(message: dict, writer: asyncio.StreamWriter):
    peer_name = writer.get_extra_info("peername")
    data = dump_message(message)
    logging.debug(f"Sending {data!r} to {peer_name}")
    writer.write(data)
    await writer.drain()


async def read_message(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> dict:
    peer_name = writer.get_extra_info("peername")
    data = await reader.readline()
    logging.debug(f"Received {data!r} from {peer_name}")
    return parse_message(data)


def parse_message(data: bytes) -> dict:
    return json.loads(data)


def dump_message(message: dict) -> bytes:
    return canonicalize(message) + b"\n"


def handle_hello_message(message: dict):
    validate(message, schemas.HELLO_MESSAGE)


async def handle_message(message: dict) -> dict:
    validate(message, schemas.MESSAGE)
    match message["type"]:
        case "getpeers":
            return {"type": "peers", "peers": [peer for peer in peers_dict]}
        case "peers":
            validate(message, schemas.PEERS_MESSAGE)
            await add_peers(message["peers"])
        case "hello":
            raise ProtocolError("Received a second 'hello' message, even though handshake is completed", message)


def handle_error(error: Exception) -> dict:
    if isinstance(error, JSONDecodeError):
        msg = f"Failed to parse incoming message as JSON: {error.doc!r}"
    elif isinstance(error, ValidationError):
        msg = f"The received message does not match one of the known message formats: {error.message!r}"
    elif isinstance(error, ProtocolError):
        msg = str(error.msg)
    else:
        msg = str(error)
    return {"type": "error", "error": msg}


async def handle_connection_reader(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    while True:
        message = await read_message(reader, writer)
        if message := await handle_message(message):
            await write_message(message, writer)


async def handle_connection_writer(writer: asyncio.StreamWriter):
    while True:
        await write_message(messages.GET_PEERS, writer)
        await asyncio.sleep(PEER_DISCOVERY_INTERVAL)


async def handle_connection(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    peer_name = writer.get_extra_info("peername")
    logging.info(f"Connection with {peer_name}")

    try:
        await write_message(messages.HELLO, writer)
        message = await read_message(reader, writer)
        handle_hello_message(message)
        await asyncio.gather(handle_connection_reader(reader, writer), handle_connection_writer(writer))
    except (ValidationError, ProtocolError, JSONDecodeError) as error:
        logging.error(f"Unable to handle message from {peer_name}: {error}")
        message = handle_error(error)
        await write_message(message, writer)
    logging.info(f"Close the connection with {peer_name}")
    writer.close()


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
    while peer := await peers_queue.get():
        try:
            logging.info(f"Connecting to {peer}")
            reader, writer = await asyncio.open_connection(*peer.rsplit(":", 1))
            await handle_connection(reader, writer)
        except OSError as error:
            logging.error(f"Connection to {peer} failed: {error}")


async def main():
    await asyncio.gather(serve(), *[connect() for _ in range(CLIENT_WORKERS)])


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    asyncio.run(main())
