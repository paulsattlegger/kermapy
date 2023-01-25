import asyncio

from tests.test_kermapy import KermaTestCase, Client

GET_PEERS = b'{"type":"getpeers"}\n'
ERROR_PARSE_JSON = b'{"error":"Failed to parse incoming message as JSON","type":"error"}\n'


class Task1TestCase(KermaTestCase):

    async def test_getHello(self):
        # The grader node “Grader” should be able to connect to your node
        # Grader should receive a valid hello message on connecting
        client = await Client.new()
        response = await client.readline()
        self.assertIn(b'"type":"hello"', response)
        await client.close()

    async def test_getPeers(self):
        # The hello message should be followed by a getpeers message.
        client = await Client.new()
        await client.readline()
        response = await client.readline()
        self.assertIn(b'"type":"getpeers"', response)
        await client.close()

    async def test_getReconnectHello(self):
        # Grader should be able to disconnect, then connect to your node again.
        client = await Client.new()
        response1 = await client.readline()
        await client.readline()
        await client.close()
        client2 = await Client.new()
        response2 = await client2.readline()
        self.assertIn(b'"type":"hello"', response1)
        self.assertIn(b'"type":"hello"', response2)
        await client.close()
        await client2.close()

    async def test_getValidPeers(self):
        # If Grader sends a getpeers message, it must receive a valid peers message.
        client = await Client.new_established()
        await client.write(GET_PEERS)
        response = await client.readline()
        self.assertIn(b'"type":"peers"', response)
        await client.close()

    async def test_getValidPeersDelayed(self):
        # If Grader sends {"type":ge, waits for 0.1 second, then sends tpeers"}, your node should reply with a valid
        # peers message.
        client = await Client.new_established()
        await client.write(b'{"type":"ge')
        await asyncio.sleep(0.1)
        await client.write(b'tpeers"}\n')
        response = await client.readline()
        self.assertIn(b'"type":"peers"', response)
        await client.close()

    async def test_getErrorNoHelloMsg(self):
        # If Grader sends any message before sending hello, your node should send an error message and then disconnect.
        client = await Client.new()
        await client.readline()
        await client.readline()
        await client.readline()
        await client.readline()
        await client.write(GET_PEERS)
        response = await client.readline()
        self.assertIn(
            b'{"error":"Failed to validate incoming message: \'version\' is a required property","type":"error"}\n',
            response)
        await client.close()

    async def test_getErrorWrongPattern1(self):
        # If Grader sends an invalid message, your node should send an error message.
        client = await Client.new_established()
        await client.write(b'Wbgygvf7rgtyv7tfbgy{{{\n')
        response = await client.readline()
        self.assertIn(ERROR_PARSE_JSON, response)
        await client.close()

    async def test_getErrorWrongPattern2(self):
        # If Grader sends an invalid message, your node should send an error message.
        client = await Client.new_established()
        await client.write(b'"type":"diufygeuybhv"\n')
        response = await client.readline()
        self.assertIn(ERROR_PARSE_JSON, response)
        await client.close()

    async def test_getErrorWrongPattern3(self):
        # If Grader sends an invalid message, your node should send an error message.
        client = await Client.new_established()
        await client.write(b'"type":"hello"\n')
        response = await client.readline()
        self.assertIn(ERROR_PARSE_JSON, response)
        await client.close()

    async def test_getErrorWrongPattern4(self):
        # If Grader sends an invalid message, your node should send an error message.
        client = await Client.new_established()
        await client.write(b'"type":"hello","version":"jd3.x"\n')
        response = await client.readline()
        self.assertIn(ERROR_PARSE_JSON, response)
        await client.close()

    async def test_getErrorWrongPattern5(self):
        # If Grader sends an invalid message, your node should send an error message.
        client = await Client.new_established()
        await client.write(b'"type":"hello","version":"5.8.2"\n')
        response = await client.readline()
        self.assertIn(ERROR_PARSE_JSON, response)
        await client.close()

    async def test_getPeersAfterReConnect(self):
        # If grader sends a set of peers in a valid peers message, disconnects, reconnects and sends a getpeers
        # message, it must receive a peers message containing at least the peers sent in the first message.
        client = await Client.new_established()
        # Every peer is a string in the form of <host>:<port>. The default port is 18018 but other ports are valid.
        await client.write(b'{"type":"peers", "peers":["123.123.123.123:40000"]}\n')
        await client.close()
        client2 = await Client.new_established()
        await client2.write(GET_PEERS)
        response = await client2.readline()
        self.assertIn(b'"123.123.123.123:40000"', response)
        await client2.close()

    async def test_getHelloMessageSimultaneously(self):
        # Grader should be able to create two connections to your node simultaneously.
        client = await Client.new_established()
        client2 = await Client.new_established()

        await client.write(GET_PEERS)
        await client2.write(GET_PEERS)
        response1 = await client.readline()
        response2 = await client2.readline()
        self.assertIn(b'"type":"peers"', response1)
        self.assertIn(b'"type":"peers"', response2)
        await client.close()
        await client2.close()

    async def test_getErrorNonUnicode(self):
        client = await Client.new_established()
        await client.write(b'\xFF\n')
        response = await client.readline()
        self.assertIn(ERROR_PARSE_JSON, response)
        await client.close()
