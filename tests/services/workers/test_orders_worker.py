from decimal import Decimal
from unittest.mock import AsyncMock, Mock, patch
from uuid import UUID

import pytest

from app.services.clients.schemas.binance import OrderBookSnapshot
from app.services.collectors.common import Collector
from app.services.collectors.workers.orders_worker import (AnomalyKey,
                                                           OrderAnomaly,
                                                           OrderAnomalyDto,
                                                           OrdersWorker)
from app.services.messengers.order_book_discord_messenger import \
    OrderAnomalyNotification


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
    "app.services.collectors.workers.orders_worker.get_current_time",
)
async def test_valid_anomaly_detection_first_positions(
    mock_get_current_time: Mock,
    mock_order_book_discord_messenger: AsyncMock,
    collector: Collector,
) -> None:
    current_time = 1.0
    mock_get_current_time.return_value = current_time
    collector.order_book = OrderBookSnapshot(
        lastUpdateId=1,
        bids={
            Decimal("27200.0"): Decimal("9.0"),
            Decimal("27100.0"): Decimal("2.0"),
            Decimal("27000.0"): Decimal("3.0"),
            Decimal("26900.0"): Decimal("1.0"),
            Decimal("26800.0"): Decimal("20.0"),
        },
        asks={
            Decimal("27300.0"): Decimal("9.0"),
            Decimal("27400.0"): Decimal("1.0"),
            Decimal("27500.0"): Decimal("1.0"),
            Decimal("27600.0"): Decimal("1.0"),
            Decimal("27800.0"): Decimal("20.0"),
        },
    )
    worker = OrdersWorker(
        collector=collector,
        discord_messenger=mock_order_book_discord_messenger,
        order_anomaly_multiplier=1.5,
        anomalies_detection_ttl=1,
        anomalies_observing_ttl=1,
        anomalies_observing_ratio=0.5,
        top_n_orders=4,
    )

    await worker._run_worker()

    assert mock_order_book_discord_messenger.send_notifications.call_count == 1

    order_anomaly_notifications_call = (
        mock_order_book_discord_messenger.send_notifications.call_args_list[0]
    )
    order_anomaly_notifications = order_anomaly_notifications_call[0][0]

    expected_notifications = [
        OrderAnomalyNotification(
            price=Decimal("27300.0"),
            quantity=Decimal("9.0"),
            order_liquidity=Decimal("245700.00"),
            average_liquidity=Decimal("27500.00"),
            type="ask",
            position=0,
        ),
        OrderAnomalyNotification(
            price=Decimal("27200.0"),
            quantity=Decimal("9.0"),
            order_liquidity=Decimal("244800.00"),
            average_liquidity=Decimal("54033.33333333333333333333333"),
            type="bid",
            position=0,
        ),
    ]

    assert order_anomaly_notifications == expected_notifications

    assert worker._detected_anomalies == {
        AnomalyKey(price=Decimal("27300.0"), type="ask"): OrderAnomalyDto(
            time=current_time,
            order_anomaly=OrderAnomaly(
                price=Decimal("27300.0"),
                quantity=Decimal("9.0"),
                order_liquidity=Decimal("245700.00"),
                average_liquidity=Decimal("27500.00"),
                type="ask",
                position=0,
            ),
        ),
        AnomalyKey(price=Decimal("27200.0"), type="bid"): OrderAnomalyDto(
            time=current_time,
            order_anomaly=OrderAnomaly(
                price=Decimal("27200.0"),
                quantity=Decimal("9.0"),
                order_liquidity=Decimal("244800.00"),
                average_liquidity=Decimal("54033.33333333333333333333333"),
                type="bid",
                position=0,
            ),
        ),
    }
    assert worker._observing_anomalies == {}


