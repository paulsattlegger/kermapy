from . import objects


class UtxoError(Exception):
    pass


def create_utxo_set(block: dict, objs: objects.Objects) -> dict:
    prev_block_id = block["previd"]

    if prev_block_id:
        try:
            utxo_set = objs.utxo(prev_block_id)
        except KeyError:
            raise UtxoError(
                f"Could not find utxo for block '{prev_block_id}' in utxo database")
    else:
        utxo_set = dict()

    tx_ids = block["txids"]

    for tx_id in tx_ids:
        try:
            adjust_utxo_set_add_transaction(utxo_set, tx_id, objs)
        except KeyError:
            raise UtxoError(
                f"Could not find transaction '{tx_id}' in object database")
    return utxo_set


def adjust_utxo_set_add_transaction(utxo_set: dict, tx_id: str, objs: objects.Objects) -> None:
    tx = objs.get(tx_id)

    if "inputs" in tx:
        for inpt in tx["inputs"]:
            outpoint = inpt["outpoint"]
            input_tx_id = outpoint["txid"]
            input_tx_index = outpoint["index"]

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
