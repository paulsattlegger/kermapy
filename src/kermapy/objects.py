import asyncio
import hashlib
import json
from collections import defaultdict
from weakref import WeakSet

import plyvel

from org.webpki.json.Canonicalize import canonicalize
from . import config


class Objects:
    def __init__(self, storage_path: str):
        self._db: plyvel.DB = plyvel.DB(storage_path, create_if_missing=True)
        self._objects: plyvel.PrefixedDB = self._db.prefixed_db(b'object:')
        self._heights: plyvel.PrefixedDB = self._db.prefixed_db(b'height:')
        self._utxos: plyvel.PrefixedDB = self._db.prefixed_db(b'utxo:')
        self._chaintip: plyvel.PrefixedDB = self._db.prefixed_db(b'chaintip')
        self._mempool: plyvel.PrefixedDB = self._db.prefixed_db(b'mempool')
        self._events: dict[str, WeakSet[asyncio.Event]] = defaultdict(WeakSet)
        if self.id(config.GENESIS) not in self:
            self.put_block(config.GENESIS, {}, 0, True)

    def close(self):
        return self._db.close()

    @staticmethod
    def id(obj: dict) -> str:
        canonical_object = canonicalize(obj)
        return hashlib.sha256(canonical_object).hexdigest()

    def height(self, object_id: str) -> int:
        value = self._heights.get(bytes.fromhex(object_id))
        if not value:
            raise KeyError(object_id)
        return int.from_bytes(value, 'big', signed=False)

    def utxo(self, object_id: str) -> dict:
        value = self._utxos.get(bytes.fromhex(object_id))
        if not value:
            raise KeyError(object_id)
        return json.loads(value)

    def chaintip(self) -> str:
        value = self._chaintip.get(b'')
        if value:
            return value.hex()

    def get(self, object_id: str) -> dict:
        value = self._objects.get(bytes.fromhex(object_id))
        if not value:
            raise KeyError(object_id)
        return json.loads(value)

    def put_object(self, obj: dict) -> None:
        object_id = self.id(obj)
        for event in self._events[object_id]:
            event.set()
        del self._events[object_id]
        self._objects.put(bytes.fromhex(object_id), canonicalize(obj))

    def put_block(self, obj: dict, utxo_set: dict, height: int, new_chaintip: bool):
        object_id = self.id(obj)
        if new_chaintip:
            self._chaintip.put(b'', bytes.fromhex(object_id))
        self._heights.put(bytes.fromhex(object_id), int.to_bytes(height, 256, 'big', signed=False))
        self._utxos.put(bytes.fromhex(object_id), canonicalize(utxo_set))
        self.put_object(obj)

    def event_for(self, object_id: str) -> asyncio.Event:
        event = asyncio.Event()
        self._events[object_id].add(event)
        return event

    def __contains__(self, object_id: str):
        return self._objects.get(bytes.fromhex(object_id)) is not None
