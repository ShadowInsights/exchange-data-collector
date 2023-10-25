import asyncio
import logging


def set_interval(seconds) -> callable:
    def decorator(func):
        async def wrapper(*args, **kwargs):
            while True:
                try:
                    await asyncio.sleep(seconds)
                    asyncio.create_task(func(*args, **kwargs))
                except Exception as e:
                    logging.exception(e)

        return wrapper

    return decorator
