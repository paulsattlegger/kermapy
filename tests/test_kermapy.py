import asyncio
import os
import pathlib
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
        host, port = "127.0.0.1", 19000
        self._tmp_file_path = pathlib.Path(tempfile.mkdtemp(), "storage.json")
        node = Node(f"{host}:{port}", str(self._tmp_file_path))
        self._server = asyncio.create_task(node.serve())
        self._client = Client(*await asyncio.open_connection(host, port))

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
        self._server.cancel()

        if self._tmp_file_path.exists():
            self._tmp_file_path.unlink()

    async def on_cleanup(self):
        pass


if __name__ == "__main__":
    unittest.main()
