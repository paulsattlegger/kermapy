import os


def _get_bootstrap_nodes() -> dict[str, str]:
    raw_nodes = os.getenv("BOOTSTRAP_NODES", "128.130.122.101:18018")
    nodes = raw_nodes.split(",")
    return {item: "" for item in nodes}


VERSION = "1.2.0"
BOOTSTRAP_NODES = _get_bootstrap_nodes()
LISTEN_ADDR = os.getenv("LISTEN_ADDR", "0.0.0.0:18018")
STORAGE_PATH = os.getenv("STORAGE_PATH", "../../data")
CLIENT_CONNECTIONS = int(os.getenv("CLIENT_CONNECTIONS", "8"))
BUFFER_SIZE = int(os.getenv("BUFFER_SIZE", "1048576"))
