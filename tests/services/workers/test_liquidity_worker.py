from decimal import Decimal
from unittest.mock import AsyncMock, Mock, patch
from uuid import UUID

import pytest

from app.services.collectors.common import Collector
from app.services.collectors.workers.liquidity_worker import LiquidityWorker


class MockCollector(Collector):
    def __init__(
        self,
        launch_id: UUID,
        pair_id: UUID,
        exchange_id: UUID,
        symbol: str,
        delimiter: Decimal,
    ):
        super().__init__(launch_id, pair_id, exchange_id, symbol, delimiter)

    async def run(self):
        pass


@pytest.fixture
def collector() -> Collector:
    return MockCollector(
        launch_id=UUID("d8f4b7c5-5d9c-4b9c-8b3b-9c0c5d9f4b7c"),
        pair_id=UUID("d8f4b7c5-5d9c-4b9c-8b3b-9c0c5d9f4b7c"),
        exchange_id=UUID("d8f4b7c5-5d9c-4b9c-8b3b-9c0c5d9f4b7c"),
        symbol="BTCUSDT",
        delimiter=Decimal("0.1"),
    )


@patch(
    "app.services.collectors.workers.orders_worker.OrderBookDiscordMessenger.send_notifications",
    new_callable=AsyncMock,
)
@patch(
    "app.services.collectors.workers.liquidity_worker.LiquidityWorker._find_last_average_volumes"
)
@patch(
    "app.services.collectors.workers.liquidity_worker.save_liquidity",
    new_callable=AsyncMock,
)
async def test_non_anomaly_anomaly(
    mock_save_liquidity: AsyncMock,
    mock_find_last_average_volumes: Mock,
    mock_liquidity_discord_messenger: AsyncMock,
    collector: Collector,
) -> None:
    mock_find_last_average_volumes.return_value = [32, 16, 23231, 11, 0]

    collector.avg_volume = 3000

    worker = LiquidityWorker(
        collector=collector,
        discord_messenger=mock_liquidity_discord_messenger,
        comparable_liquidity_set_size=5,
        liquidity_anomaly_ratio=2,
    )

    await worker._run_worker()
    _deviation = mock_liquidity_discord_messenger.send_notification.call_args

    assert _deviation is None
    assert worker._last_avg_volumes == [16, 23231, 11, 0, 3000]
    assert mock_liquidity_discord_messenger.send_notification.call_count == 0


@patch(
    "app.services.collectors.workers.orders_worker.OrderBookDiscordMessenger.send_notifications",
    new_callable=AsyncMock,
)
@patch(
    "app.services.collectors.workers.liquidity_worker.LiquidityWorker._find_last_average_volumes"
)
@patch(
    "app.services.collectors.workers.liquidity_worker.save_liquidity",
    new_callable=AsyncMock,
)
async def test_inflow_anomaly_detection(
    mock_save_liquidity: AsyncMock,
    mock_find_last_average_volumes: Mock,
    mock_liquidity_discord_messenger: AsyncMock,
    collector: Collector,
) -> None:
    mock_find_last_average_volumes.return_value = [10, 20, 30]

    collector.avg_volume = 40

    worker = LiquidityWorker(
        collector=collector,
        discord_messenger=mock_liquidity_discord_messenger,
        comparable_liquidity_set_size=3,
        liquidity_anomaly_ratio=2,
    )

    await worker._run_worker()
    _deviation = mock_liquidity_discord_messenger.send_notification.call_args[1]['deviation']

    assert _deviation is not None
    assert collector.avg_volume == 0
    assert worker._last_avg_volumes == [20, 30, 40]
    assert mock_liquidity_discord_messenger.send_notification.call_count == 1
    liquidity_anomaly_notification = mock_liquidity_discord_messenger.send_notification.call_args[1]

    expected_notification = {
        "pair_id": UUID('d8f4b7c5-5d9c-4b9c-8b3b-9c0c5d9f4b7c'),
        "deviation": 2.0,
        "current_avg_volume": 40,
        "previous_avg_volume": 20,
    }

    assert liquidity_anomaly_notification == expected_notification


@patch(
    "app.services.collectors.workers.orders_worker.OrderBookDiscordMessenger.send_notifications",
    new_callable=AsyncMock,
)
@patch(
    "app.services.collectors.workers.liquidity_worker.LiquidityWorker._find_last_average_volumes"
)
@patch(
    "app.services.collectors.workers.liquidity_worker.save_liquidity",
    new_callable=AsyncMock,
)
async def test_outflow_anomaly_detection(
    mock_save_liquidity: AsyncMock,
    mock_find_last_average_volumes: Mock,
    mock_liquidity_discord_messenger: AsyncMock,
    collector: Collector,
) -> None:
    mock_find_last_average_volumes.return_value = [125827, 315291, 723125]

    collector.avg_volume = 250000

    worker = LiquidityWorker(
        collector=collector,
        discord_messenger=mock_liquidity_discord_messenger,
        comparable_liquidity_set_size=3,
        liquidity_anomaly_ratio=1.5,
    )

    await worker._run_worker()
    _deviation = mock_liquidity_discord_messenger.send_notification.call_args[1]['deviation']

    assert _deviation is not None
    assert worker._last_avg_volumes == [315291, 723125, 250000]
    assert collector.avg_volume == 0
    assert mock_liquidity_discord_messenger.send_notification.call_count == 1

    liquidity_anomaly_notification = mock_liquidity_discord_messenger.send_notification.call_args[1]

    expected_notification = {
        "pair_id": UUID('d8f4b7c5-5d9c-4b9c-8b3b-9c0c5d9f4b7c'),
        "deviation": 0.6441954128133044,
        "current_avg_volume": 250000,
        "previous_avg_volume": 388081,
    }

    assert liquidity_anomaly_notification == expected_notification


