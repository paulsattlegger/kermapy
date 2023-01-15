import asyncio
import json
import logging
import time

from jsonschema.exceptions import ValidationError
from jsonschema.validators import validate

from org.webpki.json.Canonicalize import canonicalize
from . import config, messages, objects, peers, schemas, transaction_validation, utxo, mempool


class ProtocolError(Exception):
    pass


class TaskError(Exception):
    pass


class Connection:
    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter, incoming: bool) -> None:
        self._reader: asyncio.StreamReader = reader
        self._writer: asyncio.StreamWriter = writer
        self.incoming: bool = incoming
        self.peer_name: str = "{}:{}".format(
            *writer.get_extra_info("peername"))
        logging.info(
            f"Established connection {'from' if incoming else 'to'} {self.peer_name}")

    async def close(self) -> None:
        logging.info(
            f"Closing the connection {'from' if self.incoming else 'to'} {self.peer_name}")
        try:
            self._writer.close()
            await self._writer.wait_closed()
        except ConnectionError as e:
            logging.debug(e)

    async def write_message(self, message: dict) -> None:
        data = canonicalize(message) + b"\n"
        logging.debug(f"Sending {data!r} to {self.peer_name}")
        self._writer.write(data)
        await self._writer.drain()

    async def write_error(self, error: str) -> None:
        await self.write_message({
            "type": "error",
            "error": error
        })

    async def read_message(self) -> dict:
        data = await self._reader.readuntil()
        logging.debug(f"Received {data!r} from {self.peer_name}")
        return json.loads(data)


