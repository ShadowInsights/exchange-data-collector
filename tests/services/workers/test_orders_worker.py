from decimal import Decimal
from typing import AsyncGenerator
from unittest.mock import AsyncMock, Mock, patch
from uuid import UUID

import pytest

from app.application.common.collector import Collector
from app.application.common.processor import Processor
from app.application.workers.orders_worker import (AnomalyKey, OrderAnomaly,
                                                   OrderAnomalyInTime,
                                                   OrderAnomalySaved,
                                                   OrdersWorker)
from app.infrastructure.clients.order_book_client.schemas.common import (
    OrderBook, OrderBookEvent)
from app.infrastructure.db.models.order_book_anomaly import \
    OrderBookAnomalyModel
from app.utilities.event_utils import EventHandler


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

    async def _broadcast_stream(self) -> AsyncGenerator[OrderBookEvent, None]:
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
    "app.application.workers.orders_worker.create_order_book_anomalies",
    new_callable=AsyncMock,
)
@patch(
    "app.application.workers.orders_worker.OrdersWorker._send_anomalies",
    new_callable=AsyncMock,
)
@patch(
    "app.application.workers.orders_worker.get_current_time",
)
async def test_valid_anomaly_detection_first_positions_not_match_liquidity(
    mock_get_current_time: Mock,
    mock_send_anomalies: AsyncMock,
    mock_create_order_book_anomalies: AsyncMock,
    processor: Processor,
) -> None:
    current_time = 1.0
    mock_get_current_time.return_value = current_time
    processor._order_book = OrderBook(
        b={
            Decimal("27200.0"): Decimal("9.0"),
            Decimal("27100.0"): Decimal("2.0"),
            Decimal("27000.0"): Decimal("3.0"),
            Decimal("26900.0"): Decimal("1.0"),
            Decimal("26800.0"): Decimal("20.0"),
        },
        a={
            Decimal("27300.0"): Decimal("9.0"),
            Decimal("27400.0"): Decimal("1.0"),
            Decimal("27500.0"): Decimal("1.0"),
            Decimal("27600.0"): Decimal("1.0"),
            Decimal("27800.0"): Decimal("20.0"),
        },
    )
    worker = OrdersWorker(
        processor=processor,
        order_anomaly_multiplier=1.5,
        anomalies_detection_ttl=1,
        anomalies_observing_ttl=1,
        anomalies_observing_ratio=0.5,
        top_n_orders=4,
    )

    await worker._run_worker()

    assert mock_send_anomalies.call_count == 1
    assert mock_create_order_book_anomalies.call_count == 1

    order_anomaly_notifications_call = mock_send_anomalies.call_args_list[0]
    order_anomaly_notifications = order_anomaly_notifications_call[0][0]

    order_anomalies_creation_call = (
        mock_create_order_book_anomalies.call_args_list[0]
    )
    order_anomalies_creation = order_anomalies_creation_call[0][1]

    expected_notifications = [
        OrderAnomaly(
            price=Decimal("27300.0"),
            quantity=Decimal("9.0"),
            order_liquidity=Decimal("245700.00"),
            average_liquidity=Decimal("27500.00"),
            position=0,
            type="ask",
        ),
        OrderAnomaly(
            price=Decimal("27200.0"),
            quantity=Decimal("9.0"),
            order_liquidity=Decimal("244800.00"),
            average_liquidity=Decimal("54033.33333333333333333333333"),
            position=0,
            type="bid",
        ),
    ]
    expected_models = [
        OrderBookAnomalyModel(
            price=Decimal("27300.0"),
            quantity=Decimal("9.0"),
            order_liquidity=Decimal("245700.00"),
            average_liquidity=Decimal("27500.00"),
            type="ask",
            position=0,
            is_cancelled=False,
        ),
        OrderBookAnomalyModel(
            price=Decimal("27200.0"),
            quantity=Decimal("9.0"),
            order_liquidity=Decimal("244800.00"),
            average_liquidity=Decimal("54033.33333333333333333333333"),
            type="bid",
            position=0,
            is_cancelled=False,
        ),
    ]

    assert order_anomaly_notifications == expected_notifications

    assert order_anomalies_creation[0].price == expected_models[0].price
    assert order_anomalies_creation[0].quantity == expected_models[0].quantity
    assert (
        order_anomalies_creation[0].order_liquidity
        == expected_models[0].order_liquidity
    )
    assert (
        order_anomalies_creation[0].average_liquidity
        == expected_models[0].average_liquidity
    )
    assert order_anomalies_creation[0].type == expected_models[0].type
    assert order_anomalies_creation[0].position == expected_models[0].position
    assert (
        order_anomalies_creation[0].is_cancelled
        == expected_models[0].is_cancelled
    )

    assert order_anomalies_creation[1].price == expected_models[1].price
    assert order_anomalies_creation[1].quantity == expected_models[1].quantity
    assert (
        order_anomalies_creation[1].order_liquidity
        == expected_models[1].order_liquidity
    )
    assert (
        order_anomalies_creation[1].average_liquidity
        == expected_models[1].average_liquidity
    )
    assert order_anomalies_creation[1].type == expected_models[1].type
    assert order_anomalies_creation[1].position == expected_models[1].position
    assert (
        order_anomalies_creation[1].is_cancelled
        == expected_models[1].is_cancelled
    )

    assert len(worker._observing_saved_limit_anomalies) == 0

    assert worker._detected_anomalies == {
        AnomalyKey(price=Decimal("27300.0"), type="ask"): OrderAnomalyInTime(
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
        AnomalyKey(price=Decimal("27200.0"), type="bid"): OrderAnomalyInTime(
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
    "app.application.workers.orders_worker.create_order_book_anomalies",
    new_callable=AsyncMock,
)
@patch(
    "app.application.workers.orders_worker.OrdersWorker._send_anomalies",
    new_callable=AsyncMock,
)
@patch(
    "app.application.workers.orders_worker.get_current_time",
)
async def test_valid_anomaly_detection_and_put_for_observe_non_first_positions(
    mock_get_current_time: Mock,
    mock_send_anomalies: AsyncMock,
    mock_create_order_book_anomalies: AsyncMock,
    processor: Processor,
) -> None:
    current_time = 1.0
    mock_get_current_time.return_value = current_time
    processor._order_book = OrderBook(
        b={
            Decimal("27200.0"): Decimal("1.0"),
            Decimal("27100.0"): Decimal("2.0"),
            Decimal("27000.0"): Decimal("9.0"),
            Decimal("26900.0"): Decimal("1.0"),
            Decimal("26800.0"): Decimal("20.0"),
        },
        a={
            Decimal("27300.0"): Decimal("1.0"),
            Decimal("27400.0"): Decimal("1.0"),
            Decimal("27600.0"): Decimal("1.0"),
            Decimal("27500.0"): Decimal("9.0"),
            Decimal("27800.0"): Decimal("20.0"),
        },
    )
    worker = OrdersWorker(
        processor=processor,
        order_anomaly_multiplier=1.5,
        anomalies_detection_ttl=1,
        anomalies_observing_ttl=1,
        anomalies_observing_ratio=0.5,
        top_n_orders=4,
    )

    await worker._run_worker()

    assert mock_send_anomalies.call_count == 0
    assert mock_create_order_book_anomalies.call_count == 0
    assert worker._detected_anomalies == {
        AnomalyKey(price=Decimal("27500.0"), type="ask"): OrderAnomalyInTime(
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
        AnomalyKey(price=Decimal("27000.0"), type="bid"): OrderAnomalyInTime(
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
        AnomalyKey(price=Decimal("27500.0"), type="ask"): OrderAnomalyInTime(
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
        AnomalyKey(price=Decimal("27000.0"), type="bid"): OrderAnomalyInTime(
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
    "app.application.workers.orders_worker.create_order_book_anomalies",
    new_callable=AsyncMock,
)
@patch(
    "app.application.workers.orders_worker.OrdersWorker._send_anomalies",
    new_callable=AsyncMock,
)
@patch(
    "app.application.workers.orders_worker.get_current_time",
)
async def test_non_first_already_observing_anomalies_for_notification_after_expiration_of_observing_ttl(
    mock_get_current_time: Mock,
    mock_send_anomalies: AsyncMock,
    mock_create_order_book_anomalies: AsyncMock,
    processor: Processor,
) -> None:
    current_time = 2.5
    mock_get_current_time.return_value = current_time
    processor._order_book = OrderBook(
        b={
            Decimal("27200.0"): Decimal("1.0"),
            Decimal("27100.0"): Decimal("2.0"),
            Decimal("27000.0"): Decimal("8.2"),
            Decimal("26900.0"): Decimal("1.0"),
            Decimal("26800.0"): Decimal("20.0"),
        },
        a={
            Decimal("27300.0"): Decimal("1.0"),
            Decimal("27400.0"): Decimal("1.0"),
            Decimal("27600.0"): Decimal("1.0"),
            Decimal("27500.0"): Decimal("8.0"),
            Decimal("27800.0"): Decimal("20.0"),
        },
    )
    worker = OrdersWorker(
        processor=processor,
        order_anomaly_multiplier=1.5,
        anomalies_detection_ttl=1,
        anomalies_observing_ttl=1,
        anomalies_observing_ratio=0.2,
        top_n_orders=4,
    )
    worker._observing_anomalies = {
        AnomalyKey(price=Decimal("27500.0"), type="ask"): OrderAnomalyInTime(
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
        AnomalyKey(price=Decimal("27000.0"), type="bid"): OrderAnomalyInTime(
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

    assert mock_send_anomalies.call_count == 1
    assert mock_create_order_book_anomalies.call_count == 1

    order_anomaly_notifications_call = mock_send_anomalies.call_args_list[0]
    order_anomaly_notifications = order_anomaly_notifications_call[0][0]

    expected_notifications = [
        OrderAnomaly(
            price=Decimal("27500.0"),
            quantity=Decimal("8.0"),
            order_liquidity=Decimal("220000.00"),
            average_liquidity=Decimal("27433.33333333333333333333333"),
            position=2,
            type="ask",
        ),
        OrderAnomaly(
            price=Decimal("27000.0"),
            quantity=Decimal("8.2"),
            order_liquidity=Decimal("221400.00"),
            average_liquidity=Decimal("36100.00"),
            position=2,
            type="bid",
        ),
    ]

    assert order_anomaly_notifications == expected_notifications


@patch(
    "app.application.workers.orders_worker.create_order_book_anomalies",
    new_callable=AsyncMock,
)
@patch(
    "app.application.workers.orders_worker.get_current_time",
)
async def test_real_orders_valid_processing_when_new_one_appears(
    mock_get_current_time: Mock,
    mock_create_order_book_anomalies: AsyncMock,
    processor: Processor,
) -> None:
    current_time = 2.5
    mock_get_current_time.return_value = current_time
    processor._order_book = OrderBook(
        b={
            Decimal("27200.0"): Decimal("1.0"),
            Decimal("27100.0"): Decimal("2.0"),
            Decimal("27000.0"): Decimal("8.2"),
            Decimal("26900.0"): Decimal("1.0"),
            Decimal("26800.0"): Decimal("20.0"),
        },
        a={
            Decimal("27300.0"): Decimal("1.0"),
            Decimal("27400.0"): Decimal("20.0"),
            Decimal("27600.0"): Decimal("1.0"),
            Decimal("27500.0"): Decimal("8.0"),
            Decimal("27800.0"): Decimal("20.0"),
        },
    )
    worker = OrdersWorker(
        processor=processor,
        order_anomaly_multiplier=1.5,
        anomalies_detection_ttl=1,
        anomalies_observing_ttl=1,
        anomalies_observing_ratio=0.2,
        top_n_orders=4,
    )
    worker._observing_anomalies = {
        AnomalyKey(price=Decimal("27500.0"), type="ask"): OrderAnomalyInTime(
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
        AnomalyKey(price=Decimal("27000.0"), type="bid"): OrderAnomalyInTime(
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
        AnomalyKey(price=Decimal("27400.0"), type="ask"): OrderAnomalyInTime(
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
    "app.application.workers.orders_worker.get_current_time",
)
async def test_real_orders_observing_does_not_exist(
    mock_get_current_time: Mock,
    processor: Processor,
) -> None:
    current_time = 2.5
    mock_get_current_time.return_value = current_time
    processor._order_book = OrderBook(
        b={
            Decimal("33000.0"): Decimal("1.0"),
            Decimal("37100.0"): Decimal("1.0"),
            Decimal("37000.0"): Decimal("1.2"),
            Decimal("36900.0"): Decimal("1.0"),
            Decimal("36800.0"): Decimal("1.0"),
        },
        a={
            Decimal("37300.0"): Decimal("1.0"),
            Decimal("37400.0"): Decimal("1.0"),
            Decimal("37600.0"): Decimal("1.0"),
            Decimal("37500.0"): Decimal("1.0"),
            Decimal("37800.0"): Decimal("1.0"),
        },
    )
    worker = OrdersWorker(
        processor=processor,
        order_anomaly_multiplier=1.5,
        anomalies_detection_ttl=1,
        anomalies_observing_ttl=1,
        anomalies_observing_ratio=0.2,
        top_n_orders=4,
    )
    worker._observing_anomalies = {
        AnomalyKey(price=Decimal("27500.0"), type="ask"): OrderAnomalyInTime(
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
        AnomalyKey(price=Decimal("27000.0"), type="bid"): OrderAnomalyInTime(
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
    "app.application.workers.orders_worker.OrdersWorker._send_anomalies",
    new_callable=AsyncMock,
)
@patch(
    "app.application.workers.orders_worker.get_current_time",
)
async def test_real_orders_valid_processing_changed_more_than_ratio(
    mock_get_current_time: Mock,
    mock_send_anomalies: AsyncMock,
    processor: Processor,
) -> None:
    current_time = 2.5
    mock_get_current_time.return_value = current_time
    processor._order_book = OrderBook(
        b={
            Decimal("27200.0"): Decimal("1.0"),
            Decimal("27100.0"): Decimal("2.0"),
            Decimal("27000.0"): Decimal("5.2"),
            Decimal("26900.0"): Decimal("1.0"),
            Decimal("26800.0"): Decimal("20.0"),
        },
        a={
            Decimal("27300.0"): Decimal("1.0"),
            Decimal("27400.0"): Decimal("1.0"),
            Decimal("27600.0"): Decimal("1.0"),
            Decimal("27500.0"): Decimal("4.0"),
            Decimal("27800.0"): Decimal("20.0"),
        },
    )
    worker = OrdersWorker(
        processor=processor,
        order_anomaly_multiplier=1.5,
        anomalies_detection_ttl=1,
        anomalies_observing_ttl=1,
        anomalies_observing_ratio=0.2,
        top_n_orders=4,
    )
    worker._observing_anomalies = {
        AnomalyKey(price=Decimal("27500.0"), type="ask"): OrderAnomalyInTime(
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
        AnomalyKey(price=Decimal("27000.0"), type="bid"): OrderAnomalyInTime(
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

    assert mock_send_anomalies.call_count == 0


@patch(
    "app.application.workers.orders_worker.OrdersWorker._send_anomalies",
    new_callable=AsyncMock,
)
@patch(
    "app.application.workers.orders_worker.get_current_time",
)
async def test_real_orders_nothing_match_order_anomaly_multiplier(
    mock_get_current_time: Mock,
    mock_send_anomalies: AsyncMock,
    processor: Processor,
) -> None:
    current_time = 2.5
    mock_get_current_time.return_value = current_time
    processor._order_book = OrderBook(
        b={
            Decimal("27200.0"): Decimal("1.0"),
            Decimal("27100.0"): Decimal("2.0"),
            Decimal("27000.0"): Decimal("5.2"),
            Decimal("26900.0"): Decimal("1.0"),
            Decimal("26800.0"): Decimal("20.0"),
        },
        a={
            Decimal("27300.0"): Decimal("1.0"),
            Decimal("27400.0"): Decimal("1.0"),
            Decimal("27600.0"): Decimal("1.0"),
            Decimal("27500.0"): Decimal("4.0"),
            Decimal("27800.0"): Decimal("20.0"),
        },
    )
    worker = OrdersWorker(
        processor=processor,
        order_anomaly_multiplier=20,
        anomalies_detection_ttl=1,
        anomalies_observing_ttl=1,
        anomalies_observing_ratio=0.2,
        top_n_orders=4,
    )

    await worker._run_worker()

    assert worker._observing_anomalies == {}

    assert mock_send_anomalies.call_count == 0


@patch(
    "app.application.workers.orders_worker.OrdersWorker._send_anomalies",
    new_callable=AsyncMock,
)
@patch(
    "app.application.workers.orders_worker.get_current_time",
)
async def test_skipping_the_first_position_anomaly_that_has_non_expired_key_in_cache(
    mock_get_current_time: Mock,
    mock_send_anomalies: AsyncMock,
    processor: Processor,
) -> None:
    current_time = 2.5
    mock_get_current_time.return_value = current_time
    processor._order_book = OrderBook(
        b={
            Decimal("27200.0"): Decimal("30.0"),
            Decimal("27100.0"): Decimal("2.0"),
            Decimal("27000.0"): Decimal("5.2"),
            Decimal("26900.0"): Decimal("1.0"),
            Decimal("26800.0"): Decimal("4.0"),
        },
        a={
            Decimal("27300.0"): Decimal("1.0"),
            Decimal("27400.0"): Decimal("1.0"),
            Decimal("27600.0"): Decimal("1.0"),
            Decimal("27500.0"): Decimal("4.0"),
            Decimal("27800.0"): Decimal("4.0"),
        },
    )
    worker = OrdersWorker(
        processor=processor,
        order_anomaly_multiplier=5,
        anomalies_detection_ttl=4,
        anomalies_observing_ttl=1,
        anomalies_observing_ratio=0.2,
        top_n_orders=4,
    )

    worker._detected_anomalies = {
        AnomalyKey(price=Decimal("27200.0"), type="bid"): OrderAnomalyInTime(
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

    assert mock_send_anomalies.call_count == 0


@patch(
    "app.application.workers.orders_worker.OrdersWorker._send_anomalies",
    new_callable=AsyncMock,
)
@patch(
    "app.application.workers.orders_worker.get_current_time",
)
async def test_skipping_non_first_position_anomaly_that_has_non_expired_key_in_cache_and_not_observing(
    mock_get_current_time: Mock,
    mock_order_book_discord_messenger: AsyncMock,
    processor: Processor,
) -> None:
    current_time = 2.5
    mock_get_current_time.return_value = current_time
    processor._order_book = OrderBook(
        b={
            Decimal("27200.0"): Decimal("2.0"),
            Decimal("27100.0"): Decimal("2.0"),
            Decimal("27000.0"): Decimal("1.2"),
            Decimal("26900.0"): Decimal("1.0"),
            Decimal("26800.0"): Decimal("20.0"),
        },
        a={
            Decimal("27300.0"): Decimal("1.0"),
            Decimal("27400.0"): Decimal("1.0"),
            Decimal("27600.0"): Decimal("1.0"),
            Decimal("27500.0"): Decimal("4.0"),
            Decimal("27800.0"): Decimal("4.0"),
        },
    )
    worker = OrdersWorker(
        processor=processor,
        order_anomaly_multiplier=6,
        anomalies_detection_ttl=4,
        anomalies_observing_ttl=4,
        anomalies_observing_ratio=0.2,
        top_n_orders=5,
    )

    order_anomaly = {
        AnomalyKey(price=Decimal("26800.0"), type="bid"): OrderAnomalyInTime(
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

    assert (
        mock_order_book_discord_messenger.send_anomaly_detection_notifications.call_count
        == 0
    )

    assert worker._observing_anomalies == {}

    assert worker._detected_anomalies == order_anomaly


@patch(
    "app.application.workers.orders_worker.create_order_book_anomalies",
    new_callable=AsyncMock,
)
@patch(
    "app.application.workers.orders_worker.OrdersWorker._send_anomalies",
    new_callable=AsyncMock,
)
@patch(
    "app.application.workers.orders_worker.get_current_time",
)
async def test_passing_first_position_anomaly_and_adding_to_cache_if_anomaly_key_not_exist_in_cache(
    mock_get_current_time: Mock,
    mock_send_anomalies: AsyncMock,
    mock_create_order_book_anomalies: AsyncMock,
    processor: Processor,
) -> None:
    current_time = 2.5
    mock_get_current_time.return_value = current_time
    processor._order_book = OrderBook(
        b={
            Decimal("27200.0"): Decimal("30.0"),
            Decimal("27100.0"): Decimal("2.0"),
            Decimal("27000.0"): Decimal("5.2"),
            Decimal("26900.0"): Decimal("1.0"),
            Decimal("26800.0"): Decimal("4.0"),
        },
        a={
            Decimal("27300.0"): Decimal("1.0"),
            Decimal("27400.0"): Decimal("1.0"),
            Decimal("27600.0"): Decimal("1.0"),
            Decimal("27500.0"): Decimal("4.0"),
            Decimal("27800.0"): Decimal("4.0"),
        },
    )
    worker = OrdersWorker(
        processor=processor,
        order_anomaly_multiplier=5,
        anomalies_detection_ttl=4,
        anomalies_observing_ttl=1,
        anomalies_observing_ratio=0.2,
        top_n_orders=4,
    )

    await worker._run_worker()

    assert mock_send_anomalies.call_count == 1
    assert mock_create_order_book_anomalies.call_count == 1

    assert worker._detected_anomalies == {
        AnomalyKey(price=Decimal("27200.0"), type="bid"): OrderAnomalyInTime(
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
    "app.application.workers.orders_worker.create_order_book_anomalies",
    new_callable=AsyncMock,
)
@patch(
    "app.application.workers.orders_worker.OrdersWorker._send_anomalies",
    new_callable=AsyncMock,
)
@patch(
    "app.application.workers.orders_worker.get_current_time",
)
async def test_passing_first_position_anomaly_and_adding_to_cache_if_anomaly_key_is_expired_in_cache(
    mock_get_current_time: Mock,
    mock_send_anomalies: AsyncMock,
    mock_create_order_book_anomalies: AsyncMock,
    processor: Processor,
) -> None:
    current_time = 5
    mock_get_current_time.return_value = current_time
    processor._order_book = OrderBook(
        b={
            Decimal("27200.0"): Decimal("30.0"),
            Decimal("27100.0"): Decimal("2.0"),
            Decimal("27000.0"): Decimal("5.2"),
            Decimal("26900.0"): Decimal("1.0"),
            Decimal("26800.0"): Decimal("4.0"),
        },
        a={
            Decimal("27300.0"): Decimal("1.0"),
            Decimal("27400.0"): Decimal("1.0"),
            Decimal("27600.0"): Decimal("1.0"),
            Decimal("27500.0"): Decimal("4.0"),
            Decimal("27800.0"): Decimal("4.0"),
        },
    )
    worker = OrdersWorker(
        processor=processor,
        order_anomaly_multiplier=5,
        anomalies_detection_ttl=2,
        anomalies_observing_ttl=1,
        anomalies_observing_ratio=0.2,
        top_n_orders=4,
    )

    worker._detected_anomalies = {
        AnomalyKey(price=Decimal("27200.0"), type="bid"): OrderAnomalyInTime(
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

    assert mock_send_anomalies.call_count == 1
    assert mock_create_order_book_anomalies.call_count == 1

    assert worker._detected_anomalies == {
        AnomalyKey(price=Decimal("27200.0"), type="bid"): OrderAnomalyInTime(
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
    "app.application.workers.orders_worker.create_order_book_anomalies",
    new_callable=AsyncMock,
)
@patch(
    "app.application.workers.orders_worker.OrdersWorker._send_anomalies",
    new_callable=AsyncMock,
)
@patch(
    "app.application.workers.orders_worker.get_current_time",
)
async def test_passing_first_position_anomaly_and_adding_to_cache_if_input_anomaly_is_significantly_increased(
    mock_get_current_time: Mock,
    mock_send_anomalies: AsyncMock,
    mock_create_order_book_anomalies: AsyncMock,
    processor: Processor,
) -> None:
    current_time = 2.5
    mock_get_current_time.return_value = current_time
    processor._order_book = OrderBook(
        b={
            Decimal("27200.0"): Decimal("60.0"),
            Decimal("27100.0"): Decimal("2.0"),
            Decimal("27000.0"): Decimal("5.2"),
            Decimal("26900.0"): Decimal("1.0"),
            Decimal("26800.0"): Decimal("4.0"),
        },
        a={
            Decimal("27300.0"): Decimal("1.0"),
            Decimal("27400.0"): Decimal("1.0"),
            Decimal("27600.0"): Decimal("1.0"),
            Decimal("27500.0"): Decimal("4.0"),
            Decimal("27800.0"): Decimal("4.0"),
        },
    )
    worker = OrdersWorker(
        processor=processor,
        order_anomaly_multiplier=5,
        anomalies_detection_ttl=3,
        anomalies_observing_ttl=1,
        anomalies_observing_ratio=0.2,
        top_n_orders=4,
        anomalies_significantly_increased_ratio=2,
    )

    worker._detected_anomalies = {
        AnomalyKey(price=Decimal("27200.0"), type="bid"): OrderAnomalyInTime(
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

    assert mock_send_anomalies.call_count == 1
    assert mock_create_order_book_anomalies.call_count == 1

    assert worker._detected_anomalies == {
        AnomalyKey(price=Decimal("27200.0"), type="bid"): OrderAnomalyInTime(
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
    "app.application.workers.orders_worker.OrdersWorker._send_anomalies",
    new_callable=AsyncMock,
)
@patch(
    "app.application.workers.orders_worker.get_current_time",
)
async def test_passing_non_first_position_anomaly_and_adding_to_cache_if_anomaly_key_not_exist_in_cache(
    mock_get_current_time: Mock,
    mock_send_anomalies: AsyncMock,
    processor: Processor,
) -> None:
    current_time = 2.5
    mock_get_current_time.return_value = current_time
    processor._order_book = OrderBook(
        b={
            Decimal("27200.0"): Decimal("1.0"),
            Decimal("27100.0"): Decimal("2.0"),
            Decimal("27000.0"): Decimal("5.2"),
            Decimal("26900.0"): Decimal("1.0"),
            Decimal("26800.0"): Decimal("4.0"),
        },
        a={
            Decimal("27300.0"): Decimal("1.0"),
            Decimal("27400.0"): Decimal("1.0"),
            Decimal("27600.0"): Decimal("20.0"),
            Decimal("27500.0"): Decimal("4.0"),
            Decimal("27800.0"): Decimal("4.0"),
        },
    )
    worker = OrdersWorker(
        processor=processor,
        order_anomaly_multiplier=5,
        anomalies_detection_ttl=4,
        anomalies_observing_ttl=4,
        anomalies_observing_ratio=0.2,
        top_n_orders=4,
    )

    worker._observing_anomalies = {}
    worker._detected_anomalies = {}

    await worker._run_worker()

    assert mock_send_anomalies.call_count == 0

    order_anomaly_dto = {
        AnomalyKey(price=Decimal("27600.0"), type="ask"): OrderAnomalyInTime(
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
    "app.application.workers.orders_worker.OrdersWorker._send_anomalies",
    new_callable=AsyncMock,
)
@patch(
    "app.application.workers.orders_worker.get_current_time",
)
async def test_passing_non_first_position_anomaly_and_adding_to_cache_if_anomaly_key_is_expired_in_cache(
    mock_get_current_time: Mock,
    mock_send_anomalies: AsyncMock,
    processor: Processor,
) -> None:
    current_time = 5
    mock_get_current_time.return_value = current_time
    processor._order_book = OrderBook(
        b={
            Decimal("27200.0"): Decimal("1.0"),
            Decimal("27100.0"): Decimal("2.0"),
            Decimal("27000.0"): Decimal("5.2"),
            Decimal("26900.0"): Decimal("1.0"),
            Decimal("26800.0"): Decimal("4.0"),
        },
        a={
            Decimal("27300.0"): Decimal("1.0"),
            Decimal("27400.0"): Decimal("1.0"),
            Decimal("27600.0"): Decimal("20.0"),
            Decimal("27500.0"): Decimal("4.0"),
            Decimal("27800.0"): Decimal("4.0"),
        },
    )
    worker = OrdersWorker(
        processor=processor,
        order_anomaly_multiplier=5,
        anomalies_detection_ttl=2,
        anomalies_observing_ttl=1,
        anomalies_observing_ratio=0.2,
        top_n_orders=4,
    )

    worker._detected_anomalies = {
        AnomalyKey(price=Decimal("27600.0"), type="ask"): OrderAnomalyInTime(
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

    assert mock_send_anomalies.call_count == 0

    order_anomaly_dto = {
        AnomalyKey(price=Decimal("27600.0"), type="ask"): OrderAnomalyInTime(
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
    "app.application.workers.orders_worker.OrdersWorker._send_anomalies",
    new_callable=AsyncMock,
)
@patch(
    "app.application.workers.orders_worker.get_current_time",
)
async def test_passing_non_first_position_anomaly_and_adding_to_cache_if_input_anomaly_is_significantly_increased(
    mock_get_current_time: Mock,
    mock_send_anomalies: AsyncMock,
    processor: Processor,
) -> None:
    current_time = 2.5
    mock_get_current_time.return_value = current_time
    processor._order_book = OrderBook(
        b={
            Decimal("27200.0"): Decimal("1.0"),
            Decimal("27100.0"): Decimal("2.0"),
            Decimal("27000.0"): Decimal("5.2"),
            Decimal("26900.0"): Decimal("1.0"),
            Decimal("26800.0"): Decimal("4.0"),
        },
        a={
            Decimal("27300.0"): Decimal("1.0"),
            Decimal("27400.0"): Decimal("1.0"),
            Decimal("27600.0"): Decimal("40.0"),
            Decimal("27500.0"): Decimal("4.0"),
            Decimal("27800.0"): Decimal("4.0"),
        },
    )
    worker = OrdersWorker(
        processor=processor,
        order_anomaly_multiplier=5,
        anomalies_detection_ttl=3,
        anomalies_observing_ttl=3,
        anomalies_observing_ratio=0.2,
        top_n_orders=4,
        anomalies_significantly_increased_ratio=2,
    )

    worker._detected_anomalies = {
        AnomalyKey(price=Decimal("27600.0"), type="ask"): OrderAnomalyInTime(
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

    assert mock_send_anomalies.call_count == 0

    order_anomaly_dto = {
        AnomalyKey(price=Decimal("27600.0"), type="ask"): OrderAnomalyInTime(
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
    "app.application.workers.orders_worker.OrdersWorker._send_anomalies",
    new_callable=AsyncMock,
)
@patch(
    "app.application.workers.orders_worker.get_current_time",
)
async def test_deleting_expired_keys_from_cache_that_doesnt_exist_in_order_book(
    mock_get_current_time: Mock,
    mock_send_anomalies: AsyncMock,
    processor: Processor,
) -> None:
    current_time = 10
    mock_get_current_time.return_value = current_time
    processor._order_book = OrderBook(
        b={
            Decimal("27200.0"): Decimal("1.0"),
            Decimal("27100.0"): Decimal("2.0"),
            Decimal("27000.0"): Decimal("5.2"),
            Decimal("26900.0"): Decimal("1.0"),
            Decimal("26800.0"): Decimal("4.0"),
        },
        a={
            Decimal("27300.0"): Decimal("1.0"),
            Decimal("27400.0"): Decimal("1.0"),
            Decimal("27600.0"): Decimal("4.0"),
            Decimal("27500.0"): Decimal("4.0"),
            Decimal("27800.0"): Decimal("4.0"),
        },
    )
    worker = OrdersWorker(
        processor=processor,
        order_anomaly_multiplier=5,
        anomalies_detection_ttl=3,
        anomalies_observing_ttl=5,
        anomalies_observing_ratio=0.2,
        top_n_orders=4,
        anomalies_significantly_increased_ratio=2,
    )

    worker._detected_anomalies = {
        AnomalyKey(price=Decimal("27900.0"), type="ask"): OrderAnomalyInTime(
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


@patch(
    "app.application.workers.orders_worker.OrdersWorker._send_anomalies",
    new_callable=AsyncMock,
)
@patch(
    "app.application.workers.orders_worker.get_current_time",
)
async def test_valid_anomaly_detection_first_positions_not_match_minimum_liquidity(
    mock_get_current_time: Mock,
    mock_send_anomalies: AsyncMock,
    processor: Processor,
) -> None:
    current_time = 1.0
    mock_get_current_time.return_value = current_time
    processor._order_book = OrderBook(
        b={
            Decimal("27200.0"): Decimal("9.0"),
            Decimal("27100.0"): Decimal("2.0"),
            Decimal("27000.0"): Decimal("3.0"),
            Decimal("26900.0"): Decimal("1.0"),
            Decimal("26800.0"): Decimal("20.0"),
        },
        a={
            Decimal("27300.0"): Decimal("9.0"),
            Decimal("27400.0"): Decimal("1.0"),
            Decimal("27500.0"): Decimal("1.0"),
            Decimal("27600.0"): Decimal("1.0"),
            Decimal("27800.0"): Decimal("20.0"),
        },
    )
    worker = OrdersWorker(
        processor=processor,
        order_anomaly_multiplier=1.5,
        anomalies_detection_ttl=1,
        anomalies_observing_ttl=1,
        anomalies_observing_ratio=0.5,
        top_n_orders=4,
        order_anomaly_minimum_liquidity=100000000.0,
    )

    await worker._run_worker()

    assert mock_send_anomalies.call_count == 0
    assert worker._detected_anomalies == {}
    assert worker._observing_anomalies == {}


@patch(
    "app.application.workers.orders_worker.OrdersWorker._send_anomalies",
    new_callable=AsyncMock,
)
@patch(
    "app.application.workers.orders_worker.get_current_time",
)
async def test_valid_anomaly_detection_valid_match_maximum_anomalies_per_overbook_none_found(
    mock_get_current_time: Mock,
    mock_send_anomalies: AsyncMock,
    processor: Processor,
) -> None:
    current_time = 1.0
    mock_get_current_time.return_value = current_time
    processor._order_book = OrderBook(
        b={
            Decimal("27300.0"): Decimal("1.5"),
            Decimal("27400.0"): Decimal("1.5"),
            Decimal("27500.0"): Decimal("1.5"),
            Decimal("27600.0"): Decimal("3.0"),
            Decimal("27800.0"): Decimal("3.0"),
        },
        a={
            Decimal("27300.0"): Decimal("1.5"),
            Decimal("27400.0"): Decimal("1.5"),
            Decimal("27500.0"): Decimal("1.5"),
            Decimal("27600.0"): Decimal("3.0"),
            Decimal("27800.0"): Decimal("3.0"),
        },
    )
    worker = OrdersWorker(
        processor=processor,
        order_anomaly_multiplier=1.5,
        anomalies_detection_ttl=1,
        anomalies_observing_ttl=1,
        anomalies_observing_ratio=0.5,
        top_n_orders=5,
        order_anomaly_minimum_liquidity=1000.0,
        maximum_order_book_anomalies=1,
    )

    await worker._run_worker()

    assert mock_send_anomalies.call_count == 0
    assert worker._detected_anomalies == {}
    assert worker._observing_anomalies == {}


@patch(
    "app.application.workers.orders_worker.create_order_book_anomalies",
    new_callable=AsyncMock,
)
@patch(
    "app.application.workers.orders_worker.OrdersWorker._send_anomalies",
    new_callable=AsyncMock,
)
@patch(
    "app.application.workers.orders_worker.get_current_time",
)
async def test_valid_anomaly_detection_valid_match_maximum_anomalies_per_order_book(
    mock_get_current_time: Mock,
    mock_send_anomalies: AsyncMock,
    mock_create_order_book_anomalies: AsyncMock,
    processor: Processor,
) -> None:
    current_time = 1.0
    mock_get_current_time.return_value = current_time
    processor._order_book = OrderBook(
        b={
            Decimal("27300.0"): Decimal("1.5"),
            Decimal("27400.0"): Decimal("1.5"),
            Decimal("27500.0"): Decimal("1.5"),
            Decimal("27600.0"): Decimal("3.0"),
            Decimal("27800.0"): Decimal("3.0"),
        },
        a={
            Decimal("27300.0"): Decimal("1.5"),
            Decimal("27400.0"): Decimal("1.5"),
            Decimal("27500.0"): Decimal("1.5"),
            Decimal("27600.0"): Decimal("3.0"),
            Decimal("27800.0"): Decimal("3.0"),
        },
    )
    worker = OrdersWorker(
        processor=processor,
        order_anomaly_multiplier=1.5,
        anomalies_detection_ttl=1,
        anomalies_observing_ttl=1,
        anomalies_observing_ratio=0.5,
        top_n_orders=5,
        order_anomaly_minimum_liquidity=1000.0,
        maximum_order_book_anomalies=2,
    )

    await worker._run_worker()

    assert mock_send_anomalies.call_count == 1
    assert mock_create_order_book_anomalies.call_count == 1
    assert len(worker._detected_anomalies) == 4
    assert len(worker._observing_anomalies) == 3


@patch(
    "app.application.workers.orders_worker.create_order_book_anomalies",
    new_callable=AsyncMock,
)
@patch(
    "app.application.workers.orders_worker.OrdersWorker._send_anomalies",
    new_callable=AsyncMock,
)
@patch(
    "app.application.workers.orders_worker.get_current_time",
)
@patch(
    "app.application.workers.orders_worker.confirm_anomalies_list",
    new_callable=AsyncMock,
)
async def test_non_first_already_observing_anomalies_for_db_saving_after_expiration_of_observing_ttl(
    mock_confirm_anomalies_list: AsyncMock,
    mock_get_current_time: Mock,
    mock_send_anomalies: AsyncMock,
    mock_create_order_book_anomalies: AsyncMock,
    processor: Processor,
) -> None:
    current_time = 2.5
    mock_get_current_time.return_value = current_time
    mock_create_order_book_anomalies.return_value = [
        OrderBookAnomalyModel(
            id=UUID("d1f0f0f0-1f0f-1f0f-1f0f-1f0f1f0f1f0f"),
            price=Decimal("27500.0"),
            quantity=Decimal("8.0"),
            order_liquidity=Decimal("220000.00"),
            average_liquidity=Decimal("27433.33333333333333333333333"),
            type="ask",
            position=2,
            is_cancelled=None,
        ),
        OrderBookAnomalyModel(
            id=UUID("d1f0f0f0-1f0f-1f0f-1f0f-1f0f1f0f1f0f"),
            price=Decimal("27000.0"),
            quantity=Decimal("8.2"),
            order_liquidity=Decimal("221400.00"),
            average_liquidity=Decimal("36100.00"),
            type="bid",
            position=2,
            is_cancelled=None,
        ),
    ]
    processor._order_book = OrderBook(
        b={
            Decimal("27200.0"): Decimal("1.0"),
            Decimal("27100.0"): Decimal("2.0"),
            Decimal("27000.0"): Decimal("8.2"),
            Decimal("26900.0"): Decimal("1.0"),
            Decimal("26800.0"): Decimal("20.0"),
        },
        a={
            Decimal("27300.0"): Decimal("1.0"),
            Decimal("27400.0"): Decimal("1.0"),
            Decimal("27600.0"): Decimal("1.0"),
            Decimal("27500.0"): Decimal("8.0"),
            Decimal("27800.0"): Decimal("20.0"),
        },
    )
    worker = OrdersWorker(
        processor=processor,
        order_anomaly_multiplier=1.5,
        anomalies_detection_ttl=1,
        anomalies_observing_ttl=1,
        anomalies_observing_ratio=0.2,
        top_n_orders=4,
    )
    worker._observing_anomalies = {
        AnomalyKey(price=Decimal("27500.0"), type="ask"): OrderAnomalyInTime(
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
        AnomalyKey(price=Decimal("27000.0"), type="bid"): OrderAnomalyInTime(
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

    assert mock_send_anomalies.call_count == 1
    assert mock_create_order_book_anomalies.call_count == 1

    order_anomaly_notifications_call = mock_send_anomalies.call_args_list[0]
    order_anomaly_notifications = order_anomaly_notifications_call[0][0]

    order_anomalies_creation_call = (
        mock_create_order_book_anomalies.call_args_list[0]
    )
    order_anomalies_creation = order_anomalies_creation_call[0][1]

    expected_notifications = [
        OrderAnomaly(
            price=Decimal("27500.0"),
            quantity=Decimal("8.0"),
            order_liquidity=Decimal("220000.00"),
            average_liquidity=Decimal("27433.33333333333333333333333"),
            position=2,
            type="ask",
        ),
        OrderAnomaly(
            price=Decimal("27000.0"),
            quantity=Decimal("8.2"),
            order_liquidity=Decimal("221400.00"),
            average_liquidity=Decimal("36100.00"),
            position=2,
            type="bid",
        ),
    ]
    expected_models = [
        OrderBookAnomalyModel(
            price=Decimal("27500.0"),
            quantity=Decimal("8.0"),
            order_liquidity=Decimal("220000.00"),
            average_liquidity=Decimal("27433.33333333333333333333333"),
            type="ask",
            position=2,
            is_cancelled=None,
        ),
        OrderBookAnomalyModel(
            price=Decimal("27000.0"),
            quantity=Decimal("8.2"),
            order_liquidity=Decimal("221400.00"),
            average_liquidity=Decimal("36100.00"),
            type="bid",
            position=2,
            is_cancelled=None,
        ),
    ]

    assert order_anomaly_notifications == expected_notifications

    assert order_anomalies_creation[0].price == expected_models[0].price
    assert order_anomalies_creation[0].quantity == expected_models[0].quantity
    assert (
        order_anomalies_creation[0].order_liquidity
        == expected_models[0].order_liquidity
    )
    assert (
        order_anomalies_creation[0].average_liquidity
        == expected_models[0].average_liquidity
    )
    assert order_anomalies_creation[0].type == expected_models[0].type
    assert order_anomalies_creation[0].position == expected_models[0].position
    assert (
        order_anomalies_creation[0].is_cancelled
        == expected_models[0].is_cancelled
    )

    assert order_anomalies_creation[1].price == expected_models[1].price
    assert order_anomalies_creation[1].quantity == expected_models[1].quantity
    assert (
        order_anomalies_creation[1].order_liquidity
        == expected_models[1].order_liquidity
    )
    assert (
        order_anomalies_creation[1].average_liquidity
        == expected_models[1].average_liquidity
    )
    assert order_anomalies_creation[1].type == expected_models[1].type
    assert order_anomalies_creation[1].position == expected_models[1].position
    assert (
        order_anomalies_creation[1].is_cancelled
        == expected_models[1].is_cancelled
    )

    assert len(worker._observing_saved_limit_anomalies) == 2


@patch(
    "app.application.workers.orders_worker.create_order_book_anomalies",
    new_callable=AsyncMock,
)
@patch(
    "app.application.workers.orders_worker.OrdersWorker._send_anomalies",
    new_callable=AsyncMock,
)
@patch(
    "app.application.workers.orders_worker.get_current_time",
)
@patch(
    "app.application.workers.orders_worker.confirm_anomalies_list",
    new_callable=AsyncMock,
)
async def test_non_first_placed_in_observing_saved_limit_anomalies_ratio(
    mock_confirm_anomalies_list: AsyncMock,
    mock_get_current_time: Mock,
    mock_send_anomalies: AsyncMock,
    mock_create_order_book_anomalies: AsyncMock,
    processor: Processor,
) -> None:
    current_time = 2.5
    mock_get_current_time.return_value = current_time
    mock_create_order_book_anomalies.return_value = [
        OrderBookAnomalyModel(
            id=UUID("d1f0f0f0-1f0f-1f0f-1f0f-1f0f1f0f1f0f"),
            price=Decimal("27500.0"),
            quantity=Decimal("8.0"),
            order_liquidity=Decimal("220000.00"),
            average_liquidity=Decimal("27433.33333333333333333333333"),
            type="ask",
            position=2,
            is_cancelled=None,
        ),
        OrderBookAnomalyModel(
            id=UUID("d1f0f0f0-1f0f-1f0f-1f0f-1f0f1f0f1f0f"),
            price=Decimal("27000.0"),
            quantity=Decimal("8.2"),
            order_liquidity=Decimal("221400.00"),
            average_liquidity=Decimal("36100.00"),
            type="bid",
            position=2,
            is_cancelled=None,
        ),
    ]
    processor._order_book = OrderBook(
        b={
            Decimal("27200.0"): Decimal("1.0"),
            Decimal("27100.0"): Decimal("2.0"),
            Decimal("27000.0"): Decimal("8.2"),
            Decimal("26900.0"): Decimal("1.0"),
            Decimal("26800.0"): Decimal("20.0"),
        },
        a={
            Decimal("27300.0"): Decimal("1.0"),
            Decimal("27400.0"): Decimal("1.0"),
            Decimal("27600.0"): Decimal("1.0"),
            Decimal("27500.0"): Decimal("8.0"),
            Decimal("27800.0"): Decimal("20.0"),
        },
    )
    worker = OrdersWorker(
        processor=processor,
        order_anomaly_multiplier=1.5,
        anomalies_detection_ttl=1,
        anomalies_observing_ttl=1,
        anomalies_observing_ratio=0.2,
        top_n_orders=4,
    )
    worker._observing_anomalies = {
        AnomalyKey(price=Decimal("27500.0"), type="ask"): OrderAnomalyInTime(
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
        AnomalyKey(price=Decimal("27000.0"), type="bid"): OrderAnomalyInTime(
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

    expected_ask_anomaly_key = AnomalyKey(price=Decimal("27500.0"), type="ask")
    expected_bid_anomaly_key = AnomalyKey(price=Decimal("27000.0"), type="bid")

    assert len(worker._observing_saved_limit_anomalies) == 2
    assert expected_ask_anomaly_key in worker._observing_saved_limit_anomalies
    assert expected_bid_anomaly_key in worker._observing_saved_limit_anomalies


@patch(
    "app.application.workers.orders_worker.create_order_book_anomalies",
    new_callable=AsyncMock,
)
@patch(
    "app.application.workers.orders_worker.OrdersWorker._send_anomalies",
    new_callable=AsyncMock,
)
@patch(
    "app.application.workers.orders_worker.get_current_time",
)
@patch(
    "app.application.workers.orders_worker.cancel_anomalies_list",
    new_callable=AsyncMock,
)
@patch(
    "app.application.workers.orders_worker.OrdersWorker._send_canceled_anomalies",
    new_callable=AsyncMock,
)
async def test_non_first_anomaly_did_not_canceled(
    mock_send_anomaly_cancellations: AsyncMock,
    mock_cancel_anomalies: AsyncMock,
    mock_get_current_time: Mock,
    mock_send_anomalies: AsyncMock,
    mock_create_order_book_anomalies: AsyncMock,
    processor: Processor,
) -> None:
    current_time = 2.5
    mock_get_current_time.return_value = current_time
    processor._order_book = OrderBook(
        b={
            Decimal("27200.0"): Decimal("1.0"),
            Decimal("27100.0"): Decimal("2.0"),
            Decimal("27000.0"): Decimal("8.2"),
            Decimal("26900.0"): Decimal("1.0"),
            Decimal("26800.0"): Decimal("20.0"),
        },
        a={
            Decimal("27300.0"): Decimal("1.0"),
            Decimal("27400.0"): Decimal("1.0"),
            Decimal("27600.0"): Decimal("1.0"),
            Decimal("27500.0"): Decimal("8.0"),
            Decimal("27800.0"): Decimal("20.0"),
        },
    )
    worker = OrdersWorker(
        processor=processor,
        order_anomaly_multiplier=1.5,
        anomalies_detection_ttl=1,
        anomalies_observing_ttl=1,
        anomalies_observing_ratio=0.2,
        top_n_orders=4,
        observing_saved_limit_anomalies_ratio=0.25,
    )
    worker._observing_saved_limit_anomalies = {
        AnomalyKey(price=Decimal("27500.0"), type="ask"): OrderAnomaly(
            price=Decimal("27500.0"),
            quantity=Decimal("9.0"),
            order_liquidity=Decimal("247500.00"),
            average_liquidity=Decimal("27433.33333333333333333333333"),
            position=2,
            type="ask",
        ),
        AnomalyKey(price=Decimal("27000.0"), type="bid"): OrderAnomaly(
            price=Decimal("27000.0"),
            quantity=Decimal("9.0"),
            order_liquidity=Decimal("243000.00"),
            average_liquidity=Decimal("36100.00"),
            position=2,
            type="bid",
        ),
    }

    await worker._run_worker()

    expected_ask_anomaly_key = AnomalyKey(price=Decimal("27500.0"), type="ask")
    expected_bid_anomaly_key = AnomalyKey(price=Decimal("27000.0"), type="bid")

    assert len(worker._observing_saved_limit_anomalies) == 2
    assert expected_ask_anomaly_key in worker._observing_saved_limit_anomalies
    assert expected_bid_anomaly_key in worker._observing_saved_limit_anomalies
    assert mock_send_anomaly_cancellations.call_count == 0
    assert mock_cancel_anomalies.call_count == 0


@patch(
    "app.application.workers.orders_worker.create_order_book_anomalies",
    new_callable=AsyncMock,
)
@patch(
    "app.application.workers.orders_worker.OrdersWorker._send_anomalies",
    new_callable=AsyncMock,
)
@patch(
    "app.application.workers.orders_worker.get_current_time",
)
@patch(
    "app.application.workers.orders_worker.cancel_anomalies_list",
    new_callable=AsyncMock,
)
@patch(
    "app.application.workers.orders_worker.OrdersWorker._send_canceled_anomalies"
)
async def test_non_first_anomaly_canceled(
    mock_send_anomaly_cancellations: Mock,
    mock_cancel_anomalies: AsyncMock,
    mock_get_current_time: Mock,
    mock_send_anomalies: AsyncMock,
    mock_create_order_book_anomalies: AsyncMock,
    processor: Processor,
) -> None:
    current_time = 2.5
    mock_get_current_time.return_value = current_time
    mock_send_anomaly_cancellations.return_value = []

    processor._order_book = OrderBook(
        b={
            Decimal("27200.0"): Decimal("1.0"),
            Decimal("27100.0"): Decimal("2.0"),
            Decimal("27000.0"): Decimal("6.2"),
            Decimal("26900.0"): Decimal("1.0"),
            Decimal("26800.0"): Decimal("20.0"),
        },
        a={
            Decimal("27300.0"): Decimal("1.0"),
            Decimal("27400.0"): Decimal("1.0"),
            Decimal("27600.0"): Decimal("1.0"),
            Decimal("27500.0"): Decimal("6.0"),
            Decimal("27800.0"): Decimal("20.0"),
        },
    )
    worker = OrdersWorker(
        processor=processor,
        messengers=[],
        order_anomaly_multiplier=1.5,
        anomalies_detection_ttl=1,
        anomalies_observing_ttl=1,
        anomalies_observing_ratio=0.2,
        top_n_orders=4,
        observing_saved_limit_anomalies_ratio=0.25,
    )
    worker._observing_saved_limit_anomalies = {
        AnomalyKey(price=Decimal("27500.0"), type="ask"): OrderAnomalySaved(
            id=UUID("00000000-0000-0000-0000-000000000001"),
            price=Decimal("27500.0"),
            quantity=Decimal("9.0"),
            order_liquidity=Decimal("247500.00"),
            average_liquidity=Decimal("27433.33333333333333333333333"),
            position=2,
            type="ask",
        ),
        AnomalyKey(price=Decimal("27000.0"), type="bid"): OrderAnomalySaved(
            id=UUID("00000000-0000-0000-0000-000000000002"),
            price=Decimal("27000.0"),
            quantity=Decimal("9.0"),
            order_liquidity=Decimal("243000.00"),
            average_liquidity=Decimal("36100.00"),
            position=2,
            type="bid",
        ),
    }

    await worker._run_worker()

    assert len(worker._observing_saved_limit_anomalies) == 0
    assert mock_send_anomaly_cancellations.call_count == 1
    assert mock_cancel_anomalies.call_count == 1

    order_anomaly_cancellation_call = (
        mock_send_anomaly_cancellations.call_args_list[0]
    )

    order_anomaly_cancellation = order_anomaly_cancellation_call[0][0]
    expected_order_anomaly_cancellation = [
        OrderAnomalySaved(
            id=UUID("00000000-0000-0000-0000-000000000001"),
            price=Decimal("27500.0"),
            quantity=Decimal("9.0"),
            order_liquidity=Decimal("247500.00"),
            average_liquidity=Decimal("27433.33333333333333333333333"),
            position=2,
            type="ask",
        ),
        OrderAnomalySaved(
            id=UUID("00000000-0000-0000-0000-000000000002"),
            price=Decimal("27000.0"),
            quantity=Decimal("9.0"),
            order_liquidity=Decimal("243000.00"),
            average_liquidity=Decimal("36100.00"),
            position=2,
            type="bid",
        ),
    ]

    assert order_anomaly_cancellation == expected_order_anomaly_cancellation


@patch(
    "app.application.workers.orders_worker.create_order_book_anomalies",
    new_callable=AsyncMock,
)
@patch(
    "app.application.workers.orders_worker.OrdersWorker._send_anomalies",
    new_callable=AsyncMock,
)
@patch(
    "app.application.workers.orders_worker.get_current_time",
)
@patch(
    "app.application.workers.orders_worker.cancel_anomalies_list",
    new_callable=AsyncMock,
)
@patch(
    "app.application.workers.orders_worker.OrdersWorker._send_canceled_anomalies"
)
async def test_valid_anomaly_canceled(
    mock_send_anomaly_cancellations: Mock,
    mock_cancel_anomalies: AsyncMock,
    mock_get_current_time: Mock,
    mock_order_book_discord_messenger: AsyncMock,
    mock_create_order_book_anomalies: AsyncMock,
    processor: Processor,
) -> None:
    current_time = 2.5
    mock_get_current_time.return_value = current_time
    processor._order_book = OrderBook(
        b={
            Decimal("27200.0"): Decimal("1.0"),
            Decimal("27100.0"): Decimal("2.0"),
            Decimal("26900.0"): Decimal("1.0"),
            Decimal("26800.0"): Decimal("20.0"),
        },
        a={
            Decimal("27300.0"): Decimal("1.0"),
            Decimal("27400.0"): Decimal("1.0"),
            Decimal("27600.0"): Decimal("1.0"),
            Decimal("27800.0"): Decimal("20.0"),
        },
    )
    worker = OrdersWorker(
        processor=processor,
        order_anomaly_multiplier=1.5,
        anomalies_detection_ttl=1,
        anomalies_observing_ttl=1,
        anomalies_observing_ratio=0.2,
        top_n_orders=4,
        observing_saved_limit_anomalies_ratio=0.25,
    )
    worker._observing_saved_limit_anomalies = {
        AnomalyKey(price=Decimal("27500.0"), type="ask"): OrderAnomalySaved(
            id=UUID("00000000-0000-0000-0000-000000000001"),
            price=Decimal("27500.0"),
            quantity=Decimal("9.0"),
            order_liquidity=Decimal("247500.00"),
            average_liquidity=Decimal("27433.33333333333333333333333"),
            position=2,
            type="ask",
        ),
        AnomalyKey(price=Decimal("27000.0"), type="bid"): OrderAnomalySaved(
            id=UUID("00000000-0000-0000-0000-000000000002"),
            price=Decimal("27000.0"),
            quantity=Decimal("9.0"),
            order_liquidity=Decimal("243000.00"),
            average_liquidity=Decimal("36100.00"),
            position=2,
            type="bid",
        ),
    }

    await worker._run_worker()

    assert len(worker._observing_saved_limit_anomalies) == 0
    assert mock_send_anomaly_cancellations.call_count == 1
    assert mock_cancel_anomalies.call_count == 1

    order_anomaly_cancellation_call = (
        mock_send_anomaly_cancellations.call_args_list[0]
    )

    order_anomaly_cancellation = order_anomaly_cancellation_call[0][0]
    expected_order_anomaly_cancellation = [
        OrderAnomalySaved(
            id=UUID("00000000-0000-0000-0000-000000000001"),
            price=Decimal("27500.0"),
            quantity=Decimal("9.0"),
            order_liquidity=Decimal("247500.00"),
            average_liquidity=Decimal("27433.33333333333333333333333"),
            position=2,
            type="ask",
        ),
        OrderAnomalySaved(
            id=UUID("00000000-0000-0000-0000-000000000002"),
            price=Decimal("27000.0"),
            quantity=Decimal("9.0"),
            order_liquidity=Decimal("243000.00"),
            average_liquidity=Decimal("36100.00"),
            position=2,
            type="bid",
        ),
    ]

    assert order_anomaly_cancellation == expected_order_anomaly_cancellation


@patch(
    "app.application.workers.orders_worker.create_order_book_anomalies",
    new_callable=AsyncMock,
)
@patch(
    "app.application.workers.orders_worker.OrdersWorker._send_anomalies",
    new_callable=AsyncMock,
)
@patch(
    "app.application.workers.orders_worker.get_current_time",
)
@patch(
    "app.application.workers.orders_worker.cancel_anomalies_list",
    new_callable=AsyncMock,
)
@patch(
    "app.application.workers.orders_worker.OrdersWorker._send_canceled_anomalies"
)
@patch(
    "app.application.workers.orders_worker.confirm_anomalies_list",
    new_callable=AsyncMock,
)
@patch(
    "app.application.workers.orders_worker.OrdersWorker._send_realized_anomalies"
)
async def test_valid_anomaly_canceled_ask_by_unexpected_changing(
    mock_send_anomalies_realizations: Mock,
    mock_confirm_anomalies: AsyncMock,
    mock_send_anomaly_cancellations: Mock,
    mock_cancel_anomalies: AsyncMock,
    mock_get_current_time: Mock,
    mock_send_anomalies: AsyncMock,
    mock_create_order_book_anomalies: AsyncMock,
    processor: Processor,
) -> None:
    current_time = 2.5
    mock_get_current_time.return_value = current_time
    processor._order_book = OrderBook(
        b={
            Decimal("30000.0"): Decimal("1.0"),
        },
        a={
            Decimal("29900.0"): Decimal("1.0"),
        },
    )
    worker = OrdersWorker(
        processor=processor,
        order_anomaly_multiplier=1.5,
        anomalies_detection_ttl=1,
        anomalies_observing_ttl=1,
        anomalies_observing_ratio=0.2,
        top_n_orders=4,
        observing_saved_limit_anomalies_ratio=0.25,
    )
    worker._observing_saved_limit_anomalies = {
        AnomalyKey(price=Decimal("27500.0"), type="ask"): OrderAnomalySaved(
            id=UUID("00000000-0000-0000-0000-000000000001"),
            price=Decimal("27500.0"),
            quantity=Decimal("9.0"),
            order_liquidity=Decimal("247500.00"),
            average_liquidity=Decimal("27433.33333333333333333333333"),
            position=2,
            type="ask",
        ),
        AnomalyKey(price=Decimal("27000.0"), type="bid"): OrderAnomalySaved(
            id=UUID("00000000-0000-0000-0000-000000000002"),
            price=Decimal("27000.0"),
            quantity=Decimal("9.0"),
            order_liquidity=Decimal("243000.00"),
            average_liquidity=Decimal("36100.00"),
            position=2,
            type="bid",
        ),
    }

    await worker._run_worker()

    cancellation_call = mock_send_anomaly_cancellations.call_args_list[0]
    order_anomaly_cancellation = cancellation_call[0][0]
    realization_call = mock_send_anomalies_realizations.call_args_list[0]
    order_anomaly_realization = realization_call[0][0]

    expected_order_anomaly_cancellation = [
        OrderAnomalySaved(
            id=UUID("00000000-0000-0000-0000-000000000002"),
            price=Decimal("27000.0"),
            quantity=Decimal("9.0"),
            order_liquidity=Decimal("243000.00"),
            average_liquidity=Decimal("36100.00"),
            position=2,
            type="bid",
        )
    ]
    expected_order_anomaly_realization = [
        OrderAnomalySaved(
            id=UUID("00000000-0000-0000-0000-000000000001"),
            price=Decimal("27500.0"),
            quantity=Decimal("9.0"),
            order_liquidity=Decimal("247500.00"),
            average_liquidity=Decimal("27433.33333333333333333333333"),
            position=2,
            type="ask",
        )
    ]

    assert len(worker._observing_saved_limit_anomalies) == 0

    assert mock_send_anomaly_cancellations.call_count == 1
    assert mock_cancel_anomalies.call_count == 1
    assert order_anomaly_cancellation == expected_order_anomaly_cancellation

    assert mock_send_anomalies_realizations.call_count == 1
    assert mock_confirm_anomalies.call_count == 1
    assert order_anomaly_realization == expected_order_anomaly_realization


@patch(
    "app.application.workers.orders_worker.create_order_book_anomalies",
    new_callable=AsyncMock,
)
@patch(
    "app.application.workers.orders_worker.OrdersWorker._send_anomalies",
    new_callable=AsyncMock,
)
@patch(
    "app.application.workers.orders_worker.get_current_time",
)
@patch(
    "app.application.workers.orders_worker.cancel_anomalies_list",
    new_callable=AsyncMock,
)
@patch(
    "app.application.workers.orders_worker.OrdersWorker._send_canceled_anomalies"
)
@patch(
    "app.application.workers.orders_worker.confirm_anomalies_list",
    new_callable=AsyncMock,
)
@patch(
    "app.application.workers.orders_worker.OrdersWorker._send_realized_anomalies"
)
async def test_valid_anomaly_canceled_bid_by_unexpected_changing(
    mock_send_anomalies_realizations: Mock,
    mock_confirm_anomalies: AsyncMock,
    mock_send_anomaly_cancellations: Mock,
    mock_cancel_anomalies: AsyncMock,
    mock_get_current_time: Mock,
    mock_send_anomalies: AsyncMock,
    mock_create_order_book_anomalies: AsyncMock,
    processor: Processor,
) -> None:
    current_time = 2.5
    mock_get_current_time.return_value = current_time
    processor._order_book = OrderBook(
        b={
            Decimal("20000.0"): Decimal("1.0"),
        },
        a={
            Decimal("19000.0"): Decimal("1.0"),
        },
    )
    worker = OrdersWorker(
        processor=processor,
        order_anomaly_multiplier=1.5,
        anomalies_detection_ttl=1,
        anomalies_observing_ttl=1,
        anomalies_observing_ratio=0.2,
        top_n_orders=4,
        observing_saved_limit_anomalies_ratio=0.25,
    )
    worker._observing_saved_limit_anomalies = {
        AnomalyKey(price=Decimal("27500.0"), type="ask"): OrderAnomalySaved(
            id=UUID("00000000-0000-0000-0000-000000000001"),
            price=Decimal("27500.0"),
            quantity=Decimal("9.0"),
            order_liquidity=Decimal("247500.00"),
            average_liquidity=Decimal("27433.33333333333333333333333"),
            position=2,
            type="ask",
        ),
        AnomalyKey(price=Decimal("27000.0"), type="bid"): OrderAnomalySaved(
            id=UUID("00000000-0000-0000-0000-000000000002"),
            price=Decimal("27000.0"),
            quantity=Decimal("9.0"),
            order_liquidity=Decimal("243000.00"),
            average_liquidity=Decimal("36100.00"),
            position=2,
            type="bid",
        ),
    }

    await worker._run_worker()

    cancellation_call = mock_send_anomaly_cancellations.call_args_list[0]
    order_anomaly_cancellation = cancellation_call[0][0]
    realization_call = mock_send_anomalies_realizations.call_args_list[0]
    order_anomaly_realization = realization_call[0][0]

    expected_order_anomaly_cancellation = [
        OrderAnomalySaved(
            id=UUID("00000000-0000-0000-0000-000000000001"),
            price=Decimal("27500.0"),
            quantity=Decimal("9.0"),
            order_liquidity=Decimal("247500.00"),
            average_liquidity=Decimal("27433.33333333333333333333333"),
            position=2,
            type="ask",
        )
    ]
    expected_order_anomaly_realization = [
        OrderAnomalySaved(
            id=UUID("00000000-0000-0000-0000-000000000002"),
            price=Decimal("27000.0"),
            quantity=Decimal("9.0"),
            order_liquidity=Decimal("243000.00"),
            average_liquidity=Decimal("36100.00"),
            position=2,
            type="bid",
        )
    ]

    assert len(worker._observing_saved_limit_anomalies) == 0

    assert mock_send_anomaly_cancellations.call_count == 1
    assert mock_cancel_anomalies.call_count == 1
    assert order_anomaly_cancellation == expected_order_anomaly_cancellation

    assert mock_send_anomalies_realizations.call_count == 1
    assert mock_confirm_anomalies.call_count == 1
    assert order_anomaly_realization == expected_order_anomaly_realization


@patch(
    "app.application.workers.orders_worker.create_order_book_anomalies",
    new_callable=AsyncMock,
)
@patch(
    "app.application.workers.orders_worker.OrdersWorker._send_anomalies",
    new_callable=AsyncMock,
)
@patch(
    "app.application.workers.orders_worker.get_current_time",
)
@patch(
    "app.application.workers.orders_worker.cancel_anomalies_list",
    new_callable=AsyncMock,
)
@patch(
    "app.application.workers.orders_worker.OrdersWorker._send_canceled_anomalies"
)
@patch(
    "app.application.workers.orders_worker.confirm_anomalies_list",
    new_callable=AsyncMock,
)
@patch(
    "app.application.workers.orders_worker.OrdersWorker._send_realized_anomalies"
)
async def test_valid_anomaly_first_position_realized(
    mock_send_anomalies_realizations: Mock,
    mock_confirm_anomalies: AsyncMock,
    mock_send_anomaly_cancellations: Mock,
    mock_cancel_anomalies: AsyncMock,
    mock_get_current_time: Mock,
    mock_send_anomalies: AsyncMock,
    mock_create_order_book_anomalies: AsyncMock,
    processor: Processor,
) -> None:
    current_time = 2.5
    mock_get_current_time.return_value = current_time
    processor._order_book = OrderBook(
        b={
            Decimal("27200.0"): Decimal("1.0"),
            Decimal("27100.0"): Decimal("2.0"),
            Decimal("26900.0"): Decimal("1.0"),
            Decimal("26800.0"): Decimal("20.0"),
        },
        a={
            Decimal("27300.0"): Decimal("1.0"),
            Decimal("27400.0"): Decimal("1.0"),
            Decimal("27600.0"): Decimal("1.0"),
            Decimal("27800.0"): Decimal("20.0"),
        },
    )
    worker = OrdersWorker(
        processor=processor,
        order_anomaly_multiplier=1.5,
        anomalies_detection_ttl=1,
        anomalies_observing_ttl=1,
        anomalies_observing_ratio=0.2,
        top_n_orders=4,
        observing_saved_limit_anomalies_ratio=0.25,
    )
    worker._observing_saved_limit_anomalies = {
        AnomalyKey(price=Decimal("27300.0"), type="ask"): OrderAnomalySaved(
            id=UUID("00000000-0000-0000-0000-000000000001"),
            price=Decimal("27300.0"),
            quantity=Decimal("9.0"),
            order_liquidity=Decimal("245700.00"),
            average_liquidity=Decimal("27433.33333333333333333333333"),
            position=2,
            type="ask",
        ),
        AnomalyKey(price=Decimal("27200.0"), type="bid"): OrderAnomalySaved(
            id=UUID("00000000-0000-0000-0000-000000000002"),
            price=Decimal("27200.0"),
            quantity=Decimal("9.0"),
            order_liquidity=Decimal("244800.00"),
            average_liquidity=Decimal("36100.00"),
            position=2,
            type="bid",
        ),
    }

    await worker._run_worker()

    realization_call = mock_send_anomalies_realizations.call_args_list[0]
    order_anomaly_realization = realization_call[0][0]
    expected_order_anomaly_realization = [
        OrderAnomalySaved(
            id=UUID("00000000-0000-0000-0000-000000000001"),
            price=Decimal("27300.0"),
            quantity=Decimal("9.0"),
            order_liquidity=Decimal("245700.00"),
            average_liquidity=Decimal("27433.33333333333333333333333"),
            position=2,
            type="ask",
        ),
        OrderAnomalySaved(
            id=UUID("00000000-0000-0000-0000-000000000002"),
            price=Decimal("27200.0"),
            quantity=Decimal("9.0"),
            order_liquidity=Decimal("244800.00"),
            average_liquidity=Decimal("36100.00"),
            position=2,
            type="bid",
        ),
    ]

    assert len(worker._observing_saved_limit_anomalies) == 0
    assert mock_send_anomaly_cancellations.call_count == 0
    assert mock_cancel_anomalies.call_count == 0

    assert mock_send_anomalies_realizations.call_count == 1
    assert mock_confirm_anomalies.call_count == 1
    assert order_anomaly_realization == expected_order_anomaly_realization
