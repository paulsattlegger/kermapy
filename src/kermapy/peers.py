import json
import pathlib

from constants import PEERS, BOOTSTRAP_NODES


def parse_peers() -> dict:
    path = pathlib.Path(PEERS)
    if path.exists():
        with path.open() as fp:
            return json.load(fp)
    return BOOTSTRAP_NODES


def dump_peers(peers: dict):
    path = pathlib.Path(PEERS)
    with path.open("w") as fp:
        json.dump(peers, fp, indent=4)


def update_peers(new_peers: list):
    peers = parse_peers()
    for new_peer in new_peers:
        peers.setdefault(new_peer, {})
        peers[new_peer]["active"] = True
    dump_peers(peers)
