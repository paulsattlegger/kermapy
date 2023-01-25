import json
import os
import sys
from unittest import TestCase
from unittest.mock import Mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src/kermapy')))  # noqa

from src.kermapy import transaction_validation, objects  # noqa: E402


class TransactionValidationTests(TestCase):
    @staticmethod
    def test_validateTransaction_shouldValidateCorrectly():
        # Arrange
        objs = Mock(objects.Objects)
        objs.get.return_value = {
            "height": 0, "outputs": [
                {"pubkey": "8dbcd2401c89c04d6e53c81c90aa0b551cc8fc47c0469217c8f5cfbae1e911f9", "value": 50000000000}],
            "type": "transaction"
        }

        message = {
            "inputs": [{
                "outpoint": {
                    "index": 0, "txid":
                        "1bb37b637d07100cd26fc063dfd4c39a7931cc88dae3417871219715a5e374af"
                }, "sig":
                    "1d0d7d774042607c69a87ac5f1cdf92bf474c25fafcc089fe667602bfefb0494726c519e92266957429ced875256e6915eb8cea2ea66366e739415efc47a6805"
            }],
            "outputs": [{"pubkey": "8dbcd2401c89c04d6e53c81c90aa0b551cc8fc47c0469217c8f5cfbae1e911f9", "value": 10}],
            "type": "transaction"
        }

        # Act & Assert
        transaction_validation.validate_transaction(message, objs)

    @staticmethod
    def test_validateTransaction_multipleInAndOutputs_shouldValidateCorrectly():
        # Arrange
        def mock_get(tx: str):
            if tx == "582b0efba0ea9756541e8ff30cae1b76e9ea088b20e23576a1d5cc688202963c":
                return ({
                    "height": 0, "outputs": [
                        {"pubkey": "344fd304e608eb462e733c4e5eb4eb7ae5fa28e05c1576b1fcf97d1a0aec5f7a", "value": 10}],
                    "type": "transaction"
                })
            elif tx == "821927f195ac13a80a3c7b12811b6b09ddf842a778086f306cc7cd11a572bdc1":
                return ({
                    "height": 0, "outputs": [
                        {"pubkey": "8bc6cdd11175a292ea2933ead0626bece01df76e8a2a5d5d2399c6838605c880", "value": 5}],
                    "type": "transaction"
                })

            return None

        objs = Mock(objects.Objects)
        objs.get.side_effect = mock_get

        message = {
            "inputs": [{
                "outpoint": {
                    "index": 0, "txid": "582b0efba0ea9756541e8ff30cae1b76e9ea088b20e23576a1d5cc688202963c"
                },
                "sig": "7c86433d9004a7ce2fb26234224b66fb94d5f19db8abe99a768d251f36c8e3a2b1a8c2183015a940291a636c5c357eeee66f97e4a8e9e6c129935eedc767080e"
            }, {
                "outpoint": {
                    "index": 0, "txid": "821927f195ac13a80a3c7b12811b6b09ddf842a778086f306cc7cd11a572bdc1"
                },
                "sig": "0c5d4691a383e18ad43417e4fbde35506fb99444b7ed65484a92fbafa5753b266f827982ad21c6d5995726d04713ee8063e5ae00f0900fc630e8651fa542eb04"
            }],
            "outputs": [{"pubkey": "344fd304e608eb462e733c4e5eb4eb7ae5fa28e05c1576b1fcf97d1a0aec5f7a", "value": 5},
                        {"pubkey": "8bc6cdd11175a292ea2933ead0626bece01df76e8a2a5d5d2399c6838605c880", "value": 10}],
            "type": "transaction"
        }

        # Act & Assert
        transaction_validation.validate_transaction(message, objs)

    def test_validateTransaction_invalidSignature_shouldRaiseError(self):
        # Arrange
        objs = Mock(objects.Objects)
        objs.get.return_value = ({
            "height": 0,
            "outputs": [
                {
                    "pubkey": "8dbcd2401c89c04d6e53c81c90aa0b551cc8fc47c0469217c8f5cfbae1e911f9",
                    "value": 50000000000
                }
            ], "type": "transaction"
        })

        message = {
            "inputs": [{
                "outpoint": {
                    "index": 0, "txid": "1bb37b637d07100cd26fc063dfd4c39a7931cc88dae3417871219715a5e374af"
                },
                "sig": "8cad10c82c38411b89386adb399696e9df34478aa571326883f4a27f16fcdc3d4852d87a55571a9cca886b6fe7b47a4443177cb7f806ad071306307bfb4f480b"
            }],
            "outputs": [{"pubkey": "8dbcd2401c89c04d6e53c81c90aa0b551cc8fc47c0469217c8f5cfbae1e911f9", "value": 10}],
            "type": "transaction"
        }

        # Act & Assert
        try:
            transaction_validation.validate_transaction(message, objs)
            self.fail("Expected an error but none was raised")
        except transaction_validation.InvalidTransaction as e:
            self.assertIn("Invalid signature", str(e))

    def test_validateTransaction_invalidPubKey_shouldRaiseError(self):
        # Arrange
        objs = Mock(objects.Objects)
        objs.get.return_value = ({
            "height": 0,
            "outputs": [{
                "pubkey": "a2ba5aebc27d7ffb476e45cdef00146eaabc2614eeb0b3a878541d96605e5a52",
                "value": 50000000000
            }], "type": "transaction"
        })

        message = {
            "inputs": [{
                "outpoint": {
                    "index": 0, "txid": "1bb37b637d07100cd26fc063dfd4c39a7931cc88dae3417871219715a5e374af"
                },
                "sig": "1d0d7d774042607c69a87ac5f1cdf92bf474c25fafcc089fe667602bfefb0494726c519e92266957429ced875256e6915eb8cea2ea66366e739415efc47a6805"
            }],
            "outputs": [{"pubkey": "8dbcd2401c89c04d6e53c81c90aa0b551cc8fc47c0469217c8f5cfbae1e911f9", "value": 10}],
            "type": "transaction"
        }

        # Act & Assert
        try:
            transaction_validation.validate_transaction(message, objs)
            self.fail("Expected an error but none was raised")
        except transaction_validation.InvalidTransaction as e:
            self.assertIn("Invalid signature", str(e))

    def test_validateTransaction_canNotFindTx_shouldRaiseError(self):
        # Arrange
        objs = Mock(objects.Objects)
        objs.get.side_effect = KeyError

        message = {
            "inputs": [{
                "outpoint": {
                    "index": 0, "txid": "1bb37b637d07100cd26fc063dfd4c39a7931cc88dae3417871219715a5e374af"
                },
                "sig": "1d0d7d774042607c69a87ac5f1cdf92bf474c25fafcc089fe667602bfefb0494726c519e92266957429ced875256e6915eb8cea2ea66366e739415efc47a6805"
            }],
            "outputs": [{"pubkey": "8dbcd2401c89c04d6e53c81c90aa0b551cc8fc47c0469217c8f5cfbae1e911f9", "value": 10}],
            "type": "transaction"
        }

        # Act & Assert
        try:
            transaction_validation.validate_transaction(message, objs)
            self.fail("Expected an error but none was raised")
        except transaction_validation.InvalidTransaction as e:
            self.assertIn("Could not find", str(e))

    def test_validateTransaction_invalidIndex_shouldRaiseError(self):
        # Arrange
        objs = Mock(objects.Objects)
        objs.get.return_value = ({
            "height": 0,
            "outputs": [
                {
                    "pubkey": "a2ba5aebc27d7ffb476e45cdef00146eaabc2614eeb0b3a878541d96605e5a52",
                    "value": 50000000000
                }],
            "type": "transaction"
        })

        message = {
            "inputs": [{
                "outpoint": {
                    "index": 2, "txid": "1bb37b637d07100cd26fc063dfd4c39a7931cc88dae3417871219715a5e374af"
                },
                "sig": "1d0d7d774042607c69a87ac5f1cdf92bf474c25fafcc089fe667602bfefb0494726c519e92266957429ced875256e6915eb8cea2ea66366e739415efc47a6805"
            }],
            "outputs": [{"pubkey": "8dbcd2401c89c04d6e53c81c90aa0b551cc8fc47c0469217c8f5cfbae1e911f9", "value": 10}],
            "type": "transaction"
        }

        # Act & Assert
        try:
            transaction_validation.validate_transaction(message, objs)
            self.fail("Expected an error but none was raised")
        except transaction_validation.InvalidTransaction as e:
            self.assertIn("index", str(e))

    def test_validateTransaction_outputGreaterInput_shouldRaiseError(self):
        # Arrange
        objs = Mock(objects.Objects)
        objs.get.return_value = ({
            "height": 0, "outputs": [{
                "pubkey": "344fd304e608eb462e733c4e5eb4eb7ae5fa28e05c1576b1fcf97d1a0aec5f7a", "value": 5
            }], "type": "transaction"
        })

        message = {
            "inputs": [{
                "outpoint": {
                    "index": 0, "txid": "1bb37b637d07100cd26fc063dfd4c39a7931cc88dae3417871219715a5e374af"
                },
                "sig": "129493e34b72ff3f86b0e31d9e7f92b0adde10a201134c93de5564c543f6a5116b3d0a1f71a85321e4a0c12ea4fb2c69003e5235b18729c6a6e49c74eb516003"
            }],
            "outputs": [{"pubkey": "344fd304e608eb462e733c4e5eb4eb7ae5fa28e05c1576b1fcf97d1a0aec5f7a", "value": 10}],
            "type": "transaction"
        }

        # Act & Assert
        try:
            transaction_validation.validate_transaction(message, objs)
            self.fail("Expected an error but none was raised")
        except transaction_validation.InvalidTransaction as e:
            self.assertIn("Sum of input values is smaller", str(e))

    # Schema validation tests

    def test_validateTransaction_coinbase_shouldBeValid(self):
        # Arrange
        objs = Mock(objects.Objects)
        message = {
            "height": 0, "outputs": [
                {"pubkey": "344fd304e608eb462e733c4e5eb4eb7ae5fa28e05c1576b1fcf97d1a0aec5f7a", "value": 5}],
            "type": "transaction"
        }

        # Act & Assert
        transaction_validation.validate_transaction(message, objs)

    def test_validateTransaction_coinbase_pubKeyToShort_shouldRaiseError(self):
        # Arrange
        objs = Mock(objects.Objects)
        message = {
            "height": 0, "outputs": [
                {"pubkey": "344fd304e608eb462e733c4e5eb4eb7ae5fa28e05c1576b1fcf97d1a0aec5f7", "value": 5}],
            "type": "transaction"
        }

        # Act & Assert
        try:
            transaction_validation.validate_transaction(message, objs)
            self.fail("Expected an error but none was raised")
        except transaction_validation.InvalidTransaction as e:
            self.assertIn("not well formed", str(e))

    def test_validateTransaction_coinbase_pubKeyToLong_shouldRaiseError(self):
        # Arrange
        objs = Mock(objects.Objects)
        message = json.loads(
            '{"height":0,"outputs":[{"pubkey":"344fd304e608eb462e733c4e5eb4eb7ae5fa28e05c1576b1fcf97d1a0aec5f777","value":5}],"type":"transaction"}')

        # Act & Assert
        try:
            transaction_validation.validate_transaction(message, objs)
            self.fail("Expected an error but none was raised")
        except transaction_validation.InvalidTransaction as e:
            self.assertIn("not well formed", str(e))

    def test_validateTransaction_coinbase_missingHeight_shouldRaiseError(self):
        # Arrange
        objs = Mock(objects.Objects)
        message = json.loads(
            '{"outputs":[{"pubkey":"344fd304e608eb462e733c4e5eb4eb7ae5fa28e05c1576b1fcf97d1a0aec5f777","value":5}],"type":"transaction"}')

        # Act & Assert
        try:
            transaction_validation.validate_transaction(message, objs)
            self.fail("Expected an error but none was raised")
        except transaction_validation.InvalidTransaction as e:
            self.assertIn("not well formed", str(e))

    def test_validateTransaction_coinbase_missingType_shouldRaiseError(self):
        # Arrange
        objs = Mock(objects.Objects)
        message = {
            "height": 0, "outputs": [
                {"pubkey": "344fd304e608eb462e733c4e5eb4eb7ae5fa28e05c1576b1fcf97d1a0aec5f777", "value": 5}]
        }

        # Act & Assert
        try:
            transaction_validation.validate_transaction(message, objs)
            self.fail("Expected an error but none was raised")
        except transaction_validation.InvalidTransaction as e:
            self.assertIn("not well formed", str(e))

    def test_validateTransaction_coinbase_negativeValue_shouldRaiseError(self):
        # Arrange
        objs = Mock(objects.Objects)
        message = json.loads(
            '{"height":0,"outputs":[{"pubkey":"344fd304e608eb462e733c4e5eb4eb7ae5fa28e05c1576b1fcf97d1a0aec5f7a","value":-5}],"type":"transaction"}')

        # Act & Assert
        try:
            transaction_validation.validate_transaction(message, objs)
            self.fail("Expected an error but none was raised")
        except transaction_validation.InvalidTransaction as e:
            self.assertIn("not well formed", str(e))

    def test_validateTransaction_tx_missingType_shouldRaiseError(self):
        # Arrange
        objs = Mock(objects.Objects)
        message = {
            "inputs": [{
                "outpoint": {
                    "index": 0, "txid": "1bb37b637d07100cd26fc063dfd4c39a7931cc88dae3417871219715a5e374af"
                },
                "sig": "1d0d7d774042607c69a87ac5f1cdf92bf474c25fafcc089fe667602bfefb0494726c519e92266957429ced875256e6915eb8cea2ea66366e739415efc47a6805"
            }],
            "outputs": [{"pubkey": "8dbcd2401c89c04d6e53c81c90aa0b551cc8fc47c0469217c8f5cfbae1e911f9", "value": 10}]
        }
        # Act & Assert
        try:
            transaction_validation.validate_transaction(message, objs)
            self.fail("Expected an error but none was raised")
        except transaction_validation.InvalidTransaction as e:
            self.assertIn("not well formed", str(e))

    def test_validateTransaction_tx_negativeValue_shouldRaiseError(self):
        # Arrange
        objs = Mock(objects.Objects)
        message = {
            "inputs": [{
                "outpoint": {
                    "index": 0, "txid": "1bb37b637d07100cd26fc063dfd4c39a7931cc88dae3417871219715a5e374af"
                },
                "sig": "1d0d7d774042607c69a87ac5f1cdf92bf474c25fafcc089fe667602bfefb0494726c519e92266957429ced875256e6915eb8cea2ea66366e739415efc47a6805"
            }],
            "outputs": [{"pubkey": "8dbcd2401c89c04d6e53c81c90aa0b551cc8fc47c0469217c8f5cfbae1e911f9", "value": -10}],
            "type": "transaction"
        }
        # Act & Assert
        try:
            transaction_validation.validate_transaction(message, objs)
            self.fail("Expected an error but none was raised")
        except transaction_validation.InvalidTransaction as e:
            self.assertIn("not well formed", str(e))

    def test_validateTransaction_tx_negativeIndex_shouldRaiseError(self):
        # Arrange
        objs = Mock(objects.Objects)
        message = {
            "inputs": [{
                "outpoint": {
                    "index": -1, "txid": "1bb37b637d07100cd26fc063dfd4c39a7931cc88dae3417871219715a5e374af"
                },
                "sig": "1d0d7d774042607c69a87ac5f1cdf92bf474c25fafcc089fe667602bfefb0494726c519e92266957429ced875256e6915eb8cea2ea66366e739415efc47a6805"
            }],
            "outputs": [{"pubkey": "8dbcd2401c89c04d6e53c81c90aa0b551cc8fc47c0469217c8f5cfbae1e911f9", "value": 10}],
            "type": "transaction"
        }
        # Act & Assert
        try:
            transaction_validation.validate_transaction(message, objs)
            self.fail("Expected an error but none was raised")
        except transaction_validation.InvalidTransaction as e:
            self.assertIn("not well formed", str(e))

    def test_validateTransaction_tx_signatureToShort_shouldRaiseError(self):
        # Arrange
        objs = Mock(objects.Objects)
        message = {
            "inputs": [{
                "outpoint": {
                    "index": 0, "txid": "1bb37b637d07100cd26fc063dfd4c39a7931cc88dae3417871219715a5e374af"
                },
                "sig": "1d0d7d774042607c69a87ac5f1cdf92bf474c25fafcc089fe667602bfefb0494726c519e92266957429ced875256e6915eb8cea2ea66366e739415efc47a680"
            }],
            "outputs": [{"pubkey": "8dbcd2401c89c04d6e53c81c90aa0b551cc8fc47c0469217c8f5cfbae1e911f9", "value": 10}],
            "type": "transaction"
        }
        # Act & Assert
        try:
            transaction_validation.validate_transaction(message, objs)
            self.fail("Expected an error but none was raised")
        except transaction_validation.InvalidTransaction as e:
            self.assertIn("not well formed", str(e))

    def test_validateTransaction_tx_signatureToLong_shouldRaiseError(self):
        # Arrange
        objs = Mock(objects.Objects)
        message = {
            "inputs": [{
                "outpoint": {
                    "index": 0, "txid": "1bb37b637d07100cd26fc063dfd4c39a7931cc88dae3417871219715a5e374af"
                },
                "sig": "1d0d7d774042607c69a87ac5f1cdf92bf474c25fafcc089fe667602bfefb0494726c519e92266957429ced875256e6915eb8cea2ea66366e739415efc47a68056"
            }],
            "outputs": [{"pubkey": "8dbcd2401c89c04d6e53c81c90aa0b551cc8fc47c0469217c8f5cfbae1e911f9", "value": 10}],
            "type": "transaction"
        }
        # Act & Assert
        try:
            transaction_validation.validate_transaction(message, objs)
            self.fail("Expected an error but none was raised")
        except transaction_validation.InvalidTransaction as e:
            self.assertIn("not well formed", str(e))

    def test_validateTransaction_tx_signature_invalidHex_shouldRaiseError(self):
        # Arrange
        objs = Mock(objects.Objects)
        message = {
            "inputs": [{
                "outpoint": {
                    "index": 0, "txid": "1bb37b637d07100cd26fc063dfd4c39a7931cc88dae3417871219715a5e374af"
                },
                "sig": "1d0d7d774042607c69a87ac5f1cdfg2bf474c25fafcc089fe667602bfefb0494726c519e92266957429ced875256e6915eb8cea2ea66366e739415efc47a6805"
            }],
            "outputs": [{"pubkey": "8dbcd2401c89c04d6e53c81c90aa0b551cc8fc47c0469217c8f5cfbae1e911f9", "value": 10}],
            "type": "transaction"
        }
        # Act & Assert
        try:
            transaction_validation.validate_transaction(message, objs)
            self.fail("Expected an error but none was raised")
        except transaction_validation.InvalidTransaction as e:
            self.assertIn("not well formed", str(e))

    def test_validateTransaction_tx_missingInputs_shouldRaiseError(self):
        # Arrange
        objs = Mock(objects.Objects)
        message = {
            "outputs": [{"pubkey": "8dbcd2401c89c04d6e53c81c90aa0b551cc8fc47c0469217c8f5cfbae1e911f9", "value": 10}],
            "type": "transaction"
        }
        # Act & Assert
        try:
            transaction_validation.validate_transaction(message, objs)
            self.fail("Expected an error but none was raised")
        except transaction_validation.InvalidTransaction as e:
            self.assertIn("not well formed", str(e))

    def test_validateTransaction_tx_missingOutputs_shouldRaiseError(self):
        # Arrange
        objs = Mock(objects.Objects)
        message = {
            "inputs": [{
                "outpoint": {
                    "index": 0, "txid": "1bb37b637d07100cd26fc063dfd4c39a7931cc88dae3417871219715a5e374af"
                },
                "sig": "1d0d7d774042607c69a87ac5f1cdf92bf474c25fafcc089fe667602bfefb0494726c519e92266957429ced875256e6915eb8cea2ea66366e739415efc47a6805"
            }], "type": "transaction"
        }
        # Act & Assert
        try:
            transaction_validation.validate_transaction(message, objs)
            self.fail("Expected an error but none was raised")
        except transaction_validation.InvalidTransaction as e:
            self.assertIn("not well formed", str(e))

    def test_validateTransaction_tx_outpoint_pubKeyToShort_shouldRaiseError(self):
        # Arrange
        objs = Mock(objects.Objects)
        message = {
            "inputs": [{
                "outpoint": {
                    "index": 0, "txid": "1bb37b637d07100cd26fc063dfd4c39a7931cc88dae3417871219715a5e374a"
                },
                "sig": "1d0d7d774042607c69a87ac5f1cdf92bf474c25fafcc089fe667602bfefb0494726c519e92266957429ced875256e6915eb8cea2ea66366e739415efc47a6805"
            }],
            "outputs": [{"pubkey": "8dbcd2401c89c04d6e53c81c90aa0b551cc8fc47c0469217c8f5cfbae1e911f9", "value": 10}],
            "type": "transaction"
        }
        # Act & Assert
        try:
            transaction_validation.validate_transaction(message, objs)
            self.fail("Expected an error but none was raised")
        except transaction_validation.InvalidTransaction as e:
            self.assertIn("not well formed", str(e))

    def test_validateTransaction_tx_outpoint_pubKeyToLong_shouldRaiseError(self):
        # Arrange
        objs = Mock(objects.Objects)
        message = {
            "inputs": [{
                "outpoint": {
                    "index": 0, "txid": "1bb37b637d07100cd26fc063dfd4c39a7931cc88dae3417871219715a5e374afa"
                },
                "sig": "1d0d7d774042607c69a87ac5f1cdf92bf474c25fafcc089fe667602bfefb0494726c519e92266957429ced875256e6915eb8cea2ea66366e739415efc47a6805"
            }],
            "outputs": [{"pubkey": "8dbcd2401c89c04d6e53c81c90aa0b551cc8fc47c0469217c8f5cfbae1e911f9", "value": 10}],
            "type": "transaction"
        }
        # Act & Assert
        try:
            transaction_validation.validate_transaction(message, objs)
            self.fail("Expected an error but none was raised")
        except transaction_validation.InvalidTransaction as e:
            self.assertIn("not well formed", str(e))

    def test_validateTransaction_tx_outputs_pubKeyToShort_shouldRaiseError(self):
        # Arrange
        objs = Mock(objects.Objects)
        message = {
            "inputs": [{
                "outpoint": {
                    "index": 0, "txid": "1bb37b637d07100cd26fc063dfd4c39a7931cc88dae3417871219715a5e374af"
                },
                "sig": "1d0d7d774042607c69a87ac5f1cdf92bf474c25fafcc089fe667602bfefb0494726c519e92266957429ced875256e6915eb8cea2ea66366e739415efc47a6805"
            }],
            "outputs": [{"pubkey": "8dbcd2401c89c04d6e53c81c90aa0b551cc8fc47c0469217c8fcfbae1e911f9", "value": 10}],
            "type": "transaction"
        }
        # Act & Assert
        try:
            transaction_validation.validate_transaction(message, objs)
            self.fail("Expected an error but none was raised")
        except transaction_validation.InvalidTransaction as e:
            self.assertIn("not well formed", str(e))

    def test_validateTransaction_tx_outputs_pubKeyToLong_shouldRaiseError(self):
        # Arrange
        objs = Mock(objects.Objects)
        message = {
            "inputs": [{
                "outpoint": {
                    "index": 0, "txid": "1bb37b637d07100cd26fc063dfd4c39a7931cc88dae3417871219715a5e374af"
                },
                "sig": "1d0d7d774042607c69a87ac5f1cdf92bf474c25fafcc089fe667602bfefb0494726c519e92266957429ced875256e6915eb8cea2ea66366e739415efc47a6805"
            }],
            "outputs": [{"pubkey": "8dbcd2401c89c04d6e53c81c90aa0b551cc8fc47c0469217c8f5acfbae1e911f9", "value": 10}],
            "type": "transaction"
        }
        # Act & Assert
        try:
            transaction_validation.validate_transaction(message, objs)
            self.fail("Expected an error but none was raised")
        except transaction_validation.InvalidTransaction as e:
            self.assertIn("not well formed", str(e))

    def test_validateTransaction_tx_outputs_pubKeyInvalidHex_shouldRaiseError(self):
        # Arrange
        objs = Mock(objects.Objects)
        message = {
            "inputs": [{
                "outpoint": {
                    "index": 0, "txid": "1bb37b637d07100cd26fc063dfd4c39a7931cc88dae3417871219715a5e374af"
                },
                "sig": "1d0d7d774042607c69a87ac5f1cdf92bf474c25fafcc089fe667602bfefb0494726c519e92266957429ced875256e6915eb8cea2ea66366e739415efc47a6805"
            }],
            "outputs": [{"pubkey": "8dbcd2401c89c04d6e53c81c90aa0b551cc8fc47c0469217c8fgcfbae1e911f9", "value": 10}],
            "type": "transaction"
        }
        # Act & Assert
        try:
            transaction_validation.validate_transaction(message, objs)
            self.fail("Expected an error but none was raised")
        except transaction_validation.InvalidTransaction as e:
            self.assertIn("not well formed", str(e))

    def test_validateTransaction_tx_inputsUseSameOutpoints_shouldRaiseError(self):
        # Arrange
        objs = Mock(objects.Objects)
        objs.get.return_value = {
            "height": 0, "outputs": [
                {"pubkey": "8617c757e825ca8e5b5754daaa1afd814d55d4474a8e59de561d0110efa47cb3", "value": 50000000000}],
            "type": "transaction"
        }

        message = {
            "inputs": [
                {
                    "outpoint": {
                        "index": 0, "txid":
                            "1bb37b637d07100cd26fc063dfd4c39a7931cc88dae3417871219715a5e374af"
                    }, "sig":
                    "371d35ec68bfb67858369eaa4f28ef5844d22aae0af7f3ad6992b99cbe6c55b47962efd3377cbf6d802654297dc1af1d844c84550b7c8513865291dc750deb0b"
                },
                {
                    "outpoint": {
                        "index": 0, "txid":
                            "1bb37b637d07100cd26fc063dfd4c39a7931cc88dae3417871219715a5e374af"
                    }, "sig":
                    "371d35ec68bfb67858369eaa4f28ef5844d22aae0af7f3ad6992b99cbe6c55b47962efd3377cbf6d802654297dc1af1d844c84550b7c8513865291dc750deb0b"
                }
            ],
            "outputs": [{"pubkey": "8dbcd2401c89c04d6e53c81c90aa0b551cc8fc47c0469217c8f5cfbae1e911f9", "value": 10}],
            "type": "transaction"
        }
        # Act & Assert
        try:
            transaction_validation.validate_transaction(message, objs)
            self.fail("Expected an error but none was raised")
        except transaction_validation.InvalidTransaction as e:
            self.assertIn("has multiple inputs with the same outpoint", str(e))
