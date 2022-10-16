import asyncio
import logging

from constants import PEER_DISCOVERY_CONNECTIONS, PEER_DISCOVERY_INTERVAL
from peers import parse_peers, dump_peers
from server import handle_connection


async def handle_peer(semaphore: asyncio.Semaphore, peer: str) -> bool:
    async with semaphore:
        try:
            logging.info(f"Connecting to {peer}")
            reader, writer = await asyncio.open_connection(*peer.rsplit(":", 1))
            await handle_connection(reader, writer)
        except OSError as error:
            logging.error(f"Connection to {peer} failed: {error}")
            return False
    return True


async def peer_discovery():
    """
    Peer discovery policy:
      - Connect to up to PEER_DISCOVERY_CONNECTIONS (default: 8) peers concurrently
      - Mark peers as inactive if peer discovery was unsuccessful, and do not connect to those peers again unless the
      peer is recovered elsewhere
      - After one peer discover round wait PEER_DISCOVERY_INTERVAL seconds (default: 180)
    :return:
    """
    semaphore = asyncio.Semaphore(PEER_DISCOVERY_CONNECTIONS)
    while True:
        peers = parse_peers()
        logging.info(f"Loaded {len(peers)} peers")

        results = await asyncio.gather(*[handle_peer(semaphore, peer) for peer in peers])
        for peer, result in zip(peers, results):
            peers[peer]["active"] = result
        dump_peers(peers)

        logging.debug(f"Peer discovery sleeping {PEER_DISCOVERY_INTERVAL} seconds")
        await asyncio.sleep(PEER_DISCOVERY_INTERVAL)


async def main():
    await peer_discovery()


if __name__ == "__main__":
    asyncio.run(main())
