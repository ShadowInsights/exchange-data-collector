from app.infrastructure.clients.apy_client.schemas.common import (APYSnapshot,
                                                                  APYUpdate)


class BinanceAPYSnapshot(APYSnapshot):
    pass


class BinanceAPYUpdate(APYUpdate):
    event_time: int
    first_update_id: int
    final_update_id: int
