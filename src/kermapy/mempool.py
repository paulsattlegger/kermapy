import logging
from abc import ABC, abstractmethod
from enum import Enum
from typing import List

from . import objects
from . import utxo


class MempoolState(Enum):
    MEMPOOL = 1
    CHAIN = 2


class MempoolTxStorage(ABC):
    @abstractmethod
    def put(self, tx_id: str, state: MempoolState) -> None:
        pass

    @abstractmethod
    def remove(self, tx_id: str) -> None:
        pass

    @abstractmethod
    def contains(self, tx_id: str) -> bool:
        pass

    @abstractmethod
    def get(self, tx_id: str) -> MempoolState | None:
        pass

    @abstractmethod
    def get_all(self) -> List[str]:
        pass

    @abstractmethod
    def get_all_with_filter(self, state: MempoolState):
        pass


class LocalMempoolTxStorage(MempoolTxStorage):
    def __init__(self) -> None:
        self._tx = dict()

    def put(self, tx_id: str, state: MempoolState) -> None:
        self._tx[tx_id] = state

    def remove(self, tx_id: str) -> None:
        del self._tx[tx_id]

    def contains(self, tx_id: str) -> bool:
        if tx_id in self._tx:
            return True
        else:
            return False

    def get(self, tx_id: str) -> MempoolState | None:
        if self.contains(tx_id):
            return self._tx[tx_id]
        else:
            return None

    def get_all(self) -> List[str]:
        return list(self._tx.keys())

    def get_all_with_filter(self, state: MempoolState):
        return list(
            filter(lambda x: self._tx[x] == state, self.get_all())
        )


class Mempool:
    def __init__(self, objs: objects.Objects) -> None:
        self._chain_block_list: List[str] = []
        self._utxo_tmp = dict()
        self._chaintip_id = None
        self._height = None
        self._objs = objs
        self._storage: MempoolTxStorage = LocalMempoolTxStorage()

    def add_tx(self, tx_id: str) -> None:
        existing = self._storage.get(tx_id)

        if existing is not None:
            return

        try:
            utxo.adjust_utxo_set_add_transaction(self._utxo_tmp, tx_id, self._objs)
            self._storage.put(tx_id, MempoolState.MEMPOOL)
        except utxo.UtxoError:
            logging.warning(f"Rejected tx with id '{tx_id}' because of utxo error when adding tx")

    def init(self) -> None:
        try:
            self._chaintip_id = self._objs.chaintip()

            # Nothing there yet
            if self._chaintip_id is None:
                self._height = -1
                return

            self._chain_block_list.clear()
            self._utxo_tmp = self._objs.utxo(self._chaintip_id)

            self._height = self._objs.height(self._chaintip_id)

            block_id = self._chaintip_id

            # Add all transactions of chain to mempool
            while block_id is not None:
                block = self._objs.get(block_id)
                tx_ids = block["txids"]

                for tx_id in tx_ids:
                    self._storage.put(tx_id, MempoolState.CHAIN)

                self._chain_block_list.append(block_id)

                block_id = block["previd"]

        except KeyError:
            pass

    def handle_chaintip_change(self):
        new_chaintip_id = self._objs.chaintip()
        new_height = self._objs.height(new_chaintip_id)

        new_chaintip = self._objs.get(new_chaintip_id)

        # check if just a block was appended to the existing chain (no fork)
        if new_chaintip["previd"] == self._chaintip_id and (new_height - 1) == self._height:
            tx_ids = new_chaintip["txids"]

            for tx_id in tx_ids:
                self._storage.put(tx_id, MempoolState.CHAIN)

            self._utxo_tmp = self._objs.utxo(new_chaintip_id)

            for tx_id in self._storage.get_all_with_filter(MempoolState.MEMPOOL):
                utxo.adjust_utxo_set_add_transaction(self._utxo_tmp, tx_id, self._objs)

            self._chaintip_id = new_chaintip_id
            self._height = new_height
            self._chain_block_list.insert(0, new_chaintip_id)
        # fork it is
        else:
            txs_to_move_to_mempool: List[str] = []

            new_chaintip_id = self._objs.chaintip()
            new_chaintip = self._objs.get(new_chaintip_id)

            shared_block_id = new_chaintip["previd"]

            # Find shared block by both chains
            while shared_block_id is not None and shared_block_id not in self._chain_block_list:
                shared_block_id = self._objs.get(shared_block_id)["previd"]

            old_chaintip = self._objs.get(self._chaintip_id)
            txs_to_move_to_mempool.extend(old_chaintip["txids"])

            prev_block_id = old_chaintip["previd"]

            # Mark transactions to be removed up to the shared block
            while prev_block_id != shared_block_id:
                prev_block = self._objs.get(prev_block_id)
                txs_to_move_to_mempool.extend(prev_block["txids"])
                prev_block_id = prev_block["previd"]

            for tx_id in txs_to_move_to_mempool:
                tx = self._objs.get(tx_id)

                # is coinbase tx
                if "height" in tx:
                    self._storage.remove(tx_id)
                else:
                    self._storage.put(tx_id, MempoolState.MEMPOOL)

            # can be optimized to not start from scratch
            self.init()

            for tx_id in self._storage.get_all_with_filter(MempoolState.MEMPOOL):
                try:
                    utxo.adjust_utxo_set_add_transaction(self._utxo_tmp, tx_id, self._objs)
                except utxo.UtxoError:
                    self._storage.remove(tx_id)

    def get_pending(self) -> List[str]:
        return self._storage.get_all_with_filter(MempoolState.MEMPOOL)
