from typing import Optional
from models.binance_response import BinanceResponse
from exchange_services.exchange_service import ExchangeService
import asyncio
import websockets
import json

class BinanceExchangeService(ExchangeService):
    def __init__(self, symbol: str, limit: Optional[int] = 100):
        self.symbol = symbol
        self.limit = limit if limit <= 5000 else 5000
        self.base_url = "https://api.binance.com/api/v3"

    async def collect_data(self):
        params = {"symbol": self.symbol, "limit": self.limit}
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/depth", params=params)
        data = response.json()
        binance_response = BinanceResponse.from_dict(data)
        return binance_response
    
    async def get_trade_stream(self, callback):
        async with websockets.connect('wss://stream.binance.com:9443/ws') as websocket:
            payload = {
                "method": "SUBSCRIBE",
                "params": [
                    f"{self.symbol.lower()}@trade"
                ],
                "id": 1
            }

            await websocket.send(json.dumps(payload))
            
            while True:
                try:
                    response = await websocket.recv()
                    trade_data = json.loads(response)
                    await callback(trade_data)
                except websockets.ConnectionClosed:
                    break