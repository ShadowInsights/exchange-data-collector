import asyncio
import logging
from typing import Any, Callable, Coroutine

from app.utilities.time_utils import get_current_time


class SetInterval:
    def __init__(self, interval_time: float, name: str | None = None):
        self._interval_time = interval_time
        self._is_interrupted = False
        self._name = name

    def __call__(
        self, func: Callable[..., Coroutine[Any, Any, None]]
    ) -> Callable[..., Coroutine[Any, Any, None]]:
        async def wrapper(*args: str, **kwargs: int) -> None:
            await asyncio.sleep(self._interval_time)
            while not self.get_is_interrupted():
                try:
                    logging.debug("Worker function cycle started")

                    callback_event = asyncio.Event()
                    start_time = get_current_time()

                    asyncio.create_task(
                        func(*args, callback_event=callback_event, **kwargs)
                    )
                    await callback_event.wait()
                    callback_event.clear()

                    time_spent = get_current_time() - start_time
                    if time_spent < self._interval_time:
                        await asyncio.sleep(self._interval_time - time_spent)
                    else:
                        logging.warning(
                            f"Active work took longer than the interval time: {time_spent} seconds"
                            f" (interval time: {self._interval_time} seconds)"
                            f" (name: {self._name})"
                        )
                except Exception as err:
                    logging.exception(exc_info=err, msg="Error occurred")

        return wrapper

    def get_is_interrupted(self) -> bool:
        return self._is_interrupted
