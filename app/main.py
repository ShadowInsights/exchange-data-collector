import asyncio
import logging
import uuid

from prometheus_client import start_http_server

from app.common.maestro import Maestro


def start_metrics_server() -> None:
    logging.info("Starting metrics server")
    start_http_server(9010)
    logging.info("Metrics server started")


async def main() -> None:
    launch_id = uuid.uuid4()
    maestro = Maestro(launch_id)
    await maestro.run()


if __name__ == "__main__":
    logging.info("Starting application...")

    try:
        start_metrics_server()
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("\nInterrupted. Closing application...")
    except Exception:
        logging.exception(
            "An unexpected error occurred. Closing application..."
        )
