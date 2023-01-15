import objects
from abc import ABC, abstractmethod
from typing import List
from enum import Enum


class MempoolState(Enum):
    MEMPOOL = 1
    CHAIN = 2


class MempoolOpenTxStorage(ABC):
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


class LocalMempoolOpenTxStorage(MempoolOpenTxStorage):
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


class Mempool:
    def __init__(self, objs: objects.Objects) -> None:
        self._chaintip_id = None
        self._height = None
        self._objs = objs
        self._storage: MempoolOpenTxStorage = LocalMempoolOpenTxStorage()

    def add_tx(self, tx_id: str) -> None:
        # TODO tmp utxo handling
        existing = self._storage.get(tx_id)

        if existing is not None:
            pass

        self._storage.put(tx_id, MempoolState.MEMPOOL)

    def add_tx_from_block(self, tx_id: str) -> None:
        # TODO tmp utxo handling
        self._storage.put(tx_id, MempoolState.CHAIN)

    def init(self) -> None:
        try:
            self._chaintip_id = self._objs.chaintip()

            # Nothing there yet
            if self._chaintip_id is None:
                self._height = -1
                return

            self._height = self._objs.height(self._chaintip_id)

            chaintip = self._objs.get(self._chaintip_id)

            prev_block_id = chaintip["previd"]

            while prev_block_id is not None:
                tx_ids = chaintip["txids"]

                for tx_id in tx_ids:
                    self.add_tx_from_block(tx_id)

                prev_block_id = chaintip["previd"]

        except KeyError:
            pass

    def handle_chaintip_change(self):
        new_chaintip_id = self._objs.chaintip()
        new_height = self._objs.height(new_chaintip_id)

        new_chaintip = self._objs.get(self._chaintip_id)

        if new_chaintip["previd"] is self._chaintip_id and new_height - 1 is self._height:
            tx_ids = new_chaintip["txids"]

            for tx_id in tx_ids:
                self.add_tx_from_block(tx_id)

            self._chaintip_id = new_chaintip_id
            self._height = new_height
        else:
            # TODO handle chain switch
            pass

    def get_pending(self) -> List[str]:
        return self._storage.get_all()
