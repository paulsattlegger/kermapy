import asyncio
import itertools
import json
import logging

from src.kermapy.constants import LISTEN_ADDR
from src.kermapy.exceptions import ProtocolError
from src.kermapy.messages import HELLO, GET_PEERS
from src.kermapy.org.webpki.json.Canonicalize import canonicalize
from src.kermapy.peers import parse_peers, update_peers


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


def handle_message(num: int, message: dict) -> dict:
    if "type" not in message:
        raise ProtocolError("Mandatory key 'type' not found", message)
    if num == 0:
        if message["type"] != "hello":
            raise ProtocolError("Initial message must be type 'hello'", message)
        if "version" not in message:
            raise ProtocolError("Mandatory key 'version' not found", message)
        if message["type"] != "hello" or message["version"] != "0.8.0":
            raise ProtocolError("Message type not 'hello' or version not '0.8.0'", message)
    else:
        if message["type"] == "getpeers":
            peers = parse_peers()
            return {"type": "peers", "peers": list(peers)}
        elif message["type"] == "peers":
            peers = message["peers"]
            logging.info(f"Discovered peers {peers}")
            update_peers(peers)


def handle_error(error: ProtocolError) -> dict:
    return {"type": "error", "error": str(error.msg)}


async def handle_connection(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    peer_name = writer.get_extra_info("peername")
    logging.info(f"Connection with {peer_name}")

    await write_message(HELLO, writer)
    await write_message(GET_PEERS, writer)

    try:
        for num in itertools.count():
            message = await read_message(reader, writer)
            message = handle_message(num, message)
            if message:
                await write_message(message, writer)
    except json.decoder.JSONDecodeError as error:
        logging.error(f"Unable to parse message {error.doc!r} from {peer_name}: {error.msg!r}")
    except ProtocolError as error:
        logging.error(f"Unable to handle message {error.doc!r} from {peer_name}: {error.msg!r}")
        message = handle_error(error)
        await write_message(message, writer)
    logging.info(f"Close the connection with {peer_name}")
    writer.close()


async def main():
    server = await asyncio.start_server(handle_connection, *LISTEN_ADDR.rsplit(":", 1))

    addrs = ", ".join(str(sock.getsockname()) for sock in server.sockets)
    logging.info(f"Serving on {addrs}")

    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    asyncio.run(main())
