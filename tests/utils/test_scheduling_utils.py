import asyncio
from unittest.mock import AsyncMock, Mock, patch

from app.utils.scheduling_utils import SetInterval


@SetInterval(5)
async def func(callback_event: asyncio.Event = None):
    if callback_event:
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
    max_call_counts = 200
    expected_call_counts = 12
    func_time = 3
    interval_time = 5
    tested_time = 59

    expected_call = [False] * max_call_counts + [True]
    time_sequence_response = [i // 2 * interval_time if i % 2 == 0 else (func_time + i // 2 * interval_time) \
                              for i in range(2 * max_call_counts)]

    mock_get_is_interrupted.side_effect = expected_call
    mock_get_current_time.side_effect = time_sequence_response

    assert time_sequence_response[(2 * (expected_call_counts - 1))] <= tested_time
    assert time_sequence_response[(2 * expected_call_counts)] >= tested_time


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
    max_call_counts = 200
    expected_call_counts = 8
    func_time = 8
    tested_time = 59

    expected_call = [False] * max_call_counts + [True]
    time_sequence_response = [i // 2 * func_time if i % 2 == 0 else (func_time + i // 2 * func_time) \
                              for i in range(2 * max_call_counts)]

    mock_get_is_interrupted.side_effect = expected_call
    mock_get_current_time.side_effect = time_sequence_response

    assert time_sequence_response[(2 * (expected_call_counts - 1))] <= tested_time
    assert time_sequence_response[(2 * expected_call_counts)] >= tested_time
