import asyncio
import copy
import json
import shutil
import tempfile
import unittest
from unittest import IsolatedAsyncioTestCase

from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives.serialization import PublicFormat, Encoding

from src.kermapy.kermapy import Node, ProtocolError
from src.kermapy.org.webpki.json.Canonicalize import canonicalize

HOST = "127.0.0.1"
PORT = 19000
HELLO = b'{"type":"hello","version":"0.8.0","agent":"Kermapy 0.0.x"}\n'
GET_PEERS = b'{"type":"getpeers"}\n'
ERROR_PARSE_JSON = b'{"error":"Failed to parse incoming message as JSON","type":"error"}\n'
GET_CHAINTIP = b'{"type":"getchaintip"}\n'
GET_MEMPOOL = b'{"type":"getmempool"}\n'


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

        response = await client.read_dict()
        self.assertIn("error", response['type'])
        self.assertIn("not find transaction", response['error'])

        await client.close()

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

        response = await client1.read_dict()
        self.assertIn("error", response['type'])
        self.assertIn(
            "Could not find UTXO entry for key '2a9458a2e75ed8bd0341b3cb2ab21015bbc13f21ea06229340a7b2b75720c4df_f66c7d51551d344b74e071d3b988d2bc09c3ffa82857302620d14f2469cfbf60_0'",
            response['error'])

        await client1.close()

    async def test_sendBlockTransactionAttemptsToSpendAnOutput_shouldReceiveErrorMessage(self):
        # e. A transaction attempts to spend an output
        client1 = await Client.new_established()

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

        response = await client1.read_dict()
        self.assertIn("error", response['type'])
        self.assertIn(
            "Could not find UTXO entry for key '2a9458a2e75ed8bd0341b3cb2ab21015bbc13f21ea06229340a7b2b75720c4df_f66c7d51551d344b74e071d3b988d2bc09c3ffa82857302620d14f2469cfbf60_0'",
            response['error'])

        await client1.close()

    async def test_sendBlockCoinbaseTransactionExceedsBlockRewards_shouldReceiveErrorMessage(self):
        # f. The coinbase transaction has an output that exceeds the block rewards and the fees.
        client1 = await Client.new_established()

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
        self.assertIn('Received block with coinbase transaction that exceed block rewards and the fees',
                      response['error'])

        await client1.close()

    async def test_sendBlockCoinbaseTransactionNotExceedsBlockRewardsAndFees_shouldReceiveIHaveObjectMessage(self):
        # f. The coinbase transaction has an output that exceeds the block rewards and the fees.
        client1 = await Client.new_established()

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
        await client1.close()

    async def test_sendBlockCoinbaseTransactionExceedsBlockRewardsAndFees_shouldReceiveErrorMessage(self):
        # f. The coinbase transaction has an output that exceeds the block rewards and the fees.
        client1 = await Client.new_established()

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
        self.assertIn('Received block with coinbase transaction that exceed block rewards and the fees',
                      response["error"])

        await client1.close()

    async def test_sendBlockCoinbaseTransactionHeightNotMatchingBlockHeight_shouldReceiveErrorMessage(self):
        client1 = await Client.new_established()

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

        await self.append_block1(client1)

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
                "created": 1669675927,
                "miner": "Kermars",
                "nonce": "00000000000000000000000000000000000000000000000040000000003983aa",
                "note": "Second block after genesis with CBTX and TX",
                "previd": "0000000108bdb42de5993bcf5f7d92557585dd6abfe9fb68e796518fe7f2ed2e",
                "txids": [
                    "7ef80f2da40b3f681a5aeb7962731beddccea25fa51e6e7ae6fbce8a58dbe799",
                    "73231cc901774ddb4196ee7e9e6b857b208eea04aee26ced038ac465e1e706d2"
                ],
                "type": "block"
            },
            "type": "object"
        }
        await client1.write_dict(block_message)

        response = await client1.read_dict()
        self.assertIn("error", response['type'])
        self.assertIn("index", response["error"])

        await client1.close()

    async def test_sendBlockTwoCoinbaseTransactions_shouldReceiveErrorMessage(self):
        client1 = await Client.new_established()

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
                    "T": "00000002af000000000000000000000000000000000000000000000000000000",
                    "created": 1669676789,
                    "miner": "Kermars",
                    "nonce": "00000000000000000000000000000000000000000000000080000000087eee3d",
                    "previd": "00000000a420b7cefa2b7730243316921ed59ffe836e111ca3801f82a4f5360e",
                    "txids": [
                        "2fb7adb654b373e85c6b5c596cc110dcb6643ee138768f4aa947e9ddb7d91f8d",
                        "48c2ae2fbb4dead4bcc5801f6eaa9a350123a43750d22d05c53802b69c7cd9fb"
                    ],
                    "type": "block"
                },
            "type": "object"
        }
        await client1.write_dict(block_message)

        response = await client1.read_dict()
        self.assertIn("error", response['type'])
        self.assertIn("more than one coinbase", response["error"])

        await client1.close()

    async def test_sendBlockCoinbaseTransactionSpentInAnotherTransactionSameBlock_shouldReceiveErrorMessage(self):
        client1 = await Client.new_established()

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
        self.assertDictEqual(ihaveobject_message, await client1.write_tx(cb_block1_after_genesis))

        client2 = await Client.new_established()

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
        await client1.write_dict(block_message)

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

    async def test_sendBlockInvalidCharLengthMiner_shouldReceiveErrorMessage(self):
        # c. There is an invalid transaction in the block.
        client = await Client.new_established()

        block_message = {
            "object":
                {
                    "T": "00000002af000000000000000000000000000000000000000000000000000000", "created": 1624219079,
                    "miner": "Invalid Note char length! Invalid Note char length! Invalid Note char length! Invalid Note char length! Invalid Note char length! ",
                    "nonce": "0000000000000000000000000000000000000000000000000000002634878840",
                    "note": "The Economist 2021-06-20: Crypto-miners are probably to blame for the graphics-chip shortage",
                    "previd": None, "txids": [], "type": "block"
                },
            "type": "object"
        }

        await client.write_dict(block_message)

        response = await client.read_dict()
        self.assertIn("error", response['type'])
        self.assertIn("Failed to validate", response['error'])

        await client.close()

    async def test_sendBlockInvalidCharLengthNote_shouldReceiveErrorMessage(self):
        # c. There is an invalid transaction in the block.
        client = await Client.new_established()

        block_message = {
            "object":
                {
                    "T": "00000002af000000000000000000000000000000000000000000000000000000", "created": 1624219079,
                    "miner": "dionyziz",
                    "nonce": "0000000000000000000000000000000000000000000000000000002634878840",
                    "note": "Invalid Note char length! Invalid Note char length! Invalid Note char length! Invalid Note char length! Invalid Note char length!",
                    "previd": None, "txids": [], "type": "block"
                },
            "type": "object"
        }

        await client.write_dict(block_message)

        response = await client.read_dict()
        self.assertIn("error", response['type'])
        self.assertIn("Failed to validate", response['error'])

        await client.close()


