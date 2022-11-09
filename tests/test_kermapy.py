import asyncio
import os
import shutil
import sys
import tempfile
import unittest
from unittest import IsolatedAsyncioTestCase

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src/kermapy')))

from src.kermapy.kermapy import Node  # noqa: E402

HOST = "127.0.0.1"
PORT = 19000
HELLO = b'{"type":"hello","version":"0.8.0","agent":"Kermapy 0.0.x"}\n'
GET_PEERS = b'{"type":"getpeers"}\n'


class Client:
    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        self._reader = reader
        self._writer = writer

    @staticmethod
    async def new() -> 'Client':
        return Client(*await asyncio.open_connection(HOST, PORT))

    @staticmethod
    async def new_established() -> 'Client':
        client = await Client.new()
        await client.readline()
        await client.write(HELLO)
        await client.readline()
        return client

    async def readline(self) -> bytes:
        return await self._reader.readline()

    async def write(self, message: bytes):
        self._writer.write(message)
        await self._writer.drain()

    async def close(self) -> None:
        self._writer.close()
        await self._writer.wait_closed()


background_tasks = set()


class KermaTestCase(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self._tmp_directory = tempfile.mkdtemp()
        self._node = Node(f"{HOST}:{PORT}", self._tmp_directory)
        await self._node.start_server()
        task = asyncio.create_task(self._node.serve())
        background_tasks.add(task)
        task.add_done_callback(background_tasks.discard)

    def tearDown(self):
        shutil.rmtree(self._tmp_directory)

    async def asyncTearDown(self):
        await self._node.shutdown()
        await asyncio.gather(*background_tasks, return_exceptions=True)


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
        await client.write(GET_PEERS)
        response = await client.readline()
        self.assertIn(b'"type":"error"', response)
        await client.close()

    async def test_getErrorWrongPattern1(self):
        # If Grader sends an invalid message, your node should send an error message.
        client = await Client.new_established()
        await client.write(b'Wbgygvf7rgtyv7tfbgy{{{\n')
        response = await client.readline()
        self.assertIn(b'"type":"error"', response)
        await client.close()

    async def test_getErrorWrongPattern2(self):
        # If Grader sends an invalid message, your node should send an error message.
        client = await Client.new_established()
        await client.write(b'"type":"diufygeuybhv"\n')
        response = await client.readline()
        self.assertIn(b'"type":"error"', response)
        await client.close()

    async def test_getErrorWrongPattern3(self):
        # If Grader sends an invalid message, your node should send an error message.
        client = await Client.new_established()
        await client.write(b'"type":"hello"\n')
        response = await client.readline()
        self.assertIn(b'"type":"error"', response)
        await client.close()

    async def test_getErrorWrongPattern4(self):
        # If Grader sends an invalid message, your node should send an error message.
        client = await Client.new_established()
        await client.write(b'"type":"hello","version":"jd3.x"\n')
        response = await client.readline()
        self.assertIn(b'"type":"error"', response)
        await client.close()

    async def test_getErrorWrongPattern5(self):
        # If Grader sends an invalid message, your node should send an error message.
        client = await Client.new_established()
        await client.write(b'"type":"hello","version":"5.8.2"\n')
        response = await client.readline()
        self.assertIn(b'"type":"error"', response)
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
        self.assertIn(b'"type":"error"', response)
        await client.close()


class Task2TestCase(KermaTestCase):

    async def test_getSameObject(self):
        # If Grader 1 sends a new valid transaction object and then requests the same object, Grader 1 should receive
        # the object.
        client = await Client.new_established()
        await client.write(b'{"type":"object","object":{"type":"block","txids":['
                           b'"740bcfb434c89abe57bb2bc80290cd5495e87ebf8cd0dadb076bc50453590104"],'
                           b'"nonce":"a26d92800cf58e88a5ecf37156c031a4147c2128beeaf1cca2785c93242a4c8b",'
                           b'"previd":"0024839ec9632d382486ba7aac7e0bda3b4bda1d4bd79be9ae78e7e1e813ddd8",'
                           b'"created":"1622825642",'
                           b'"T":"003a000000000000000000000000000000000000000000000000000000000000"}}\n')
        await client.write(
            b'{"type":"getobject","objectid":"4e8174073cb429906c1a04d739b309f435d9333eed3f2904aa4d6ff10d01277b"}\n')
        response = await client.readline()
        self.assertIn(b'"740bcfb434c89abe57bb2bc80290cd5495e87ebf8cd0dadb076bc50453590104"', response)
        self.assertIn(b'"type":"object"', response)
        await client.close()

    async def test_getSameObjectOtherClient(self):
        # If Grader 1 sends a new valid transaction object and then Grader 2 requests the same object,
        # Grader 2 should receive the object.
        client = await Client.new_established()
        await client.write(b'{"type":"object","object":{"type":"block","txids":['
                           b'"740bcfb434c89abe57bb2bc80290cd5495e87ebf8cd0dadb076bc50453590104"],'
                           b'"nonce":"a26d92800cf58e88a5ecf37156c031a4147c2128beeaf1cca2785c93242a4c8b",'
                           b'"previd":"0024839ec9632d382486ba7aac7e0bda3b4bda1d4bd79be9ae78e7e1e813ddd8",'
                           b'"created":"1622825642",'
                           b'"T":"003a000000000000000000000000000000000000000000000000000000000000"}}\n')

        client2 = await Client.new_established()
        await client2.write(
            b'{"type":"getobject","objectid":"4e8174073cb429906c1a04d739b309f435d9333eed3f2904aa4d6ff10d01277b"}\n')
        response = await client2.readline()
        self.assertIn(b'"740bcfb434c89abe57bb2bc80290cd5495e87ebf8cd0dadb076bc50453590104"', response)
        self.assertIn(b'"type":"object"', response)
        await client.close()
        await client2.close()

    async def test_getIHaveObjMessage(self):
        # If Grader 1 sends a new valid transaction object, Grader 2 must receive an ihaveobject message with the
        # object id.
        client = await Client.new_established()
        client2 = await Client.new_established()

        await client.write(b'{"type":"object","object":{"type":"block","txids":['
                           b'"740bcfb434c89abe57bb2bc80290cd5495e87ebf8cd0dadb076bc50453590104"],'
                           b'"nonce":"a26d92800cf58e88a5ecf37156c031a4147c2128beeaf1cca2785c93242a4c8b",'
                           b'"previd":"0024839ec9632d382486ba7aac7e0bda3b4bda1d4bd79be9ae78e7e1e813ddd8",'
                           b'"created":"1622825642",'
                           b'"T":"003a000000000000000000000000000000000000000000000000000000000000"}}\n')

        response = await client2.readline()
        self.assertIn(b'"objectid":"4e8174073cb429906c1a04d739b309f435d9333eed3f2904aa4d6ff10d01277b"', response)
        self.assertIn(b'"type":"ihaveobject"', response)
        await client.close()
        await client2.close()

    async def test_getGetObjMessage(self):
        # If Grader 1 sends an ihaveobject message with the id of a new object, Grader 1 must receive a getobject
        # message with the same object id.
        client = await Client.new_established()
        await client.write(
            b'{"type":"ihaveobject","objectid":"3e8174073cb429906c1a04d739b309f435d9333eed3f2904aa4d6ff10d01277b"}\n')
        response = await client.readline()
        self.assertIn(b'"objectid":"3e8174073cb429906c1a04d739b309f435d9333eed3f2904aa4d6ff10d01277b"', response)
        self.assertIn(b'"type":"getobject"', response)
        await client.close()

    async def test_objectSentAndHandshakeNotCompleted_shouldNotReceiveIHaveObject(self):
        client = await Client.new_established()
        client2 = await Client.new()
        await client2.readline()
        await client2.readline()

        await client.write(b'{"type":"object","object":{"type":"block","txids":['
                           b'"740bcfb434c89abe57bb2bc80290cd5495e87ebf8cd0dadb076bc50453590104"],'
                           b'"nonce":"a26d92800cf58e88a5ecf37156c031a4147c2128beeaf1cca2785c93242a4c8b",'
                           b'"previd":"0024839ec9632d382486ba7aac7e0bda3b4bda1d4bd79be9ae78e7e1e813ddd8",'
                           b'"created":"1622825642",'
                           b'"T":"003a000000000000000000000000000000000000000000000000000000000000"}}\n')

        with self.assertRaises(asyncio.TimeoutError):
            await asyncio.wait_for(client2.readline(), 0.5)
        await client.close()
        await client2.close()


if __name__ == "__main__":
    unittest.main()
