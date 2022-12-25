from .config import VERSION

HELLO = {"type": "hello", "version": "0.8.0", "agent": f"Kermapy {VERSION}"}
GET_PEERS = {"type": "getpeers"}
GET_CHAINTIP = {"type": "getchaintip"}
GET_MEMPOOL = {"type": "getmempool"}
