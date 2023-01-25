import asyncio
import json
import shutil
import tempfile
from unittest import IsolatedAsyncioTestCase

from src.kermapy.kermapy import Node
from src.kermapy.org.webpki.json.Canonicalize import canonicalize

HOST = "127.0.0.1"
PORT = 19000

HELLO = b'{"type":"hello","version":"0.8.0","agent":"Kermapy 0.0.x"}\n'


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
        await client.readline()
        await client.readline()
        return client

    async def readline(self) -> bytes:
        return await self._reader.readline()

    async def read_with_timeout(self, timeout: int) -> bytes | None:
        try:
            return await asyncio.wait_for(self._reader.readline(), timeout)
        except asyncio.TimeoutError:
            return None

    async def read_dict(self) -> dict:
        return json.loads(await self._reader.readline())

    async def write(self, message: bytes) -> None:
        self._writer.write(message)
        await self._writer.drain()

    async def write_dict(self, message: dict) -> None:
        await self.write(canonicalize(message) + b"\n")

    async def write_tx(self, tx: dict) -> dict:
        await self.write_dict({
            "object": tx,
            "type": "object"
        })
        return await self.read_dict()

    async def close(self) -> None:
        self._writer.close()
        await self._writer.wait_closed()


background_tasks = set()


class KermaTestCase(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self._tmp_directory = tempfile.mkdtemp()
        self._node = Node(f"{HOST}:{PORT}", self._tmp_directory, 0.5)
        await self._node.start_server()
        task = asyncio.create_task(self._node.serve())
        background_tasks.add(task)
        task.add_done_callback(background_tasks.discard)

    def tearDown(self):
        shutil.rmtree(self._tmp_directory)

    async def asyncTearDown(self):
        await self._node.shutdown()
        await asyncio.gather(*background_tasks, return_exceptions=True)
