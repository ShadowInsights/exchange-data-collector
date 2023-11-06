import asyncio
import logging
from datetime import datetime
from typing import Any, Callable, Coroutine


def set_interval(
        interval_time: float,
) -> Callable[
    [Callable[..., Coroutine[Any, Any, None]]],
    Callable[..., Coroutine[Any, Any, None]],
]:
    def decorator(
            func: Callable[..., Coroutine[Any, Any, None]]
    ) -> Callable[..., Coroutine[Any, Any, None]]:
        async def wrapper(*args: Any, **kwargs: Any) -> None:
            while True:
                logging.debug("Worker function cycle started")

                callback_event = asyncio.Event()
                kwargs["callback_event"] = callback_event

                start_time = datetime.now()

                task = asyncio.create_task(func(*args, **kwargs))
                await callback_event.wait()

                time_spent = (datetime.now() - start_time).total_seconds()

                await task
                callback_event.clear()

                if time_spent < interval_time:
                    await asyncio.sleep(interval_time - time_spent)
                else:
                    logging.warn(f"Active work took longer than the interval time: {time_spent} seconds")

        return wrapper

    return decorator
