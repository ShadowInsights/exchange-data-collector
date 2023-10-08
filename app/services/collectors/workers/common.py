import asyncio
import logging
from abc import ABC, abstractmethod


class Worker(ABC):
    @abstractmethod
    async def run(self):
        pass


def set_interval(seconds):
    def decorator(func):
        async def wrapper(*args, **kwargs):
            while True:
                try:
                    await asyncio.sleep(seconds)
                    await func(*args, **kwargs)
                except Exception as error:
                    logging.error(
                        f"Error was occurred while running job {error}"
                    )

        return wrapper

    return decorator
