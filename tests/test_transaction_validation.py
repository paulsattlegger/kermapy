import os
import sys
import plyvel
import json
from unittest import TestCase
from unittest.mock import Mock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src/kermapy')))  # noqa

from src.kermapy import transaction_validation  # noqa: E402


class TransactionValidationTests(TestCase):
    def test_validateTransaction_shouldValidateCorrectly(self):
        # Arrange
        db = Mock(plyvel.DB)
        db.get.return_value = (b'{"height":0,"outputs":[{"pubkey":'
                               b'"8dbcd2401c89c04d6e53c81c90aa0b551cc8fc47c0469217c8f5cfbae1e911f9",'
                               b'"value":50000000000}],"type":"transaction"}')

        message = json.loads('{"inputs":[{"outpoint":{"index":0,"txid":'
                             '"1bb37b637d07100cd26fc063dfd4c39a7931cc88dae3417871219715a5e374af"},"sig":'
                             '"1d0d7d774042607c69a87ac5f1cdf92bf474c25fafcc089fe667602bfefb049472'
                             '6c519e92266957429ced875256e6915eb8cea2ea66366e739415efc47a6805"}],'
                             '"outputs":[{"pubkey":"8dbcd2401c89c04d6e53c81c90aa0b551cc8fc47c0469217c8f5'
                             'cfbae1e911f9","value":10}],"type":"transaction"}')

        # Act & Assert
        transaction_validation.validate_transaction(message, db)

    def test_validateTransaction_multipleInAndOutputs_shouldValidateCorrectly(self):
        # Arrange
        def mock_get(tx: bytes):
            if tx == bytes.fromhex("582b0efba0ea9756541e8ff30cae1b76e9ea088b20e23576a1d5cc688202963c"):
                return (b'{"height":0,"outputs":[{"pubkey":"344fd304e608eb462e733c4e5eb4eb7ae5fa28e05c157'
                        b'6b1fcf97d1a0aec5f7a","value":10}],"type":"transaction"}')
            elif tx == bytes.fromhex("821927f195ac13a80a3c7b12811b6b09ddf842a778086f306cc7cd11a572bdc1"):
                return (b'{"height":0,"outputs":[{"pubkey":"8bc6cdd11175a292ea2933ead0626bece01df76e8a2a5d5'
                        b'd2399c6838605c880","value":5}],"type":"transaction"}')

            return None

        db = Mock(plyvel.DB)
        db.get.side_effect = mock_get

        message = json.loads('{"inputs":[{"outpoint":{"index":0,"txid":"582b0efba0ea9756541e'
                             '8ff30cae1b76e9ea088b20e23576a1d5cc688202963c"},'
                             '"sig":"7c86433d9004a7ce2fb26234224b66fb94d5f19db8abe99a768d251f36c8e3a2b1a8c21'
                             '83015a940291a636c5c357eeee66f97e4a8e9e6c129935eedc767080e"},'
                             '{"outpoint":{"index":0,"txid":"821927f195ac13a80a3c7b12811b6b09ddf842a778086f30'
                             '6cc7cd11a572bdc1"},'
                             '"sig":"0c5d4691a383e18ad43417e4fbde35506fb99444b7ed65484a92fbafa5753b266f827982'
                             'ad21c6d5995726d04713ee8063e5ae00f0900fc630e8651fa542eb04"}],'
                             '"outputs":[{"pubkey":"344fd304e608eb462e733c4e5eb4eb7ae5fa28e05c1576b1fcf97d1a0a'
                             'ec5f7a","value":5},{"pubkey": "8bc6cdd11175a292ea2933ead0626bece01df76e8a2a5d5d23'
                             '99c6838605c880","value":10}],"type":"transaction"}')

        # Act & Assert
        transaction_validation.validate_transaction(message, db)

    def test_validateTransaction_invalidSignature_shouldRaiseError(self):
        # Arrange
        db = Mock(plyvel.DB)
        db.get.return_value = (b'{"height":0,"outputs":[{"pubkey":"8dbcd2401c89c04d6e53c81c90aa0b551cc8fc47c04692'
                               b'17c8f5cfbae1e911f9","value":50000000000}],"type":"transaction"}')

        message = json.loads('{"inputs":[{"outpoint":{"index":0,"txid":"1bb37b637d07100cd26fc063dfd4'
                             'c39a7931cc88dae3417871219715a5e374af"},"sig":"8cad10c82c38411b89386adb399696e9df34478a'
                             'a571326883f4a27f16fcdc3d4852d87a55571a9cca886b6fe7b47a4443177cb7f806ad071306307bfb4f480b"}],'
                             '"outputs":[{"pubkey":"8dbcd2401c89c04d6e53c81c90aa0b551cc8fc47c0469217c8f5cfbae1e911f9",'
                             '"value":10}],"type":"transaction"}')

        # Act & Assert
        try:
            transaction_validation.validate_transaction(message, db)
            self.fail("Expected an error but none was raised")
        except transaction_validation.InvalidTransaction as e:
            self.assertIn("Invalid signature", str(e))

    def test_validateTransaction_invalidPubKey_shouldRaiseError(self):
        # Arrange
        db = Mock(plyvel.DB)
        db.get.return_value = (b'{"height":0,"outputs":[{"pubkey":"a2ba5aebc27d7ffb476e45cdef00146eaabc2614eeb0b3a878541d9'
                               b'6605e5a52","value":50000000000}],"type":"transaction"}')

        message = json.loads('{"inputs":[{"outpoint":{"index":0,"txid":"1bb37b637d07100cd26fc063dfd4c39a7931'
                             'cc88dae3417871219715a5e374af"},"sig":"1d0d7d774042607c69a87ac5f1cdf92bf474c25fafcc089fe667602b'
                             'fefb0494726c519e92266957429ced875256e6915eb8cea2ea66366e739415efc47a6805"}],'
                             '"outputs":[{"pubkey":"8dbcd2401c89c04d6e53c81c90aa0b551cc8fc47c0469217c8f5cfbae1e911f9",'
                             '"value":10}],"type":"transaction"}')

        # Act & Assert
        try:
            transaction_validation.validate_transaction(message, db)
            self.fail("Expected an error but none was raised")
        except transaction_validation.InvalidTransaction as e:
            self.assertIn("Invalid signature", str(e))

    def test_validateTransaction_canNotFindTx_shouldRaiseError(self):
        # Arrange
        db = Mock(plyvel.DB)
        db.get.return_value = None

        message = json.loads('{"inputs":[{"outpoint":{"index":0,"txid":"1bb37b637d07100cd26fc063dfd4c39a7931cc8'
                             '8dae3417871219715a5e374af"},"sig":"1d0d7d774042607c69a87ac5f1cdf92bf474c25fafcc089fe667602bfefb0'
                             '494726c519e92266957429ced875256e6915eb8cea2ea66366e739415efc47a6805"}],'
                             '"outputs":[{"pubkey":"8dbcd2401c89c04d6e53c81c90aa0b551cc8fc47c0469217c8f5cfbae1e911f9",'
                             '"value":10}],"type":"transaction"}')

        # Act & Assert
        try:
            transaction_validation.validate_transaction(message, db)
            self.fail("Expected an error but none was raised")
        except transaction_validation.InvalidTransaction as e:
            self.assertIn("Could not find", str(e))

    def test_validateTransaction_invalidIndex_shouldRaiseError(self):
        # Arrange
        db = Mock(plyvel.DB)
        db.get.return_value = (b'{"height":0,"outputs":[{"pubkey":"a2ba5aebc27d7ffb476e45cdef00146eaabc261'
                               b'4eeb0b3a878541d96605e5a52","value":50000000000}],"type":"transaction"}')

        message = json.loads('{"inputs":[{"outpoint":{"index":2,"txid":"1bb37b637d07100cd26fc063dfd4c39a7931'
                             'cc88dae3417871219715a5e374af"},"sig":"1d0d7d774042607c69a87ac5f1cdf92bf474c25f'
                             'afcc089fe667602bfefb0494726c519e92266957429ced875256e6915eb8cea2ea66366e739415'
                             'efc47a6805"}],"outputs":[{"pubkey":"8dbcd2401c89c04d6e53c81c90aa0b'
                             '551cc8fc47c0469217c8f5cfbae1e911f9","value":10}],"type":"transaction"}')

        # Act & Assert
        try:
            transaction_validation.validate_transaction(message, db)
            self.fail("Expected an error but none was raised")
        except transaction_validation.InvalidTransaction as e:
            self.assertIn("index", str(e))

    def test_validateTransaction_outputGreaterInput_shouldRaiseError(self):
        # Arrange
        db = Mock(plyvel.DB)
        db.get.return_value = (b'{"height":0,"outputs":[{"pubkey":"344fd304e608eb462e733c4e5eb4eb7ae5fa28e05c15'
                               b'76b1fcf97d1a0aec5f7a","value":5}],"type":"transaction"}')

        message = json.loads('{"inputs":[{"outpoint":{"index":0,"txid":"1bb37b637d07100cd26fc063dfd4c39a7931cc88dae3417'
                             '871219715a5e374af"},"sig":"129493e34b72ff3f86b0e31d9e7f92b0adde10a201134c93de5564c543f6a5'
                             '116b3d0a1f71a85321e4a0c12ea4fb2c69003e5235b18729c6a6e49c74eb516003"}],"outputs":[{"pubkey":'
                             '"344fd304e608eb462e733c4e5eb4eb7ae5fa28e05c1576b1fcf97d1a0aec5f7a","value":10}],'
                             '"type":"transaction"}')

        # Act & Assert
        try:
            transaction_validation.validate_transaction(message, db)
            self.fail("Expected an error but none was raised")
        except transaction_validation.InvalidTransaction as e:
            self.assertIn("Sum of input values is smaller", str(e))

    # Schema validation tests

    def test_validateTransaction_coinbase_shouldBeValid(self):
        # Arrange
        db = Mock(plyvel.DB)
        message = json.loads('{"height":0,"outputs":[{"pubkey":"344fd304e608eb462e733c4e5eb4eb7ae5fa28e05c1576b1fcf97d1'
                             'a0aec5f7a","value":5}],"type":"transaction"}')

        # Act & Assert
        transaction_validation.validate_transaction(message, db)

    def test_validateTransaction_coinbase_pubKeyToShort_shouldRaiseError(self):
        # Arrange
        db = Mock(plyvel.DB)
        message = json.loads('{"height":0,"outputs":[{"pubkey":"344fd304e608eb462e733c4e5eb4eb7ae5fa28e05c1576b1fcf97d1'
                             'a0aec5f7","value":5}],"type":"transaction"}')

        # Act & Assert
        try:
            transaction_validation.validate_transaction(message, db)
            self.fail("Expected an error but none was raised")
        except transaction_validation.InvalidTransaction as e:
            self.assertIn("not well formed", str(e))

    def test_validateTransaction_coinbase_pubKeyToLong_shouldRaiseError(self):
        # Arrange
        db = Mock(plyvel.DB)
        message = json.loads('{"height":0,"outputs":[{"pubkey":"344fd304e608eb462e733c4e5eb4eb7ae5fa28e05c1576b1fcf97d1a'
                             '0aec5f777","value":5}],"type":"transaction"}')

        # Act & Assert
        try:
            transaction_validation.validate_transaction(message, db)
            self.fail("Expected an error but none was raised")
        except transaction_validation.InvalidTransaction as e:
            self.assertIn("not well formed", str(e))

    def test_validateTransaction_coinbase_missingHeight_shouldRaiseError(self):
        # Arrange
        db = Mock(plyvel.DB)
        message = json.loads('{"outputs":[{"pubkey":"344fd304e608eb462e733c4e5eb4eb7ae5fa28e05c1576b1fcf97d1a0aec5f777",'
                             '"value":5}],"type":"transaction"}')

        # Act & Assert
        try:
            transaction_validation.validate_transaction(message, db)
            self.fail("Expected an error but none was raised")
        except transaction_validation.InvalidTransaction as e:
            self.assertIn("not well formed", str(e))

    def test_validateTransaction_coinbase_missingType_shouldRaiseError(self):
        # Arrange
        db = Mock(plyvel.DB)
        message = json.loads('{"height":0,"outputs":[{"pubkey":"344fd304e608eb462e733c4e5eb4eb7ae5fa28e05c1576b1fcf97d1'
                             'a0aec5f777","value":5}]}')

        # Act & Assert
        try:
            transaction_validation.validate_transaction(message, db)
            self.fail("Expected an error but none was raised")
        except transaction_validation.InvalidTransaction as e:
            self.assertIn("not well formed", str(e))

    def test_validateTransaction_coinbase_negativeValue_shouldRaiseError(self):
        # Arrange
        db = Mock(plyvel.DB)
        message = json.loads('{"height":0,"outputs":[{"pubkey":"344fd304e608eb462e733c4e5eb4eb7ae5fa28e05c1576b1fcf97d1a'
                             '0aec5f7a","value":-5}],"type":"transaction"}')

        # Act & Assert
        try:
            transaction_validation.validate_transaction(message, db)
            self.fail("Expected an error but none was raised")
        except transaction_validation.InvalidTransaction as e:
            self.assertIn("not well formed", str(e))

    def test_validateTransaction_tx_missingType_shouldRaiseError(self):
        # Arrange
        db = Mock(plyvel.DB)
        message = json.loads('{"inputs":[{"outpoint":{"index":0,"txid":'
                             '"1bb37b637d07100cd26fc063dfd4c39a7931cc88dae3417871219715a5e374af"},"sig":'
                             '"1d0d7d774042607c69a87ac5f1cdf92bf474c25fafcc089fe667602bfefb049472'
                             '6c519e92266957429ced875256e6915eb8cea2ea66366e739415efc47a6805"}],'
                             '"outputs":[{"pubkey":"8dbcd2401c89c04d6e53c81c90aa0b551cc8fc47c0469217c8f5'
                             'cfbae1e911f9","value":10}]}')
        # Act & Assert
        try:
            transaction_validation.validate_transaction(message, db)
            self.fail("Expected an error but none was raised")
        except transaction_validation.InvalidTransaction as e:
            self.assertIn("not well formed", str(e))

    def test_validateTransaction_tx_negativeValue_shouldRaiseError(self):
        # Arrange
        db = Mock(plyvel.DB)
        message = json.loads('{"inputs":[{"outpoint":{"index":0,"txid":'
                             '"1bb37b637d07100cd26fc063dfd4c39a7931cc88dae3417871219715a5e374af"},"sig":'
                             '"1d0d7d774042607c69a87ac5f1cdf92bf474c25fafcc089fe667602bfefb049472'
                             '6c519e92266957429ced875256e6915eb8cea2ea66366e739415efc47a6805"}],'
                             '"outputs":[{"pubkey":"8dbcd2401c89c04d6e53c81c90aa0b551cc8fc47c0469217c8f5'
                             'cfbae1e911f9","value":-10}],"type":"transaction"}')
        # Act & Assert
        try:
            transaction_validation.validate_transaction(message, db)
            self.fail("Expected an error but none was raised")
        except transaction_validation.InvalidTransaction as e:
            self.assertIn("not well formed", str(e))

    def test_validateTransaction_tx_negativeIndex_shouldRaiseError(self):
        # Arrange
        db = Mock(plyvel.DB)
        message = json.loads('{"inputs":[{"outpoint":{"index":-1,"txid":'
                             '"1bb37b637d07100cd26fc063dfd4c39a7931cc88dae3417871219715a5e374af"},"sig":'
                             '"1d0d7d774042607c69a87ac5f1cdf92bf474c25fafcc089fe667602bfefb049472'
                             '6c519e92266957429ced875256e6915eb8cea2ea66366e739415efc47a6805"}],'
                             '"outputs":[{"pubkey":"8dbcd2401c89c04d6e53c81c90aa0b551cc8fc47c0469217c8f5'
                             'cfbae1e911f9","value":10}],"type":"transaction"}')
        # Act & Assert
        try:
            transaction_validation.validate_transaction(message, db)
            self.fail("Expected an error but none was raised")
        except transaction_validation.InvalidTransaction as e:
            self.assertIn("not well formed", str(e))

    def test_validateTransaction_tx_signatureToShort_shouldRaiseError(self):
        # Arrange
        db = Mock(plyvel.DB)
        message = json.loads('{"inputs":[{"outpoint":{"index":0,"txid":'
                             '"1bb37b637d07100cd26fc063dfd4c39a7931cc88dae3417871219715a5e374af"},"sig":'
                             '"1d0d7d774042607c69a87ac5f1cdf92bf474c25fafcc089fe667602bfefb049472'
                             '6c519e92266957429ced875256e6915eb8cea2ea66366e739415efc47a680"}],'
                             '"outputs":[{"pubkey":"8dbcd2401c89c04d6e53c81c90aa0b551cc8fc47c0469217c8f5'
                             'cfbae1e911f9","value":10}],"type":"transaction"}')
        # Act & Assert
        try:
            transaction_validation.validate_transaction(message, db)
            self.fail("Expected an error but none was raised")
        except transaction_validation.InvalidTransaction as e:
            self.assertIn("not well formed", str(e))

    def test_validateTransaction_tx_signatureToLong_shouldRaiseError(self):
        # Arrange
        db = Mock(plyvel.DB)
        message = json.loads('{"inputs":[{"outpoint":{"index":0,"txid":'
                             '"1bb37b637d07100cd26fc063dfd4c39a7931cc88dae3417871219715a5e374af"},"sig":'
                             '"1d0d7d774042607c69a87ac5f1cdf92bf474c25fafcc089fe667602bfefb049472'
                             '6c519e92266957429ced875256e6915eb8cea2ea66366e739415efc47a68056"}],'
                             '"outputs":[{"pubkey":"8dbcd2401c89c04d6e53c81c90aa0b551cc8fc47c0469217c8f5'
                             'cfbae1e911f9","value":10}],"type":"transaction"}')
        # Act & Assert
        try:
            transaction_validation.validate_transaction(message, db)
            self.fail("Expected an error but none was raised")
        except transaction_validation.InvalidTransaction as e:
            self.assertIn("not well formed", str(e))

    def test_validateTransaction_tx_signature_invalidHex_shouldRaiseError(self):
        # Arrange
        db = Mock(plyvel.DB)
        message = json.loads('{"inputs":[{"outpoint":{"index":0,"txid":'
                             '"1bb37b637d07100cd26fc063dfd4c39a7931cc88dae3417871219715a5e374af"},"sig":'
                             '"1d0d7d774042607c69a87ac5f1cdfg2bf474c25fafcc089fe667602bfefb049472'
                             '6c519e92266957429ced875256e6915eb8cea2ea66366e739415efc47a6805"}],'
                             '"outputs":[{"pubkey":"8dbcd2401c89c04d6e53c81c90aa0b551cc8fc47c0469217c8f5'
                             'cfbae1e911f9","value":10}],"type":"transaction"}')
        # Act & Assert
        try:
            transaction_validation.validate_transaction(message, db)
            self.fail("Expected an error but none was raised")
        except transaction_validation.InvalidTransaction as e:
            self.assertIn("not well formed", str(e))

    def test_validateTransaction_tx_missingInputs_shouldRaiseError(self):
        # Arrange
        db = Mock(plyvel.DB)
        message = json.loads('{"outputs":[{"pubkey":"8dbcd2401c89c04d6e53c81c90aa0b551cc8fc47c0469217c8f5'
                             'cfbae1e911f9","value":10}],"type":"transaction"}')
        # Act & Assert
        try:
            transaction_validation.validate_transaction(message, db)
            self.fail("Expected an error but none was raised")
        except transaction_validation.InvalidTransaction as e:
            self.assertIn("not well formed", str(e))

    def test_validateTransaction_tx_missingOutputs_shouldRaiseError(self):
        # Arrange
        db = Mock(plyvel.DB)
        message = json.loads('{"inputs":[{"outpoint":{"index":0,"txid":'
                             '"1bb37b637d07100cd26fc063dfd4c39a7931cc88dae3417871219715a5e374af"},"sig":'
                             '"1d0d7d774042607c69a87ac5f1cdf92bf474c25fafcc089fe667602bfefb049472'
                             '6c519e92266957429ced875256e6915eb8cea2ea66366e739415efc47a6805"}],'
                             '"type":"transaction"}')
        # Act & Assert
        try:
            transaction_validation.validate_transaction(message, db)
            self.fail("Expected an error but none was raised")
        except transaction_validation.InvalidTransaction as e:
            self.assertIn("not well formed", str(e))

    def test_validateTransaction_tx_outpoint_pubKeyToShort_shouldRaiseError(self):
        # Arrange
        db = Mock(plyvel.DB)
        message = json.loads('{"inputs":[{"outpoint":{"index":0,"txid":'
                             '"1bb37b637d07100cd26fc063dfd4c39a7931cc88dae3417871219715a5e374a"},"sig":'
                             '"1d0d7d774042607c69a87ac5f1cdf92bf474c25fafcc089fe667602bfefb049472'
                             '6c519e92266957429ced875256e6915eb8cea2ea66366e739415efc47a6805"}],'
                             '"outputs":[{"pubkey":"8dbcd2401c89c04d6e53c81c90aa0b551cc8fc47c0469217c8f5'
                             'cfbae1e911f9","value":10}],"type":"transaction"}')
        # Act & Assert
        try:
            transaction_validation.validate_transaction(message, db)
            self.fail("Expected an error but none was raised")
        except transaction_validation.InvalidTransaction as e:
            self.assertIn("not well formed", str(e))

    def test_validateTransaction_tx_outpoint_pubKeyToLong_shouldRaiseError(self):
        # Arrange
        db = Mock(plyvel.DB)
        message = json.loads('{"inputs":[{"outpoint":{"index":0,"txid":'
                             '"1bb37b637d07100cd26fc063dfd4c39a7931cc88dae3417871219715a5e374afa"},"sig":'
                             '"1d0d7d774042607c69a87ac5f1cdf92bf474c25fafcc089fe667602bfefb049472'
                             '6c519e92266957429ced875256e6915eb8cea2ea66366e739415efc47a6805"}],'
                             '"outputs":[{"pubkey":"8dbcd2401c89c04d6e53c81c90aa0b551cc8fc47c0469217c8f5'
                             'cfbae1e911f9","value":10}],"type":"transaction"}')
        # Act & Assert
        try:
            transaction_validation.validate_transaction(message, db)
            self.fail("Expected an error but none was raised")
        except transaction_validation.InvalidTransaction as e:
            self.assertIn("not well formed", str(e))

    def test_validateTransaction_tx_outputs_pubKeyToShort_shouldRaiseError(self):
        # Arrange
        db = Mock(plyvel.DB)
        message = json.loads('{"inputs":[{"outpoint":{"index":0,"txid":'
                             '"1bb37b637d07100cd26fc063dfd4c39a7931cc88dae3417871219715a5e374af"},"sig":'
                             '"1d0d7d774042607c69a87ac5f1cdf92bf474c25fafcc089fe667602bfefb049472'
                             '6c519e92266957429ced875256e6915eb8cea2ea66366e739415efc47a6805"}],'
                             '"outputs":[{"pubkey":"8dbcd2401c89c04d6e53c81c90aa0b551cc8fc47c0469217c8f'
                             'cfbae1e911f9","value":10}],"type":"transaction"}')
        # Act & Assert
        try:
            transaction_validation.validate_transaction(message, db)
            self.fail("Expected an error but none was raised")
        except transaction_validation.InvalidTransaction as e:
            self.assertIn("not well formed", str(e))

    def test_validateTransaction_tx_outputs_pubKeyToLong_shouldRaiseError(self):
        # Arrange
        db = Mock(plyvel.DB)
        message = json.loads('{"inputs":[{"outpoint":{"index":0,"txid":'
                             '"1bb37b637d07100cd26fc063dfd4c39a7931cc88dae3417871219715a5e374af"},"sig":'
                             '"1d0d7d774042607c69a87ac5f1cdf92bf474c25fafcc089fe667602bfefb049472'
                             '6c519e92266957429ced875256e6915eb8cea2ea66366e739415efc47a6805"}],'
                             '"outputs":[{"pubkey":"8dbcd2401c89c04d6e53c81c90aa0b551cc8fc47c0469217c8f5a'
                             'cfbae1e911f9","value":10}],"type":"transaction"}')
        # Act & Assert
        try:
            transaction_validation.validate_transaction(message, db)
            self.fail("Expected an error but none was raised")
        except transaction_validation.InvalidTransaction as e:
            self.assertIn("not well formed", str(e))

    def test_validateTransaction_tx_outputs_pubKeyInvalidHex_shouldRaiseError(self):
        # Arrange
        db = Mock(plyvel.DB)
        message = json.loads('{"inputs":[{"outpoint":{"index":0,"txid":'
                             '"1bb37b637d07100cd26fc063dfd4c39a7931cc88dae3417871219715a5e374af"},"sig":'
                             '"1d0d7d774042607c69a87ac5f1cdf92bf474c25fafcc089fe667602bfefb049472'
                             '6c519e92266957429ced875256e6915eb8cea2ea66366e739415efc47a6805"}],'
                             '"outputs":[{"pubkey":"8dbcd2401c89c04d6e53c81c90aa0b551cc8fc47c0469217c8fg'
                             'cfbae1e911f9","value":10}],"type":"transaction"}')
        # Act & Assert
        try:
            transaction_validation.validate_transaction(message, db)
            self.fail("Expected an error but none was raised")
        except transaction_validation.InvalidTransaction as e:
            self.assertIn("not well formed", str(e))
