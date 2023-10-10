import time as t
from datetime import datetime, time


class TradingSession:
    def __init__(self, start_time: time, end_time: time):
        self.start_time = start_time
        self.end_time = end_time

    def is_time_inside(self, current_time: datetime) -> bool:
        # Check only the hour and minute, ignore the date
        current_time_only = current_time.time()
        return self.start_time <= current_time_only <= self.end_time


TOKYO_TRADING_SESSION = TradingSession(
    start_time=time(0, 0), end_time=time(9, 0)
)
LONDON_TRADING_SESSION = TradingSession(
    start_time=time(8, 0), end_time=time(16, 0)
)
NEW_YORK_TRADING_SESSION = TradingSession(
    start_time=time(13, 0), end_time=time(22, 0)
)


def is_current_time_inside_trading_sessions(
    trading_sessions: list[TradingSession],
) -> bool:
    current_time = datetime.utcnow()

    # Ignore weekends
    if current_time.weekday() >= 5:  # 5 is Saturday, 6 is Sunday
        return False

    for trading_session in trading_sessions:
        if trading_session.is_time_inside(current_time):
            return True

    return False


def get_current_time() -> float:
    return t.time()
