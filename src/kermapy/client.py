import asyncio
import logging

from src.kermapy.constants import PEER_DISCOVERY_CONNECTIONS, PEER_DISCOVERY_INTERVAL
from src.kermapy.peers import parse_peers
from src.kermapy.server import handle_connection


async def peer_discovery(semaphore: asyncio.Semaphore, peer: str):
    async with semaphore:
        try:
            reader, writer = await asyncio.open_connection(*peer.rsplit(":", 1))
        except OSError as error:
            logging.error(f"Connection with {peer} failed: {error}")
        await handle_connection(reader, writer)


async def main():
    semaphore = asyncio.Semaphore(PEER_DISCOVERY_CONNECTIONS)
    while True:
        peers = parse_peers()
        logging.info(f"{len(peers)} peers loaded")
        await asyncio.gather(*[peer_discovery(semaphore, peer) for peer in peers])
        await asyncio.sleep(PEER_DISCOVERY_INTERVAL)


if __name__ == "__main__":
    asyncio.run(main())
