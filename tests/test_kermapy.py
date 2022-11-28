import asyncio
import json
import os
import shutil
import sys
import tempfile
import time
import unittest
from unittest import IsolatedAsyncioTestCase

sys.path.insert(0, os.path.abspath(os.path.join(
    os.path.dirname(__file__), '../src/kermapy')))

from kermapy import Node, ProtocolError  # noqa
from org.webpki.json.Canonicalize import canonicalize  # noqa

HOST = "127.0.0.1"
PORT = 19000
HELLO = b'{"type":"hello","version":"0.8.0","agent":"Kermapy 0.0.x"}\n'
GET_PEERS = b'{"type":"getpeers"}\n'
ERROR_PARSE_JSON = b'{"error":"Failed to parse incoming message as JSON","type":"error"}\n'



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
        await client.write(GET_PEERS)
        response = await client.readline()
        self.assertIn(b'{"error":"Failed to validate incoming message: \'version\' is a required property","type":"error"}\n', response)
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


class Task2TestCase(KermaTestCase):

    async def test_getSameObject(self):
        # If Grader 1 sends a new valid transaction object and then requests the same object, Grader 1 should receive
        # the object.
        client = await Client.new_established()
        await client.write(b'{"type":"object","object":{"height":1,"outputs":['
                           b'{"pubkey":"62b7c521cd9211579cf70fd4099315643767b96711febaa5c76dc3daf27c281c",'
                           b'"value":50000000000000}],"type":"transaction"}}\n')
        await client.write(
            b'{"type":"getobject","objectid":"48c2ae2fbb4dead4bcc5801f6eaa9a350123a43750d22d05c53802b69c7cd9fb"}\n')
        response = await client.readline()
        self.assertIn(
            b'"62b7c521cd9211579cf70fd4099315643767b96711febaa5c76dc3daf27c281c"', response)
        self.assertIn(b'"type":"object"', response)
        await client.close()

    async def test_getSameObject_2(self):
        # If Grader 1 sends a new valid transaction object and then requests the same object, Grader 1 should receive
        # the object.
        client = await Client.new_established()
        await client.write(b'{"type":"object","object":{"height":1,"outputs":['
                           b'{"pubkey":"62b7c521cd9211579cf70fd4099315643767b96711febaa5c76dc3daf27c281c",'
                           b'"value":50000000000000}],"type":"transaction"}}\n')

        await client.write(b'{"type":"object","object":{"inputs":['
                           b'{"outpoint":{"index":0,"txid":"48c2ae2fbb4dead4bcc5801f6eaa9a350123a43750d22d0'
                           b'5c53802b69c7cd9fb"},"sig":"d51e82d5c121c5db21c83404aaa3f591f2099bccf731208c4b0b'
                           b'676308be1f994882f9d991c0ebfd8fdecc90a4aec6165fc3440ade9c83b043cba95b2bba1d0a"}],'
                           b'"outputs":[{"pubkey":"228ee807767047682e9a556ad1ed78dff8d7edf4bc2a5f4fa02e4634cfcad7e0",'
                           b'"value":49000000000000}],"type":"transaction"}}\n')

        await client.write(
            b'{"type":"getobject","objectid":"d33ac384ea704025a6cac53f669c8e924eff7205b0cd0d6a231f0881b6265a8e  "}\n')
        response = await client.readline()
        self.assertIn(
            b'"48c2ae2fbb4dead4bcc5801f6eaa9a350123a43750d22d05c53802b69c7cd9fb"', response)
        self.assertIn(b'"type":"object"', response)
        await client.close()

    async def test_getSameObjectOtherClient(self):
        # If Grader 1 sends a new valid transaction object and then Grader 2 requests the same object,
        # Grader 2 should receive the object.
        client = await Client.new_established()
        await client.write(b'{"type":"object","object":{"height":1,"outputs":['
                           b'{"pubkey":"62b7c521cd9211579cf70fd4099315643767b96711febaa5c76dc3daf27c281c",'
                           b'"value":50000000000000}],"type":"transaction"}}\n')

        await client.write(b'{"type":"object","object":{"inputs":['
                           b'{"outpoint":{"index":0,"txid":"48c2ae2fbb4dead4bcc5801f6eaa9a350123a43750d22d0'
                           b'5c53802b69c7cd9fb"},"sig":"d51e82d5c121c5db21c83404aaa3f591f2099bccf731208c4b0b'
                           b'676308be1f994882f9d991c0ebfd8fdecc90a4aec6165fc3440ade9c83b043cba95b2bba1d0a"}],'
                           b'"outputs":[{"pubkey":"228ee807767047682e9a556ad1ed78dff8d7edf4bc2a5f4fa02e4634cfcad7e0",'
                           b'"value":49000000000000}],"type":"transaction"}}\n')

        client2 = await Client.new_established()
        await client2.write(
            b'{"type":"getobject","objectid":"d33ac384ea704025a6cac53f669c8e924eff7205b0cd0d6a231f0881b6265a8e"}\n')
        response = await client2.readline()
        self.assertIn(
            b'"48c2ae2fbb4dead4bcc5801f6eaa9a350123a43750d22d05c53802b69c7cd9fb"', response)
        self.assertIn(b'"type":"object"', response)
        await client.close()
        await client2.close()

    async def test_getIHaveObjMessage(self):
        # If Grader 1 sends a new valid transaction object, Grader 2 must receive an ihaveobject message with the
        # object id.
        client = await Client.new_established()
        client2 = await Client.new_established()

        await client.write(b'{"type":"object","object":{"height":1,"outputs":['
                           b'{"pubkey":"62b7c521cd9211579cf70fd4099315643767b96711febaa5c76dc3daf27c281c",'
                           b'"value":50000000000000}],"type":"transaction"}}\n')

        response = await client2.readline()
        self.assertIn(
            b'"objectid":"48c2ae2fbb4dead4bcc5801f6eaa9a350123a43750d22d05c53802b69c7cd9fb"', response)
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
        self.assertIn(
            b'"objectid":"3e8174073cb429906c1a04d739b309f435d9333eed3f2904aa4d6ff10d01277b"', response)
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
                           b'"created":1624219079,'
                           b'"T":"003a000000000000000000000000000000000000000000000000000000000000"}}\n')

        with self.assertRaises(asyncio.TimeoutError):
            await asyncio.wait_for(client2.readline(), 0.5)
        await client.close()
        await client2.close()


