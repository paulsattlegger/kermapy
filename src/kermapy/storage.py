import json
import pathlib
from typing import Iterator

from config import BOOTSTRAP_NODES


class Storage:
    def __init__(self, path: str) -> None:
        self._dict: dict[str] = {}
        self._path: pathlib.Path = pathlib.Path(path)
        self.load()

    def __iter__(self) -> Iterator[str]:
        return self._dict.__iter__()

    def add(self, peer: str) -> None:
        if peer not in self._dict:
            self._dict[peer] = ""

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
