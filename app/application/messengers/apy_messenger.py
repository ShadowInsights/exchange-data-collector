from abc import abstractmethod
from typing import NamedTuple
from uuid import UUID

from _decimal import Decimal

from app.infrastructure.messengers.common import BaseMessenger


class APYNotification(NamedTuple):
    apy_asset_id: UUID
    deviation: Decimal
    current_apy: Decimal
    previous_apy: Decimal


class APYMessenger(BaseMessenger):
    @abstractmethod
    async def send_notification(self, notification: APYNotification) -> None:
        pass
