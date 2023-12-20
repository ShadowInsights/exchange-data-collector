from datetime import datetime
from datetime import datetime as original_datetime
from datetime import time
from typing import Callable
from unittest.mock import patch

from app.utilities.time_utils import (
    LONDON_TRADING_SESSION,
    NEW_YORK_TRADING_SESSION,
    TOKYO_TRADING_SESSION,
    TradingSession,
    get_current_time,
    is_current_time_inside_trading_sessions,
)


def test_trading_session() -> None:
    ts1 = TradingSession(time(10, 0), time(12, 0))
    assert ts1.is_time_inside(original_datetime(2022, 1, 1, 10, 30))
    assert not ts1.is_time_inside(original_datetime(2022, 1, 1, 9, 59))
    assert not ts1.is_time_inside(original_datetime(2022, 1, 1, 12, 1))


class MockDateTime:
    @classmethod
    def utcnow(cls) -> Callable[[], datetime]:
        return cls.mocked_utcnow()

    @staticmethod
    def time(*args: str, **kwargs: int) -> time:
        return original_datetime.time(*args, **kwargs)

    @staticmethod
    def datetime(*args: str, **kwargs: int) -> datetime:
        return original_datetime(*args, **kwargs)


@patch("app.utilities.time_utils.datetime", new=MockDateTime)
def test_is_current_time_inside_trading_sessions() -> None:
    MockDateTime.mocked_utcnow = lambda: original_datetime(2022, 1, 1, 1, 0)
    assert not is_current_time_inside_trading_sessions(
        [
            TOKYO_TRADING_SESSION,
            LONDON_TRADING_SESSION,
            NEW_YORK_TRADING_SESSION,
        ]
    )

    MockDateTime.mocked_utcnow = lambda: original_datetime(2022, 1, 3, 1, 0)
    assert is_current_time_inside_trading_sessions(
        [
            TOKYO_TRADING_SESSION,
            LONDON_TRADING_SESSION,
            NEW_YORK_TRADING_SESSION,
        ]
    )

    MockDateTime.mocked_utcnow = lambda: original_datetime(2022, 1, 3, 8, 30)
    assert is_current_time_inside_trading_sessions(
        [
            TOKYO_TRADING_SESSION,
            LONDON_TRADING_SESSION,
            NEW_YORK_TRADING_SESSION,
        ]
    )

    MockDateTime.mocked_utcnow = lambda: original_datetime(2022, 1, 3, 13, 30)
    assert is_current_time_inside_trading_sessions(
        [
            TOKYO_TRADING_SESSION,
            LONDON_TRADING_SESSION,
            NEW_YORK_TRADING_SESSION,
        ]
    )


def test_get_current_time() -> None:
    result = get_current_time()
    assert isinstance(result, float)
