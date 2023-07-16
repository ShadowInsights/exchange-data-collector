
from abc import abstractmethod
import time
import uuid

from db.models.binance_order import BinanceOrderModel
from db.repositories.binance_order_repository import create_order


class ExchangeService:
    def __init__(self):
        self.data = []

    @abstractmethod
    def collect_data(self):
        pass
    
    # TODO: Тут должно быть так чтобы save_data_to_db мог писать любые данные, а тут привязка к BinanceOrderModel :(
    async def save_data_to_db(self):
        reponse_data = await self.collect_data()
        for bid in reponse_data.bids:
            order = BinanceOrderModel(
                id=uuid.uuid4(),
                symbol=self.symbol,
                binance_id=reponse_data.lastUpdateId,
                price=float(bid[0]),
                qty=float(bid[1]),
                quote_qty=float(bid[0]) * float(bid[1]),
                time=int(time.time()),  # current time in seconds since epoch
                is_buyer_maker=True,
                is_best_match=True,    # This should be derived from your business logic
            )
            create_order(order)

        for ask in reponse_data.asks:
            order = BinanceOrderModel(
                id=uuid.uuid4(),
                symbol=self.symbol,
                binance_id=reponse_data.lastUpdateId,
                price=float(ask[0]),
                qty=float(ask[1]),
                quote_qty=float(ask[0]) * float(ask[1]),
                time=int(time.time()),  # current time in seconds since epoch
                is_buyer_maker=False,
                is_best_match=True,    # This should be derived from your business logic
            )
            create_order(order)