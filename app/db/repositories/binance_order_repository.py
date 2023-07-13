from db.database import get_db
from db.models.binance_order import BinanceOrderModel


def create_order(binance_order: BinanceOrderModel) -> BinanceOrderModel:
    with get_db() as session:
        session.add(binance_order)
        session.commit()
        return binance_order
