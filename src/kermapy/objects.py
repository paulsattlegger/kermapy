import asyncio
import hashlib
import json
from collections import defaultdict

import plyvel

from org.webpki.json.Canonicalize import canonicalize


def to_u256(b: bytes) -> int:
    return int.from_bytes(b, 'big', signed=False)


def from_u256(i: int) -> bytes:
    return int.to_bytes(i, 256, 'big', signed=False)


class Objects:
    def __init__(self, storage_path: str):
        self._db: plyvel.DB = plyvel.DB(storage_path, create_if_missing=True)
        self._events: dict[str, set[asyncio.Event]] = defaultdict(set)

    def close(self):
        return self._db.close()

    @staticmethod
    def id(obj: dict) -> str:
        canonical_object = canonicalize(obj)
        return hashlib.sha256(canonical_object).hexdigest()

    def height(self, object_id: str) -> int:
        return to_u256(self._db.get(b'height:' + bytes.fromhex(object_id)))

    def get(self, object_id: str) -> dict:
        value = self._db.get(b'object:' + bytes.fromhex(object_id))
        if not value:
            raise KeyError(object_id)
        return json.loads(value)

    def put(self, obj: dict) -> None:
        object_id = self.id(obj)
        for event in self._events[object_id]:
            event.set()
        del self._events[object_id]

        if obj["type"] == "block":
            if obj["previd"]:
                height = to_u256(self._db.get(b'height:' + bytes.fromhex(obj["previd"])))
                height += 1
            else:
                height = 0
            self._db.put(b'height:' + bytes.fromhex(object_id), from_u256(height))
        self._db.put(b'object:' + bytes.fromhex(object_id), canonicalize(obj))

    def event_for(self, object_id: str) -> asyncio.Event:
        event = asyncio.Event()
        self._events[object_id].add(event)
        return event

    def __contains__(self, object_id: str):
        return self._db.get(b'object:' + bytes.fromhex(object_id)) is not None
