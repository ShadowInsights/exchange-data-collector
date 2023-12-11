from decimal import Decimal
from typing import AsyncGenerator
from unittest.mock import AsyncMock, Mock, patch
from uuid import UUID

import pytest

from app.common.processor import Processor
from app.services.collectors.clients.schemas.common import OrderBookEvent
from app.services.collectors.common import Collector
from app.services.workers.orders_anomalies_summary_worker import (
    OrdersAnomaliesSummary,
    OrdersAnomaliesSummaryWorker,
)
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
    "app.services.workers.orders_anomalies_summary_worker.get_latest_orders_anomalies_summary",
    new_callable=AsyncMock,
)
@patch(
    "app.services.workers.orders_anomalies_summary_worker.get_order_book_anomalies_sum_in_date_range",
    new_callable=AsyncMock,
)
@patch(
    "app.services.workers.orders_anomalies_summary_worker.create_orders_anomalies_summary",
    new_callable=AsyncMock,
)
@patch(
    "app.services.workers.orders_anomalies_summary_worker.OrdersAnomaliesSummaryWorker._send_notification",
    new_callable=AsyncMock,
)
async def test_worker_should_valid_create_orders_anomalies_summary(
    mock_send_notification: AsyncMock,
    mock_create_orders_anomalies_summary: AsyncMock,
    mock_get_order_book_anomalies_sum_in_date_range: AsyncMock,
    mock_get_latest_orders_anomalies_summary: AsyncMock,
    processor: Processor,
) -> None:
    worker = OrdersAnomaliesSummaryWorker(
        processor=processor, volume_anomaly_ratio=0.5
    )
    mock_get_order_book_anomalies_sum_in_date_range.side_effect = [
        10,
        20,
    ]

    await worker._run_worker()

    create_orders_anomalies_summary = (
        mock_create_orders_anomalies_summary.call_args[1][
            "orders_anomalies_summary_in"
        ]
    )

    mock_get_latest_orders_anomalies_summary.assert_called()
    mock_get_order_book_anomalies_sum_in_date_range.assert_called()

    assert create_orders_anomalies_summary.pair_id == processor.pair_id
    assert create_orders_anomalies_summary.launch_id == processor.launch_id
    assert create_orders_anomalies_summary.orders_total_difference == -10


@patch(
    "app.services.workers.orders_anomalies_summary_worker.get_latest_orders_anomalies_summary",
    new_callable=AsyncMock,
)
@patch(
    "app.services.workers.orders_anomalies_summary_worker.get_order_book_anomalies_sum_in_date_range",
    new_callable=AsyncMock,
)
@patch(
    "app.services.workers.orders_anomalies_summary_worker.create_orders_anomalies_summary",
    new_callable=AsyncMock,
)
@patch(
    "app.services.workers.orders_anomalies_summary_worker.OrdersAnomaliesSummaryWorker._send_notification",
    new_callable=AsyncMock,
)
async def test_worker_should_valid_send_orders_anomalies_summary_anomaly_when_deviation_exists(
    mock_send_notification: AsyncMock,
    mock_create_orders_anomalies_summary: AsyncMock,
    mock_get_order_book_anomalies_sum_in_date_range: AsyncMock,
    mock_get_latest_orders_anomalies_summary: AsyncMock,
    processor: Processor,
) -> None:
    worker = OrdersAnomaliesSummaryWorker(
        processor=processor, volume_anomaly_ratio=0.5
    )
    mock_get_latest_orders_anomalies_summary.side_effect = [
        [],
        [
            Mock(orders_total_difference=Decimal("10")),
            Mock(orders_total_difference=Decimal("56")),
            Mock(orders_total_difference=Decimal("60")),
            Mock(orders_total_difference=Decimal("40")),
        ],
    ]

    await worker._run_worker()

    assert mock_send_notification.call_count == 1

    actual_notification = mock_send_notification.call_args[0][0]
    assert actual_notification == OrdersAnomaliesSummary(
        current_total_difference=Decimal("10"),
        previous_total_difference=Decimal("52"),
        deviation=Decimal("0.19"),
    )


@patch(
    "app.services.workers.orders_anomalies_summary_worker.get_latest_orders_anomalies_summary",
    new_callable=AsyncMock,
)
@patch(
    "app.services.workers.orders_anomalies_summary_worker.get_order_book_anomalies_sum_in_date_range",
    new_callable=AsyncMock,
)
@patch(
    "app.services.workers.orders_anomalies_summary_worker.create_orders_anomalies_summary",
    new_callable=AsyncMock,
)
@patch(
    "app.services.workers.orders_anomalies_summary_worker.OrdersAnomaliesSummaryWorker._send_notification",
    new_callable=AsyncMock,
)
async def test_worker_should_valid_send_orders_anomalies_summary_anomaly_when_numbers_do_not_have_same_sign(
    mock_send_notification: AsyncMock,
    mock_create_orders_anomalies_summary: AsyncMock,
    mock_get_order_book_anomalies_sum_in_date_range: AsyncMock,
    mock_get_latest_orders_anomalies_summary: AsyncMock,
    processor: Processor,
) -> None:
    worker = OrdersAnomaliesSummaryWorker(
        processor=processor, volume_anomaly_ratio=0.5
    )
    mock_get_latest_orders_anomalies_summary.side_effect = [
        [],
        [
            Mock(orders_total_difference=-Decimal("0.1")),
            Mock(orders_total_difference=Decimal("1")),
            Mock(orders_total_difference=Decimal("1.2")),
            Mock(orders_total_difference=Decimal("1.25")),
        ],
    ]

    await worker._run_worker()

    assert mock_send_notification.call_count == 1

    actual_notification = mock_send_notification.call_args[0][0]
    assert actual_notification == OrdersAnomaliesSummary(
        current_total_difference=Decimal("-0.1"),
        previous_total_difference=Decimal("1.15"),
        deviation=Decimal("-0.09"),
    )


@patch(
    "app.services.workers.orders_anomalies_summary_worker.get_latest_orders_anomalies_summary",
    new_callable=AsyncMock,
)
@patch(
    "app.services.workers.orders_anomalies_summary_worker.get_order_book_anomalies_sum_in_date_range",
    new_callable=AsyncMock,
)
@patch(
    "app.services.workers.orders_anomalies_summary_worker.create_orders_anomalies_summary",
    new_callable=AsyncMock,
)
@patch(
    "app.services.workers.orders_anomalies_summary_worker.OrdersAnomaliesSummaryWorker._send_notification",
    new_callable=AsyncMock,
)
async def test_worker_should_not_send_orders_anomalies_summary_anomaly_when_no_changes(
    mock_send_notification: AsyncMock,
    mock_create_orders_anomalies_summary: AsyncMock,
    mock_get_order_book_anomalies_sum_in_date_range: AsyncMock,
    mock_get_latest_orders_anomalies_summary: AsyncMock,
    processor: Processor,
) -> None:
    worker = OrdersAnomaliesSummaryWorker(
        processor=processor, volume_anomaly_ratio=2
    )
    mock_get_latest_orders_anomalies_summary.side_effect = [
        [],
        [
            Mock(orders_total_difference=Decimal("10")),
            Mock(orders_total_difference=Decimal("12")),
            Mock(orders_total_difference=Decimal("11")),
            Mock(orders_total_difference=Decimal("10")),
        ],
    ]

    await worker._run_worker()

    assert mock_send_notification.call_count == 0
