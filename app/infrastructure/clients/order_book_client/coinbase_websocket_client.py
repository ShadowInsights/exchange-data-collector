import json
import logging
from typing import AsyncGenerator, Callable, Union

import websockets
from _decimal import Decimal

from app.infrastructure.clients.common import WebsocketClient
from app.infrastructure.clients.order_book_client.schemas.coinbase import (
    CoinbaseEventType, CoinbaseOrderBook, CoinbaseOrderBookDepthUpdate,
    CoinbaseOrderBookSnapshot, CoinbaseOrderType, CoinbaseSnapshotPayload)
from app.infrastructure.clients.order_book_client.schemas.common import (
    OrderBookEvent, OrderBookSnapshot, OrderBookUpdate)

EVENT_TYPE_KEY = "type"


class CoinbaseWebsocketClient(WebsocketClient):
    def __init__(self, symbol: str):
        super().__init__(symbol=symbol, symbol_splitter="-")
        self._uri = "wss://ws-feed.exchange.coinbase.com"
        self._channel = "level2_batch"

    async def listen_depth_stream(
        self,
    ) -> AsyncGenerator[OrderBookEvent | None, None]:
        async with websockets.connect(self._uri) as websocket:
            ws_payload = CoinbaseSnapshotPayload(
                product_ids=[self.symbol], channels=[self._channel]
            )

            await websocket.send(ws_payload.model_dump_json())

            async for message in websocket:
                body = self.__deserialize_message(message=message)

                if body is None:
                    continue

                switch: dict[type[CoinbaseOrderBook], Callable] = {
                    CoinbaseOrderBookSnapshot: self.__handle_snapshot,
                    CoinbaseOrderBookDepthUpdate: self.__handle_update,
                }

                # Retrieve and execute the handler
                handler = switch.get(type(body))
                if handler:
                    yield handler(body)
                else:
                    yield None

    def __deserialize_message(
        self, message: Union[str, bytes]
    ) -> CoinbaseOrderBook | None:
        try:
            if message is None:
                return None

            body = json.loads(message)

            if EVENT_TYPE_KEY in body:
                if body[EVENT_TYPE_KEY] == CoinbaseEventType.SNAPSHOT.value:
                    return CoinbaseOrderBookSnapshot.model_validate(body)

                if body[EVENT_TYPE_KEY] == CoinbaseEventType.UPDATE.value:
                    return CoinbaseOrderBookDepthUpdate.model_validate(body)
        except Exception as err:
            logging.exception(
                exc_info=err, msg="Error occurred in Coinbase collector"
            )

        return None

    def __handle_snapshot(
        self, body: CoinbaseOrderBookSnapshot
    ) -> OrderBookEvent:
        return OrderBookSnapshot(
            a={Decimal(order[0]): Decimal(order[1]) for order in body.asks},
            b={Decimal(order[0]): Decimal(order[1]) for order in body.bids},
        )

    def __handle_update(
        self, body: CoinbaseOrderBookDepthUpdate
    ) -> OrderBookEvent:
        type_position = 0
        price_position = 1
        volume_position = 2

        asks = {
            Decimal(order[price_position]): Decimal(order[volume_position])
            for order in body.changes
            if order[type_position] == CoinbaseOrderType.SELL.value
        }

        bids = {
            Decimal(order[price_position]): Decimal(order[volume_position])
            for order in body.changes
            if order[type_position] == CoinbaseOrderType.BUY.value
        }

        return OrderBookUpdate(a=asks, b=bids)
