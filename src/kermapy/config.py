import os


def _get_bootstrap_nodes() -> dict[str, str]:
    raw_nodes = os.getenv("BOOTSTRAP_NODES", "128.130.122.101:18018")
    nodes = raw_nodes.split(",")
    return {item: "" for item in nodes}


VERSION = "1.2.0"
TARGET = "00000002af000000000000000000000000000000000000000000000000000000"
GENESIS = "00000000a420b7cefa2b7730243316921ed59ffe836e111ca3801f82a4f5360e"
BU = 10 ** 12
BLOCK_REWARD = 50 * BU

BOOTSTRAP_NODES = _get_bootstrap_nodes()
LISTEN_ADDR = os.getenv("LISTEN_ADDR", "0.0.0.0:18018")
STORAGE_PATH = os.getenv("STORAGE_PATH", "../../data")
CLIENT_CONNECTIONS = int(os.getenv("CLIENT_CONNECTIONS", "8"))
BUFFER_SIZE = int(os.getenv("BUFFER_SIZE", "1048576"))
