import asyncio
import json
import pathlib
from typing import Iterator

from config import BOOTSTRAP_NODES


class Peers:
    def __init__(self, path: str) -> None:
        self.dict: dict[str] = {}
        self.queue: asyncio.Queue = asyncio.Queue()
        self.path: pathlib.Path = pathlib.Path(path)
        self.load()

    def __iter__(self) -> Iterator[str]:
        return self.dict.__iter__()

    async def add(self, peer: str) -> None:
        if peer not in self.dict:
            self.dict[peer] = ""
            await self.queue.put(peer)
            self.dump()

    async def add_all(self, peers: list[str]) -> None:
        for peer in peers:
            self.dict[peer] = ""
            await self.queue.put(peer)
        self.dump()

    def remove(self, peer: str) -> None:
        if peer in self.dict:
            del self.dict[peer]
            self.dump()

    def dump(self) -> None:
        with self.path.open("w") as fp:
            json.dump(self.dict, fp, indent=4)

    def load(self) -> None:
        if self.path.exists():
            with self.path.open() as fp:
                peers = json.load(fp)
        else:
            peers = BOOTSTRAP_NODES
        for peer in peers:
            self.queue.put_nowait(peer)
        self.dict = peers
