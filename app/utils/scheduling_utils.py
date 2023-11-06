import asyncio
import logging
from datetime import datetime
from typing import Awaitable


def set_interval(interval_time: int):
    def decorator(func: Awaitable):
        async def wrapper(*args, **kwargs):
            while True:

                callback_event = asyncio.Event()
                logging.debug("Worker function cycle started")
                kwargs["callback_event"] = callback_event

                start_time = datetime.now()

                task = asyncio.create_task(func(*args, **kwargs))

                await callback_event.wait()

                # Calculate the elapsed time
                time_spent = (datetime.now() - start_time).total_seconds()

                await task
                callback_event.clear()
                # Sleep the remaining time of the interval, if necessary
                if time_spent < interval_time:
                    await asyncio.sleep(interval_time - time_spent)
                else:
                    logging.warn(f"Active work took longer than the interval time: {time_spent} seconds")

        return wrapper

    return decorator
