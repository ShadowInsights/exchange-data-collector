from decimal import Decimal
from typing import AsyncGenerator
from unittest.mock import AsyncMock, Mock, patch
from uuid import UUID

import pytest

from app.common.processor import Processor
from app.services.collectors.clients.schemas.common import OrderBookEvent
from app.services.collectors.common import Collector
from app.services.workers.volume_worker import VolumeWorker
from app.utils.event_utils import EventHandler


class MockCollector(Collector):
    def __init__(
        self,
        launch_id: UUID,
        pair_id: UUID,
        symbol: str,
        delimiter: Decimal,
    ):
        super().__init__(
            launch_id=launch_id,
            pair_id=pair_id,
            symbol=symbol,
            delimiter=delimiter,
        )

    async def _broadcast_stream(
        self,
    ) -> AsyncGenerator[OrderBookEvent | None, None]:
        pass


@pytest.fixture
def processor(collector: Collector) -> Processor:
    return Processor(
        launch_id=UUID("d8f4b7c5-5d9c-4b9c-8b3b-9c0c5d9f4b7c"),
        pair_id=UUID("d8f4b7c5-5d9c-4b9c-8b3b-9c0c5d9f4b7c"),
        event_handler=EventHandler(),
        symbol="BTC/USDT",
        delimiter=Decimal("0.1"),
        collector=collector,
    )


@pytest.fixture
def collector() -> Collector:
    return MockCollector(
        launch_id=UUID("d8f4b7c5-5d9c-4b9c-8b3b-9c0c5d9f4b7c"),
        pair_id=UUID("d8f4b7c5-5d9c-4b9c-8b3b-9c0c5d9f4b7c"),
        symbol="BTC/USDT",
        delimiter=Decimal("0.1"),
    )


@patch(
    "app.services.workers.volume_worker.VolumeDiscordMessenger.send_notification",
    new_callable=AsyncMock,
)
@patch(
    "app.services.workers.volume_worker.VolumeWorker._find_last_average_volumes"
)
@patch(
    "app.services.workers.volume_worker.VolumeWorker._find_last_bid_ask_ratio"
)
@patch(
    "app.services.workers.volume_worker.save_volume",
    new_callable=AsyncMock,
)
@patch("app.services.workers.volume_worker.calculate_avg_by_summary")
async def test_non_anomaly_anomaly(
    mock_calculate_avg_by_summary: Mock,
    mock_save_volume: AsyncMock,
    mock_find_last_bid_ask_ratio: Mock,
    mock_find_last_average_volumes: Mock,
    mock_volume_discord_messenger: AsyncMock,
    processor: Processor,
) -> None:
    expected_average_volume = 5000
    mock_find_last_average_volumes.return_value = [32, 16, 23231, 11, 0]
    mock_find_last_bid_ask_ratio.return_value = [
        0.10,
        0.15,
        0.00,
        -0.10,
        -0.20,
    ]

    volume_comparative_array_size = 5
    volume_anomaly_ratio = Decimal(2)

    mock_calculate_avg_by_summary.return_value = expected_average_volume

    worker = VolumeWorker(
        processor=processor,
        event_handler=EventHandler(),
        discord_messenger=mock_volume_discord_messenger,
        volume_comparative_array_size=volume_comparative_array_size,
        volume_anomaly_ratio=volume_anomaly_ratio,
    )

    await worker._run_worker()

    assert mock_save_volume.call_count == 1
    assert (
        mock_save_volume.call_args.kwargs["avg_volume"]
        == expected_average_volume
    )

    assert mock_volume_discord_messenger.send_notification.call_count == 0

    assert worker._summary_volume_per_interval == 0
    assert worker._volume_updates_counter_per_interval == 0

    assert worker._last_average_volumes == [
        16,
        23231,
        11,
        0,
        expected_average_volume,
    ]


