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
        db.get.return_value = b"{\"height\":0,\"outputs\":[{\"pubkey\":\"8dbcd2401c89c04d6e53c81c90aa0b551cc8fc47c0469217c8f5cfbae1e911f9\",\"value\":50000000000}],\"type\":\"transaction\"}"

        message = json.loads("{\"transaction\":{\"inputs\":[{\"outpoint\":{\"index\":0,\"txid\":\"1bb37b637d07100cd26fc063dfd4c39a7931cc88dae3417871219715a5e374af\"},\"sig\":" +
                             "\"1d0d7d774042607c69a87ac5f1cdf92bf474c25fafcc089fe667602bfefb0494726c519e92266957429ced875256e6915eb8cea2ea66366e739415efc47a6805\"}]," +
                             "\"outputs\":[{\"pubkey\":\"8dbcd2401c89c04d6e53c81c90aa0b551cc8fc47c0469217c8f5cfbae1e911f9\",\"value\":10}],\"type\":\"transaction\"},\"type\":\"object\"}")

        # Act & Assert
        try:
            transaction_validation.validate_transaction(message, db)
        except:
            self.fail("An exception was thrown")

    def test_validateTransaction_invalidSignature_shouldRaiseError(self):
        # Arrange
        db = Mock(plyvel.DB)
        db.get.return_value = b"{\"height\":0,\"outputs\":[{\"pubkey\":\"8dbcd2401c89c04d6e53c81c90aa0b551cc8fc47c0469217c8f5cfbae1e911f9\",\"value\":50000000000}],\"type\":\"transaction\"}"

        message = json.loads("{\"transaction\":{\"inputs\":[{\"outpoint\":{\"index\":0,\"txid\":\"1bb37b637d07100cd26fc063dfd4c39a7931cc88dae3417871219715a5e374af\"},\"sig\":" +
                             "\"8cad10c82c38411b89386adb399696e9df34478aa571326883f4a27f16fcdc3d4852d87a55571a9cca886b6fe7b47a4443177cb7f806ad071306307bfb4f480b\"}]," +
                             "\"outputs\":[{\"pubkey\":\"8dbcd2401c89c04d6e53c81c90aa0b551cc8fc47c0469217c8f5cfbae1e911f9\",\"value\":10}],\"type\":\"transaction\"},\"type\":\"object\"}")

        # Act & Assert
        try:
            transaction_validation.validate_transaction(message, db)
            self.fail("Expected an error but none was raised")
        except transaction_validation.InvalidTransaction:
            return
        except:
            self.fail("Wrong error was raised")

    def test_validateTransaction_invalidPubKey_shouldRaiseError(self):
        # Arrange
        db = Mock(plyvel.DB)
        db.get.return_value = b"{\"height\":0,\"outputs\":[{\"pubkey\":\"a2ba5aebc27d7ffb476e45cdef00146eaabc2614eeb0b3a878541d96605e5a52\",\"value\":50000000000}],\"type\":\"transaction\"}"

        message = json.loads("{\"transaction\":{\"inputs\":[{\"outpoint\":{\"index\":0,\"txid\":\"1bb37b637d07100cd26fc063dfd4c39a7931cc88dae3417871219715a5e374af\"},\"sig\":" +
                             "\"1d0d7d774042607c69a87ac5f1cdf92bf474c25fafcc089fe667602bfefb0494726c519e92266957429ced875256e6915eb8cea2ea66366e739415efc47a6805\"}]," +
                             "\"outputs\":[{\"pubkey\":\"8dbcd2401c89c04d6e53c81c90aa0b551cc8fc47c0469217c8f5cfbae1e911f9\",\"value\":10}],\"type\":\"transaction\"},\"type\":\"object\"}")

        # Act & Assert
        try:
            transaction_validation.validate_transaction(message, db)
            self.fail("Expected an error but none was raised")
        except transaction_validation.InvalidTransaction:
            return
        except:
            self.fail("Wrong error was raised")
