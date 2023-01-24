import asyncio

from src.kermapy.kermapy import ProtocolError
from tests.test_kermapy import KermaTestCase, Client


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
