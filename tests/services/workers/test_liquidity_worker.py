from decimal import Decimal
from unittest.mock import patch
from uuid import UUID

from app.services.collectors.common import Collector


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


# @pytest.fixture
# def collector() -> Collector:
#     return MockCollector(
#         launch_id=UUID("d8f4b7c5-5d9c-4b9c-8b3b-9c0c5d9f4b7c"),
#         pair_id=UUID("d8f4b7c5-5d9c-4b9c-8b3b-9c0c5d9f4b7c"),
#         exchange_id=UUID("d8f4b7c5-5d9c-4b9c-8b3b-9c0c5d9f4b7c"),
#         symbol="BTCUSDT",
#         delimiter=Decimal("0.1"),
#     )


@patch("app.services.collectors.workers.liquidity_worker.find_last_average_volumes")
async def test_worker() -> None:
    assert True == True