@patch(
    "app.services.workers.volume_worker.VolumeDiscordMessenger.send_notification",
    new_callable=AsyncMock,
)
@patch(
    "app.services.workers.volume_worker.VolumeWorker._find_last_average_volumes"
)
@patch(
    "app.services.workers.volume_worker.VolumeWorker._find_last_bid_ask_ratio"
)
@patch(
    "app.services.workers.volume_worker.save_volume",
    new_callable=AsyncMock,
)
@patch("app.services.workers.volume_worker.calculate_avg_by_summary")
async def test_inflow_volume_anomaly_detection(
    mock_calculate_avg_by_summary: Mock,
    mock_save_volume: AsyncMock,
    mock_find_last_bid_ask_ratio: Mock,
    mock_find_last_average_volumes: Mock,
    mock_volume_discord_messenger: AsyncMock,
    processor: Processor,
) -> None:
    expected_average_volume = 40
    mock_find_last_average_volumes.return_value = [10, 20, 30]
    mock_find_last_bid_ask_ratio.return_value = [-0.10, 0.10, 0.00]

    volume_comparative_array_size = 3
    volume_anomaly_ratio = Decimal(2)

    mock_calculate_avg_by_summary.return_value = expected_average_volume

    worker = VolumeWorker(
        processor=processor,
        event_handler=EventHandler(),
        discord_messenger=mock_volume_discord_messenger,
        volume_comparative_array_size=volume_comparative_array_size,
        volume_anomaly_ratio=volume_anomaly_ratio,
    )

    await worker._run_worker()

    assert mock_save_volume.call_count == 1
    assert (
        mock_save_volume.call_args.kwargs["avg_volume"]
        == expected_average_volume
    )

    assert worker._summary_volume_per_interval == 0
    assert worker._volume_updates_counter_per_interval == 0

    expected_deviation = 2.0
    assert mock_volume_discord_messenger.send_notification.call_count == 1
    volume_anomaly_notification = (
        mock_volume_discord_messenger.send_notification.call_args[1]
    )
    print(mock_volume_discord_messenger.send_notification.call_args[1])
    expected_notification = {
        "pair_id": UUID("d8f4b7c5-5d9c-4b9c-8b3b-9c0c5d9f4b7c"),
        "deviation": expected_deviation,
        "current_bid_ask_ratio": 0.0,
        "previous_bid_ask_ratio": 0.0,
        "current_avg_volume": expected_average_volume,
        "previous_avg_volume": 20,
    }

    assert volume_anomaly_notification == expected_notification

    assert worker._last_average_volumes == [20, 30, expected_average_volume]


@patch(
    "app.services.workers.volume_worker.VolumeDiscordMessenger.send_notification",
    new_callable=AsyncMock,
)
@patch(
    "app.services.workers.volume_worker.VolumeWorker._find_last_average_volumes"
)
@patch(
    "app.services.workers.volume_worker.VolumeWorker._find_last_bid_ask_ratio"
)
@patch(
    "app.services.workers.volume_worker.save_volume",
    new_callable=AsyncMock,
)
@patch("app.services.workers.volume_worker.calculate_avg_by_summary")
async def test_outflow_volume_anomaly_detection(
    mock_calculate_avg_by_summary: Mock,
    mock_save_volume: AsyncMock,
    mock_find_last_bid_ask_ratio: Mock,
    mock_find_last_average_volumes: Mock,
    mock_volume_discord_messenger: AsyncMock,
    processor: Processor,
) -> None:
    expected_average_volume = 200
    mock_find_last_average_volumes.return_value = [250, 353, 412, 1123]
    mock_find_last_bid_ask_ratio.return_value = [0.10, 0.10, 0.05, 0.03]

    volume_comparative_array_size = 4
    volume_anomaly_ratio = Decimal(1.5)

    mock_calculate_avg_by_summary.return_value = expected_average_volume

    worker = VolumeWorker(
        processor=processor,
        event_handler=EventHandler(),
        discord_messenger=mock_volume_discord_messenger,
        volume_comparative_array_size=volume_comparative_array_size,
        volume_anomaly_ratio=volume_anomaly_ratio,
    )

    await worker._run_worker()

    assert mock_save_volume.call_count == 1
    assert (
        mock_save_volume.call_args.kwargs["avg_volume"]
        == expected_average_volume
    )

    assert worker._summary_volume_per_interval == 0
    assert worker._volume_updates_counter_per_interval == 0

    expected_deviation = 0.37453183520599254

    assert mock_volume_discord_messenger.send_notification.call_count == 1
    volume_anomaly_notification = (
        mock_volume_discord_messenger.send_notification.call_args[1]
    )

    expected_notification = {
        "pair_id": UUID("d8f4b7c5-5d9c-4b9c-8b3b-9c0c5d9f4b7c"),
        "deviation": expected_deviation,
        "current_bid_ask_ratio": 0.00,
        "previous_bid_ask_ratio": 0.07,
        "current_avg_volume": expected_average_volume,
        "previous_avg_volume": 534,
    }

    assert volume_anomaly_notification == expected_notification

    assert worker._last_average_volumes == [
        353,
        412,
        1123,
        expected_average_volume,
    ]


