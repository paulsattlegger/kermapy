import asyncio
import hashlib
import json
from collections import defaultdict
from weakref import WeakSet

import plyvel

from org.webpki.json.Canonicalize import canonicalize


class Objects:
    def __init__(self, storage_path: str):
        self._db: plyvel.DB = plyvel.DB(storage_path, create_if_missing=True)
        self._events: dict[str, WeakSet[asyncio.Event]] = defaultdict(WeakSet)

    def close(self):
        return self._db.close()

    @staticmethod
    def id(obj: dict) -> str:
        canonical_object = canonicalize(obj)
        return hashlib.sha256(canonical_object).hexdigest()

    def _get(self, namespace: bytes, object_id: str) -> bytes:
        value = self._db.get(namespace + bytes.fromhex(object_id))
        if not value:
            raise KeyError(object_id)
        return value

    def height(self, object_id: str) -> int:
        value = self._get(b'height:', object_id)
        return int.from_bytes(value, 'big', signed=False)

    def utxo(self, object_id: str) -> dict:
        value = self._get(b'utxo:', object_id)
        return json.loads(value)

    def get(self, object_id: str) -> dict:
        value = self._get(b'object:', object_id)
        return json.loads(value)

    def put_object(self, obj: dict) -> None:
        object_id = self.id(obj)
        for event in self._events[object_id]:
            event.set()
        del self._events[object_id]
        self._db.put(b'object:' + bytes.fromhex(object_id), canonicalize(obj))

    def put_block(self, obj: dict, utxo_set: dict):
        object_id = self.id(obj)
        if obj["previd"]:
            height = self.height(obj["previd"]) + 1
        else:
            height = 0
        self._db.put(b'height:' + bytes.fromhex(object_id), int.to_bytes(height, 256, 'big', signed=False))
        self._db.put(b'utxo:' + bytes.fromhex(object_id), canonicalize(utxo_set))
        self.put_object(obj)

    def event_for(self, object_id: str) -> asyncio.Event:
        event = asyncio.Event()
        self._events[object_id].add(event)
        return event

    def __contains__(self, object_id: str):
        return self._db.get(b'object:' + bytes.fromhex(object_id)) is not None