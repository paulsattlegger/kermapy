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
OBJECT = {
    "type": "object",
    "properties": {
        "type": {
            "type": "string",
            "enum": ["object"]
        },
    },
    "required": ["type"],
    "additionalProperties": True
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
                            "txid": {
                                "type": "string",
                                "pattern": r"^[0-9a-f]+$",
                                "minLength": 64,
                                "maxLength": 64
                            },
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
                    "pubkey": {
                        "type": "string",
                        "pattern": r"^[0-9a-f]+$",
                        "minLength": 64,
                        "maxLength": 64
                    },
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
                    "pubkey": {
                        "type": "string",
                        "pattern": r"^[0-9a-f]+$",
                        "minLength": 64,
                        "maxLength": 64
                    },
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

MESSAGE = {
    "anyOf": [
        HELLO,
        PEERS,
        GET_PEERS,
        ERROR,
        OBJECT,
        HAVE_OBJECT,
        GET_OBJECT,
        {
            "type": "object",
            "properties": {
                "type": {
                    "type": "string",
                    "enum": [
                        "getmempool",
                        "mempool",
                        "getchaintip",
                        "chaintip"]
                }
            },
            "required": ["type"]
        }
    ]
}