@patch(
    "app.services.collectors.workers.orders_worker.OrderBookDiscordMessenger.send_notifications",
    new_callable=AsyncMock,
)
@patch(
    "app.services.collectors.workers.orders_worker.get_current_time",
)
async def test_valid_anomaly_detection_and_put_for_observe_non_first_positions(
    mock_get_current_time: Mock,
    mock_order_book_discord_messenger: AsyncMock,
    collector: Collector,
) -> None:
    current_time = 1.0
    mock_get_current_time.return_value = current_time
    collector.order_book = OrderBookSnapshot(
        lastUpdateId=1,
        bids={
            Decimal("27200.0"): Decimal("1.0"),
            Decimal("27100.0"): Decimal("2.0"),
            Decimal("27000.0"): Decimal("9.0"),
            Decimal("26900.0"): Decimal("1.0"),
            Decimal("26800.0"): Decimal("20.0"),
        },
        asks={
            Decimal("27300.0"): Decimal("1.0"),
            Decimal("27400.0"): Decimal("1.0"),
            Decimal("27600.0"): Decimal("1.0"),
            Decimal("27500.0"): Decimal("9.0"),
            Decimal("27800.0"): Decimal("20.0"),
        },
    )
    worker = OrdersWorker(
        collector=collector,
        discord_messenger=mock_order_book_discord_messenger,
        order_anomaly_multiplier=1.5,
        anomalies_detection_ttl=1,
        anomalies_observing_ttl=1,
        anomalies_observing_ratio=0.5,
        top_n_orders=4,
    )

    await worker._run_worker()

    assert mock_order_book_discord_messenger.send_notifications.call_count == 0
    assert worker._detected_anomalies == {
        AnomalyKey(price=Decimal("27500.0"), type="ask"): OrderAnomalyDto(
            time=1.0,
            order_anomaly=OrderAnomaly(
                price=Decimal("27500.0"),
                quantity=Decimal("9.0"),
                order_liquidity=Decimal("247500.00"),
                average_liquidity=Decimal("27433.33333333333333333333333"),
                position=2,
                type="ask",
            ),
        ),
        AnomalyKey(price=Decimal("27000.0"), type="bid"): OrderAnomalyDto(
            time=1.0,
            order_anomaly=OrderAnomaly(
                price=Decimal("27000.0"),
                quantity=Decimal("9.0"),
                order_liquidity=Decimal("243000.00"),
                average_liquidity=Decimal("36100.00"),
                position=2,
                type="bid",
            ),
        ),
    }
    assert worker._observing_anomalies == {
        AnomalyKey(price=Decimal("27500.0"), type="ask"): OrderAnomalyDto(
            time=1.0,
            order_anomaly=OrderAnomaly(
                price=Decimal("27500.0"),
                quantity=Decimal("9.0"),
                order_liquidity=Decimal("247500.00"),
                average_liquidity=Decimal("27433.33333333333333333333333"),
                position=2,
                type="ask",
            ),
        ),
        AnomalyKey(price=Decimal("27000.0"), type="bid"): OrderAnomalyDto(
            time=1.0,
            order_anomaly=OrderAnomaly(
                price=Decimal("27000.0"),
                quantity=Decimal("9.0"),
                order_liquidity=Decimal("243000.00"),
                average_liquidity=Decimal("36100.00"),
                position=2,
                type="bid",
            ),
        ),
    }


@patch(
    "app.services.collectors.workers.orders_worker.OrderBookDiscordMessenger.send_notifications",
    new_callable=AsyncMock,
)
@patch(
    "app.services.collectors.workers.orders_worker.get_current_time",
)
async def test_non_first_already_observing_anomalies_for_notification_after_expiration_of_observing_ttl(
    mock_get_current_time: Mock,
    mock_order_book_discord_messenger: AsyncMock,
    collector: Collector,
) -> None:
    current_time = 2.5
    mock_get_current_time.return_value = current_time
    collector.order_book = OrderBookSnapshot(
        lastUpdateId=1,
        bids={
            Decimal("27200.0"): Decimal("1.0"),
            Decimal("27100.0"): Decimal("2.0"),
            Decimal("27000.0"): Decimal("8.2"),
            Decimal("26900.0"): Decimal("1.0"),
            Decimal("26800.0"): Decimal("20.0"),
        },
        asks={
            Decimal("27300.0"): Decimal("1.0"),
            Decimal("27400.0"): Decimal("1.0"),
            Decimal("27600.0"): Decimal("1.0"),
            Decimal("27500.0"): Decimal("8.0"),
            Decimal("27800.0"): Decimal("20.0"),
        },
    )
    worker = OrdersWorker(
        collector=collector,
        discord_messenger=mock_order_book_discord_messenger,
        order_anomaly_multiplier=1.5,
        anomalies_detection_ttl=1,
        anomalies_observing_ttl=1,
        anomalies_observing_ratio=0.2,
        top_n_orders=4,
    )
    worker._observing_anomalies = {
        AnomalyKey(price=Decimal("27500.0"), type="ask"): OrderAnomalyDto(
            time=1.0,
            order_anomaly=OrderAnomaly(
                price=Decimal("27500.0"),
                quantity=Decimal("9.0"),
                order_liquidity=Decimal("247500.00"),
                average_liquidity=Decimal("27433.33333333333333333333333"),
                position=2,
                type="ask",
            ),
        ),
        AnomalyKey(price=Decimal("27000.0"), type="bid"): OrderAnomalyDto(
            time=1.0,
            order_anomaly=OrderAnomaly(
                price=Decimal("27000.0"),
                quantity=Decimal("9.0"),
                order_liquidity=Decimal("243000.00"),
                average_liquidity=Decimal("36100.00"),
                position=2,
                type="bid",
            ),
        ),
    }

    await worker._run_worker()
    assert worker._observing_anomalies == {}

    assert mock_order_book_discord_messenger.send_notifications.call_count == 1

    order_anomaly_notifications_call = (
        mock_order_book_discord_messenger.send_notifications.call_args_list[0]
    )
    order_anomaly_notifications = order_anomaly_notifications_call[0][0]

    expected_notifications = [
        OrderAnomalyNotification(
            price=Decimal("27500.0"),
            quantity=Decimal("8.0"),
            order_liquidity=Decimal("220000.00"),
            average_liquidity=Decimal("27433.33333333333333333333333"),
            type="ask",
            position=2,
        ),
        OrderAnomalyNotification(
            price=Decimal("27000.0"),
            quantity=Decimal("8.2"),
            order_liquidity=Decimal("221400.00"),
            average_liquidity=Decimal("36100.00"),
            type="bid",
            position=2,
        ),
    ]

    assert order_anomaly_notifications == expected_notifications


