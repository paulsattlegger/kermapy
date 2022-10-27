import asyncio
import os
import sys
import tempfile
import unittest
from unittest import IsolatedAsyncioTestCase

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src/kermapy')))  # noqa

from src.kermapy.kermapy import Node


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


class Task1TestCase(IsolatedAsyncioTestCase):

    def setUp(self):
        pass

    async def asyncSetUp(self):
        self._tmp_file_path = os.path.join(tempfile.mkdtemp(), "peers.json")
        node = Node("127.0.0.1:19000", self._tmp_file_path, False)
        self._serve_task = asyncio.ensure_future(node.serve())

        self._client = Client(*await asyncio.open_connection('127.0.0.1', 19000))

    async def test_hello(self):
        response = await self._client.readline()
        self.assertIn(b'"type":"hello"', response)

    async def test_getpeers(self):
        await self._client.readline()
        response = await self._client.readline()
        self.assertIn(b'"type":"getpeers"', response)

    def tearDown(self):
        pass

    async def asyncTearDown(self):
        await self._client.close()

        self._serve_task.cancel()

        if os.path.exists(self._tmp_file_path):
            os.remove(self._tmp_file_path)

    async def on_cleanup(self):
        pass


if __name__ == "__main__":
    unittest.main()
