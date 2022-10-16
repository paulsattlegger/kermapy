import asyncio
import logging

from src.kermapy.constants import PEER_DISCOVERY_CONNECTIONS, PEER_DISCOVERY_INTERVAL
from src.kermapy.peers import parse_peers, dump_peers
from src.kermapy.server import handle_connection


async def peer_discovery(semaphore: asyncio.Semaphore, peer: str) -> bool:
    async with semaphore:
        try:
            logging.info(f"Connecting to {peer}")
            reader, writer = await asyncio.open_connection(*peer.rsplit(":", 1))
        except OSError as error:
            logging.error(f"Connection to {peer} failed: {error}")
            return False
        await handle_connection(reader, writer)
        return True


async def main():
    semaphore = asyncio.Semaphore(PEER_DISCOVERY_CONNECTIONS)
    while True:
        peers = parse_peers()
        logging.info(f"Loaded {len(peers)} peers")
        # Policy:
        #  - Connect to up to PEER_DISCOVERY_CONNECTIONS (default: 8) peers concurrently
        #  - Mark peers as inactive if peer discovery was unsuccessful, and do not connect to those peers again unless
        #    the peer is recovered elsewhere
        #  - After one peer discover round wait PEER_DISCOVERY_INTERVAL seconds (default: 180)
        actives = await asyncio.gather(*[peer_discovery(semaphore, peer) for peer in peers if peers[peer]["active"]])
        for peer, active in zip(peers, actives):
            peers[peer]["active"] = active
        dump_peers(peers)
        logging.info(f"Sleeping {PEER_DISCOVERY_INTERVAL} seconds")
        await asyncio.sleep(PEER_DISCOVERY_INTERVAL)


if __name__ == "__main__":
    asyncio.run(main())
