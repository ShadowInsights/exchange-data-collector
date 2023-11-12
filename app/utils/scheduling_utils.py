import asyncio
import logging
from typing import Any, Callable, Coroutine

from app.utils.time_utils import get_current_time


class SetInterval:
    def __init__(self, interval_time: float):
        self.interval_time = interval_time
        self._is_interrupted = False

    def __call__(
        self, func: Callable[..., Coroutine[Any, Any, None]]
    ) -> Callable[..., Coroutine[Any, Any, None]]:
        async def wrapper(*args, **kwargs) -> None:
            while self.get_is_interrupted() is not True:
                try:
                    logging.debug("Worker function cycle started")

                    callback_event = asyncio.Event()

                    start_time = get_current_time()

                    task = asyncio.create_task(
                        func(*args, callback_event=callback_event, **kwargs)
                    )
                    await callback_event.wait()

                    time_spent = get_current_time() - start_time

                    callback_event.clear()

                    if time_spent < self.interval_time:
                        await asyncio.sleep(self.interval_time - time_spent)
                    else:
                        await task

                        logging.warn(
                            f"Active work took longer than the interval time: {time_spent} seconds"
                        )
                except Exception as err:
                    logging.exception(exc_info=err, msg="Error occurred")

        return wrapper

    def get_is_interrupted(self) -> bool:
        return self._is_interrupted
