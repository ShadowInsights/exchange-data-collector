import asyncio
from common.config import Settings
from exchange_services.binance_service import BinanceExchangeService
from db.database import Base, engine
from db.models.binance_order import BinanceOrderModel
from db.repositories.binance_order_repository import create_order


def create_tables() -> None:
    Base.metadata.create_all(bind=engine)


def create_sample_order() -> None:
    # create a sample order
    sample_order = BinanceOrderModel(
        symbol="BTCUSDT",
        binance_id=123,
        price=400.00,
        qty=12.00,
        quote_qty=4800.12,
        time=1626867861234,
        is_buyer_maker=True,
        is_best_match=True,
    )
    create_order(sample_order)
    

async def handle_trade_data(trade_data):
    print(trade_data)


def main() -> None:
    # create_tables()
    # create_sample_order()

    binance_service = BinanceExchangeService("BTCUSDT")
    loop = asyncio.get_event_loop()
    loop.run_until_complete(binance_service.get_trade_stream())



if __name__ == "__main__":
    main()