class Task3TestCase(KermaTestCase):
    # 1. On receiving an object message from Grader 1 containing any invalid block, Grader 1 must receive an error
    #    message and the transaction must not be gossiped to Grader 2.
    async def test_validate_block_incorrectTarget_shouldRaiseProtocolError(self):
        # a. The block has an incorrect target.
        block = {
            "T": "0000000000000000000000000000000000000000000000000000000000000000", "created": 1624229079,
            "miner": "TUWien-Kerma",
            "nonce": "0000000000000000000000000000000000000000000000000000000000000000",
            "note": "First block. Yayy, I have 50 ker now!!",
            "previd": "00000000a420b7cefa2b7730243316921ed59ffe836e111ca3801f82a4f5360e",
            "txids": ["1bb37b637d07100cd26fc063dfd4c39a7931cc88dae3417871219715a5e374af"], "type": "block"
        }
        with self.assertRaises(ProtocolError) as cm:
            await self._node.validate_block(block)

        the_exception = cm.exception
        self.assertIn("invalid target", str(the_exception))

    async def test_validate_block_proofOfWorkInvalid_shouldRaiseProtocolError(self):
        # b. The block has an invalid proof-of-work.
        block = {
            "T": "00000002af000000000000000000000000000000000000000000000000000000", "created": 1624229079,
            "miner": "TUWien-Kerma",
            "nonce": "0000000000000000000000000000000000000000000000000000000000000000",
            "note": "First block. Yayy, I have 50 ker now!!",
            "previd": "00000000a420b7cefa2b7730243316921ed59ffe836e111ca3801f82a4f5360e",
            "txids": ["1bb37b637d07100cd26fc063dfd4c39a7931cc88dae3417871219715a5e374af"], "type": "block"
        }
        with self.assertRaises(ProtocolError) as cm:
            await self._node.validate_block(block)

        the_exception = cm.exception
        self.assertIn("proof-of-work", str(the_exception))

    async def test_validate_block_timestampFuture_shouldRaiseProtocolError(self):
        block = {
            "T": "00000002af000000000000000000000000000000000000000000000000000000", "created": int(time.time() + 3600),
            "miner": "TUWien-Kerma",
            "nonce": "0000000000000000000000000000000000000000000000000000000000000000",
            "note": "First block. Yayy, I have 50 ker now!!",
            "previd": "00000000a420b7cefa2b7730243316921ed59ffe836e111ca3801f82a4f5360e",
            "txids": ["1bb37b637d07100cd26fc063dfd4c39a7931cc88dae3417871219715a5e374af"], "type": "block"
        }
        with self.assertRaises(ProtocolError) as cm:
            await self._node.validate_block(block)

        the_exception = cm.exception
        self.assertIn("future", str(the_exception))

    async def test_sendBlockInvalidTransaction_shouldReceiveErrorMessage(self):
        # c. There is an invalid transaction in the block.
        client = await Client.new_established()

        block_message = {
            "object":
                {
                    "T": "00000002af000000000000000000000000000000000000000000000000000000",
                    "created": 1669626529,
                    "miner": "Kermars",
                    "nonce": "000000000000000000000000000000000000000000000000800000000fca06a3",
                    "note": "Invalid_TX_no_outputs",
                    "previd": "00000000a420b7cefa2b7730243316921ed59ffe836e111ca3801f82a4f5360e",
                    "txids": [
                        "2374cb9b22bb0b1d865397e4ee88de4532e8fbf5232a32f956298d703ea8f913"
                    ],
                    "type": "block"
                },
            "type": "object"
        }

        await client.write_dict(block_message)

        getobject_message = {
            "type": "getobject",
            "objectid": "2374cb9b22bb0b1d865397e4ee88de4532e8fbf5232a32f956298d703ea8f913"
        }

        self.assertDictEqual(getobject_message, await client.read_dict())

        tx_message = {
            "object": {
                "inputs": [{
                    "outpoint": {
                        "index": 0, "txid": "29e793963f3933af943d20cb3b8da893488c2e4fd169d88fd47c8081a368794c"
                    },
                    "sig": "648d0db001fe44edda0493b9635a9747b5f1b7e4b90032c17a3abc2aa874f4e2a0090ad7f43d1ce22614a52f6a13797dc2908e602a1c46c8cf32ec2ad910600b"
                }],
                "outputs": [
                    {"pubkey": "8bd22d5b544887762cd6104b433d93e1f9a5f451fe47d641733e517d9551ab05", "value": 51}],
                "type": "transaction"
            }, "type": "object"
        }

        await client.write_dict(tx_message)

        response = await client.read_dict();
        self.assertIn("error", response['type'])
        self.assertIn('Received block contains transactions that could not be received', response['error'])

    async def append_block0(self, client):
        block_message = {
            "object":
                {
                    "T": "00000002af000000000000000000000000000000000000000000000000000000", "created": 1624219079,
                    "miner": "dionyziz", "nonce": "0000000000000000000000000000000000000000000000000000002634878840",
                    "note": "The Economist 2021-06-20: Crypto-miners are probably to blame for the graphics-chip shortage",
                    "previd": None, "txids": [], "type": "block"
                },
            "type": "object"
        }

        await client.write_dict(block_message)
        ihaveobject_message = {
            "type": "ihaveobject",
            "objectid": "00000000a420b7cefa2b7730243316921ed59ffe836e111ca3801f82a4f5360e"
        }
        self.assertDictEqual(ihaveobject_message, await client.read_dict())

    async def append_block1(self, client):
        cb_block1_after_genesis = {
            "height": 1, "outputs": [
                {
                    "pubkey": "f66c7d51551d344b74e071d3b988d2bc09c3ffa82857302620d14f2469cfbf60",
                    "value": 50000000000000
                }],
            "type": "transaction"
        }
        ihaveobject_message = {
            "type": "ihaveobject",
            "objectid": "2a9458a2e75ed8bd0341b3cb2ab21015bbc13f21ea06229340a7b2b75720c4df"
        }
        self.assertDictEqual(ihaveobject_message, await client.write_tx(cb_block1_after_genesis))

        block_message = {
            "object": {
                "T": "00000002af000000000000000000000000000000000000000000000000000000", "created": 1624220079,
                "miner": "Snekel testminer",
                "nonce": "000000000000000000000000000000000000000000000000000000009d8b60ea",
                "note": "First block after genesis with CBTX",
                "previd": "00000000a420b7cefa2b7730243316921ed59ffe836e111ca3801f82a4f5360e",
                "txids": ["2a9458a2e75ed8bd0341b3cb2ab21015bbc13f21ea06229340a7b2b75720c4df"], "type": "block"
            }, "type": "object"
        }
        ihaveobject_message = {
            "type": "ihaveobject",
            "objectid": "0000000108bdb42de5993bcf5f7d92557585dd6abfe9fb68e796518fe7f2ed2e"
        }
        await client.write_dict(block_message)
        self.assertDictEqual(ihaveobject_message, await client.read_dict())

    async def append_block2_cb(self, client):
        tx_block2_after_genesis = {
            "height": 2, "outputs": [
                {
                    "pubkey": "c7c2c13afd02be7986dee0f4630df01abdbc950ea379055f1a423a6090f1b2b3",
                    "value": 50000000000000
                }],
            "type": "transaction"
        }
        ihaveobject_message = {
            "type": "ihaveobject",
            "objectid": "73231cc901774ddb4196ee7e9e6b857b208eea04aee26ced038ac465e1e706d2"
        }
        self.assertDictEqual(ihaveobject_message, await client.write_tx(tx_block2_after_genesis))

        block_message = {
            "object": {
                "T": "00000002af000000000000000000000000000000000000000000000000000000", "created": 1624221079,
                "miner": "Snekel testminer",
                "nonce": "000000000000000000000000000000000000000000000000000000004d82fc68",
                "note": "Second block after genesis with CBTX",
                "previd": "0000000108bdb42de5993bcf5f7d92557585dd6abfe9fb68e796518fe7f2ed2e",
                "txids": ["73231cc901774ddb4196ee7e9e6b857b208eea04aee26ced038ac465e1e706d2"], "type": "block"
            }, "type": "object"
        }
        ihaveobject_message = {
            "type": "ihaveobject",
            "objectid": "00000002a8986627f379547ed1ec990841e1f1c6ba616a56bfcd4b410280dc6d"
        }
        await client.write_dict(block_message)
        self.assertDictEqual(ihaveobject_message, await client.read_dict())

    async def append_block2_cb_tx(self, client):
        cb_block2_after_genesis = {
            "height": 2, "outputs": [
                {
                    "pubkey": "c7c2c13afd02be7986dee0f4630df01abdbc950ea379055f1a423a6090f1b2b3",
                    "value": 50000000000000
                }],
            "type": "transaction"
        }
        ihaveobject_message = {
            "type": "ihaveobject",
            "objectid": "73231cc901774ddb4196ee7e9e6b857b208eea04aee26ced038ac465e1e706d2"
        }
        self.assertDictEqual(ihaveobject_message, await client.write_tx(cb_block2_after_genesis))

        tx_block2_after_genesis = {
            "inputs": [
                {
                    "outpoint": {
                        "index": 0,
                        "txid": "2a9458a2e75ed8bd0341b3cb2ab21015bbc13f21ea06229340a7b2b75720c4df"
                    },
                    "sig": "49cc4f9a1fb9d600a7debc99150e7909274c8c74edd7ca183626dfe49eb4aa21c6ff0e4c5f0dc2a328ad6b8ba10bf7169d5f42993a94bf67e13afa943b749c0b"
                }
            ],
            "outputs": [
                {
                    "pubkey": "c7c2c13afd02be7986dee0f4630df01abdbc950ea379055f1a423a6090f1b2b3",
                    "value": 50
                }
            ],
            "type": "transaction"
        }
        ihaveobject_message = {
            "type": "ihaveobject",
            "objectid": "7ef80f2da40b3f681a5aeb7962731beddccea25fa51e6e7ae6fbce8a58dbe799"
        }
        self.assertDictEqual(ihaveobject_message, await client.write_tx(tx_block2_after_genesis))

        block_message = {
            "object": {
                "T": "00000002af000000000000000000000000000000000000000000000000000000",
                "created": 1624221079,
                "miner": "Snekel testminer",
                "nonce": "00000000000000000000000000000000000000000000000000000000182b95ea",
                "note": "Second block after genesis with CBTX and TX",
                "previd": "0000000108bdb42de5993bcf5f7d92557585dd6abfe9fb68e796518fe7f2ed2e",
                "txids": [
                    "73231cc901774ddb4196ee7e9e6b857b208eea04aee26ced038ac465e1e706d2",
                    "7ef80f2da40b3f681a5aeb7962731beddccea25fa51e6e7ae6fbce8a58dbe799"
                ],
                "type": "block"
            },
            "type": "object"
        }
        ihaveobject_message = {
            "type": "ihaveobject",
            "objectid": "000000021dc4cfdcd0970084949f94da17f97504e1cc3e354851bb4768842b57"
        }
        await client.write_dict(block_message)
        self.assertDictEqual(ihaveobject_message, await client.read_dict())

    async def test_sendBlockTwoTransactionSpendTheSameOutput_shouldReceiveErrorMessage(self):
        # d. There are two transactions in the block that spend the same output.
        client1 = await Client.new_established()

        await self.append_block0(client1)
        await self.append_block1(client1)
        await self.append_block2_cb(client1)

        tx_1 = {
            "inputs": [{
                "outpoint": {
                    "index": 0, "txid": "2a9458a2e75ed8bd0341b3cb2ab21015bbc13f21ea06229340a7b2b75720c4df"
                },
                "sig": "334939cac007a71e72484ffa5f34fabe3e3aff31297003a7d3d24795ed33d04a72f8b14316bce3e6467b2f6e66d481f8142ccd9933279fdcb3aef7ace145f10b"
            }, {
                "outpoint": {
                    "index": 0, "txid": "73231cc901774ddb4196ee7e9e6b857b208eea04aee26ced038ac465e1e706d2"
                },
                "sig": "032c6c0a1074b7a965e58fa5071aa9e518bf5c4db9e2880ca5bb5c55dcea47cfd6e0a9859526a16d2bb0b46da0ca4c6f90be8ddf16b149be66016d7f272e6708"
            }],
            "outputs": [
                {"pubkey": "f66c7d51551d344b74e071d3b988d2bc09c3ffa82857302620d14f2469cfbf60", "value": 20}],
            "type": "transaction"
        }
        ihaveobject_message = {
            "objectid": "fbb455506e5a7ce628fed88c8429e43810d3e306c4ff0c5a8313a1aeed6da88d",
            "type": "ihaveobject"
        }
        self.assertDictEqual(ihaveobject_message, await client1.write_tx(tx_1))

        tx_2 = {
            "inputs": [{
                "outpoint": {
                    "index": 0,
                    "txid": "2a9458a2e75ed8bd0341b3cb2ab21015bbc13f21ea06229340a7b2b75720c4df"
                },
                "sig": "49cc4f9a1fb9d600a7debc99150e7909274c8c74edd7ca183626dfe49eb4aa21c6ff0e4c5f0dc2a328ad6b8ba10bf7169d5f42993a94bf67e13afa943b749c0b"
            }], "outputs": [
                {"pubkey": "c7c2c13afd02be7986dee0f4630df01abdbc950ea379055f1a423a6090f1b2b3", "value": 50}],
            "type": "transaction"
        }
        ihaveobject_message = {
            "objectid": "7ef80f2da40b3f681a5aeb7962731beddccea25fa51e6e7ae6fbce8a58dbe799",
            "type": "ihaveobject"
        }
        self.assertDictEqual(ihaveobject_message, await client1.write_tx(tx_2))

        double_spend_2_block = {
            "object": {
                "T": "00000002af000000000000000000000000000000000000000000000000000000", "created": 1624222079,
                "miner": "Snekel testminer",
                "nonce": "00000000000000000000000000000000000000000000000000000000062d431b",
                "note": "Third block after genesis with double-spending TX",
                "previd": "00000002a8986627f379547ed1ec990841e1f1c6ba616a56bfcd4b410280dc6d",
                "txids": ["fbb455506e5a7ce628fed88c8429e43810d3e306c4ff0c5a8313a1aeed6da88d",
                          "7ef80f2da40b3f681a5aeb7962731beddccea25fa51e6e7ae6fbce8a58dbe799"], "type": "block"
            }, "type": "object"
        }

        await client1.write_dict(double_spend_2_block)

        response = await client1.read_dict();
        self.assertIn("error", response['type'])
        self.assertIn("Could not find UTXO entry for key '2a9458a2e75ed8bd0341b3cb2ab21015bbc13f21ea06229340a7b2b75720c4df_f66c7d51551d344b74e071d3b988d2bc09c3ffa82857302620d14f2469cfbf60_0'", response['error'])

        client1.close()    

    async def test_sendBlockTransactionAttemptsToSpendAnOutput_shouldReceiveErrorMessage(self):
        # e. A transaction attempts to spend an output
        client1 = await Client.new_established()

        await self.append_block0(client1)
        await self.append_block1(client1)
        await self.append_block2_cb_tx(client1)

        tx = {
            "inputs": [{
                "outpoint": {
                    "index": 0, "txid": "2a9458a2e75ed8bd0341b3cb2ab21015bbc13f21ea06229340a7b2b75720c4df"
                },
                "sig": "334939cac007a71e72484ffa5f34fabe3e3aff31297003a7d3d24795ed33d04a72f8b14316bce3e6467b2f6e66d481f8142ccd9933279fdcb3aef7ace145f10b"
            }, {
                "outpoint": {
                    "index": 0, "txid": "73231cc901774ddb4196ee7e9e6b857b208eea04aee26ced038ac465e1e706d2"
                },
                "sig": "032c6c0a1074b7a965e58fa5071aa9e518bf5c4db9e2880ca5bb5c55dcea47cfd6e0a9859526a16d2bb0b46da0ca4c6f90be8ddf16b149be66016d7f272e6708"
            }],
            "outputs": [{"pubkey": "f66c7d51551d344b74e071d3b988d2bc09c3ffa82857302620d14f2469cfbf60", "value": 20}],
            "type": "transaction"
        }
        ihaveobject_message = {
            "type": "ihaveobject",
            "objectid": "fbb455506e5a7ce628fed88c8429e43810d3e306c4ff0c5a8313a1aeed6da88d"
        }
        self.assertDictEqual(ihaveobject_message, await client1.write_tx(tx))

        double_spend_1_block = {
            "object": {
                "T": "00000002af000000000000000000000000000000000000000000000000000000", "created": 1624222079,
                "miner": "Snekel testminer",
                "nonce": "0000000000000000000000000000000000000000000000000000000010fea5cc",
                "note": "Third block after genesis with double-spending TX",
                "previd": "000000021dc4cfdcd0970084949f94da17f97504e1cc3e354851bb4768842b57",
                "txids": ["fbb455506e5a7ce628fed88c8429e43810d3e306c4ff0c5a8313a1aeed6da88d"], "type": "block"
            }, "type": "object"
        }

        await client1.write_dict(double_spend_1_block)

        response = await client1.read_dict();
        self.assertIn("error", response['type'])
        self.assertIn("Could not find UTXO entry for key '2a9458a2e75ed8bd0341b3cb2ab21015bbc13f21ea06229340a7b2b75720c4df_f66c7d51551d344b74e071d3b988d2bc09c3ffa82857302620d14f2469cfbf60_0'", response['error'])

        client1.close()

    async def test_sendBlockCoinbaseTransactionExceedsBlockRewards_shouldReceiveErrorMessage(self):
        # f. The coinbase transaction has an output that exceeds the block rewards and the fees.
        client1 = await Client.new_established()

        await self.append_block0(client1)

        tx_block1_after_genesis = {
            "height": 1, "outputs": [
                {
                    "pubkey": "f66c7d51551d344b74e071d3b988d2bc09c3ffa82857302620d14f2469cfbf60",
                    "value": 50000000000001
                }],
            "type": "transaction"
        }
        ihaveobject_message = {
            "type": "ihaveobject",
            "objectid": "19d554113147de6ea9d8211dc0ccb3211c63de9904a3c10f80c017694130896c"
        }
        self.assertDictEqual(ihaveobject_message, await client1.write_tx(tx_block1_after_genesis))

        block_message = {
            "object": {
                "T": "00000002af000000000000000000000000000000000000000000000000000000",
                "created": 1669629178,
                "miner": "Kermars",
                "nonce": "000000000000000000000000000000000000000000000000a000000000e298ca",
                "note": "First block after genesis with CBTX exceeding block rewards",
                "previd": "00000000a420b7cefa2b7730243316921ed59ffe836e111ca3801f82a4f5360e",
                "txids": [
                    "19d554113147de6ea9d8211dc0ccb3211c63de9904a3c10f80c017694130896c"
                ],
                "type": "block"
            }, "type": "object"
        }

        await client1.write_dict(block_message)

        response = await client1.read_dict()
        self.assertIn("error", response['type'])
        self.assertIn('Received block with coinbase transaction that exceed block rewards and the fees', response['error'])

        client1.close()

    async def test_sendBlockCoinbaseTransactionNotExceedsBlockRewardsAndFees_shouldReceiveIHaveObjectMessage(self):
        # f. The coinbase transaction has an output that exceeds the block rewards and the fees.
        client1 = await Client.new_established()

        await self.append_block0(client1)
        await self.append_block1(client1)

        cb_block2_after_genesis = {
            "height": 2, "outputs": [
                {
                    "pubkey": "c7c2c13afd02be7986dee0f4630df01abdbc950ea379055f1a423a6090f1b2b3",
                    "value": 99999999999950
                }],
            "type": "transaction"
        }
        ihaveobject_message = {
            "type": "ihaveobject",
            "objectid": "80f961fd526ac8aa7d5f2dfe51c72235b7643fe58f6f651cb35aaedf1bb3d5db"
        }
        self.assertDictEqual(ihaveobject_message, await client1.write_tx(cb_block2_after_genesis))

        tx_block2_after_genesis = {
            "inputs": [
                {
                    "outpoint": {
                        "index": 0,
                        "txid": "2a9458a2e75ed8bd0341b3cb2ab21015bbc13f21ea06229340a7b2b75720c4df"
                    },
                    "sig": "49cc4f9a1fb9d600a7debc99150e7909274c8c74edd7ca183626dfe49eb4aa21c6ff0e4c5f0dc2a328ad6b8ba10bf7169d5f42993a94bf67e13afa943b749c0b"
                }
            ],
            "outputs": [
                {
                    "pubkey": "c7c2c13afd02be7986dee0f4630df01abdbc950ea379055f1a423a6090f1b2b3",
                    "value": 50
                }
            ],
            "type": "transaction"
        }
        ihaveobject_message = {
            "type": "ihaveobject",
            "objectid": "7ef80f2da40b3f681a5aeb7962731beddccea25fa51e6e7ae6fbce8a58dbe799"
        }
        self.assertDictEqual(ihaveobject_message, await client1.write_tx(tx_block2_after_genesis))

        block_message = {
            "object": {
                "T": "00000002af000000000000000000000000000000000000000000000000000000",
                "created": 1669664108,
                "miner": "Kermars",
                "nonce": "000000000000000000000000000000000000000000000000600000001bd27c57",
                "note": "Second block after genesis with CBTX and TX",
                "previd": "0000000108bdb42de5993bcf5f7d92557585dd6abfe9fb68e796518fe7f2ed2e",
                "txids": [
                    "80f961fd526ac8aa7d5f2dfe51c72235b7643fe58f6f651cb35aaedf1bb3d5db",
                    "7ef80f2da40b3f681a5aeb7962731beddccea25fa51e6e7ae6fbce8a58dbe799"
                ],
                "type": "block"
            },
            "type": "object"
        }
        ihaveobject_message = {
            "type": "ihaveobject",
            "objectid": "000000028a9ddb2bdb02cc6d0c155596ee3cfcf5ff948475dda871dc94755689"
        }
        await client1.write_dict(block_message)
        self.assertDictEqual(ihaveobject_message, await client1.read_dict())

    async def test_sendBlockCoinbaseTransactionExceedsBlockRewardsAndFees_shouldReceiveErrorMessage(self):
        # f. The coinbase transaction has an output that exceeds the block rewards and the fees.
        client1 = await Client.new_established()

        await self.append_block0(client1)
        await self.append_block1(client1)

        cb_block2_after_genesis = {
            "height": 2, "outputs": [
                {
                    "pubkey": "c7c2c13afd02be7986dee0f4630df01abdbc950ea379055f1a423a6090f1b2b3",
                    "value": 99999999999951
                }],
            "type": "transaction"
        }
        ihaveobject_message = {
            "type": "ihaveobject",
            "objectid": "afcdaa10d98d1e03672b4160d329090cfed59baba22e3008f4b5dabf0fcdfbeb"
        }
        self.assertDictEqual(ihaveobject_message, await client1.write_tx(cb_block2_after_genesis))

        tx_block2_after_genesis = {
            "inputs": [
                {
                    "outpoint": {
                        "index": 0,
                        "txid": "2a9458a2e75ed8bd0341b3cb2ab21015bbc13f21ea06229340a7b2b75720c4df"
                    },
                    "sig": "49cc4f9a1fb9d600a7debc99150e7909274c8c74edd7ca183626dfe49eb4aa21c6ff0e4c5f0dc2a328ad6b8ba10bf7169d5f42993a94bf67e13afa943b749c0b"
                }
            ],
            "outputs": [
                {
                    "pubkey": "c7c2c13afd02be7986dee0f4630df01abdbc950ea379055f1a423a6090f1b2b3",
                    "value": 50
                }
            ],
            "type": "transaction"
        }
        ihaveobject_message = {
            "type": "ihaveobject",
            "objectid": "7ef80f2da40b3f681a5aeb7962731beddccea25fa51e6e7ae6fbce8a58dbe799"
        }
        self.assertDictEqual(ihaveobject_message, await client1.write_tx(tx_block2_after_genesis))

        block_message = {
            "object": {
                "T": "00000002af000000000000000000000000000000000000000000000000000000",
                "created": 1669664684,
                "miner": "Kermars",
                "nonce": "000000000000000000000000000000000000000000000000600000000e9aa668",
                "note": "Second block after genesis with CBTX and TX",
                "previd": "0000000108bdb42de5993bcf5f7d92557585dd6abfe9fb68e796518fe7f2ed2e",
                "txids": [
                    "afcdaa10d98d1e03672b4160d329090cfed59baba22e3008f4b5dabf0fcdfbeb",
                    "7ef80f2da40b3f681a5aeb7962731beddccea25fa51e6e7ae6fbce8a58dbe799"
                ],
                "type": "block"
            },
            "type": "object"
        }
        await client1.write_dict(block_message)
        response = await client1.read_dict()
        self.assertIn("error", response['type'])
        self.assertIn('Received block with coinbase transaction that exceed block rewards and the fees', response["error"])

        await client1.close()

    async def test_sendBlockCoinbaseTransactionHeightNotMatchingBlockHeight_shouldReceiveErrorMessage(self):
        client1 = await Client.new_established()

        await self.append_block0(client1)

        tx_cb_message = {
            "height": 2, "outputs": [
                {
                    "pubkey": "c7c2c13afd02be7986dee0f4630df01abdbc950ea379055f1a423a6090f1b2b3",
                    "value": 50000000000000
                }],
            "type": "transaction"
        }
        ihaveobject_message = {
            "type": "ihaveobject",
            "objectid": "73231cc901774ddb4196ee7e9e6b857b208eea04aee26ced038ac465e1e706d2"
        }
        self.assertDictEqual(ihaveobject_message, await client1.write_tx(tx_cb_message))

        block_message = {
            "object":
                {
                    "T": "00000002af000000000000000000000000000000000000000000000000000000",
                    "created": 1669629282,
                    "miner": "Kermars",
                    "nonce": "00000000000000000000000000000000000000000000000060000000006ef53e",
                    "previd": "00000000a420b7cefa2b7730243316921ed59ffe836e111ca3801f82a4f5360e",
                    "txids": [
                        "73231cc901774ddb4196ee7e9e6b857b208eea04aee26ced038ac465e1e706d2"
                    ],
                    "type": "block"
                },
            "type": "object"
        }
        await client1.write_dict(block_message)

        response = await client1.read_dict()
        self.assertIn("error", response['type'])
        self.assertIn('Received block with coinbase transaction height does not match block height', response["error"])
        
        await client1.close()

    async def test_sendBlockCoinbaseTransactionIndex1_shouldReceiveErrorMessage(self):
        client1 = await Client.new_established()

        await self.append_block0(client1)

        tx_cb_message = {
            "object": {
                "height": 1, "outputs": [{
                    "pubkey": "62b7c521cd9211579cf70fd4099315643767b96711febaa5c76dc3daf27c281c",
                    "value": 50000000000000
                }], "type": "transaction"
            }, "type": "object"
        }
        await client1.write_dict(tx_cb_message)

        tx_message = {
            "object": {
                "inputs": [{
                    "outpoint": {
                        "index": 0,
                        "txid": "48c2ae2fbb4dead4bcc5801f6eaa9a350123a43750d22d05c53802b69c7cd9fb"
                    },
                    "sig": "d51e82d5c121c5db21c83404aaa3f591f2099bccf731208c4b0b676308be1f994882f9d991c0ebfd8fdecc90a4aec6165fc3440ade9c83b043cba95b2bba1d0a"
                }], "outputs": [{
                    "pubkey": "228ee807767047682e9a556ad1ed78dff8d7edf4bc2a5f4fa02e4634cfcad7e0",
                    "value": 49000000000000
                }], "type": "transaction"
            }, "type": "object"
        }
        await client1.write_dict(tx_message)

        # skip ihaveobject
        await client1.readline()
        await client1.readline()

        block_message = {
            "object":
                {
                    "T": "00000002af000000000000000000000000000000000000000000000000000000",
                    "created": 1669629465,
                    "miner": "Kermars",
                    "nonce": "000000000000000000000000000000000000000000000000000000000acd429d",
                    "previd": "00000000a420b7cefa2b7730243316921ed59ffe836e111ca3801f82a4f5360e",
                    "txids": [
                        "d33ac384ea704025a6cac53f669c8e924eff7205b0cd0d6a231f0881b6265a8e",
                        "48c2ae2fbb4dead4bcc5801f6eaa9a350123a43750d22d05c53802b69c7cd9fb"
                    ],
                    "type": "block"
                },
            "type": "object"
        }
        await client1.write_dict(block_message)

        response = await client1.read_dict()
        self.assertIn("error", response['type'])
        self.assertIn("Could not find UTXO entry for key '48c2ae2fbb4dead4bcc5801f6eaa9a350123a43750d22d05c53802b69c7cd9fb_62b7c521cd9211579cf70fd4099315643767b96711febaa5c76dc3daf27c281c_0'", response["error"])
        
        await client1.close()

    async def test_sendBlockTwoCoinbaseTransactions_shouldReceiveErrorMessage(self):
        client1 = await Client.new_established()

        await self.append_block0(client1)
        tx_cb_1_message = {
            "object": {
                "height": 1, "outputs": [{
                    "pubkey": "62b7c521cd9211579cf70fd4099315643767b96711febaa5c76dc3daf27c281c",
                    "value": 50000000000000
                }], "type": "transaction"
            }, "type": "object"
        }
        await client1.write_dict(tx_cb_1_message)

        tx_cb_2_message = {
            "object": {
                "height": 0,
                "outputs": [
                    {"pubkey": "57558a6dae91ac3ab8caf3f543eac9c51cba4ac680ba5ba0d81b5575dc06bc46", "value": 50}],
                "type": "transaction"
            }, "type": "object"
        }
        await client1.write_dict(tx_cb_2_message)

        # skip ihaveobject
        await client1.readline()
        await client1.readline()

        block_message = {
            "object":
                {
                    "T": "00000002af000000000000000000000000000000000000000000000000000000", "created": 1624229079,
                    "miner": "Kermapy", "nonce": "0000000000000000000000000000000000000000000000000000000000000000",
                    "previd": "00000000a420b7cefa2b7730243316921ed59ffe836e111ca3801f82a4f5360e",
                    "txids": ["2fb7adb654b373e85c6b5c596cc110dcb6643ee138768f4aa947e9ddb7d91f8d",
                              "48c2ae2fbb4dead4bcc5801f6eaa9a350123a43750d22d05c53802b69c7cd9fb"], "type": "block"
                },
            "type": "object"
        }
        await client1.write_dict(block_message)

        response = await client1.read_dict()
        self.assertIn("error", response['type'])
        self.assertIn('Received block does not satisfy the proof-of-work equation', response["error"])
        
        await client1.close()

    async def test_sendBlockCoinbaseTransactionSpentInAnotherTransactionSameBlock_shouldReceiveErrorMessage(self):
        client1 = await Client.new_established()

        await self.append_block0(client1)

        cbtx_message = {
            "object": {
                "height": 1, "outputs": [
                    {
                        "pubkey": "f66c7d51551d344b74e071d3b988d2bc09c3ffa82857302620d14f2469cfbf60",
                        "value": 50000000000000
                    }],
                "type": "transaction"
            }, "type": "object"
        }
        await client1.write_dict(cbtx_message)
        ihaveobject_message = {
            "type": "ihaveobject",
            "objectid": "2a9458a2e75ed8bd0341b3cb2ab21015bbc13f21ea06229340a7b2b75720c4df"
        }
        self.assertDictEqual(ihaveobject_message, await client1.read_dict())

        tx_message = {
            "object": {
                "inputs": [{
                    "outpoint": {
                        "index": 0,
                        "txid": "2a9458a2e75ed8bd0341b3cb2ab21015bbc13f21ea06229340a7b2b75720c4df"
                    },
                    "sig": "49cc4f9a1fb9d600a7debc99150e7909274c8c74edd7ca183626dfe49eb4aa21c6ff0e4c5f0dc2a328ad6b8ba10bf7169d5f42993a94bf67e13afa943b749c0b"
                }], "outputs": [
                    {"pubkey": "c7c2c13afd02be7986dee0f4630df01abdbc950ea379055f1a423a6090f1b2b3", "value": 50}],
                "type": "transaction"
            }, "type": "object"
        }
        await client1.write_dict(tx_message)
        ihaveobject_message = {
            "type": "ihaveobject",
            "objectid": "7ef80f2da40b3f681a5aeb7962731beddccea25fa51e6e7ae6fbce8a58dbe799"
        }
        self.assertDictEqual(ihaveobject_message, await client1.read_dict())

        cbtx_spend_in_same_block_message = {
            "object":
                {
                    "T": "00000002af000000000000000000000000000000000000000000000000000000", "created": 1624220079,
                    "miner": "Snekel testminer",
                    "nonce": "000000000000000000000000000000000000000000000000000000001beecbf3",
                    "note": "First block after genesis with CBTX and TX spending it",
                    "previd": "00000000a420b7cefa2b7730243316921ed59ffe836e111ca3801f82a4f5360e",
                    "txids": ["2a9458a2e75ed8bd0341b3cb2ab21015bbc13f21ea06229340a7b2b75720c4df",
                              "7ef80f2da40b3f681a5aeb7962731beddccea25fa51e6e7ae6fbce8a58dbe799"], "type": "block"
                }, "type": "object"
        }

        await client1.write_dict(cbtx_spend_in_same_block_message)

        response = await client1.read_dict()
        self.assertIn("error", response['type'])
        self.assertIn('Received block with coinbase transaction spend in another transaction', response["error"])
        
        await client1.close()

    async def test_sendValidBlockGrader1_shouldReceiveIHaveObjectGrader2(self):
        # 2. On receiving an object message from Grader 1 containing a valid block, the block must
        #    be gossiped to Grader 2 by sending an ihaveobject message with the correct blockid.
   
        client1 = await Client.new_established()
        client2 = await Client.new_established()

        block_message = {
            "object":
                {
                    "T": "00000002af000000000000000000000000000000000000000000000000000000", "created": 1624219079,
                    "miner": "dionyziz", "nonce": "0000000000000000000000000000000000000000000000000000002634878840",
                    "note": "The Economist 2021-06-20: Crypto-miners are probably to blame for the graphics-chip shortage",
                    "previd": None, "txids": [], "type": "block"
                },
            "type": "object"
        }

        await client1.write_dict(block_message)

        ihaveobject_message = {
            "type": "ihaveobject",
            "objectid": "00000000a420b7cefa2b7730243316921ed59ffe836e111ca3801f82a4f5360e"
        }

        self.assertDictEqual(ihaveobject_message, await client1.read_dict())
        self.assertDictEqual(ihaveobject_message, await client2.read_dict())

        await client1.close()
        await client2.close()

    async def test_sendValidBlockUnknownTxGrader1_shouldFetchTxFromGrader1AndGrader2(self):
        client1 = await Client.new_established()
        client2 = await Client.new_established()

        block_message = {
            "object":
                {
                    "T": "00000002af000000000000000000000000000000000000000000000000000000", "created": 1624229079,
                    "miner": "TUWien-Kerma",
                    "nonce": "000000000000000000000000af298d050e4395d69670b12b7f4100048da50800",
                    "note": "First block. Yayy, I have 50 ker now!!",
                    "previd": "00000000a420b7cefa2b7730243316921ed59ffe836e111ca3801f82a4f5360e",
                    "txids": ["1bb37b637d07100cd26fc063dfd4c39a7931cc88dae3417871219715a5e374af"], "type": "block"
                },
            "type": "object"
        }

        await client1.write_dict(block_message)

        getobject_message = {
            "type": "getobject",
            "objectid": "1bb37b637d07100cd26fc063dfd4c39a7931cc88dae3417871219715a5e374af"
        }

        self.assertDictEqual(getobject_message, await client1.read_dict())
        self.assertDictEqual(getobject_message, await client2.read_dict())

        await client1.close()
        await client2.close()

    async def test_sendValidBlockUnknownTxGrader1_shouldFailAfter5Sec(self):
        client1 = await Client.new_established()
        client2 = await Client.new_established()

        block_message = {
            "object":
                {
                    "T": "00000002af000000000000000000000000000000000000000000000000000000", "created": 1624229079,
                    "miner": "TUWien-Kerma",
                    "nonce": "000000000000000000000000af298d050e4395d69670b12b7f4100048da50800",
                    "note": "First block. Yayy, I have 50 ker now!!",
                    "previd": "00000000a420b7cefa2b7730243316921ed59ffe836e111ca3801f82a4f5360e",
                    "txids": ["1bb37b637d07100cd26fc063dfd4c39a7931cc88dae3417871219715a5e374af"], "type": "block"
                },
            "type": "object"
        }

        await client1.write_dict(block_message)

        # skip getobject
        await client1.readline()
        await client2.readline()

        response = await client1.read_dict()
        self.assertIn("error", response['type'])
        self.assertIn('Received block contains transactions that could not be received', response["error"])

        await client1.close()
        await client2.close()

    async def test_sendInvalidBlockGrader1_shouldNotReceiveIHaveObjectGrader2(self):
        client1 = await Client.new_established()
        client2 = await Client.new_established()

        block_message = {
            "object": {
                "T": "0000000000000000000000000000000000000000000000000000000000000000", "created": 1624229079,
                "miner": "TUWien-Kerma",
                "nonce": "200000000000000000000000000000000000000000000000000000000e762cb9",
                "note": "First block. Yayy, I have 50 ker now!!",
                "previd": "00000000a420b7cefa2b7730243316921ed59ffe836e111ca3801f82a4f5360e",
                "txids": ["1bb37b637d07100cd26fc063dfd4c39a7931cc88dae3417871219715a5e374af"], "type": "block"
            }, "type": "object"
        }

        await client1.write_dict(block_message)

        with self.assertRaises(asyncio.TimeoutError):
            await asyncio.wait_for(client2.readline(), 0.5)

        await client1.close()
        await client2.close()


if __name__ == "__main__":
    unittest.main()
