import asyncio
import logging

from src.kermapy import client
from src.kermapy import server

background_tasks = set()


async def main():
    server_task = asyncio.create_task(server.main())
    client_task = asyncio.create_task(client.main())

    # Add task to the set. This creates a strong reference.
    background_tasks.add(server_task)
    background_tasks.add(client_task)

    # To prevent keeping references to finished tasks forever,
    # make each task remove its own reference from the set after
    # completion:
    server_task.add_done_callback(background_tasks.discard)
    client_task.add_done_callback(background_tasks.discard)

    await server_task
    await client_task


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    asyncio.run(main())
