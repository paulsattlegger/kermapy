MESSAGE = {
    "anyOf": [
        {
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
        },
        {
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
        },
        {
            "type": "object",
            "properties": {
                "type": {
                    "type": "string",
                    "enum": ["getpeers", "getobject", "ihaveobject", "object", "getmempool", "mempool", "getchaintip",
                             "chaintip"]
                }
            },
            "required": ["type"]
        }
    ]
}
