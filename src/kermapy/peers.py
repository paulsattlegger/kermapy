import ipaddress
import json
import logging
import pathlib
from collections import Counter
from typing import Iterator

from config import BOOTSTRAP_NODES


class Peers:
    def __init__(self, path: str) -> None:
        self._dict: dict[str] = {}
        self._cntr: Counter[str] = Counter()
        self._path: pathlib.Path = pathlib.Path(path)
        self.load()

    def __iter__(self) -> Iterator[str]:
        return self._dict.__iter__()

    def add(self, peer: str) -> None:
        if peer not in self._dict:
            host, port = peer.rsplit(":", 1)
            try:
                ip = ipaddress.ip_address(host)
            except ValueError:
                logging.warning(f"Invalid peer: {peer}")
                return
            if ip.is_global:
                if port == "18018" or self._cntr[host] < 10:
                    self._dict[peer] = ""
                    self._cntr[host] += 1
                else:
                    logging.debug(f"Too many peers for same host: {peer}")
            else:
                logging.warning(f"Peer IP is not global: {peer}")

    def add_all(self, peers: list[str]) -> None:
        for peer in peers:
            self.add(peer)

    def dump(self) -> None:
        with self._path.open("w") as fp:
            json.dump(self._dict, fp, indent=4)

    def load(self) -> None:
        if self._path.exists():
            with self._path.open() as fp:
                peers = json.load(fp)
        else:
            peers = BOOTSTRAP_NODES
        self._dict = peers
