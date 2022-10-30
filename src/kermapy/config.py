import os


def __get_bootstrap_nodes() -> dict[str, str]:
    raw_nodes = os.environ.get("BOOTSTRAP_NODES", "128.130.122.101:18018")
    nodes = raw_nodes.split(",")
    dict = {}

    for item in nodes:
        dict[item] = ""

    return dict


VERSION = "1.0.2"
BOOTSTRAP_NODES = __get_bootstrap_nodes()
LISTEN_ADDR = os.environ.get("LISTEN_ADDR", "0.0.0.0:18018")
STORAGE_PATH = os.environ.get("STORAGE_PATH", "../../data/storage.json")
CLIENT_CONNECTIONS = int(os.environ.get("CLIENT_CONNECTIONS", 8))
