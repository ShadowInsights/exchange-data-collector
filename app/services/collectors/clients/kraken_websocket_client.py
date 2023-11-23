import json
import logging
from typing import AsyncGenerator, Union

import websockets

from app.services.collectors.clients.common import WebsocketClient
from app.services.collectors.clients.schemas.common import (
    OrderBookEvent,
    OrderBookSnapshot,
    OrderBookUpdate,
)
from app.services.collectors.clients.schemas.kraken import (
    KrakenOrder,
    KrakenOrderBook,
    KrakenOrderBookDepthUpdate,
    KrakenOrderBookSnapshot,
    KrakenOrdersDict,
    KrakenSnapshotPayload,
)


class KrakenWebsocketClient(WebsocketClient):
    def __init__(self, symbol: str) -> None:
        super().__init__(symbol=symbol, symbol_splitter="/")
        self._uri = "wss://ws.kraken.com/"

    async def listen_depth_stream(
        self,
    ) -> AsyncGenerator[OrderBookEvent | None, None]:
        async with websockets.connect(self._uri) as websocket:
            ws_payload = KrakenSnapshotPayload(pair=[self.symbol])

            await websocket.send(ws_payload.model_dump_json())

            async for message in websocket:
                body = self.__deserialize_message(message=message)

                match body:
                    case KrakenOrderBookSnapshot():
                        yield OrderBookSnapshot(
                            a={
                                order.price: order.volume
                                for order in body.orders.a
                            },
                            b={
                                order.price: order.volume
                                for order in body.orders.b
                            },
                        )
                    case KrakenOrderBookDepthUpdate():
                        yield OrderBookUpdate(
                            a={
                                order.price: order.volume
                                for order in body.orders.a
                            },
                            b={
                                order.price: order.volume
                                for order in body.orders.b
                            },
                        )

                yield None

    def __deserialize_message(
        self,
        message: Union[str, bytes],
    ) -> KrakenOrderBook | None:
        try:
            if message is None:
                return None

            body = json.loads(message)

            if type(body) is list and len(body) == 4:
                if "as" in body[1] or "bs" in body[1]:
                    return self.__convert_to_order_book_snapshot(body=body)

                if "a" in body[1] or "b" in body[1]:
                    return self.__convert_to_order_book_update(body=body)
        except Exception as err:
            logging.exception(
                exc_info=err, msg="Error occurred in Kraken collector"
            )

        return None

    def __convert_to_order_book_snapshot(
        self, body: list
    ) -> KrakenOrderBookSnapshot:
        asks = [
            KrakenOrder(price=price, volume=volume, timestamp=timestamp)
            for price, volume, timestamp in body[1]["as"]
        ]

        bids = [
            KrakenOrder(price=price, volume=volume, timestamp=timestamp)
            for price, volume, timestamp in body[1]["bs"]
        ]

        return KrakenOrderBookSnapshot(
            channel_id=body[0],
            orders=KrakenOrdersDict(a=asks, b=bids),
            channel_name=body[2],
            pair=body[3],
        )

    def __convert_to_order_book_update(
        self, body: list
    ) -> KrakenOrderBookDepthUpdate:
        asks = []
        bids = []

        if "a" in body[1]:
            for order in body[1]["a"]:
                if len(order) == 4 and order[3] == "r":
                    continue

                asks.append(
                    KrakenOrder(
                        price=order[0],
                        volume=order[1],
                        timestamp=order[2],
                    )
                )

        if "b" in body[1]:
            for order in body[1]["b"]:
                if len(order) == 4 and order[3] == "r":
                    continue

                bids.append(
                    KrakenOrder(
                        price=order[0],
                        volume=order[1],
                        timestamp=order[2],
                    )
                )

        return KrakenOrderBookDepthUpdate(
            channel_id=body[0],
            orders=KrakenOrdersDict(a=asks, b=bids),
            checksum=body[1]["c"],
            channel_name=body[2],
            pair=body[3],
        )
