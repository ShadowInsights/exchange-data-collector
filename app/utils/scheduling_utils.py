import asyncio
import logging
from typing import Any, Callable, Coroutine


def set_interval(
    seconds: float,
) -> Callable[
    [Callable[..., Coroutine[Any, Any, None]]],
    Callable[..., Coroutine[Any, Any, None]],
]:
    def decorator(
        func: Callable[..., Coroutine[Any, Any, None]]
    ) -> Callable[..., Coroutine[Any, Any, None]]:
        async def wrapper(*args: Any, **kwargs: Any) -> None:
            while True:
                try:
                    await asyncio.sleep(seconds)
                    await func(*args, **kwargs)
                except Exception as e:
                    logging.exception(
                        "An error occurred in the periodic task.", exc_info=e
                    )

        return wrapper

    return decorator
