import asyncio

from tests.test_kermapy import KermaTestCase, Client

GET_CHAINTIP = b'{"type":"getchaintip"}\n'
GET_MEMPOOL = b'{"type":"getmempool"}\n'


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
