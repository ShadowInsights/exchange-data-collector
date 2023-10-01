import asyncio
import logging
from abc import ABC, abstractmethod


def set_interval(seconds):
    def decorator(func):
        async def wrapper(*args, **kwargs):
            while True:
                await asyncio.sleep(seconds)
                await func(*args, **kwargs)

        return wrapper

    return decorator


class Worker(ABC):

    @abstractmethod
    async def run(self):
        pass


class DbWorker(Worker):

    @set_interval(5)
    async def run(self):
        logging.info("TEST")
