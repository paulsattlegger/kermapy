import asyncio
import itertools
import json
import logging

from org.webpki.json.Canonicalize import canonicalize

logging.basicConfig(level=logging.DEBUG)


class ProtocolError(Exception):
    pass


def parse_message(data: bytes) -> dict:
    return json.loads(data)


def dump_message(message: dict) -> bytes:
    return canonicalize(message)


def handle_message(num: int, message: dict) -> dict:
    if "type" not in message:
        raise ProtocolError("Mandatory key \"type\" not found")
    if num == 0:
        if message["type"] != "hello":
            raise ProtocolError("Initial message must be type \"hello\"")
        if "version" not in message:
            raise ProtocolError("Mandatory key \"version\" not found")
        if message["type"] != "hello" or message["version"] != "0.8.0":
            raise ProtocolError("Message type not \"hello\" or version not \"0.8.0\"")
        return {
            "type": "hello",
            "version": "0.8.0",
            "agent": "Kermapy 0.0.1"
        }


def handle_error(error: Exception) -> dict:
    message = {"type": "error"}
    if isinstance(error, json.decoder.JSONDecodeError):
        return {**message, "error": "Message not valid JSON"}
    else:
        return {**message, "error": str(error)}


async def handle_connection(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    peer_name = writer.get_extra_info("peername")
    logging.info(f"Connection from {peer_name}")

    for num in itertools.count():
        data = await reader.readline()
        logging.debug(f"Received {data!r} from {peer_name}")
        try:
            request = parse_message(data)
            response = handle_message(num, request)
        except (ValueError, ProtocolError) as error:
            response = handle_error(error)
            data = dump_message(response)
            writer.write(data)
            await writer.drain()
            break
        data = dump_message(response)
        writer.write(data)
        await writer.drain()
    logging.info(f"Close the connection from {peer_name}")
    writer.close()


async def main():
    server = await asyncio.start_server(handle_connection, "0.0.0.0", 18018)

    addrs = ", ".join(str(sock.getsockname()) for sock in server.sockets)
    logging.warning(f"Serving on {addrs}")

    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    # TODO Implement peer discovery bootstrapping by hard-coding some peers (found on TUWEL).
    # TODO Store a list of discovered peers locally. This list should survive reboots.
    # TODO Implement peer discovery using the getpeers and peers messages.
    # TODO Devise a policy to decide which peers to connect to and how many to connect to.
    asyncio.run(main())
