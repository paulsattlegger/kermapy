class ProtocolError(ValueError):
    def __init__(self, msg, doc):
        self.msg = msg
        self.doc = doc