@patch(
    "app.services.collectors.workers.orders_worker.OrderBookDiscordMessenger.send_notifications",
    new_callable=AsyncMock,
)
@patch(
    "app.services.collectors.workers.orders_worker.get_current_time",
)
async def test_real_orders_valid_processing_when_new_one_appears(
    mock_get_current_time: Mock,
    mock_order_book_discord_messenger: AsyncMock,
    collector: Collector,
) -> None:
    current_time = 2.5
    mock_get_current_time.return_value = current_time
    collector.order_book = OrderBookSnapshot(
        lastUpdateId=1,
        bids={
            Decimal("27200.0"): Decimal("1.0"),
            Decimal("27100.0"): Decimal("2.0"),
            Decimal("27000.0"): Decimal("8.2"),
            Decimal("26900.0"): Decimal("1.0"),
            Decimal("26800.0"): Decimal("20.0"),
        },
        asks={
            Decimal("27300.0"): Decimal("1.0"),
            Decimal("27400.0"): Decimal("20.0"),
            Decimal("27600.0"): Decimal("1.0"),
            Decimal("27500.0"): Decimal("8.0"),
            Decimal("27800.0"): Decimal("20.0"),
        },
    )
    worker = OrdersWorker(
        collector=collector,
        discord_messenger=mock_order_book_discord_messenger,
        order_anomaly_multiplier=1.5,
        anomalies_detection_ttl=1,
        anomalies_observing_ttl=1,
        anomalies_observing_ratio=0.2,
        top_n_orders=4,
    )
    worker._observing_anomalies = {
        AnomalyKey(price=Decimal("27500.0"), type="ask"): OrderAnomalyDto(
            time=1.0,
            order_anomaly=OrderAnomaly(
                price=Decimal("27500.0"),
                quantity=Decimal("9.0"),
                order_liquidity=Decimal("247500.00"),
                average_liquidity=Decimal("27433.33333333333333333333333"),
                position=2,
                type="ask",
            ),
        ),
        AnomalyKey(price=Decimal("27000.0"), type="bid"): OrderAnomalyDto(
            time=1.0,
            order_anomaly=OrderAnomaly(
                price=Decimal("27000.0"),
                quantity=Decimal("9.0"),
                order_liquidity=Decimal("243000.00"),
                average_liquidity=Decimal("36100.00"),
                position=2,
                type="bid",
            ),
        ),
    }

    await worker._run_worker()

    assert worker._observing_anomalies == {
        AnomalyKey(price=Decimal("27400.0"), type="ask"): OrderAnomalyDto(
            time=2.5,
            order_anomaly=OrderAnomaly(
                price=Decimal("27400.0"),
                quantity=Decimal("20.0"),
                order_liquidity=Decimal("548000.00"),
                average_liquidity=Decimal("91633.33333333333333333333333"),
                position=1,
                type="ask",
            ),
        ),
    }


@patch(
    "app.services.collectors.workers.orders_worker.OrderBookDiscordMessenger.send_notifications",
    new_callable=AsyncMock,
)
@patch(
    "app.services.collectors.workers.orders_worker.get_current_time",
)
async def test_real_orders_observing_does_not_exist(
    mock_get_current_time: Mock,
    mock_order_book_discord_messenger: AsyncMock,
    collector: Collector,
) -> None:
    current_time = 2.5
    mock_get_current_time.return_value = current_time
    collector.order_book = OrderBookSnapshot(
        lastUpdateId=1,
        bids={
            Decimal("33000.0"): Decimal("1.0"),
            Decimal("37100.0"): Decimal("1.0"),
            Decimal("37000.0"): Decimal("1.2"),
            Decimal("36900.0"): Decimal("1.0"),
            Decimal("36800.0"): Decimal("1.0"),
        },
        asks={
            Decimal("37300.0"): Decimal("1.0"),
            Decimal("37400.0"): Decimal("1.0"),
            Decimal("37600.0"): Decimal("1.0"),
            Decimal("37500.0"): Decimal("1.0"),
            Decimal("37800.0"): Decimal("1.0"),
        },
    )
    worker = OrdersWorker(
        collector=collector,
        discord_messenger=mock_order_book_discord_messenger,
        order_anomaly_multiplier=1.5,
        anomalies_detection_ttl=1,
        anomalies_observing_ttl=1,
        anomalies_observing_ratio=0.2,
        top_n_orders=4,
    )
    worker._observing_anomalies = {
        AnomalyKey(price=Decimal("27500.0"), type="ask"): OrderAnomalyDto(
            time=1.0,
            order_anomaly=OrderAnomaly(
                price=Decimal("27500.0"),
                quantity=Decimal("9.0"),
                order_liquidity=Decimal("247500.00"),
                average_liquidity=Decimal("27433.33333333333333333333333"),
                position=2,
                type="ask",
            ),
        ),
        AnomalyKey(price=Decimal("27000.0"), type="bid"): OrderAnomalyDto(
            time=1.0,
            order_anomaly=OrderAnomaly(
                price=Decimal("27000.0"),
                quantity=Decimal("9.0"),
                order_liquidity=Decimal("243000.00"),
                average_liquidity=Decimal("36100.00"),
                position=2,
                type="bid",
            ),
        ),
    }

    await worker._run_worker()

    assert worker._observing_anomalies == {}


