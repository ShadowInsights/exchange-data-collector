from abc import abstractmethod
from typing import NamedTuple
from uuid import UUID

from _decimal import Decimal

from app.services.messengers.common import BaseMessenger


class OrdersAnomaliesSummaryNotification(NamedTuple):
    pair_id: UUID
    deviation: Decimal | None
    current_total_difference: Decimal
    previous_total_difference: Decimal


class OrdersAnomaliesSummaryMessenger(BaseMessenger):
    @abstractmethod
    async def send_notification(
        self, notification: OrdersAnomaliesSummaryNotification
    ) -> None:
        pass