@patch(
    "app.services.collectors.workers.orders_worker.OrderBookDiscordMessenger.send_notifications",
    new_callable=AsyncMock,
)
@patch(
    "app.services.collectors.workers.liquidity_worker.LiquidityWorker._find_last_average_volumes"
)
@patch(
    "app.services.collectors.workers.liquidity_worker.save_liquidity",
    new_callable=AsyncMock,
)
async def test_not_enough_last_average_volumes_and_filling_this_array_with_latest_volume(
    mock_save_liquidity: AsyncMock,
    mock_find_last_average_volumes: Mock,
    mock_liquidity_discord_messenger: AsyncMock,
    collector: Collector,
) -> None:
    mock_find_last_average_volumes.return_value = [10]

    collector.avg_volume = 15

    worker = LiquidityWorker(
        collector=collector,
        discord_messenger=mock_liquidity_discord_messenger,
        comparable_liquidity_set_size=3,
        liquidity_anomaly_ratio=2,
    )

    await worker._run_worker()

    assert len(worker._last_avg_volumes) == 2
    assert worker._last_avg_volumes[1] == 15
    assert collector.avg_volume == 0
    assert mock_liquidity_discord_messenger.send_notification.call_count == 0


@patch(
    "app.services.collectors.workers.orders_worker.OrderBookDiscordMessenger.send_notifications",
    new_callable=AsyncMock,
)
@patch(
    "app.services.collectors.workers.liquidity_worker.LiquidityWorker._find_last_average_volumes"
)
@patch(
    "app.services.collectors.workers.liquidity_worker.save_liquidity",
    new_callable=AsyncMock,
)
async def test_saving_liquidity_record(
    mock_save_liquidity: AsyncMock,
    mock_find_last_average_volumes: Mock,
    mock_liquidity_discord_messenger: AsyncMock,
    collector: Collector,
) -> None:
    mock_find_last_average_volumes.return_value = [125827, 315291, 723125]

    collector.avg_volume = 250000

    worker = LiquidityWorker(
        collector=collector,
        discord_messenger=mock_liquidity_discord_messenger,
        comparable_liquidity_set_size=3,
        liquidity_anomaly_ratio=1.5,
    )

    await worker._run_worker()

    assert mock_save_liquidity.call_count == 1
    assert mock_liquidity_discord_messenger.send_notification.call_count == 1

    liquidity_anomaly_notification = mock_liquidity_discord_messenger.send_notification.call_args[1]

    expected_notification = {
        "pair_id": UUID('d8f4b7c5-5d9c-4b9c-8b3b-9c0c5d9f4b7c'),
        "deviation": 0.6441954128133044,
        "current_avg_volume": 250000,
        "previous_avg_volume": 388081,
    }

    assert liquidity_anomaly_notification == expected_notification


@patch(
    "app.services.collectors.workers.orders_worker.OrderBookDiscordMessenger.send_notifications",
    new_callable=AsyncMock,
)
@patch(
    "app.services.collectors.workers.liquidity_worker.LiquidityWorker._find_last_average_volumes"
)
@patch(
    "app.services.collectors.workers.liquidity_worker.save_liquidity",
    new_callable=AsyncMock,
)
async def test_non_anomaly_anomaly_not_send_notification(
    mock_save_liquidity: AsyncMock,
    mock_find_last_average_volumes: Mock,
    mock_liquidity_discord_messenger: AsyncMock,
    collector: Collector,
) -> None:
    mock_find_last_average_volumes.return_value = [32, 16, 23231, 11, 0]

    worker = LiquidityWorker(
        collector=collector,
        discord_messenger=mock_liquidity_discord_messenger,
        comparable_liquidity_set_size=5,
        liquidity_anomaly_ratio=2,
    )

    await worker._run_worker()

    assert mock_liquidity_discord_messenger.send_notification.call_count == 0


@patch(
    "app.services.collectors.workers.orders_worker.OrderBookDiscordMessenger.send_notifications",
    new_callable=AsyncMock,
)
@patch(
    "app.services.collectors.workers.liquidity_worker.LiquidityWorker._find_last_average_volumes"
)
@patch(
    "app.services.collectors.workers.liquidity_worker.save_liquidity",
    new_callable=AsyncMock,
)
async def test_anomaly_anomaly_send_notification(
    mock_save_liquidity: AsyncMock,
    mock_find_last_average_volumes: Mock,
    mock_liquidity_discord_messenger: AsyncMock,
    collector: Collector,
) -> None:
    mock_find_last_average_volumes.return_value = [100, 200, 300]

    collector.avg_volume = 250000

    worker = LiquidityWorker(
        collector=collector,
        discord_messenger=mock_liquidity_discord_messenger,
        comparable_liquidity_set_size=3,
        liquidity_anomaly_ratio=2,
    )

    await worker._run_worker()

    assert mock_liquidity_discord_messenger.send_notification.call_count == 1

    liquidity_anomaly_notification = mock_liquidity_discord_messenger.send_notification.call_args[1]

    expected_notification = {
        "pair_id": UUID('d8f4b7c5-5d9c-4b9c-8b3b-9c0c5d9f4b7c'),
        "deviation": 1250.0,
        "current_avg_volume": 250000,
        "previous_avg_volume": 200,
    }

    assert liquidity_anomaly_notification == expected_notification