@patch(
    "app.services.collectors.workers.orders_worker.OrderBookDiscordMessenger.send_notifications",
    new_callable=AsyncMock,
)
@patch(
    "app.services.collectors.workers.orders_worker.get_current_time",
)
async def test_real_orders_valid_processing_changed_more_than_ratio(
    mock_get_current_time: Mock,
    mock_order_book_discord_messenger: AsyncMock,
    collector: Collector,
) -> None:
    current_time = 2.5
    mock_get_current_time.return_value = current_time
    collector.order_book = OrderBookSnapshot(
        lastUpdateId=1,
        bids={
            Decimal("27200.0"): Decimal("1.0"),
            Decimal("27100.0"): Decimal("2.0"),
            Decimal("27000.0"): Decimal("5.2"),
            Decimal("26900.0"): Decimal("1.0"),
            Decimal("26800.0"): Decimal("20.0"),
        },
        asks={
            Decimal("27300.0"): Decimal("1.0"),
            Decimal("27400.0"): Decimal("1.0"),
            Decimal("27600.0"): Decimal("1.0"),
            Decimal("27500.0"): Decimal("4.0"),
            Decimal("27800.0"): Decimal("20.0"),
        },
    )
    worker = OrdersWorker(
        collector=collector,
        discord_messenger=mock_order_book_discord_messenger,
        order_anomaly_multiplier=1.5,
        anomalies_detection_ttl=1,
        anomalies_observing_ttl=1,
        anomalies_observing_ratio=0.2,
        top_n_orders=4,
    )
    worker._observing_anomalies = {
        AnomalyKey(price=Decimal("27500.0"), type="ask"): OrderAnomalyDto(
            time=1.0,
            order_anomaly=OrderAnomaly(
                price=Decimal("27500.0"),
                quantity=Decimal("9.0"),
                order_liquidity=Decimal("247500.00"),
                average_liquidity=Decimal("27433.33333333333333333333333"),
                position=2,
                type="ask",
            ),
        ),
        AnomalyKey(price=Decimal("27000.0"), type="bid"): OrderAnomalyDto(
            time=1.0,
            order_anomaly=OrderAnomaly(
                price=Decimal("27000.0"),
                quantity=Decimal("9.0"),
                order_liquidity=Decimal("243000.00"),
                average_liquidity=Decimal("36100.00"),
                position=2,
                type="bid",
            ),
        ),
    }

    await worker._run_worker()

    assert worker._observing_anomalies == {}

    assert mock_order_book_discord_messenger.send_notifications.call_count == 0


@patch(
    "app.services.collectors.workers.orders_worker.OrderBookDiscordMessenger.send_notifications",
    new_callable=AsyncMock,
)
@patch(
    "app.services.collectors.workers.orders_worker.get_current_time",
)
async def test_real_orders_nothing_match_order_anomaly_multiplier(
    mock_get_current_time: Mock,
    mock_order_book_discord_messenger: AsyncMock,
    collector: Collector,
) -> None:
    current_time = 2.5
    mock_get_current_time.return_value = current_time
    collector.order_book = OrderBookSnapshot(
        lastUpdateId=1,
        bids={
            Decimal("27200.0"): Decimal("1.0"),
            Decimal("27100.0"): Decimal("2.0"),
            Decimal("27000.0"): Decimal("5.2"),
            Decimal("26900.0"): Decimal("1.0"),
            Decimal("26800.0"): Decimal("20.0"),
        },
        asks={
            Decimal("27300.0"): Decimal("1.0"),
            Decimal("27400.0"): Decimal("1.0"),
            Decimal("27600.0"): Decimal("1.0"),
            Decimal("27500.0"): Decimal("4.0"),
            Decimal("27800.0"): Decimal("20.0"),
        },
    )
    worker = OrdersWorker(
        collector=collector,
        discord_messenger=mock_order_book_discord_messenger,
        order_anomaly_multiplier=20,
        anomalies_detection_ttl=1,
        anomalies_observing_ttl=1,
        anomalies_observing_ratio=0.2,
        top_n_orders=4,
    )

    await worker._run_worker()

    assert worker._observing_anomalies == {}

    assert mock_order_book_discord_messenger.send_notifications.call_count == 0


