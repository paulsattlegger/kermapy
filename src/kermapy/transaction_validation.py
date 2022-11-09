import json
import plyvel
import hashlib

from exceptions import ProtocolError

from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.exceptions import InvalidSignature

from org.webpki.json.Canonicalize import canonicalize


def validate_transaction(message: dict, db: plyvel.DB):
    transaction = message["transaction"]

    # is coinbase transaction
    if "height" in transaction:
        pass
    else:
        input_count = len(transaction["inputs"])
        output_count = len(transaction["outputs"])

        if input_count < output_count:
            raise ProtocolError(
                "Transactions sum of input values must be equal or exceed the sum of output values")

        total_input_value = _validate_inputs(transaction, db)
        _validate_outputs(transaction, total_input_value)


def _validate_inputs(transaction: dict, db: plyvel.DB) -> int:
    total_input_value = 0

    for input in transaction["inputs"]:
        outpoint = input["outpoint"]
        tx_id = outpoint["txid"]
        tx_id_bytes = bytes.fromhex(tx_id)

        stored_transaction_bytes = db.get(tx_id_bytes)

        if stored_transaction_bytes is None:
            raise ProtocolError(
                f"Could not find transaction '{tx_id}' in object database")

        stored_transaction = dict(
            json.loads(stored_transaction_bytes))

        index = _validate_input_index(tx_id, outpoint, stored_transaction)
        _validate_input_signature(
            tx_id, input, transaction, stored_transaction, index)

        total_input_value += int(stored_transaction["outputs"][index]["value"])

    return total_input_value


def _validate_input_index(tx_id: str, outpoint: dict, stored_transaction: dict) -> int:
    index = int(outpoint["index"])

    # Check wether the index is valid in the referenced transaction
    if index >= len(stored_transaction["outputs"]):
        raise ProtocolError(
            f"Given index '{index}' for transaction '{tx_id}' is invalid")

    return index


def _validate_input_signature(tx_id: str, input: dict, transaction: dict, stored_transaction: dict, index: int):
    # Get public key from the referenced transaction
    output = stored_transaction["outputs"][index]
    public_key_bytes = bytes.fromhex(output["pubkey"])
    public_key = ed25519.Ed25519PublicKey.from_public_bytes(
        public_key_bytes)

    # Get signature from the new transaction
    signature_bytes = bytes.fromhex(input["sig"])

    cloned_transaction = dict(transaction)

    for input in cloned_transaction["inputs"]:
        input["sig"] = None

    # create hex of data for signature verification
    canonicalized_transaction = canonicalize(cloned_transaction)
    data_bytes = bytes.fromhex(canonicalized_transaction.hex())

    try:
        public_key.verify(signature_bytes, data_bytes)
    except InvalidSignature:
        raise ProtocolError(
            f"Invalid signature for transaction '{tx_id}'")


def _validate_outputs(transaction: dict, total_input_value: int):
    total_output_value = 0

    for output in transaction["outputs"]:
        total_output_value += int(output["value"])

    if total_input_value < total_output_value:
        raise ProtocolError(
            "Sum of input values is smaller than the sum of the specified output values")
