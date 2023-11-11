import asyncio
from unittest.mock import AsyncMock, Mock, patch

from app.utils.scheduling_utils import SetInterval


class Counter:
    def __init__(self):
        self.counter = 0

    @SetInterval(10)
    async def func(self, callback_event: asyncio.Event = None):
        self.counter += 1
        callback_event.set()


@patch(
    "app.utils.scheduling_utils.get_current_time",
)
@patch(
    "app.utils.scheduling_utils.SetInterval.get_is_interrupted",
)
@patch("app.utils.scheduling_utils.asyncio.sleep", new_callable=AsyncMock)
async def test_is_fast_executed_function_invoked_n_times_in_specified_interval(
    mock_sleep: AsyncMock,
    mock_get_is_interrupted: Mock,
    mock_get_current_time: Mock,
):
    expected_call_counts = 2
    expected_call = [False] * expected_call_counts + [True]
    sequence_response = [0, 7]
    mock_get_is_interrupted.side_effect = expected_call
    mock_get_current_time.side_effect = (
        sequence_response * expected_call_counts
    )
    counter_obj = Counter()
    await counter_obj.func()

    assert counter_obj.counter == expected_call_counts


@patch(
    "app.utils.scheduling_utils.get_current_time",
)
@patch(
    "app.utils.scheduling_utils.SetInterval.get_is_interrupted",
)
@patch("app.utils.scheduling_utils.asyncio.sleep", new_callable=AsyncMock)
async def test_is_long_executed_function_invoked_n_times_in_specified_interval(
    mock_sleep: AsyncMock,
    mock_get_is_interrupted: Mock,
    mock_get_current_time: Mock,
):
    expected_call_counts = 1
    expected_call = [False] * expected_call_counts + [True]
    sequence_response = [0, 23]
    mock_get_is_interrupted.side_effect = expected_call
    mock_get_current_time.side_effect = (
        sequence_response * expected_call_counts
    )
    counter_obj = Counter()
    await counter_obj.func()

    assert counter_obj.counter == expected_call_counts
