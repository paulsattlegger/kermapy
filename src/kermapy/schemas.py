HELLO = {
    "type": "object",
    "properties": {
        "type": {
            "type": "string",
            "enum": ["hello"]
        },
        "version": {
            "type": "string",
            "pattern": r"^0\.8\.\d$"
        },
        "agent": {
            "type": "string"
        }
    },
    "required": ["type", "version"],
    "additionalProperties": False
}
PEERS = {
    "type": "object",
    "properties": {
        "type": {
            "type": "string",
            "enum": ["peers"]
        },
        "peers": {
            "type": "array",
            "items": {
                "type": "string",
                "pattern": r"^.*:([1-9][0-9]{0,3}|[1-5][0-9]{4}|6[0-4][0-9]{3}|65[0-4][0-9]{2}|655[0-2][0-9]|6553["
                           r"0-5])$"
            }
        }
    },
    "required": ["type", "peers"],
    "additionalProperties": False
}
GET_PEERS = {
    "type": "object",
    "properties": {
        "type": {
            "type": "string",
            "enum": ["getpeers"]
        },
    },
    "required": ["type"],
    "additionalProperties": False
}
ERROR = {
    "type": "object",
    "properties": {
        "type": {
            "type": "string",
            "enum": ["error"]
        },
        "error": {
            "type": "string"
        }
    },
    "required": ["type", "error"],
    "additionalProperties": False
}
HAVE_OBJECT = {
    "type": "object",
    "properties": {
        "type": {
            "type": "string",
            "enum": ["ihaveobject"]
        },
        "objectid": {
            "type": "string"
        }
    },
    "required": ["type", "objectid"],
    "additionalProperties": False
}
GET_OBJECT = {
    "type": "object",
    "properties": {
        "type": {
            "type": "string",
            "enum": ["getobject"]
        },
        "objectid": {
            "type": "string"
        }
    },
    "required": ["type", "objectid"],
    "additionalProperties": False
}
HEXIFIED_VALUE_32 = {
    "type": "string",
    "pattern": r"^[0-9a-f]+$",
    "minLength": 64,
    "maxLength": 64
}
PRINTABLE_ASCII_UP_TO_128 = {
    "type": "string",
    "pattern": "^[ -~]*$",
    "maxLength": 128
}
TRANSACTION = {
    "type": "object",
    "properties": {
        "type": {
            "type": "string",
            "enum": ["transaction"]
        },
        "inputs": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "outpoint": {
                        "type": "object",
                        "properties": {
                            "txid": HEXIFIED_VALUE_32,
                            "index": {
                                "type": "integer",
                                "minimum": 0
                            }
                        },
                        "required": ["txid", "index"],
                        "additionalProperties": False
                    },
                    "sig": {
                        "type": "string",
                        "pattern": r"^[0-9a-f]+$",
                        "minLength": 128,
                        "maxLength": 128
                    }
                },
                "required": ["outpoint", "sig"],
                "additionalProperties": False
            }
        },
        "outputs": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "pubkey": HEXIFIED_VALUE_32,
                    "value": {
                        "type": "integer",
                        "minimum": 0
                    }
                }
            },
            "required": ["pubkey", "value"],
            "additionalProperties": False
        }
    },
    "required": ["type", "inputs", "outputs"],
    "additionalProperties": False
}
COINBASE_TRANSACTION = {
    "type": "object",
    "properties": {
        "type": {
            "type": "string",
            "enum": ["transaction"]
        },
        "height": {
            "type": "integer",
            "minimum": 0
        },
        "outputs": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "pubkey": HEXIFIED_VALUE_32,
                    "value": {
                        "type": "integer",
                        "minimum": 0
                    }
                }
            },
            "required": ["pubkey", "value"],
            "additionalProperties": False
        }
    },
    "required": ["type", "height", "outputs"],
    "additionalProperties": False
}
ALL_TRANSACTIONS = {
    "anyOf": [
        COINBASE_TRANSACTION,
        TRANSACTION
    ]
}
BLOCK = {
    "type": "object",
    "properties": {
        "type": {
            "type": "string",
            "enum": ["block"]
        },
        "txids": {
            "type": "array",
            "items": HEXIFIED_VALUE_32
        },
        "nonce": HEXIFIED_VALUE_32,
        "previd": {
            "anyOf": [HEXIFIED_VALUE_32, {
                "type": "null"
            }]
        },
        "created": {
            "type": "integer"
        },
        "T": HEXIFIED_VALUE_32,
        "miner": PRINTABLE_ASCII_UP_TO_128,
        "note": PRINTABLE_ASCII_UP_TO_128
    },
    "required": ["type", "txids", "nonce", "previd", "created", "T"],  # "miner" and "note" are optional
    "additionalProperties": False
}
OBJECT = {
    "type": "object",
    "properties": {
        "type": {
            "type": "string",
            "enum": ["object"]
        },
        "object": {
            "anyOf": [ALL_TRANSACTIONS, BLOCK]
        }
    },
    "required": ["type", "object"],
    "additionalProperties": False
}
GET_CHAINTIP = { 
    "type": "object",
    "properties": {
        "type": {
            "type": "string",
            "enum": ["getchaintip"]
        },
    },
    "required": ["type"],
    "additionalProperties": False
}
CHAINTIP = {
    "type": "object",
    "properties": {
        "type": {
            "type": "string",
            "enum": ["chaintip"]
        },
        "blockid": HEXIFIED_VALUE_32
    },
    "required": ["type", "blockid"],
    "additionalProperties": False
}


MESSAGE = {
    "anyOf": [
        HELLO,
        PEERS,
        GET_PEERS,
        ERROR,
        OBJECT,
        HAVE_OBJECT,
        GET_OBJECT,
        GET_CHAINTIP,
        CHAINTIP,
        {
            "type": "object",
            "properties": {
                "type": {
                    "type": "string",
                    "enum": [
                        "getmempool",
                        "mempool",]
                }
            },
            "required": ["type"]
        }
    ]
}
