import asyncio
import json
import pathlib

from constants import PEERS, BOOTSTRAP_NODES


async def add_peer(peer: tuple[str, int]):
    host, port = peer
    key = host + ":" + str(port)
    peers_dict[key] = ""
    if peer not in peers_dict:
        await peers_queue.put(key)
        dump_peers()


def remove_peer(peer: tuple[str, int]):
    host, port = peer
    del peers_dict[host + ":" + str(port)]
    dump_peers()


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


peers_dict = parse_peers()
peers_queue = asyncio.Queue()
for p in peers_dict:
    peers_queue.put_nowait(p)