@patch(
    "app.services.workers.volume_worker.VolumeDiscordMessenger.send_notification",
    new_callable=AsyncMock,
)
@patch(
    "app.services.workers.volume_worker.VolumeWorker._find_last_average_volumes"
)
@patch(
    "app.services.workers.volume_worker.VolumeWorker._find_last_bid_ask_ratio"
)
@patch(
    "app.services.workers.volume_worker.save_volume",
    new_callable=AsyncMock,
)
@patch("app.services.workers.volume_worker.calculate_avg_by_summary")
async def test_not_enough_last_average_volumes(
    mock_calculate_avg_by_summary: Mock,
    mock_save_volume: AsyncMock,
    mock_find_last_bid_ask_ratio: Mock,
    mock_find_last_average_volumes: Mock,
    mock_volume_discord_messenger: AsyncMock,
    processor: Processor,
) -> None:
    expected_average_volume = 15
    mock_find_last_average_volumes.return_value = [10]
    mock_find_last_bid_ask_ratio.return_value = [0.0]

    volume_comparative_array_size = 3
    volume_anomaly_ratio = Decimal(2)

    mock_calculate_avg_by_summary.return_value = expected_average_volume

    worker = VolumeWorker(
        processor=processor,
        event_handler=EventHandler(),
        discord_messenger=mock_volume_discord_messenger,
        volume_comparative_array_size=volume_comparative_array_size,
        volume_anomaly_ratio=volume_anomaly_ratio,
    )

    await worker._run_worker()

    assert worker._last_average_volumes == [10, expected_average_volume]

    assert worker._summary_volume_per_interval == 0
    assert worker._volume_updates_counter_per_interval == 0

    assert mock_volume_discord_messenger.send_notification.call_count == 0

    assert mock_save_volume.call_count == 1


@patch(
    "app.services.workers.volume_worker.VolumeDiscordMessenger.send_notification",
    new_callable=AsyncMock,
)
@patch(
    "app.services.workers.volume_worker.VolumeWorker._find_last_average_volumes"
)
@patch(
    "app.services.workers.volume_worker.VolumeWorker._find_last_bid_ask_ratio"
)
@patch(
    "app.services.workers.volume_worker.save_volume",
    new_callable=AsyncMock,
)
async def test_right_calculating_average(
    mock_save_volume: AsyncMock,
    mock_find_last_bid_ask_ratio: Mock,
    mock_find_last_average_volumes: Mock,
    mock_volume_discord_messenger: AsyncMock,
    processor: Processor,
) -> None:
    summary_asks_volume_per_interval = 10500
    summary_bids_volume_per_interval = 9500
    summary_volume_per_interval = 20000
    volume_update_counter_per_interval = 5
    expected_average_volume = 4000
    mock_find_last_average_volumes.return_value = [300, 200, 500]
    mock_find_last_bid_ask_ratio.return_value = [-0.10, -0.10, -0.07]

    volume_comparative_array_size = 3
    volume_anomaly_ratio = Decimal(3)

    worker = VolumeWorker(
        processor=processor,
        event_handler=EventHandler(),
        discord_messenger=mock_volume_discord_messenger,
        volume_comparative_array_size=volume_comparative_array_size,
        volume_anomaly_ratio=volume_anomaly_ratio,
    )

    worker._summary_asks_volume_per_interval = summary_asks_volume_per_interval
    worker._summary_bids_volume_per_interval = summary_bids_volume_per_interval
    worker._summary_volume_per_interval = summary_volume_per_interval
    worker._volume_updates_counter_per_interval = (
        volume_update_counter_per_interval
    )

    await worker._run_worker()
    assert mock_volume_discord_messenger.send_notification.call_count == 1

    volume_anomaly_notification = (
        mock_volume_discord_messenger.send_notification.call_args[1]
    )

    expected_notification = {
        "pair_id": UUID("d8f4b7c5-5d9c-4b9c-8b3b-9c0c5d9f4b7c"),
        "deviation": 12.012012012012011,
        "current_bid_ask_ratio": -0.05,
        "previous_bid_ask_ratio": -0.09,
        "current_avg_volume": expected_average_volume,
        "previous_avg_volume": 333,
    }

    assert volume_anomaly_notification == expected_notification

    assert worker._last_average_volumes == [200, 500, expected_average_volume]

    assert worker._summary_volume_per_interval == 0
    assert worker._volume_updates_counter_per_interval == 0

    assert mock_save_volume.call_count == 1