@patch(
    "app.services.collectors.workers.orders_worker.OrderBookDiscordMessenger.send_notifications",
    new_callable=AsyncMock,
)
@patch(
    "app.services.collectors.workers.orders_worker.get_current_time",
)
async def test_skipping_the_first_position_anomaly_that_has_non_expired_key_in_cache(
    mock_get_current_time: Mock,
    mock_order_book_discord_messenger: AsyncMock,
    collector: Collector,
) -> None:
    current_time = 2.5
    mock_get_current_time.return_value = current_time
    collector.order_book = OrderBookSnapshot(
        lastUpdateId=1,
        bids={
            Decimal("27200.0"): Decimal("30.0"),
            Decimal("27100.0"): Decimal("2.0"),
            Decimal("27000.0"): Decimal("5.2"),
            Decimal("26900.0"): Decimal("1.0"),
            Decimal("26800.0"): Decimal("4.0"),
        },
        asks={
            Decimal("27300.0"): Decimal("1.0"),
            Decimal("27400.0"): Decimal("1.0"),
            Decimal("27600.0"): Decimal("1.0"),
            Decimal("27500.0"): Decimal("4.0"),
            Decimal("27800.0"): Decimal("4.0"),
        },
    )
    worker = OrdersWorker(
        collector=collector,
        discord_messenger=mock_order_book_discord_messenger,
        order_anomaly_multiplier=5,
        anomalies_detection_ttl=4,
        anomalies_observing_ttl=1,
        anomalies_observing_ratio=0.2,
        top_n_orders=4,
    )

    worker._detected_anomalies = {
        AnomalyKey(price=Decimal("27200.0"), type="bid"): OrderAnomalyDto(
            time=1.0,
            order_anomaly=OrderAnomaly(
                price=Decimal("27200.0"),
                quantity=Decimal("40.0"),
                order_liquidity=Decimal("1088000.00"),
                average_liquidity=Decimal("73833.33333333333333333333333"),
                position=0,
                type="bid",
            ),
        )
    }

    await worker._run_worker()

    assert mock_order_book_discord_messenger.send_notifications.call_count == 0


@patch(
    "app.services.collectors.workers.orders_worker.OrderBookDiscordMessenger.send_notifications",
    new_callable=AsyncMock,
)
@patch(
    "app.services.collectors.workers.orders_worker.get_current_time",
)
async def test_skipping_non_first_position_anomaly_that_has_non_expired_key_in_cache_and_not_observing(
    mock_get_current_time: Mock,
    mock_order_book_discord_messenger: AsyncMock,
    collector: Collector,
) -> None:
    current_time = 2.5
    mock_get_current_time.return_value = current_time
    collector.order_book = OrderBookSnapshot(
        lastUpdateId=1,
        bids={
            Decimal("27200.0"): Decimal("2.0"),
            Decimal("27100.0"): Decimal("2.0"),
            Decimal("27000.0"): Decimal("1.2"),
            Decimal("26900.0"): Decimal("1.0"),
            Decimal("26800.0"): Decimal("20.0"),
        },
        asks={
            Decimal("27300.0"): Decimal("1.0"),
            Decimal("27400.0"): Decimal("1.0"),
            Decimal("27600.0"): Decimal("1.0"),
            Decimal("27500.0"): Decimal("4.0"),
            Decimal("27800.0"): Decimal("4.0"),
        },
    )
    worker = OrdersWorker(
        collector=collector,
        discord_messenger=mock_order_book_discord_messenger,
        order_anomaly_multiplier=3,
        anomalies_detection_ttl=4,
        anomalies_observing_ttl=4,
        anomalies_observing_ratio=0.2,
        top_n_orders=5,
    )

    order_anomaly = {
        AnomalyKey(price=Decimal("26800.0"), type="bid"): OrderAnomalyDto(
            time=1,
            order_anomaly=OrderAnomaly(
                price=Decimal("26800.0"),
                quantity=Decimal("20.0"),
                order_liquidity=Decimal("536000.00"),
                average_liquidity=Decimal("41975.00"),
                position=4,
                type="bid",
            ),
        )
    }

    worker._detected_anomalies = order_anomaly

    await worker._run_worker()

    assert mock_order_book_discord_messenger.send_notifications.call_count == 0

    assert worker._observing_anomalies == {}

    assert worker._detected_anomalies == order_anomaly


@patch(
    "app.services.collectors.workers.orders_worker.OrderBookDiscordMessenger.send_notifications",
    new_callable=AsyncMock,
)
@patch(
    "app.services.collectors.workers.orders_worker.get_current_time",
)
async def test_passing_first_position_anomaly_and_adding_to_cache_if_anomaly_key_not_exist_in_cache(
    mock_get_current_time: Mock,
    mock_order_book_discord_messenger: AsyncMock,
    collector: Collector,
) -> None:
    current_time = 2.5
    mock_get_current_time.return_value = current_time
    collector.order_book = OrderBookSnapshot(
        lastUpdateId=1,
        bids={
            Decimal("27200.0"): Decimal("30.0"),
            Decimal("27100.0"): Decimal("2.0"),
            Decimal("27000.0"): Decimal("5.2"),
            Decimal("26900.0"): Decimal("1.0"),
            Decimal("26800.0"): Decimal("4.0"),
        },
        asks={
            Decimal("27300.0"): Decimal("1.0"),
            Decimal("27400.0"): Decimal("1.0"),
            Decimal("27600.0"): Decimal("1.0"),
            Decimal("27500.0"): Decimal("4.0"),
            Decimal("27800.0"): Decimal("4.0"),
        },
    )
    worker = OrdersWorker(
        collector=collector,
        discord_messenger=mock_order_book_discord_messenger,
        order_anomaly_multiplier=5,
        anomalies_detection_ttl=4,
        anomalies_observing_ttl=1,
        anomalies_observing_ratio=0.2,
        top_n_orders=4,
    )

    await worker._run_worker()

    assert mock_order_book_discord_messenger.send_notifications.call_count == 1

    assert worker._detected_anomalies == {
        AnomalyKey(price=Decimal("27200.0"), type="bid"): OrderAnomalyDto(
            time=current_time,
            order_anomaly=OrderAnomaly(
                price=Decimal("27200.0"),
                quantity=Decimal("30.0"),
                order_liquidity=Decimal("816000.00"),
                average_liquidity=Decimal("73833.33333333333333333333333"),
                position=0,
                type="bid",
            ),
        )
    }


