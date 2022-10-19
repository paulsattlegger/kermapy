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
                    "pattern": r"^0\.8\.\d$"
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
                        "type": "string",
                        "pattern": r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?["
                                   r"0-9][0-9]?):([1-9][0-9]{0,3}|[1-5][0-9]{4}|6[0-4][0-9]{3}|65[0-4][0-9]{2}|655["
                                   r"0-2][0-9]|6553[0-5])$"
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