class Task4TestCase(KermaTestCase):
    # Grader 1 sends one of the following invalid blockchains by advertising a new block with
    # the object message. Grader 1 must receive an error message, and Grader 2 must not
    # receive an ihaveobject message with the corresponding blockid.

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

    async def test_sendBlockchainNonIncreasingTimestamp_shouldReceiveErrorMessage(self):
        # b. A blockchain with non-increasing timestamps
        client1 = await Client.new_established()

        block_message = {
            "object":
                {
                    "T": "00000002af000000000000000000000000000000000000000000000000000000", "created": 1624219078,
                    "miner": "Kermars", "nonce": "00000000000000000000000000000000000000000000000020000000130b9ad4",
                    "note": "non-increasing timestamp",
                    "previd": "00000000a420b7cefa2b7730243316921ed59ffe836e111ca3801f82a4f5360e", "txids": [],
                    "type": "block"
                },
            "type": "object"
        }

        await client1.write_dict(block_message)

        response = await client1.read_dict()
        self.assertIn("error", response['type'])
        self.assertIn("timestamp not later than of its parent", response['error'])

        await client1.close()

    async def test_sendBlockchainBlockInYear2077_shouldReceiveErrorMessage(self):
        # c. A blockchain with a block in the year 2077
        client1 = await Client.new_established()

        block_message = {
            "object":
                {
                    "T": "00000002af000000000000000000000000000000000000000000000000000000", "created": 3376684800,
                    "miner": "Kermars", "nonce": "000000000000000000000000000000000000000000000000c00000000977aa54",
                    "note": "block in the year 2077",
                    "previd": "00000000a420b7cefa2b7730243316921ed59ffe836e111ca3801f82a4f5360e", "txids": [],
                    "type": "block"
                },
            "type": "object"
        }

        await client1.write_dict(block_message)

        response = await client1.read_dict()
        self.assertIn("error", response['type'])
        self.assertIn("timestamp in the future", response['error'])

        await client1.close()

    async def test_sendBlockchainStopsDifferentGenesis_shouldReceiveErrorMessage(self):
        # e. A blockchain that does not go back to the real genesis but stops at a different genesis
        # (with valid PoW but a null previd)
        client1 = await Client.new_established()

        block_message = {
            "object":
                {
                    "T": "00000002af000000000000000000000000000000000000000000000000000000", "created": 1670685988,
                    "miner": "Kermars", "nonce": "000000000000000000000000000000000000000000000000400000000fac7792",
                    "note": "different genesis", "previd": None, "txids": [], "type": "block"
                },
            "type": "object"
        }

        await client1.write_dict(block_message)

        response = await client1.read_dict()
        self.assertIn("error", response['type'])
        self.assertIn("stops at a different genesis", response['error'])

        await client1.close()

    async def test_sendBlockchainMissingParentBlock_shouldReceiveGetObjectParent(self):
        client1 = await Client.new_established()

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
        self.assertDictEqual(ihaveobject_message, await client1.write_tx(tx_block2_after_genesis))

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
        getobject_message = {
            "type": "getobject",
            "objectid": "0000000108bdb42de5993bcf5f7d92557585dd6abfe9fb68e796518fe7f2ed2e"
        }
        await client1.write_dict(block_message)
        self.assertDictEqual(getobject_message, await client1.read_dict())

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
        self.assertDictEqual(ihaveobject_message, await client1.write_tx(cb_block1_after_genesis))

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

        await client1.write_dict(block_message)
        ihaveobject_message = {
            "type": "ihaveobject",
            "objectid": "0000000108bdb42de5993bcf5f7d92557585dd6abfe9fb68e796518fe7f2ed2e"
        }
        self.assertDictEqual(ihaveobject_message, await client1.read_dict())
        ihaveobject_message = {
            "type": "ihaveobject",
            "objectid": "00000002a8986627f379547ed1ec990841e1f1c6ba616a56bfcd4b410280dc6d"
        }
        self.assertDictEqual(ihaveobject_message, await client1.read_dict())

        await client1.close()

    async def test_sendGetChaintipOnEstablishedConnections(self):
        client1 = await Client.new_established()
        await client1.close()

        client2 = await Client.new()
        client3 = await Client.new()

        await client2.readline()
        await client3.readline()
        await client2.readline()
        await client3.readline()

        self.assertEqual(GET_CHAINTIP, await client2.readline())
        self.assertEqual(GET_CHAINTIP, await client3.readline())

        await client2.close()
        await client3.close()

    async def test_sendChaintipMessage(self):
        client1 = await Client.new_established()
        await client1.write(GET_CHAINTIP)

        response = await client1.read_dict()

        self.assertEqual("chaintip", response["type"])
        self.assertEqual("00000000a420b7cefa2b7730243316921ed59ffe836e111ca3801f82a4f5360e", response["blockid"])

        await client1.close()

    async def test_sendGetObjectAfterReceivingNewChaintip(self):
        client1 = await Client.new_established()
        chaintip_message = {
            "type": "chaintip", "blockid": "0000000108bdb42de5993bcf5f7d92557585dd6abfe9fb68e796518fe7f2ed2e"
        }
        await client1.write_dict(chaintip_message)

        response = await client1.read_dict()

        self.assertEqual("getobject", response["type"])
        self.assertEqual("0000000108bdb42de5993bcf5f7d92557585dd6abfe9fb68e796518fe7f2ed2e", response["objectid"])

        await client1.close()

    async def test_doNothingAfterReceivingOldChaintip(self):
        client1 = await Client.new_established()

        chaintip_message = {
            "type": "chaintip", "blockid": "00000000a420b7cefa2b7730243316921ed59ffe836e111ca3801f82a4f5360e"
        }
        await client1.write_dict(chaintip_message)

        with self.assertRaises(asyncio.TimeoutError):
            await asyncio.wait_for(client1.readline(), 0.5)

        await client1.close()

    async def test_sendNewChaintipAfterReceivingNewBlock(self):
        # Grader 1 sends a number of valid blockchains. When Grader 1 subsequently sends a getchaintip message,
        # it must receive a chaintip message with the blockid of the tip of the longest chain.
        client1 = await Client.new_established()
        await client1.write(GET_CHAINTIP)

        response1 = await client1.read_dict()

        self.assertEqual("chaintip", response1["type"])
        self.assertEqual("00000000a420b7cefa2b7730243316921ed59ffe836e111ca3801f82a4f5360e", response1["blockid"])

        await self.append_block1(client1)
        await client1.write(GET_CHAINTIP)

        response2 = await client1.read_dict()

        self.assertEqual("chaintip", response2["type"])
        self.assertEqual("0000000108bdb42de5993bcf5f7d92557585dd6abfe9fb68e796518fe7f2ed2e", response2["blockid"])

        await client1.close()

    async def test_forkedChain_becomesMainChain_shouldChangeChaintip(self):
        client1 = await Client.new_established()
        await self.append_block1(client1)

        await client1.write(GET_CHAINTIP)

        response1 = await client1.read_dict()

        self.assertEqual("chaintip", response1["type"])
        self.assertEqual("0000000108bdb42de5993bcf5f7d92557585dd6abfe9fb68e796518fe7f2ed2e", response1["blockid"])

        second_chain_first_block_message = {
            "object": {
                "T": "00000002af000000000000000000000000000000000000000000000000000000",
                "created": 1624219100, "miner": "SneakyDude",
                "nonce": "0000000000000000000000000000000000000000000000005000000028d1f901",
                "note": "First block of second chain",
                "previd": "00000000a420b7cefa2b7730243316921ed59ffe836e111ca3801f82a4f5360e",
                "txids": [], "type": "block"
            },
            "type": "object"
        }

        await client1.write_dict(second_chain_first_block_message)
        ihaveobject_message = {
            "type": "ihaveobject",
            "objectid": "0000000107ed1ee160e589214b48e80359d801c4226b69bebd39da8b65c6e83e"
        }

        self.assertDictEqual(ihaveobject_message, await client1.read_dict())

        second_chain_second_block_message = {
            "object": {
                "T": "00000002af000000000000000000000000000000000000000000000000000000",
                "created": 1624219200, "miner": "SneakyDude",
                "nonce": "000000000000000000000000000000000000000000000000b000000007047bb1",
                "note": "Second block of second chain",
                "previd": "0000000107ed1ee160e589214b48e80359d801c4226b69bebd39da8b65c6e83e",
                "txids": [], "type": "block"
            },
            "type": "object"
        }

        await client1.write_dict(second_chain_second_block_message)
        ihaveobject_message = {
            "type": "ihaveobject",
            "objectid": "000000024297ac6fe162c32dd1f43d2352adec27c1f36ccdd6e7cf0c8b5ed40b"
        }

        self.assertDictEqual(ihaveobject_message, await client1.read_dict())

        await client1.write(GET_CHAINTIP)

        response1 = await client1.read_dict()

        self.assertEqual("chaintip", response1["type"])
        self.assertEqual("000000024297ac6fe162c32dd1f43d2352adec27c1f36ccdd6e7cf0c8b5ed40b", response1["blockid"])

        await client1.close()

    async def test_forkedChain_proofOfWorkInvalid_shouldRaiseProtocolError(self):
        client1 = await Client.new_established()
        await self.append_block1(client1)

        await client1.write(GET_CHAINTIP)

        response1 = await client1.read_dict()

        self.assertEqual("chaintip", response1["type"])
        self.assertEqual("0000000108bdb42de5993bcf5f7d92557585dd6abfe9fb68e796518fe7f2ed2e", response1["blockid"])

        second_chain_first_block_message = {
            "object": {
                "T": "00000002af000000000000000000000000000000000000000000000000000000",
                "created": 1624219100, "miner": "SneakyDude",
                "nonce": "0000000000000000000000000000000000000000000000005000000028d1f901",
                "note": "First block of second chain",
                "previd": "00000000a420b7cefa2b7730243316921ed59ffe836e111ca3801f82a4f5360e",
                "txids": [], "type": "block"
            },
            "type": "object"
        }

        await client1.write_dict(second_chain_first_block_message)
        ihaveobject_message = {
            "type": "ihaveobject",
            "objectid": "0000000107ed1ee160e589214b48e80359d801c4226b69bebd39da8b65c6e83e"
        }

        self.assertDictEqual(ihaveobject_message, await client1.read_dict())

        second_chain_second_block_message = {
            "object": {
                "T": "00000002af000000000000000000000000000000000000000000000000000000",
                "created": 1624219200, "miner": "SneakyDude",
                "nonce": "ab0000000000000000000000000000000000000000000000b000000007047bb1",
                "note": "Second block of second chain",
                "previd": "0000000107ed1ee160e589214b48e80359d801c4226b69bebd39da8b65c6e83e",
                "txids": [], "type": "block"
            },
            "type": "object"
        }

        await client1.write_dict(second_chain_second_block_message)

        response = await client1.read_dict()
        self.assertIn("error", response['type'])
        self.assertIn("proof-of-work", response['error'])

        await client1.close()

    async def test_forkedChain_blockUnavailable_shouldRaiseProtocolError(self):
        client1 = await Client.new_established()
        await self.append_block1(client1)

        await client1.write(GET_CHAINTIP)

        response1 = await client1.read_dict()

        self.assertEqual("chaintip", response1["type"])
        self.assertEqual("0000000108bdb42de5993bcf5f7d92557585dd6abfe9fb68e796518fe7f2ed2e", response1["blockid"])

        second_chain_first_block_message = {
            "object": {
                "T": "00000002af000000000000000000000000000000000000000000000000000000",
                "created": 1624219100, "miner": "SneakyDude",
                "nonce": "0000000000000000000000000000000000000000000000005000000028d1f901",
                "note": "First block of second chain",
                "previd": "00000000a420b7cefa2b7730243316921ed59ffe836e111ca3801f82a4f5360e",
                "txids": [], "type": "block"
            },
            "type": "object"
        }

        await client1.write_dict(second_chain_first_block_message)
        ihaveobject_message = {
            "type": "ihaveobject",
            "objectid": "0000000107ed1ee160e589214b48e80359d801c4226b69bebd39da8b65c6e83e"
        }

        self.assertDictEqual(ihaveobject_message, await client1.read_dict())

        second_chain_second_block_message = {
            "object": {
                "T": "00000002af000000000000000000000000000000000000000000000000000000",
                "created": 1624219200, "miner": "SneakyDude",
                "nonce": "0000000000000000000000000000000000000000000000001000000001ece041",
                "note": "Second block of second chain",
                "previd": "0000000107ed1ee160e589214b48e80359d801c4226b69bebd39da8b65c6e83a",
                "txids": [], "type": "block"
            },
            "type": "object"
        }

        await client1.write_dict(second_chain_second_block_message)

        # Read request of object (block)
        await client1.read_dict()
        response = await client1.read_dict()
        self.assertIn("error", response['type'])
        self.assertIn("parent(-s) could not be received", response['error'])

        await client1.close()

    async def test_forkedChain_coinbaseTxWrongHeight_shouldRaiseProtocolError(self):
        client1 = await Client.new_established()
        await self.append_block1(client1)

        await client1.write(GET_CHAINTIP)

        response1 = await client1.read_dict()

        self.assertEqual("chaintip", response1["type"])
        self.assertEqual("0000000108bdb42de5993bcf5f7d92557585dd6abfe9fb68e796518fe7f2ed2e", response1["blockid"])

        second_chain_first_block_message = {
            "object": {
                "T": "00000002af000000000000000000000000000000000000000000000000000000",
                "created": 1624219100, "miner": "SneakyDude",
                "nonce": "0000000000000000000000000000000000000000000000005000000028d1f901",
                "note": "First block of second chain",
                "previd": "00000000a420b7cefa2b7730243316921ed59ffe836e111ca3801f82a4f5360e",
                "txids": [], "type": "block"
            },
            "type": "object"
        }

        await client1.write_dict(second_chain_first_block_message)
        ihaveobject_message = {
            "type": "ihaveobject",
            "objectid": "0000000107ed1ee160e589214b48e80359d801c4226b69bebd39da8b65c6e83e"
        }

        self.assertDictEqual(ihaveobject_message, await client1.read_dict())

        tx_cb_message = {
            "height": 100, "outputs": [
                {
                    "pubkey": "c7c2c13afd02be7986dee0f4630df01abdbc950ea379055f1a423a6090f1b2b3",
                    "value": 50000000000000
                }],
            "type": "transaction"
        }

        ihaveobject_message = {
            "type": "ihaveobject",
            "objectid": "f541463a09a32a1a72e347779d739d5c5969b2f94b38c647d0038cbc4dfac10d"
        }
        self.assertDictEqual(ihaveobject_message, await client1.write_tx(tx_cb_message))

        second_chain_second_block_message = {
            "object": {
                "T": "00000002af000000000000000000000000000000000000000000000000000000",
                "created": 1624219200, "miner": "SneakyDude",
                "nonce": "0000000000000000000000000000000000000000000000004000000003054557",
                "note": "Second block of second chain",
                "previd": "0000000107ed1ee160e589214b48e80359d801c4226b69bebd39da8b65c6e83e",
                "txids": ["f541463a09a32a1a72e347779d739d5c5969b2f94b38c647d0038cbc4dfac10d"], "type": "block"
            },
            "type": "object"
        }

        await client1.write_dict(second_chain_second_block_message)

        response = await client1.read_dict()
        self.assertIn("error", response['type'])
        self.assertIn("height does not match block height", response['error'])

        await client1.close()


