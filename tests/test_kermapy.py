import asyncio
import os
import pathlib
import sys
import tempfile
import unittest
from unittest import IsolatedAsyncioTestCase

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src/kermapy')))

from src.kermapy.kermapy import Node  # noqa: E402


class Client:
    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        self._reader = reader
        self._writer = writer

    async def readline(self) -> bytes:
        return await self._reader.readline()

    async def write(self, message: bytes):
        self._writer.write(message)
        await self._writer.drain()

    async def close(self) -> None:
        self._writer.close()
        await self._writer.wait_closed()


background_tasks = set()


class Task1TestCase(IsolatedAsyncioTestCase):

    def setUp(self):
        pass

    async def asyncSetUp(self):
        host, port = "127.0.0.1", 19000
        self._tmp_file_path = pathlib.Path(tempfile.mkdtemp(), "storage.json")
        self._tmp_database_path = pathlib.Path(tempfile.mkdtemp(), "../../data")
        self._node = Node(f"{host}:{port}", str(self._tmp_file_path), str(self._tmp_database_path))
        await self._node.start_server()
        self._client = Client(*await asyncio.open_connection(host, port))
        task = asyncio.create_task(self._node.serve())
        background_tasks.add(task)
        task.add_done_callback(background_tasks.discard)

    async def test_getHello(self):
        # The grader node “Grader” should be able to connect to your node
        # Grader should receive a valid hello message on connecting
        response = await self._client.readline()
        self.assertIn(b'"type":"hello"', response)

    async def test_getPeers(self):
        # The hello message should be followed by a getpeers message.
        await self._client.readline()
        response = await self._client.readline()
        self.assertIn(b'"type":"getpeers"', response)

    async def test_getReconnectHello(self):
        # Grader should be able to disconnect, then connect to your node again.
        response1 = await self._client.readline()
        await self._client.readline()
        await self._client.close()
        self._client = Client(*await asyncio.open_connection("127.0.0.1", 19000))
        response2 = await self._client.readline()
        self.assertIn(b'"type":"hello"', response1)
        self.assertIn(b'"type":"hello"', response2)

    async def test_getValidPeers(self):
        # If Grader sends a getpeers message, it must receive a valid peers message.
        await self._client.readline()
        await self._client.readline()
        await self._client.write(b'{"type": "hello", "version": "0.8.0", "agent": "Kermapy 0.0.1"}\n')
        await self._client.write(b'{"type":"getpeers"}\n')
        response = await self._client.readline()
        self.assertIn(b'"type":"peers"', response)

    async def test_getValidPeersDelayed(self):
        # If Grader sends {"type":ge, waits for 0.1 second, then sends tpeers"}, your node should reply with a valid
        # peers message.
        await self._client.readline()
        await self._client.readline()
        await self._client.write(b'{"type": "hello", "version": "0.8.0", "agent": "Kermapy 0.0.1"}\n')
        await self._client.write(b'{"type":"ge')
        await asyncio.sleep(0.1)
        await self._client.write(b'tpeers"}\n')
        response = await self._client.readline()
        self.assertIn(b'"type":"peers"', response)

    async def test_getErrorNoHelloMsg(self):
        # If Grader sends any message before sending hello, your node should send an error message and then disconnect.
        await self._client.readline()
        await self._client.readline()
        await self._client.write(b'{"type":"getpeers"}\n')
        response = await self._client.readline()
        self.assertIn(b'"type":"error"', response)

    async def test_getErrorWrongPattern1(self):
        # If Grader sends an invalid message, your node should send an error message.
        await self._client.readline()
        await self._client.readline()
        await self._client.write(b'Wbgygvf7rgtyv7tfbgy{{{\n')
        response = await self._client.readline()
        self.assertIn(b'"type":"error"', response)

    async def test_getErrorWrongPattern2(self):
        # If Grader sends an invalid message, your node should send an error message.
        await self._client.readline()
        await self._client.readline()
        await self._client.write(b'"type":"diufygeuybhv"\n')
        response = await self._client.readline()
        self.assertIn(b'"type":"error"', response)

    async def test_getErrorWrongPattern3(self):
        # If Grader sends an invalid message, your node should send an error message.
        await self._client.readline()
        await self._client.readline()
        await self._client.write(b'"type":"hello"\n')
        response = await self._client.readline()
        self.assertIn(b'"type":"error"', response)

    async def test_getErrorWrongPattern4(self):
        # If Grader sends an invalid message, your node should send an error message.
        await self._client.readline()
        await self._client.readline()
        await self._client.write(b'"type":"hello","version":"jd3.x"\n')
        response = await self._client.readline()
        self.assertIn(b'"type":"error"', response)

    async def test_getErrorWrongPattern5(self):
        # If Grader sends an invalid message, your node should send an error message.
        await self._client.readline()
        await self._client.readline()
        await self._client.write(b'"type":"hello","version":"5.8.2"\n')
        response = await self._client.readline()
        self.assertIn(b'"type":"error"', response)

    async def test_getPeersAfterReConnect(self):
        # If grader sends a set of peers in a valid peers message, disconnects, reconnects and sends a getpeers
        # message, it must receive a peers message containing at least the peers sent in the first message.
        await self._client.readline()
        await self._client.readline()
        await self._client.write(b'{"type": "hello", "version": "0.8.0", "agent": "Kermapy 0.0.1"}\n')
        # Every peer is a string in the form of <host>:<port>. The default port is 18018 but other ports are valid.
        await self._client.write(b'{"type":"peers", "peers":["123.123.123.123:40000"]}\n')
        await self._client.close()
        self._client = Client(*await asyncio.open_connection("127.0.0.1", 19000))
        await self._client.readline()
        await self._client.readline()
        await self._client.write(b'{"type": "hello", "version": "0.8.0", "agent": "Kermapy 0.0.1"}\n')
        await self._client.write(b'{"type":"getpeers"}\n')
        response = await self._client.readline()
        self.assertIn(b'"123.123.123.123:40000"', response)

    async def test_getHelloMessageSimultaneously(self):
        # Grader should be able to create two connections to your node simultaneously.
        await self._client.readline()
        await self._client.readline()
        await self._client.write(b'{"type": "hello", "version": "0.8.0", "agent": "Kermapy 0.0.1"}\n')
        client2 = Client(*await asyncio.open_connection("127.0.0.1", 19000))
        await client2.readline()
        await client2.readline()
        await client2.write(b'{"type": "hello", "version": "0.8.0", "agent": "Kermapy 0.0.1"}\n')

        await self._client.write(b'{"type":"getpeers"}\n')
        await client2.write(b'{"type":"getpeers"}\n')
        response1 = await self._client.readline()
        response2 = await client2.readline()
        self.assertIn(b'"type":"peers"', response1)
        self.assertIn(b'"type":"peers"', response2)
        await client2.close()

    async def test_server_shouldAcceptArbitraryOrderInHelloMessage(self):
        # Arrange
        await self._client.readline()
        await self._client.readline()
    
        # Act
        await self._client.write(b'{"agent":"Kermapy 1.0.2","version":"0.8.0","type":"hello"}\n')
        await self._client.write(b'{"type":"getpeers"}\n')
        
        # Assert
        response = await self._client.readline()
        self.assertIn(b'"type":"peers"', response)

    async def test_getErrorNonUnicode(self):
        await self._client.readline()
        await self._client.readline()
        await self._client.write(b'\xFF\n')
        response = await self._client.readline()
        self.assertIn(b'"type":"error"', response)

    def tearDown(self):
        if self._tmp_file_path.exists():
            self._tmp_file_path.unlink()

    async def asyncTearDown(self):
        await self._node.shutdown()
        await asyncio.gather(*background_tasks, return_exceptions=True)
        await self._client.close()

    async def on_cleanup(self):
        pass


if __name__ == "__main__":
    unittest.main()
