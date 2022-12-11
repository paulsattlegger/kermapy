import asyncio
import logging

from . import kermapy, config


async def main():
    await node.start_server()
    node.peer_discovery()
    await node.serve()


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    node = kermapy.Node(config.LISTEN_ADDR, config.STORAGE_PATH)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
