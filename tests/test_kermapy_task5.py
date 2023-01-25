import copy

from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives.serialization import PublicFormat, Encoding

from src.kermapy.org.webpki.json.Canonicalize import canonicalize
from tests.test_kermapy import KermaTestCase, Client

GET_CHAINTIP = b'{"type":"getchaintip"}\n'
GET_MEMPOOL = b'{"type":"getmempool"}\n'


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
            "type": "object"
        }

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
        self.assertEqual("0000000108bdb42de5993bcf5f7d92557585dd6abfe9fb68e796518fe7f2ed2e",
                         chaintip_response['blockid'])

        await client1.write(GET_MEMPOOL)
        mempool_response = await client1.read_dict()

        self.assertIn(txid, mempool_response['txids'][0])

        await client1.close()

    # b) Grader 1 sends a transaction that is valid with respect to the mempool state.
    # Grader 1 again sends a getmempool message,
    # and this time the mempool should contain the sent transaction.
    async def test_mempoolContainsSentTransaction(self):
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

        ihaveobject_message = await client1.write_tx(mempool_transaction)

        await client1.write(GET_MEMPOOL)
        mempool_response = await client1.read_dict()

        self.assertIn(ihaveobject_message['objectid'], mempool_response['txids'][0])

        await client1.close()

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
                    "txid": '4a7f4fb59ee4b3b2f940cf0efb6a09d9b74e8f30f9f8cc381e77fe8f69e996e2'
                },
                "sig": '49cc4f9a1fb9d600a7debc99150e7909274c8c74edd7ca183626dfe49eb4aa21c6ff0e4c5f0dc2a328ad6b8ba10bf7169d5f42993a94bf67e13afa943b749c0b'
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
        self.assertIn("not find transaction", response['error'])
        client2 = await Client.new_established()

        await client2.write(GET_MEMPOOL)
        mempool_response = await client2.read_dict()

        self.assertEqual(0, len(mempool_response['txids']))

        await client1.close()

    # d) Grader 1 sends a coinbase transaction.
    # Grader 1 again sends a getmempool message and this time the mempool should not contain the sent transaction.
    async def test_mempoolContainsNotCoinbaseSentTransaction(self):
        client1 = await Client.new_established()
        await self.append_block1(client1)
        cb_transaction = {
            "height": 0,
            "outputs": [{
                "pubkey": "c7c2c13afd02be7986dee0f4630df01abdbc950ea379055f1a423a6090f1b2b3",
                "value": 1
            }
            ],
            "type": "transaction"
        }
        response = await client1.write_tx(cb_transaction)

        self.assertIn("ihaveobject", response['type'])
        client2 = await Client.new_established()

        await client2.write(GET_MEMPOOL)
        mempool_response = await client2.read_dict()

        self.assertEqual(0, len(mempool_response['txids']))

        await client1.close()
        await client2.close()

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

        await client1.close()

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
                "created": 1674580127,
                "miner": "Kermars",
                "nonce": "0000000000000000000000000000000000000000000000000000000003093f36",
                "note": "Second block of second chain",
                "previd": "0000000107ed1ee160e589214b48e80359d801c4226b69bebd39da8b65c6e83e",
                "txids": ["73231cc901774ddb4196ee7e9e6b857b208eea04aee26ced038ac465e1e706d2"],
                "type": "block"
            },
            "type": "object"
        }

        await client1.write_dict(second_chain_second_block_message)
        await client1.readline()

        second_chain_third_block_message = {
            "T": "00000002af000000000000000000000000000000000000000000000000000000",
            "created": 1674580458,
            "miner": "Kermars",
            "nonce": "000000000000000000000000000000000000000000000000a000000008405d72",
            "note": "Third block of second chain",
            "previd": "000000012399208d1bc2bbf8a4ff3d4b3a0f175d59d583ba0816e4bc3122df46",
            "txids": [],
            "type": "block"
        }

        await client2.write_tx(second_chain_third_block_message)
        # Read ihaveobject
        await client1.read_dict()

        await client1.write(GET_CHAINTIP)
        chaintip_response = await client1.read_dict()
        self.assertIn("000000023c64f148c39b0ced8d00e9e8f531e3b8d82da0614e2b4e75411d9a29", chaintip_response['blockid'])

        await client1.write(GET_MEMPOOL)
        mempool_response = await client1.read_dict()
        self.assertIn("7ef80f2da40b3f681a5aeb7962731beddccea25fa51e6e7ae6fbce8a58dbe799", mempool_response['txids'][0])

        await client1.close()
        await client2.close()

    async def test_mempoolMattermost(self):
        client1 = await Client.new_established()

        cb_tx1_message = {"object": {"height": 1, "outputs": [
            {"pubkey": "deadc0de584cd512b6f43545d8e0f5825e09928bab3a54d86981c56fdf0fdf3f", "value": 50000000000000}],
                                     "type": "transaction"}, "type": "object"}

        await client1.write_dict(cb_tx1_message)

        block1_message = {
            "object": {"T": "00000002af000000000000000000000000000000000000000000000000000000", "created": 1674407763,
                       "miner": "crdm", "nonce": "00000000000000000000000000000000000000000000000000000000e395faad",
                       "note": "Valid first block",
                       "previd": "00000000a420b7cefa2b7730243316921ed59ffe836e111ca3801f82a4f5360e",
                       "txids": ["472cac1f3a5ce611f9eb10512e109c18dfc4b1b168e63ef89ebea962a206d871"], "type": "block"},
            "type": "object"}

        await client1.write_dict(block1_message)

        tx1_spending_cb_tx1_message = {"object": {"inputs": [
            {"outpoint": {"index": 0, "txid": "472cac1f3a5ce611f9eb10512e109c18dfc4b1b168e63ef89ebea962a206d871"},
             "sig": "8457acdc8f7773379f19d9a9aa0dfdb7cf8a54a46f7a1cd30ebca1557c1846e47d24aebdd7c2297735b60b73efa6abc033f4cee3b11a3e72d347d848f65d0606"}],
            "outputs": [{
                "pubkey": "cafebabe84905f40341d44e204a1aa347025f1f3048d752de03f7187caabc9c8",
                "value": 25000000000000}, {
                "pubkey": "000000006dab2269617d3afeaf36242ee27c448708367451ac78e8919dc5a4e3",
                "value": 25000000000000}], "type": "transaction"},
            "type": "object"}

        await client1.write_dict(tx1_spending_cb_tx1_message)

        cb_tx2_message = {"object": {"height": 2, "outputs": [
            {"pubkey": "deadc0de584cd512b6f43545d8e0f5825e09928bab3a54d86981c56fdf0fdf3f", "value": 50000000000000}],
                                     "type": "transaction"}, "type": "object"}

        await client1.write_dict(cb_tx2_message)

        block2_message = {
            "object": {"T": "00000002af000000000000000000000000000000000000000000000000000000", "created": 1674421809,
                       "miner": "crdm", "nonce": "0000000000000000000000000000000000000000000000000000000061100066",
                       "note": "Valid second block, including transaction 1",
                       "previd": "000000002fc4fc77fddbf1b7d058e7d180a7cd36bdabe0c7b71bf5a89dce1bbd",
                       "txids": ["e64b2a7468f7925ca5f39b187bce0a4a077c0a19b416450e557e0d05a0427600",
                                 "e9974a7a65f2ac0c011d14849310f29f6e5910087f773947392c6f91bdbebaad"], "type": "block"},
            "type": "object"}

        await client1.write_dict(block2_message)

        tx2_spending_tx1_first_output = {"object": {"inputs": [
            {"outpoint": {"index": 0, "txid": "e9974a7a65f2ac0c011d14849310f29f6e5910087f773947392c6f91bdbebaad"},
             "sig": "ee6ca39c2c13cec05406e9966fcdbdd3c7632fae39ecea4d0097af864000a074fee6abd3e84112e86489df0b4263a0afe646b88ac32726049f5441a568044300"}],
            "outputs": [{"pubkey": "000000006dab2269617d3afeaf36242ee27c448708367451ac78e8919dc5a4e3",
                         "value": 25000000000000}], "type": "transaction"}, "type": "object"}

        await client1.write_dict(tx2_spending_tx1_first_output)

        tx3_spending_tx1_first_output = {"object": {"inputs": [
            {"outpoint": {"index": 0, "txid": "e9974a7a65f2ac0c011d14849310f29f6e5910087f773947392c6f91bdbebaad"},
             "sig": "cc0a754a08237eeb5a2db651d3ddcddca00e045ea85c5ac8010400faadc4ac88939aa08e44ce570a4afad78d5aebcc00856fc983991dd587a368e785ddabc908"}],
            "outputs": [{"pubkey": "deadc0de584cd512b6f43545d8e0f5825e09928bab3a54d86981c56fdf0fdf3f",
                         "value": 25000000000000}], "type": "transaction"}, "type": "object"}

        await client1.write_dict(tx3_spending_tx1_first_output)

        tx4_spending_tx1_second_output = {"object": {"inputs": [
            {"outpoint": {"index": 1, "txid": "e9974a7a65f2ac0c011d14849310f29f6e5910087f773947392c6f91bdbebaad"},
             "sig": "96628b8269b6d7bfa95909b26bdb56ab3665190378c512a49e393dd940807c1b744543c09e23284d255fb7fbf8787ab7fdef56f684f9a0f6f72760b6fa43810b"}],
            "outputs": [{"pubkey": "000000006dab2269617d3afeaf36242ee27c448708367451ac78e8919dc5a4e3",
                         "value": 25000000000000}], "type": "transaction"}, "type": "object"}

        await client1.write_dict(tx4_spending_tx1_second_output)

        # Assert 1
        client2 = await Client.new_established()
        await client2.write(GET_MEMPOOL)
        mempool_message = await client2.read_dict()

        self.assertEqual("mempool", mempool_message["type"])
        self.assertIn("e623a4405a4903565577697b15d4b0dcf20afff645c7c3a5e4f97a9724b54f90", mempool_message["txids"])
        self.assertIn("8945cf9d0f04265276e60034f763d940a8956654faba9122496d89414676d3ac", mempool_message["txids"])

        await client2.close()

        cb_tx3_message = {"object": {"height": 3, "outputs": [
            {"pubkey": "deadc0de584cd512b6f43545d8e0f5825e09928bab3a54d86981c56fdf0fdf3f", "value": 50000000000000}],
                                     "type": "transaction"}, "type": "object"}

        await client1.write_dict(cb_tx3_message)

        block3_message = {
            "object": {"T": "00000002af000000000000000000000000000000000000000000000000000000", "created": 1674429556,
                       "miner": "crdm", "nonce": "000000000000000000000000000000000000000000000000000000a00069bd10",
                       "note": "Valid third block, including transactions 2 and 4",
                       "previd": "000000020495925bf1cae664f5db85899fe32bb50557681eabbd108c895eecd3",
                       "txids": ["6ec7c578197d002e40c3df5f1b27d368b99d8d3356a2ffbddeff1a958b696a7c",
                                 "e623a4405a4903565577697b15d4b0dcf20afff645c7c3a5e4f97a9724b54f90",
                                 "8945cf9d0f04265276e60034f763d940a8956654faba9122496d89414676d3ac"], "type": "block"},
            "type": "object"}

        await client1.write_dict(block3_message)

        client2 = await Client.new_established()
        await client2.write(GET_CHAINTIP)
        chaintip_message = await client2.read_dict()

        # Assert 2
        self.assertEqual("chaintip", chaintip_message["type"])
        self.assertEqual("000000004bd6c055c8c5c02f4a268875abcc1efca17f0011d49a2ffd87eb89de",
                         chaintip_message["blockid"])

        await client2.write(GET_MEMPOOL)
        mempool_message = await client2.read_dict()

        self.assertEqual("mempool", mempool_message["type"])
        self.assertEqual([], mempool_message["txids"])

        await client2.close()

        block3_fork_message = {
            "object": {"T": "00000002af000000000000000000000000000000000000000000000000000000", "created": 1674422927,
                       "miner": "crdm", "nonce": "00000000000000000000000000000000000000000000000000000000224fe21e",
                       "note": "Valid third block, including transaction 3",
                       "previd": "000000020495925bf1cae664f5db85899fe32bb50557681eabbd108c895eecd3",
                       "txids": ["6ec7c578197d002e40c3df5f1b27d368b99d8d3356a2ffbddeff1a958b696a7c",
                                 "72f479f8e100d06ac823567d334407663215c871c0ff6b543be4a16ff0075ca7"], "type": "block"},
            "type": "object"}

        await client1.write_dict(block3_fork_message)

        cb_tx4_message = {"object": {"height": 4, "outputs": [
            {"pubkey": "deadc0de584cd512b6f43545d8e0f5825e09928bab3a54d86981c56fdf0fdf3f", "value": 50000000000000}],
                                     "type": "transaction"}, "type": "object"}

        await client1.write_dict(cb_tx4_message)

        # causes a chain reorganization
        block4_fork_message = {
            "object": {"T": "00000002af000000000000000000000000000000000000000000000000000000", "created": 1674423221,
                       "miner": "crdm", "nonce": "00000000000000000000000000000000000000000000000000000000b6fbd48c",
                       "note": "Valid fourth block",
                       "previd": "000000012b5b5eb1d51c85ce4829ef19af4993aef41fe9c722f2f6e108445131",
                       "txids": ["49696a0b0aed0c8b992684331db37d255775595de12de72c8757dc473c7a323d"], "type": "block"},
            "type": "object"}

        await client1.write_dict(block4_fork_message)

        client2 = await Client.new_established()
        await client2.write(GET_CHAINTIP)
        chaintip_message = await client2.read_dict()

        # Assert 3
        self.assertEqual("chaintip", chaintip_message["type"])
        self.assertEqual("000000024aced733ea96ae952e3c689fc60e3672e23c66002de2e18b6fbd9842",
                         chaintip_message["blockid"])

        await client2.write(GET_MEMPOOL)
        mempool_message = await client2.read_dict()

        self.assertEqual("mempool", mempool_message["type"])
        self.assertEqual(["8945cf9d0f04265276e60034f763d940a8956654faba9122496d89414676d3ac"],
                         mempool_message["txids"])

        await client2.close()
        await client1.close()

    async def test_invalidTransaction_shouldSendErrorAndNotCloseConnection(self):
        client1 = await Client.new_established()
        await self.append_block1(client1)

        invalid_transaction = {
            "inputs": [{
                "outpoint": {
                    "index": 0,
                    "txid": '4a7f4fb59ee4b3b2f940cf0efb6a09d9b74e8f30f9f8cc381e77fe8f69e996e2'
                },
                "sig": '49cc4f9a1fb9d600a7debc99150e7909274c8c74edd7ca183626dfe49eb4aa21c6ff0e4c5f0dc2a328ad6b8ba10bf7169d5f42993a94bf67e13afa943b749c0b'
            },
            ],
            "outputs": [{
                "pubkey": "4a7f4fb59ee4b3b2f940cf0efb6a09d9b74e8f30f9f8cc381e77fe8f69e996e2",
                "value": 49000000000000}
            ],
            "type": "transaction"
        }

        error_response = await client1.write_tx(invalid_transaction)
        self.assertIn("error", error_response)

        # connection stays alive
        await client1.write(GET_CHAINTIP)
        self.assertIsNotNone(await client1.read_dict())
