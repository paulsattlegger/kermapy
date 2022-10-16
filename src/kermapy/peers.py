import asyncio
import json
import logging
import pathlib

from config import PEERS, BOOTSTRAP_NODES


async def add_peers(peers: list[str]):
    logging.info(f"Discovered peers {peers}")
    for peer in peers:
        await add_peer(peer)
    dump_peers()


async def add_peer(peer: str | tuple[str, int]):
    if isinstance(peer, str):
        key = peer
    else:
        host, port = peer
        key = host + ":" + str(port)
    if key not in peers_dict:
        peers_dict[key] = ""
        await peers_queue.put(key)


def remove_peer(peer: str | tuple[str, int]):
    if isinstance(peer, str):
        key = peer
    else:
        host, port = peer
        key = host + ":" + str(port)
    del peers_dict[key]


def parse_peers() -> dict:
    path = pathlib.Path(PEERS)
    if path.exists():
        with path.open() as fp:
            return json.load(fp)
    return BOOTSTRAP_NODES


def dump_peers():
    path = pathlib.Path(PEERS)
    with path.open("w") as fp:
        json.dump(peers_dict, fp, indent=4)


def main():
    for peer in peers_dict:
        peers_queue.put_nowait(peer)


peers_dict = parse_peers()
peers_queue = asyncio.Queue()
main()
