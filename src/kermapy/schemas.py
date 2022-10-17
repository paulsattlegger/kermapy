MESSAGE = {
    "type": "object",
    "properties": {
        "type": {
            "type": "string",
            "enum": ["hello", "peers", "getpeers", "getobject", "ihaveobject", "object", "getmempool", "mempool",
                     "getchaintip", "chaintip"]
        }
    },
    "required": ["type"]
}
HELLO_MESSAGE = {
    "type": "object",
    "properties": {
        "type": {
            "type": "string",
            "enum": ["hello"]
        },
        "version": {
            "type": "string",
            "pattern": r"0\.8\.\d"
        },
        "agent": {
            "type": "string"
        }
    },
    "required": ["type", "version"]
}
PEERS_MESSAGE = {
    "type": "object",
    "properties": {
        "type": {
            "type": "string",
            "enum": ["peers"]
        },
        "peers": {
            "type": "array",
            "items": {
                "type": "string"
            }
        }
    },
    "required": ["type", "peers"]
}
