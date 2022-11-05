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