class Node:
    def __init__(self, listen_addr: str, storage_path: str, timeout: float = 300) -> None:
        self._server = None
        self._listen_addr: str = listen_addr
        self._peers: peers.Peers = peers.Peers(storage_path)
        self._connections: set[Connection] = set()
        self._client_conn_sem: asyncio.Semaphore = asyncio.Semaphore(
            config.CLIENT_CONNECTIONS)
        self._background_tasks: set = set()
        self._objs: objects.Objects = objects.Objects(storage_path)
        self._timeout = timeout
        self._mempool = mempool.Mempool(self._objs)
        self._mempool.init()

    async def start_server(self):
        self._server = await asyncio.start_server(self.handle_connection, *self._listen_addr.rsplit(":", 1),
                                                  limit=config.BUFFER_SIZE)

        addrs = ", ".join(str(sock.getsockname())
                          for sock in self._server.sockets)
        logging.info(f"Serving on {addrs}")

    async def serve(self) -> None:
        try:
            async with self._server:
                await self._server.serve_forever()
        finally:
            await self.shutdown()

    async def shutdown(self):
        self._objs.close()
        if self._server:
            self._server.close()
        for background_task in self._background_tasks:
            background_task.cancel()
        await asyncio.gather(*self._background_tasks)

    def peer_discovery(self) -> None:
        for peer in self._peers:
            task = asyncio.create_task(self.connect(peer))
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)

    def broadcast(self, message: dict) -> None:
        for connection in self._connections:
            task = asyncio.create_task(connection.write_message(message))
            self._background_tasks.add(task)
            task.add_done_callback(self._background_tasks.discard)

    async def connect(self, peer: str) -> None:
        async with self._client_conn_sem:
            if peer in {c.peer_name for c in self._connections}:
                logging.info(f"Already connected to {peer}")
                return
            try:
                logging.info(f"Connecting to {peer}")
                reader, writer = await asyncio.open_connection(*peer.rsplit(":", 1), limit=config.BUFFER_SIZE)
            except OSError as e:
                logging.error(f"Failed connecting to {peer}: {e}")
                return
            await self.handle_connection(reader, writer, False)

    async def handle_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter,
                                incoming=True) -> None:
        conn = Connection(reader, writer, incoming)
        try:
            async with asyncio.TaskGroup() as tg:
                try:
                    await conn.write_message(messages.HELLO)
                    await conn.write_message(messages.GET_PEERS)
                    await conn.write_message(messages.GET_CHAINTIP)
                    await conn.write_message(messages.GET_MEMPOOL)
                    # Handshake
                    message = await conn.read_message()
                    validate(message, schemas.HELLO)
                    if message["type"] != "hello":
                        await conn.write_error(f"Received message {message} prior to 'hello'")
                        return
                    self._connections.add(conn)
                    logging.info(f"Completed handshake with {conn.peer_name}")
                    # Request-response loop
                    while True:
                        message = await conn.read_message()
                        validate(message, schemas.MESSAGE)
                        logging.info(f"Received message {message} from {conn.peer_name}")
                        tg.create_task(self.handle_message(message, conn))
                except (EOFError, ConnectionError) as e:
                    logging.debug(e)
                except ValueError as e:  # JSONDecodeError, UnicodeDecodeError
                    logging.error(
                        f"Unable to parse message from {conn.peer_name}: {e}")
                    await conn.write_error("Failed to parse incoming message as JSON")
                except ValidationError as e:
                    logging.error(
                        f"Unable to validate message from {conn.peer_name}: {e}")
                    await conn.write_error(f"Failed to validate incoming message: {e.message}")
        except* TaskError:
            pass
        finally:
            await conn.close()
            self._connections.discard(conn)

    async def handle_message(self, message: dict, conn: Connection):
        try:
            match message["type"]:
                case "getpeers":
                    await conn.write_message({
                        "type": "peers",
                        "peers": [peer for peer in self._peers]
                    })
                case "peers":
                    self._peers.add_all(message["peers"])
                    self._peers.dump()
                case "object":
                    obj = message["object"]
                    object_id = objects.Objects.id(obj)
                    if object_id not in self._objs:
                        if obj["type"] == "transaction":
                            self.validate_transaction(obj)
                            self._objs.put_object(obj)
                        elif obj["type"] == "block":
                            utxo_set = await self.validate_block(obj)

                            if obj["previd"]:
                                height = self._objs.height(obj["previd"]) + 1
                            else:
                                height = 0

                            new_chaintip = False
                            current_chaintip_id = self._objs.chaintip()

                            if not current_chaintip_id or self._objs.height(current_chaintip_id) < height:
                                new_chaintip = True

                            self._objs.put_block(obj, utxo_set, height, new_chaintip)

                            if new_chaintip:
                                self._mempool.handle_chaintip_change()
                        logging.info(
                            f"Saved object: {obj} with object ID: {object_id}")
                        self.broadcast({
                            "type": "ihaveobject",
                            "objectid": object_id
                        })
                    else:
                        logging.info(
                            f"Object: {obj} ignored, already in the database")
                case "ihaveobject":
                    object_id = message["objectid"]
                    if object_id in self._objs:
                        logging.info(
                            f"Object with object ID: {object_id} is already in the database")
                    else:
                        await conn.write_message({
                            "type": "getobject",
                            "objectid": object_id
                        })
                case "getobject":
                    object_id = message["objectid"]
                    if object_id in self._objs:
                        await conn.write_message({
                            "type": "object",
                            "object": self._objs.get(object_id)
                        })
                    else:
                        logging.info(
                            f"Object with object ID: {object_id} is not in the database")
                case "getchaintip":
                    block_id = self._objs.chaintip()
                    if block_id:
                        await conn.write_message({
                            "type": "chaintip",
                            "blockid": block_id
                        })
                    else:
                        logging.info("Received a 'getchaintip' message, even though no blocks have been stored yet")
                case "chaintip":
                    block_id = message["blockid"]
                    if block_id in self._objs:
                        logging.info(
                            f"Chaintip block with ID: {block_id} is already in the database")
                    else:
                        await conn.write_message({
                            "type": "getobject",
                            "objectid": block_id
                        })
                case "getmempool":
                    # Method for getting the mempool
                    if False:
                        await conn.write_message({
                            "type": "mempool",
                            "txids": []
                        })
                    else:
                        logging.info("Received a 'getmempool' message, even though no txids been in the mempool yet")
                case "mempool":
                    await self.get_objects(message["txids"])
                case "hello":
                    raise ProtocolError(
                        "Received a second 'hello' message, even though handshake is completed")
        except ProtocolError as e:
            logging.error(
                f"Unable to handle message from {conn.peer_name}: {e}")
            await conn.write_error(str(e))
            raise TaskError

    def validate_transaction(self, transaction: dict) -> transaction_validation.TransactionMetadata:
        try:
            return transaction_validation.validate_transaction(
                transaction, self._objs)
        except transaction_validation.InvalidTransaction as e:
            logging.warning("Found invalid tx")
            raise ProtocolError(str(e))

    async def resolve_object(self, object_id: str):
        event = self._objs.event_for(object_id)
        self.broadcast({
            "type": "getobject",
            "objectid": object_id
        })
        await asyncio.wait_for(event.wait(), self._timeout)

    async def get_object(self, object_id: str):
        if object_id in self._objs:
            return self._objs.get(object_id)
        await self.resolve_object(object_id)
        return self._objs.get(object_id)

    async def get_objects(self, object_ids: list[str]) -> list[dict]:
        unknown_objs = [obj_id for obj_id in object_ids if obj_id not in self._objs]
        await asyncio.gather(*[self.resolve_object(obj_id) for obj_id in unknown_objs])
        return [self._objs.get(obj_id) for obj_id in object_ids]

    async def validate_block(self, block: dict) -> dict:
        # Ensure the target is the one required
        if block["T"] != config.TARGET:
            raise ProtocolError("Received block with invalid target")
        # Check the proof-of-work
        block_id = objects.Objects.id(block)
        if int(block_id, base=16) >= int(block['T'], base=16):
            raise ProtocolError(
                "Received block does not satisfy the proof-of-work equation")
        # Check that for all the txids in the block, you have the corresponding transaction in your
        # local object database. If not, then send a "getobject" message to your peers in order
        # to get the transaction.
        try:
            txs = await self.get_objects(block["txids"])
        except asyncio.TimeoutError:
            raise ProtocolError("Received block contains transactions that could not be received")
        # Request your peers for the parent block
        if block["previd"]:
            if block["previd"] not in self._objs:
                try:
                    await self.resolve_object(block["previd"])
                except asyncio.TimeoutError:
                    raise ProtocolError("Received block which parent(-s) could not be received")
            # Check that the timestamp of each block (the created field) is later than that of its parent,...
            if self._objs.get(block["previd"])["created"] > block["created"]:
                raise ProtocolError("Received block with timestamp not later than of its parent")
        else:
            if block_id != config.GENESIS:
                raise ProtocolError("Received block which stops at a different genesis")
        # ... and earlier than the current time.
        if block["created"] > time.time():
            raise ProtocolError("Received block with timestamp in the future")
        # For each transaction in the block, check that the transaction is valid, and update UTXO set based on the
        # transaction
        not_coinbase_txs = [tx for tx in txs if "inputs" in tx]
        fees = 0
        for tx in not_coinbase_txs:
            metadata = self.validate_transaction(tx)
            fees += metadata.total_input_value - metadata.total_output_value
        # Create new utxo set and check for problems while creation
        try:
            utxo_set = utxo.create_utxo_set(block, self._objs)
        except utxo.UtxoError as e:
            logging.warning("UTXO check was not successful")
            raise ProtocolError(
                str(e))
        # Check for coinbase transactions, there can be at most one coinbase transaction in a block
        coinbase_txs = [tx for tx in txs if "inputs" not in tx]
        if len(coinbase_txs) > 1:
            raise ProtocolError(
                "Received block contains more than one coinbase transaction")
        if len(coinbase_txs) == 1:
            coinbase_txid = objects.Objects.id(coinbase_txs[0])
            if block["txids"][0] != coinbase_txid:
                raise ProtocolError(
                    "Received block with coinbase transaction not at index 0")
            # Check the coinbase transaction cannot be spent in another transaction in the same block (this is in order
            # to make the law of conservation for the coinbase transaction easier to verify).
            for tx in not_coinbase_txs:
                for inpt in tx["inputs"]:
                    txid = inpt["outpoint"]["txid"]
                    if txid == coinbase_txid:
                        raise ProtocolError("Received block with coinbase transaction spend in another transaction")
            # Check that the height in the coinbase transaction matches the height of the block the transaction is
            # contained in.
            if coinbase_txs[0]["height"] != self._objs.height(block["previd"]) + 1:
                raise ProtocolError("Received block with coinbase transaction height does not match block height")
            # Check the coinbase transaction has no outputs that exceed the block rewards and the fees.
            outputs = sum(output["value"] for output in coinbase_txs[0]["outputs"])
            if outputs > config.BLOCK_REWARD + fees:
                raise ProtocolError("Received block with coinbase transaction that exceed block rewards and the fees")
        return utxo_set
