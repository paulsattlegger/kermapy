import asyncio
import json
import pathlib
from typing import Iterator

from config import BOOTSTRAP_NODES


class Peers:
    def __init__(self, path: str) -> None:
        self._dict: dict[str] = {}
        self._queue: asyncio.Queue = asyncio.Queue()
        self._path: pathlib.Path = pathlib.Path(path)
        self.load()

    def __iter__(self) -> Iterator[str]:
        return self._dict.__iter__()

    async def add(self, peer: str) -> None:
        if peer not in self._dict:
            self._dict[peer] = ""
            await self._queue.put(peer)

    async def add_all(self, peers: list[str]) -> None:
        for peer in peers:
            await self.add(peer)

    async def get(self) -> str:
        return await self._queue.get()

    async def put(self, peer) -> None:
        await self._queue.put(peer)

    def dump(self) -> None:
        with self._path.open("w") as fp:
            json.dump(self._dict, fp, indent=4)

    def load(self) -> None:
        if self._path.exists():
            with self._path.open() as fp:
                peers = json.load(fp)
        else:
            peers = BOOTSTRAP_NODES
        for peer in peers:
            self._queue.put_nowait(peer)
        self._dict = peers
