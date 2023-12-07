from abc import abstractmethod
from typing import List, Literal, NamedTuple
from uuid import UUID

from _decimal import Decimal

from app.services.messengers.common import BaseMessenger


class OrderAnomalyNotification(NamedTuple):
    price: Decimal
    quantity: Decimal
    order_liquidity: Decimal
    average_liquidity: Decimal
    type: Literal["ask", "bid"]
    position: int


class OrderBookMessenger(BaseMessenger):
    @abstractmethod
    async def send_anomaly_detection_notifications(
        self, anomalies: List[OrderAnomalyNotification], pair_id: UUID
    ) -> None:
        pass

    @abstractmethod
    async def send_anomaly_cancellation_notifications(
        self, anomalies: List[OrderAnomalyNotification], pair_id: UUID
    ) -> None:
        pass

    @abstractmethod
    async def send_anomaly_realization_notifications(
        self, anomalies: List[OrderAnomalyNotification], pair_id: UUID
    ) -> None:
        pass
