from db.database import Base, engine
from db.models.binance_order import BinanceOrderModel
from db.repositories.binance_order_repository import create_order


def create_tables() -> None:
    Base.metadata.create_all(bind=engine)


def create_sample_order() -> None:
    # create a sample order
    sample_order = BinanceOrderModel(
        binance_id=123,
        price=400.00,
        qty=12.00,
        quote_qty=4800.12,
        time=1626867861234,
        is_buyer_maker=True,
        is_best_match=True,
    )
    create_order(sample_order)


def main() -> None:
    create_tables()
    create_sample_order()


if __name__ == "__main__":
    main()