class Task5TestCase(KermaTestCase):
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

    async def append_block2(self, client):
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

    # Grader 1 sends one of the following invalid objects in an object message.
    # Grader 1 must receive an error message,
    # and Grader 2 must not receive an ihaveobject message with the corresponding object id.
    # a) A transaction with two inputs that share an outpoint.

    async def test_sendInvalidObjectWithTwoInputSameOutpoint(self):
        private_key = ed25519.Ed25519PrivateKey.generate()
        pubkey_hex = private_key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex()

        client1 = await Client.new_established()

        initial_transaction = {
            "height": 1,
            "outputs": [{
                "pubkey": None,
                "value": 50000000000000}
            ],
            "type": "transaction"
        }
        initial_transaction["outputs"][0]["pubkey"] = pubkey_hex
        txid = await client1.write_tx(initial_transaction)
        txid = txid['objectid']

        client2 = await Client.new_established()

        invalid_transaction_with_two_inputs = {
            "inputs": [{
                "outpoint": {
                    "index": 0,
                    "txid": txid
                },
                "sig": None
            },
                {
                    "outpoint": {
                        "index": 0,
                        "txid": txid
                    },
                    "sig": None
                },
            ],
            "outputs": [{
                "pubkey": "4a7f4fb59ee4b3b2f940cf0efb6a09d9b74e8f30f9f8cc381e77fe8f69e996e2",
                "value": 49000000000000}
            ],
            "type": "transaction"
        }
        sig = private_key.sign(
            bytes.fromhex(canonicalize(copy.deepcopy(invalid_transaction_with_two_inputs)).hex())).hex()

        invalid_transaction_with_two_inputs['inputs'][0]['sig'] = sig
        invalid_transaction_with_two_inputs['inputs'][1]['sig'] = sig

        response = await client1.write_tx(invalid_transaction_with_two_inputs)

        self.assertIn("error", response['type'])
        self.assertIn("has multiple inputs with the same outpoint", response['error'])

        self.assertIsNone(await client2.read_with_timeout(1))

        await client1.close()
        await client2.close()

    # b) A block with more than 128 characters in the note field.
    async def test_sendInvalidBlockWithNoteOver128(self):
        client1 = await Client.new_established()
        client2 = await Client.new_established()

        invalid_block_with_too_long_note = {
            "object": {
                "T": "00000002af000000000000000000000000000000000000000000000000000000",
                "created": 1669664684,
                "miner": "Kermars",
                "nonce": "000000000000000000000000000000000000000000000000600000000e9aa668",
                "note": "Invest in crypto for a decentralized future. Diversify your portfolio and join the digital revolution. #crypto #blockchain #bitcoin",
                "previd": "0000000108bdb42de5993bcf5f7d92557585dd6abfe9fb68e796518fe7f2ed2e",
                "txids": [
                    "afcdaa10d98d1e03672b4160d329090cfed59baba22e3008f4b5dabf0fcdfbeb",
                    "7ef80f2da40b3f681a5aeb7962731beddccea25fa51e6e7ae6fbce8a58dbe799"
                ],
                "type": "block"
            },
            "type": "object"
        }

        await client1.write_dict(invalid_block_with_too_long_note)

        response = await client1.read_dict()
        self.assertIn("error", response['type'])
        self.assertIn("is too long", response['error'])

        self.assertIsNone(await client2.read_with_timeout(1))

        await client1.close()
        await client2.close()

    async def test_sendInvalidBlockWithNonAscii(self):
        client1 = await Client.new_established()
        client2 = await Client.new_established()

        invalid_block_with_non_ascii = {
            "object": {
                "T": "00000002af000000000000000000000000000000000000000000000000000000", "created": 1674412823,
                "miner": "¯\\_(ツ)_/¯",
                "nonce": "00000000000000000000000000000000000000000000000000000000c1d36267",
                "note": "Invalid block, non-ASCII character in miner field",
                "previd": "00000000a420b7cefa2b7730243316921ed59ffe836e111ca3801f82a4f5360e",
                "txids": ["472cac1f3a5ce611f9eb10512e109c18dfc4b1b168e63ef89ebea962a206d871"],
                "type": "block"
            },
            "type": "object"}

        await client1.write_dict(invalid_block_with_non_ascii)

        response = await client1.read_dict()
        self.assertIn("error", response['type'])
        self.assertIn("does not match", response['error'])

        self.assertIsNone(await client2.read_with_timeout(1))

        await client1.close()
        await client2.close()

    # Grader 1 sends a valid transaction with two inputs (spending outputs with different public keys).
    # Grader 2 must receive the transaction when it sends a getobject with the corresponding transaction id.
    async def test_sendValidTransactionAndReceiveItWithGetObject(self):
        private_key = ed25519.Ed25519PrivateKey.generate()
        pubkey_hex = private_key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex()

        client1 = await Client.new_established()

        first_transaction = {
            "height": 1,
            "outputs": [{
                "pubkey": None,
                "value": 50000000000000}
            ],
            "type": "transaction"
        }
        second_transaction = {
            "height": 1,
            "outputs": [{
                "pubkey": None,
                "value": 5000000000000}
            ],
            "type": "transaction"
        }
        first_transaction["outputs"][0]["pubkey"] = pubkey_hex
        txid1 = await client1.write_tx(first_transaction)
        txid1 = txid1['objectid']
        second_transaction["outputs"][0]["pubkey"] = pubkey_hex
        txid2 = await client1.write_tx(second_transaction)
        txid2 = txid2['objectid']

        client2 = await Client.new_established()

        transaction_with_two_inputs = {
            "inputs": [{
                "outpoint": {
                    "index": 0,
                    "txid": txid1
                },
                "sig": None
            },
                {
                    "outpoint": {
                        "index": 0,
                        "txid": txid2
                    },
                    "sig": None
                },
            ],
            "outputs": [{
                "pubkey": "4a7f4fb59ee4b3b2f940cf0efb6a09d9b74e8f30f9f8cc381e77fe8f69e996e2",
                "value": 49000000000000}
            ],
            "type": "transaction"
        }
        sig = private_key.sign(bytes.fromhex(canonicalize(copy.deepcopy(transaction_with_two_inputs)).hex())).hex()

        transaction_with_two_inputs['inputs'][0]['sig'] = sig
        transaction_with_two_inputs['inputs'][1]['sig'] = sig

        await client1.write_tx(transaction_with_two_inputs)

        ihaveobject_message = await client2.read_dict()
        self.assertEqual("ihaveobject", ihaveobject_message["type"])

        getobject_message = {
            "type": "getobject",
            "objectid": ihaveobject_message["objectid"]
        }

        await client2.write_dict(getobject_message)
        self.assertIn("object", await client2.read_dict())

        await client1.close()
        await client2.close()

    # Grader 1 sends a getmempool and getchaintip message to obtain your mempool and longest chain.
    # a) The mempool must be valid with respect to the UTXO state after the chain.
    async def test_sendValidMempoolAndChain(self):
        client1 = await Client.new_established()
        await self.append_block1(client1)

        mempool_transaction = {
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

        txid = await client1.write_tx(mempool_transaction)
        txid = txid['objectid']

        await client1.write(GET_CHAINTIP)

        chaintip_response = await client1.read_dict()
        await client1.write(GET_MEMPOOL)
        mempool_response = await client1.read_dict()

        self.assertIn(txid, mempool_response['txids'][0])

    # b) Grader 1 sends a transaction that is valid with respect to the mempool state.
    # Grader 1 again sends a getmempool message,
    # and this time the mempool should contain the sent transaction.
    async def test_mempoolContainsSentTransaction(self):
        private_key = ed25519.Ed25519PrivateKey.generate()
        pubkey_hex = private_key.public_key().public_bytes(Encoding.Raw, PublicFormat.Raw).hex()

        client1 = await Client.new_established()
        await self.append_block1(client1)

        mempool_transaction = {
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

        txid = (await client1.write_tx(mempool_transaction))

        await client1.write(GET_MEMPOOL)
        mempool_response = await client1.read_dict()

        self.assertIn(txid['objectid'], mempool_response['txids'][0])

    # c) Grader 1 sends a transaction that is invalid with respect to the mempool state.
    # Grader 1 again sends a getmempool message,
    # and this time the mempool should not contain the sent transaction.
    async def test_mempoolContainsNotInvalidSentTransaction(self):
        client1 = await Client.new_established()
        await self.append_block1(client1)
        invalid_transaction = {
            "inputs": [{
                "outpoint": {
                    "index": 0,
                    "txid": 'test'
                },
                "sig": 'test'
            },
            ],
            "outputs": [{
                "pubkey": "4a7f4fb59ee4b3b2f940cf0efb6a09d9b74e8f30f9f8cc381e77fe8f69e996e2",
                "value": 49000000000000}
            ],
            "type": "transaction"
        }
        response = await client1.write_tx(invalid_transaction)

        self.assertIn("error", response['type'])
        # TODO: "Failed to validate incoming message: 'transaction' is not one of ['block']"
        """
        "sig": {
            "type": "string",
            "pattern": r"^[0-9a-f]+$",
            "minLength": 128,
            "maxLength": 128
        }
        """
        client2 = await Client.new_established()

        await client2.write(GET_MEMPOOL)
        mempool_response = await client2.read_dict()

        self.assertEqual(0, len(mempool_response['txids']))

    # d) Grader 1 sends a coinbase transaction.
    # Grader 1 again sends a getmempool message and this time the mempool should not contain the sent transaction.
    async def test_mempoolContainsNotCoinbaseSentTransaction(self):
        client1 = await Client.new_established()
        await self.append_block1(client1)
        invalid_transaction = {
            "height": 1,
            "outputs": [{
                "pubkey": "Test",
                "value": 50000000000000}
            ],
            "type": "transaction"
        }
        response = await client1.write_tx(invalid_transaction)

        self.assertIn("error", response['type'])
        # TODO: "Failed to validate incoming message: 'transaction' is not one of ['block']"
        client2 = await Client.new_established()

        await client2.write(GET_MEMPOOL)
        mempool_response = await client2.read_dict()

        self.assertEqual(0, len(mempool_response['txids']))

    # e) Grader 1 will send a longer chain (causing a reorg) and then send a getmempool message.
    # The received mempool must be consistent with the new chain:
    # i. It must not contain any transactions that are already in the new chain or
    # are invalid with respect to the new chain UTXO state.
    async def test_mempoolContainsNoTransactionFromLongerChain(self):
        client1 = await Client.new_established()
        await self.append_block1(client1)

        cb_block2_after_genesis = {
            "height": 2, "outputs": [
                {
                    "pubkey": "c7c2c13afd02be7986dee0f4630df01abdbc950ea379055f1a423a6090f1b2b3",
                    "value": 50000000000000
                }],
            "type": "transaction"
        }
        await client1.write_tx(cb_block2_after_genesis)

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
        objectid = (await client1.write_tx(tx_block2_after_genesis))["objectid"]

        await client1.write(GET_CHAINTIP)
        chaintip_response = await client1.read_dict()
        self.assertIn("0000000108bdb42de5993bcf5f7d92557585dd6abfe9fb68e796518fe7f2ed2e", chaintip_response['blockid'])

        await client1.write(GET_MEMPOOL)
        mempool_response = await client1.read_dict()
        self.assertIn(objectid, mempool_response['txids'][0])

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

        await client1.write_dict(block_message)
        await client1.readline()

        await client1.write(GET_CHAINTIP)
        chaintip_response = await client1.read_dict()
        self.assertIn("000000021dc4cfdcd0970084949f94da17f97504e1cc3e354851bb4768842b57", chaintip_response['blockid'])

        await client1.write(GET_MEMPOOL)
        mempool_response = await client1.read_dict()
        self.assertEqual(0, len(mempool_response['txids']))

    # ii. It must also contain transactions that were in the old chain but
    # are not in the new chain and valid with respect to the new chain UTXO state.

    async def test_mempoolContainsTransactionFromOldChain(self):
        client1 = await Client.new_established()
        client2 = await Client.new_established()
        await self.append_block1(client1)
        await self.append_block2(client1)

        await client1.write(GET_CHAINTIP)
        chaintip_response1 = await client1.read_dict()
        self.assertIn("000000021dc4cfdcd0970084949f94da17f97504e1cc3e354851bb4768842b57", chaintip_response1['blockid'])

        await client1.write(GET_MEMPOOL)
        mempool_response1 = await client1.read_dict()
        self.assertEqual(0, len(mempool_response1['txids']))

        second_chain_first_block_message = {
            "object": {
                "T": "00000002af000000000000000000000000000000000000000000000000000000",
                "created": 1624219100, "miner": "SneakyDude",
                "nonce": "0000000000000000000000000000000000000000000000005000000028d1f901",
                "note": "First block of second chain",
                "previd": "00000000a420b7cefa2b7730243316921ed59ffe836e111ca3801f82a4f5360e",
                "txids": [], "type": "block"
            },
            "type": "object"
        }

        await client1.write_dict(second_chain_first_block_message)
        await client1.readline()

        second_chain_second_block_message = {
            "object": {
                "T": "00000002af000000000000000000000000000000000000000000000000000000",
                "created": 1624219200, "miner": "SneakyDude",
                "nonce": "000000000000000000000000000000000000000000000000b000000007047bb1",
                "note": "Second block of second chain",
                "previd": "0000000107ed1ee160e589214b48e80359d801c4226b69bebd39da8b65c6e83e",
                "txids": [], "type": "block"
            },
            "type": "object"
        }

        await client1.write_dict(second_chain_second_block_message)
        await client1.readline()

        second_chain_third_block_message = {
            "T": "00000002af000000000000000000000000000000000000000000000000000000",
            "created": 1674424538, "miner": "Kermars",
            "nonce": "000000000000000000000000000000000000000000000000e000000014949e54",
            "note": "Third block of second chain",
            "previd": "000000024297ac6fe162c32dd1f43d2352adec27c1f36ccdd6e7cf0c8b5ed40b",
            "txids": [],
            "type": "block"
        }

        await client2.write_tx(second_chain_third_block_message)
        # Read ihaveobject
        await client1.read_dict()

        await client1.write(GET_CHAINTIP)
        chaintip_response = await client1.read_dict()
        self.assertIn("00000000f4e07f739943c7048f116970db7ec4b7f273d1e0ebba67fb347a7762", chaintip_response['blockid'])

        await client1.write(GET_MEMPOOL)
        mempool_response = await client1.read_dict()
        self.assertIn("7ef80f2da40b3f681a5aeb7962731beddccea25fa51e6e7ae6fbce8a58dbe799", mempool_response['txids'][0])


if __name__ == "__main__":
    unittest.main()
