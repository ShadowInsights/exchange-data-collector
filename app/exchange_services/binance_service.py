from typing import Optional
from models.binance_response import BinanceResponse
from exchange_services.exchange_service import ExchangeService
import asyncio
import websockets
import json
import httpx

class BinanceExchangeService(ExchangeService):
    def __init__(self, symbol: str, limit: Optional[int] = 100):
        self.symbol = symbol
        self.limit = limit
        self.base_url = "https://api.binance.com/api/v3"

    async def depth_snapshot(self):
        params = {"symbol": self.symbol, "limit": self.limit}
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{self.base_url}/depth", params=params)
        return response.json()
    
    async def get_trade_stream(self):
        async with websockets.connect('wss://stream.binance.com:9443/ws') as websocket:
            payload = {
                "method": "SUBSCRIBE",
                "params": [
                    f"{self.symbol.lower()}@depth"
                ],
                "id": 1
            }
            await websocket.send(json.dumps(payload))
            
            snapshot_data = await self.depth_snapshot()
            last_update_id = snapshot_data['lastUpdateId']
            bids = snapshot_data['bids']
            asks = snapshot_data['asks']
            print("Initial Depth Snapshot:")
            print("Bids:", bids)
            print("Asks:", asks)
            while True:
                try:
                    response = await websocket.recv()
                    depth_data = json.loads(response)
                    print(depth_data)
                                        
                    if 'b' not in depth_data or 'a' not in depth_data:
                        continue
                    
                    event_update_id = depth_data['u']
                    if event_update_id <= last_update_id:
                        continue
                    
                    if event_update_id == last_update_id + 1:
                        last_update_id = event_update_id
                        bids = self.update_price_levels(bids, depth_data['b'])
                        asks = self.update_price_levels(asks, depth_data['a'])
                        print("Updated Depth:")
                        print("Bids:", bids)
                        print("Asks:", asks)
                    else:
                        print("Out of sync. Resynchronizing...")
                        snapshot_data = await self.depth_snapshot()
                        last_update_id = snapshot_data['lastUpdateId']
                        bids = snapshot_data['bids']
                        asks = snapshot_data['asks']
                        print("Resynchronized Depth Snapshot:")
                        print("Bids:", bids)
                        print("Asks:", asks)
                except websockets.ConnectionClosed:
                    print("WebSocket connection closed.")
                    break
    def update_price_levels(price_levels, updates):
        for update in updates:
            price = float(update[0])
            quantity = float(update[1])
            if quantity == 0:
                price_levels.pop(price, None)
            else:
                price_levels[price] = quantity
        return price_levels