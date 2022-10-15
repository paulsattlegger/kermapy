import json
import pathlib

from src.kermapy.constants import PEERS, BOOTSTRAP_NODES


def parse_peers() -> dict:
    path = pathlib.Path(PEERS)
    if path.exists():
        with path.open() as fp:
            return json.load(fp)
    return BOOTSTRAP_NODES


def update_peers(new_peers: list):
    discovered_peers = parse_peers()
    peers = {**discovered_peers, **{peer: "" for peer in new_peers}}
    path = pathlib.Path(PEERS)
    with path.open("w") as fp:
        json.dump(peers, fp, indent=4)
