import asyncio
import logging

from app.common.config import settings
from app.services.collectors.binance_exchange_collector import \
    BinanceExchangeCollector

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.StreamHandler()],
    )
    logging.info("Starting data collection")
    try:
        for pair in settings.BINANCE_PAIRS:
            collector = BinanceExchangeCollector(pair)
            asyncio.run(collector.collect())
    except KeyboardInterrupt:
        # Perform cleanup here (e.g., close any open connections)
        logging.info("\nInterrupted. Closing application...")