@patch(
    "app.services.collectors.workers.orders_worker.OrderBookDiscordMessenger.send_notifications",
    new_callable=AsyncMock,
)
@patch(
    "app.services.collectors.workers.orders_worker.get_current_time",
)
async def test_passing_first_position_anomaly_and_adding_to_cache_if_anomaly_key_is_expired_in_cache(
    mock_get_current_time: Mock,
    mock_order_book_discord_messenger: AsyncMock,
    collector: Collector,
) -> None:
    current_time = 5
    mock_get_current_time.return_value = current_time
    collector.order_book = OrderBookSnapshot(
        lastUpdateId=1,
        bids={
            Decimal("27200.0"): Decimal("30.0"),
            Decimal("27100.0"): Decimal("2.0"),
            Decimal("27000.0"): Decimal("5.2"),
            Decimal("26900.0"): Decimal("1.0"),
            Decimal("26800.0"): Decimal("4.0"),
        },
        asks={
            Decimal("27300.0"): Decimal("1.0"),
            Decimal("27400.0"): Decimal("1.0"),
            Decimal("27600.0"): Decimal("1.0"),
            Decimal("27500.0"): Decimal("4.0"),
            Decimal("27800.0"): Decimal("4.0"),
        },
    )
    worker = OrdersWorker(
        collector=collector,
        discord_messenger=mock_order_book_discord_messenger,
        order_anomaly_multiplier=5,
        anomalies_detection_ttl=2,
        anomalies_observing_ttl=1,
        anomalies_observing_ratio=0.2,
        top_n_orders=4,
    )

    worker._detected_anomalies = {
        AnomalyKey(price=Decimal("27200.0"), type="bid"): OrderAnomalyDto(
            time=1,
            order_anomaly=OrderAnomaly(
                price=Decimal("27200.0"),
                quantity=Decimal("30.0"),
                order_liquidity=Decimal("816000.00"),
                average_liquidity=Decimal("73833.33333333333333333333333"),
                position=0,
                type="bid",
            ),
        )
    }

    await worker._run_worker()

    assert mock_order_book_discord_messenger.send_notifications.call_count == 1

    assert worker._detected_anomalies == {
        AnomalyKey(price=Decimal("27200.0"), type="bid"): OrderAnomalyDto(
            time=current_time,
            order_anomaly=OrderAnomaly(
                price=Decimal("27200.0"),
                quantity=Decimal("30.0"),
                order_liquidity=Decimal("816000.00"),
                average_liquidity=Decimal("73833.33333333333333333333333"),
                position=0,
                type="bid",
            ),
        )
    }


@patch(
    "app.services.collectors.workers.orders_worker.OrderBookDiscordMessenger.send_notifications",
    new_callable=AsyncMock,
)
@patch(
    "app.services.collectors.workers.orders_worker.get_current_time",
)
async def test_passing_first_position_anomaly_and_adding_to_cache_if_input_anomaly_is_significantly_increased(
    mock_get_current_time: Mock,
    mock_order_book_discord_messenger: AsyncMock,
    collector: Collector,
) -> None:
    current_time = 2.5
    mock_get_current_time.return_value = current_time
    collector.order_book = OrderBookSnapshot(
        lastUpdateId=1,
        bids={
            Decimal("27200.0"): Decimal("60.0"),
            Decimal("27100.0"): Decimal("2.0"),
            Decimal("27000.0"): Decimal("5.2"),
            Decimal("26900.0"): Decimal("1.0"),
            Decimal("26800.0"): Decimal("4.0"),
        },
        asks={
            Decimal("27300.0"): Decimal("1.0"),
            Decimal("27400.0"): Decimal("1.0"),
            Decimal("27600.0"): Decimal("1.0"),
            Decimal("27500.0"): Decimal("4.0"),
            Decimal("27800.0"): Decimal("4.0"),
        },
    )
    worker = OrdersWorker(
        collector=collector,
        discord_messenger=mock_order_book_discord_messenger,
        order_anomaly_multiplier=5,
        anomalies_detection_ttl=3,
        anomalies_observing_ttl=1,
        anomalies_observing_ratio=0.2,
        anomalies_significantly_increased_ratio=2,
        top_n_orders=4,
    )

    worker._detected_anomalies = {
        AnomalyKey(price=Decimal("27200.0"), type="bid"): OrderAnomalyDto(
            time=1,
            order_anomaly=OrderAnomaly(
                price=Decimal("27200.0"),
                quantity=Decimal("30.0"),
                order_liquidity=Decimal("816000.00"),
                average_liquidity=Decimal("73833.33333333333333333333333"),
                position=0,
                type="bid",
            ),
        )
    }

    await worker._run_worker()

    assert mock_order_book_discord_messenger.send_notifications.call_count == 1

    assert worker._detected_anomalies == {
        AnomalyKey(price=Decimal("27200.0"), type="bid"): OrderAnomalyDto(
            time=current_time,
            order_anomaly=OrderAnomaly(
                price=Decimal("27200.0"),
                quantity=Decimal("60.0"),
                order_liquidity=Decimal("1632000.00"),
                average_liquidity=Decimal("73833.33333333333333333333333"),
                position=0,
                type="bid",
            ),
        )
    }


