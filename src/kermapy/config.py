import os


def _getenv_as_list(key: str, default=None) -> list[str]:
    raw = os.getenv(key, default)
    return raw.split(",")


def _getenv_as_int(key: str, default: int) -> int:
    return int(os.getenv(key, default))


VERSION = "1.4.0"
TARGET = "00000002af000000000000000000000000000000000000000000000000000000"
GENESIS = {
    "T": "00000002af000000000000000000000000000000000000000000000000000000",
    "created": 1624219079,
    "miner": "dionyziz",
    "nonce": "0000000000000000000000000000000000000000000000000000002634878840",
    "note": "The Economist 2021-06-20: Crypto-miners are probably to blame for the graphics-chip shortage",
    "previd": None,
    "txids": [],
    "type": "block"
}
BU = 10 ** 12
BLOCK_REWARD = 50 * BU

LISTEN_ADDR = os.getenv("LISTEN_ADDR", "0.0.0.0:18018")
STORAGE_PATH = os.getenv("STORAGE_PATH", "../../data")
BOOTSTRAP_NODES = _getenv_as_list("BOOTSTRAP_NODES", "128.130.122.101:18018")
CLIENT_CONNECTIONS = _getenv_as_int("CLIENT_CONNECTIONS", 8)
BUFFER_SIZE = _getenv_as_int("BUFFER_SIZE", 1048576)
