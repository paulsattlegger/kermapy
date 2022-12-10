import asyncio
import json
import pathlib
from collections import defaultdict

import plyvel

import objects
from org.webpki.json.Canonicalize import canonicalize


class UtxoError(Exception):
    pass


def _adjust_set_for_transaction(utxo_set: dict, tx_id: str, tx: dict, objs: objects.Objects) -> None:
    if "inputs" in tx:
        for inpt in tx["inputs"]:
            outpoint = inpt["outpoint"]
            input_tx_id = outpoint["txid"]
            input_tx_index = outpoint["index"]

            prev_tx: dict

            # Get transaction where the funds come from
            try:
                prev_tx = objs.get(input_tx_id)
            except KeyError:
                raise UtxoError(
                    f"Could not find input transaction '{input_tx_id}' in object database")

            pub_key = prev_tx["outputs"][input_tx_index]["pubkey"]

            utxo_key = input_tx_id + "_" + pub_key + "_" + str(input_tx_index)

            # Check if output is till in UTXO, otherwise it has been spent already
            if utxo_key not in utxo_set:
                raise UtxoError(
                    f"Could not find UTXO entry for key '{utxo_key}'")

            del utxo_set[utxo_key]

    # Add outputs of current transaction
    for idx, output in enumerate(tx["outputs"]):
        utxo_key = tx_id + "_" + output["pubkey"] + "_" + str(idx)
        utxo_set[utxo_key] = output["value"]


class UtxoDb:
    def __init__(self, storage_path: str):
        adjusted_path = str(pathlib.Path(storage_path, "utxos"))
        self._db: plyvel.DB = plyvel.DB(adjusted_path, create_if_missing=True)
        self._events: dict[str, set[asyncio.Event]] = defaultdict(set)

    def get(self, block_id: str) -> dict:
        value = self._db.get(bytes.fromhex(block_id))
        if not value:
            raise KeyError(block_id)
        return json.loads(value)

    def put(self, block_id: str, utxo: dict) -> None:
        for event in self._events[block_id]:
            event.set()
        del self._events[block_id]
        self._db.put(bytes.fromhex(block_id), canonicalize(utxo))

    def create_item(self, block: dict, objs: objects.Objects) -> dict:
        prev_block_id = block["previd"]

        if prev_block_id:
            try:
                utxo_set = self.get(prev_block_id)
            except KeyError:
                raise UtxoError(
                    f"Could not find utxo for block '{prev_block_id}' in utxo database")
        else:
            utxo_set = dict()

        tx_ids = block["txids"]

        for tx_id in tx_ids:
            try:
                stored_tx = objs.get(tx_id)
                _adjust_set_for_transaction(utxo_set, tx_id, stored_tx, objs)
            except KeyError:
                raise UtxoError(
                    f"Could not find transaction '{tx_id}' in object database")

        return utxo_set

    def __contains__(self, block_id: str):
        return self._db.get(bytes.fromhex(block_id)) is not None

    def close(self):
        return self._db.close()