@patch(
    "app.services.collectors.workers.orders_worker.OrderBookDiscordMessenger.send_notifications",
    new_callable=AsyncMock,
)
@patch(
    "app.services.collectors.workers.orders_worker.get_current_time",
)
async def test_passing_non_first_position_anomaly_and_adding_to_cache_if_anomaly_key_not_exist_in_cache(
    mock_get_current_time: Mock,
    mock_order_book_discord_messenger: AsyncMock,
    collector: Collector,
) -> None:
    current_time = 2.5
    mock_get_current_time.return_value = current_time
    collector.order_book = OrderBookSnapshot(
        lastUpdateId=1,
        bids={
            Decimal("27200.0"): Decimal("1.0"),
            Decimal("27100.0"): Decimal("2.0"),
            Decimal("27000.0"): Decimal("5.2"),
            Decimal("26900.0"): Decimal("1.0"),
            Decimal("26800.0"): Decimal("4.0"),
        },
        asks={
            Decimal("27300.0"): Decimal("1.0"),
            Decimal("27400.0"): Decimal("1.0"),
            Decimal("27600.0"): Decimal("20.0"),
            Decimal("27500.0"): Decimal("4.0"),
            Decimal("27800.0"): Decimal("4.0"),
        },
    )
    worker = OrdersWorker(
        collector=collector,
        discord_messenger=mock_order_book_discord_messenger,
        order_anomaly_multiplier=5,
        anomalies_detection_ttl=4,
        anomalies_observing_ttl=4,
        anomalies_observing_ratio=0.2,
        top_n_orders=4,
    )

    worker._observing_anomalies = {}
    worker._detected_anomalies = {}

    await worker._run_worker()

    assert mock_order_book_discord_messenger.send_notifications.call_count == 0

    order_anomaly_dto = {
        AnomalyKey(price=Decimal("27600.0"), type="ask"): OrderAnomalyDto(
            time=2.5,
            order_anomaly=OrderAnomaly(
                price=Decimal("27600.0"),
                quantity=Decimal("20.0"),
                order_liquidity=Decimal("552000.00"),
                average_liquidity=Decimal("54900.00"),
                position=3,
                type="ask",
            ),
        )
    }
    assert worker._detected_anomalies == order_anomaly_dto

    assert worker._observing_anomalies == order_anomaly_dto


@patch(
    "app.services.collectors.workers.orders_worker.OrderBookDiscordMessenger.send_notifications",
    new_callable=AsyncMock,
)
@patch(
    "app.services.collectors.workers.orders_worker.get_current_time",
)
async def test_passing_non_first_position_anomaly_and_adding_to_cache_if_anomaly_key_is_expired_in_cache(
    mock_get_current_time: Mock,
    mock_order_book_discord_messenger: AsyncMock,
    collector: Collector,
) -> None:
    current_time = 5
    mock_get_current_time.return_value = current_time
    collector.order_book = OrderBookSnapshot(
        lastUpdateId=1,
        bids={
            Decimal("27200.0"): Decimal("1.0"),
            Decimal("27100.0"): Decimal("2.0"),
            Decimal("27000.0"): Decimal("5.2"),
            Decimal("26900.0"): Decimal("1.0"),
            Decimal("26800.0"): Decimal("4.0"),
        },
        asks={
            Decimal("27300.0"): Decimal("1.0"),
            Decimal("27400.0"): Decimal("1.0"),
            Decimal("27600.0"): Decimal("20.0"),
            Decimal("27500.0"): Decimal("4.0"),
            Decimal("27800.0"): Decimal("4.0"),
        },
    )
    worker = OrdersWorker(
        collector=collector,
        discord_messenger=mock_order_book_discord_messenger,
        order_anomaly_multiplier=5,
        anomalies_detection_ttl=2,
        anomalies_observing_ttl=1,
        anomalies_observing_ratio=0.2,
        top_n_orders=4,
    )

    worker._detected_anomalies = {
        AnomalyKey(price=Decimal("27600.0"), type="ask"): OrderAnomalyDto(
            time=2.5,
            order_anomaly=OrderAnomaly(
                price=Decimal("27600.0"),
                quantity=Decimal("20.0"),
                order_liquidity=Decimal("552000.00"),
                average_liquidity=Decimal("54900.00"),
                position=3,
                type="ask",
            ),
        )
    }

    await worker._run_worker()

    assert mock_order_book_discord_messenger.send_notifications.call_count == 0

    order_anomaly_dto = {
        AnomalyKey(price=Decimal("27600.0"), type="ask"): OrderAnomalyDto(
            time=current_time,
            order_anomaly=OrderAnomaly(
                price=Decimal("27600.0"),
                quantity=Decimal("20.0"),
                order_liquidity=Decimal("552000.00"),
                average_liquidity=Decimal("54900.00"),
                position=3,
                type="ask",
            ),
        )
    }
    assert worker._detected_anomalies == order_anomaly_dto

    assert worker._observing_anomalies == order_anomaly_dto


