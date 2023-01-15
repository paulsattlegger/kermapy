import copy

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric import ed25519
from jsonschema.exceptions import ValidationError
from jsonschema.validators import validate

from . import objects
from . import schemas
from org.webpki.json.Canonicalize import canonicalize


class InvalidTransaction(Exception):
    pass


class TransactionMetadata:
    def __init__(self, total_input_value, total_output_value):
        self.total_input_value = total_input_value
        self.total_output_value = total_output_value


def validate_transaction(transaction: dict, objs: objects.Objects) -> TransactionMetadata | None:
    """
    Validates a transaction and raises an error, if it is invalid

    Args:
        transaction (dict): The transaction that should be validated
        objs (objects.Objects): The object manager in which the referenced txs should be searched

    Raises:
        InvalidTransaction: The error that is raised when the transaction is not valid

    Returns:
        The metadata of the transaction or None (currently for coinbase transaction)
    """
    try:
        validate(transaction, schemas.ALL_TRANSACTIONS)
    except ValidationError as e:
        raise InvalidTransaction(
            f"Transaction is not well formed: {e.message}")

    # is coinbase transaction
    if "height" in transaction:
        return None
    else:
        total_input_value = _validate_inputs(transaction, objs)
        total_output_value = _validate_outputs(transaction, total_input_value)

        return TransactionMetadata(total_input_value, total_output_value)


def _validate_inputs(transaction: dict, objs: objects.Objects) -> int:
    total_input_value = 0

    outpoints_as_string = []

    for inpt in transaction["inputs"]:
        outpoint = inpt["outpoint"]
        tx_id = outpoint["txid"]

        outpoints_as_string.append(str(outpoint["index"]) + outpoint["txid"])

        try:
            stored_transaction = objs.get(tx_id)
        except KeyError:
            raise InvalidTransaction(
                f"Could not find transaction '{tx_id}' in object database")

        index = _validate_input_index(tx_id, outpoint, stored_transaction)
        _validate_input_signature(
            tx_id, inpt, transaction, stored_transaction, index)

        total_input_value += int(stored_transaction["outputs"][index]["value"])

    # Remove duplicates
    outpoints_set = set(outpoints_as_string)

    # Validate that multiple inputs do not have the same outpoint
    if len(outpoints_set) != len(outpoints_as_string):
        raise InvalidTransaction(
            f"Transaction with id '{tx_id}' has multiple inputs with the same outpoint")

    return total_input_value


def _validate_input_index(tx_id: str, outpoint: dict, stored_transaction: dict) -> int:
    index = int(outpoint["index"])

    # Check whether the index is valid in the referenced transaction
    if index >= len(stored_transaction["outputs"]):
        raise InvalidTransaction(
            f"Given index '{index}' for transaction '{tx_id}' is invalid")

    return index


def _validate_input_signature(tx_id: str, inpt: dict, transaction: dict, stored_transaction: dict, index: int) -> None:
    # Get public key from the referenced transaction
    output = stored_transaction["outputs"][index]
    public_key_bytes = bytes.fromhex(output["pubkey"])
    public_key = ed25519.Ed25519PublicKey.from_public_bytes(
        public_key_bytes)

    # Get signature from the new transaction
    signature_bytes = bytes.fromhex(inpt["sig"])

    cloned_transaction = copy.deepcopy(transaction)

    for inpt in cloned_transaction["inputs"]:
        inpt["sig"] = None

    # create hex of data for signature verification
    canonical_tx = canonicalize(cloned_transaction)
    data_bytes = bytes.fromhex(canonical_tx.hex())

    try:
        public_key.verify(signature_bytes, data_bytes)
    except InvalidSignature:
        raise InvalidTransaction(
            f"Invalid signature for transaction '{tx_id}'")


def _validate_outputs(transaction: dict, total_input_value: int) -> int:
    total_output_value = 0

    for output in transaction["outputs"]:
        total_output_value += int(output["value"])

    if total_input_value < total_output_value:
        raise InvalidTransaction(
            "Sum of input values is smaller than the sum of the specified output values")

    return total_output_value
