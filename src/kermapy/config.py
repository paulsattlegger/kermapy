import os


def _get_bootstrap_nodes() -> dict[str, str]:
    raw_nodes = os.environ.get("BOOTSTRAP_NODES", "128.130.122.101:18018")
    nodes = raw_nodes.split(",")
    return {item: "" for item in nodes}


VERSION = "1.0.4"
BOOTSTRAP_NODES = _get_bootstrap_nodes()
LISTEN_ADDR = os.environ.get("LISTEN_ADDR", "0.0.0.0:18018")
STORAGE_PATH = os.environ.get("STORAGE_PATH", "../../data/storage.json")
CLIENT_CONNECTIONS = int(os.environ.get("CLIENT_CONNECTIONS", 8))
