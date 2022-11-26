import asyncio
from collections import defaultdict
import json
import pathlib
from typing import Callable
import objects
import plyvel


class UtxoError(Exception):
    pass


class UtxoDb:

    def __init__(self, storage_path: str):
        adjusted_path = pathlib.Path(storage_path, "utxos")
        self._db: plyvel.DB = plyvel.DB(adjusted_path, create_if_missing=True)
        self._events: dict[str, set[asyncio.Event]] = defaultdict(set)

    def get(self, block_id: str) -> dict:
        value = self._db.get(bytes.fromhex(block_id))
        if not value:
            raise KeyError(block_id)
        return json.loads(value)

    def put(self, block_id: str, utxo: dict) -> None:
        self._db.put(bytes.fromhex(block_id), utxo)

    async def create_item_async(self, block: dict, objs: objects.Objects, broadcast: Callable[[dict], None]) -> dict:
        prev_block_id = block["previd"]

        utxo_set = dict()

        if prev_block_id is not None:
            if prev_block_id not in self:
                try:
                    await self._request_block_async(prev_block_id, 5, broadcast)
                except asyncio.TimeoutError:
                    raise UtxoError(
                        "Failed to get previous block in time for UTXO sets")
            try:
                utxo_set = self.get(prev_block_id)
            except KeyError:
                raise UtxoError(
                    f"Could not find utxo for block '{prev_block_id}' in utxo database")

        tx_ids = block["txids"]

        for tx_id in tx_ids:
            try:
                stored_tx = objs.get(tx_id)
                self._adjust_set_for_transaction(utxo_set, stored_tx, objs)
            except KeyError:
                raise UtxoError(
                    f"Could not find transaction '{tx_id}' in object database")

        return utxo_set

    def _adjust_set_for_transaction(self, utxo_set: dict, tx: dict, objs: objects.Objects) -> None:
        for input in tx["inputs"]:
            outpoint = input["outpoint"]
            input_tx_id = outpoint["txid"]
            input_tx_index = outpoint["index"]

            prev_tx: dict

            # Get transaction where the funds come from
            try:
                prev_tx = objs.get(input_tx_id)
            except KeyError:
                raise UtxoError(
                    f"Could not find input transaction '{input_tx_id}' in object database")

            pubKey = prev_tx["output"][input_tx_index]["pubkey"]

            utxo_key = pubKey + "_" + input_tx_index

            # Check if output is till in UTXO, otherwise it has been spent already
            if utxo_key not in utxo_set:
                raise UtxoError(
                    f"Could not find UXTO entry for key '{utxo_key}'")

            del utxo_set[utxo_key]

        # Add outputs of current transaction
        for idx, output in enumerate(tx["outputs"]):
            utxo_key = output["pubkey"] + "_" + idx
            utxo_set[utxo_key] = output["value"]

    async def _request_block_async(self, block_id: str, timeout: float, broadcast: Callable[[dict], None]):
        event = self.event_for(block_id)
        broadcast({
            "type": "getobject",
            "objectid": block_id
        })
        await asyncio.wait_for(event.wait(), timeout)

    def event_for(self, block_id: str) -> asyncio.Event:
        event = asyncio.Event()
        self._events[block_id].add(event)
        return event

    def __contains__(self, block_id: str):
        return self._db.get(bytes.fromhex(block_id)) is not None