@patch(
    "app.services.collectors.workers.orders_worker.OrderBookDiscordMessenger.send_notifications",
    new_callable=AsyncMock,
)
@patch(
    "app.services.collectors.workers.orders_worker.get_current_time",
)
async def test_passing_non_first_position_anomaly_and_adding_to_cache_if_input_anomaly_is_significantly_increased(
    mock_get_current_time: Mock,
    mock_order_book_discord_messenger: AsyncMock,
    collector: Collector,
) -> None:
    current_time = 2.5
    mock_get_current_time.return_value = current_time
    collector.order_book = OrderBookSnapshot(
        lastUpdateId=1,
        bids={
            Decimal("27200.0"): Decimal("1.0"),
            Decimal("27100.0"): Decimal("2.0"),
            Decimal("27000.0"): Decimal("5.2"),
            Decimal("26900.0"): Decimal("1.0"),
            Decimal("26800.0"): Decimal("4.0"),
        },
        asks={
            Decimal("27300.0"): Decimal("1.0"),
            Decimal("27400.0"): Decimal("1.0"),
            Decimal("27600.0"): Decimal("40.0"),
            Decimal("27500.0"): Decimal("4.0"),
            Decimal("27800.0"): Decimal("4.0"),
        },
    )
    worker = OrdersWorker(
        collector=collector,
        discord_messenger=mock_order_book_discord_messenger,
        order_anomaly_multiplier=5,
        anomalies_detection_ttl=3,
        anomalies_observing_ttl=3,
        anomalies_observing_ratio=0.2,
        anomalies_significantly_increased_ratio=2,
        top_n_orders=4,
    )

    worker._detected_anomalies = {
        AnomalyKey(price=Decimal("27600.0"), type="ask"): OrderAnomalyDto(
            time=current_time,
            order_anomaly=OrderAnomaly(
                price=Decimal("27600.0"),
                quantity=Decimal("20.0"),
                order_liquidity=Decimal("552000.00"),
                average_liquidity=Decimal("54900.00"),
                position=3,
                type="ask",
            ),
        )
    }

    await worker._run_worker()

    assert mock_order_book_discord_messenger.send_notifications.call_count == 0

    order_anomaly_dto = {
        AnomalyKey(price=Decimal("27600.0"), type="ask"): OrderAnomalyDto(
            time=2.5,
            order_anomaly=OrderAnomaly(
                price=Decimal("27600.0"),
                quantity=Decimal("40.0"),
                order_liquidity=Decimal("1104000.00"),
                average_liquidity=Decimal("54900.00"),
                position=3,
                type="ask",
            ),
        )
    }

    assert worker._detected_anomalies == order_anomaly_dto

    assert worker._observing_anomalies == order_anomaly_dto


@patch(
    "app.services.collectors.workers.orders_worker.OrderBookDiscordMessenger.send_notifications",
    new_callable=AsyncMock,
)
@patch(
    "app.services.collectors.workers.orders_worker.get_current_time",
)
async def test_deleting_expired_keys_from_cache_that_doesnt_exist_in_order_book(
    mock_get_current_time: Mock,
    mock_order_book_discord_messenger: AsyncMock,
    collector: Collector,
) -> None:
    current_time = 10
    mock_get_current_time.return_value = current_time
    collector.order_book = OrderBookSnapshot(
        lastUpdateId=1,
        bids={
            Decimal("27200.0"): Decimal("1.0"),
            Decimal("27100.0"): Decimal("2.0"),
            Decimal("27000.0"): Decimal("5.2"),
            Decimal("26900.0"): Decimal("1.0"),
            Decimal("26800.0"): Decimal("4.0"),
        },
        asks={
            Decimal("27300.0"): Decimal("1.0"),
            Decimal("27400.0"): Decimal("1.0"),
            Decimal("27600.0"): Decimal("4.0"),
            Decimal("27500.0"): Decimal("4.0"),
            Decimal("27800.0"): Decimal("4.0"),
        },
    )
    worker = OrdersWorker(
        collector=collector,
        discord_messenger=mock_order_book_discord_messenger,
        order_anomaly_multiplier=5,
        anomalies_detection_ttl=3,
        anomalies_observing_ttl=5,
        anomalies_observing_ratio=0.2,
        anomalies_significantly_increased_ratio=2,
        top_n_orders=4,
    )

    worker._detected_anomalies = {
        AnomalyKey(price=Decimal("27900.0"), type="ask"): OrderAnomalyDto(
            time=2,
            order_anomaly=OrderAnomaly(
                price=Decimal("27900.0"),
                quantity=Decimal("20.0"),
                order_liquidity=Decimal("552000.00"),
                average_liquidity=Decimal("54900.00"),
                position=3,
                type="ask",
            ),
        )
    }

    await worker._run_worker()

    assert worker._detected_anomalies == {}
