import asyncio
import hashlib
import json
from collections import defaultdict
import pathlib

import plyvel

from org.webpki.json.Canonicalize import canonicalize


class Objects:
    def __init__(self, storage_path: str):
        adjusted_path = pathlib.Path(storage_path, "objects")
        self._db: plyvel.DB = plyvel.DB(adjusted_path, create_if_missing=True)
        self._events: dict[str, set[asyncio.Event]] = defaultdict(set)

    def close(self):
        return self._db.close()

    @staticmethod
    def id(obj: dict) -> str:
        canonical_object = canonicalize(obj)
        return hashlib.sha256(canonical_object).hexdigest()

    def get(self, object_id: str) -> dict:
        value = self._db.get(bytes.fromhex(object_id))
        if not value:
            raise KeyError(object_id)
        return json.loads(value)

    def put(self, obj: dict) -> None:
        object_id = self.id(obj)
        for event in self._events[object_id]:
            event.set()
        del self._events[object_id]
        self._db.put(bytes.fromhex(object_id), canonicalize(obj))

    def event_for(self, object_id: str) -> asyncio.Event:
        event = asyncio.Event()
        self._events[object_id].add(event)
        return event

    def __contains__(self, object_id: str):
        return self._db.get(bytes.fromhex(object_id)) is not None
