from abc import abstractmethod
from typing import NamedTuple
from uuid import UUID

from _decimal import Decimal

from app.services.messengers.common import BaseMessenger


class VolumeNotification(NamedTuple):
    pair_id: UUID
    deviation: Decimal
    current_bid_ask_ratio: Decimal
    previous_bid_ask_ratio: Decimal
    current_avg_volume: int
    previous_avg_volume: int


class VolumeMessenger(BaseMessenger):
    @abstractmethod
    async def send_notification(
        self, notification: VolumeNotification
    ) -> None:
        pass
