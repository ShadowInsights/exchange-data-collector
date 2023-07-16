from typing import List, Tuple

class BinanceResponse:
    def __init__(self, lastUpdateId: int, bids: List[Tuple[str, str]], asks: List[Tuple[str, str]]):
        self.lastUpdateId = lastUpdateId
        self.bids = bids
        self.asks = asks

    @classmethod
    def from_dict(cls, data: dict) -> 'BinanceResponse':
        lastUpdateId = data['lastUpdateId']
        bids = [(str(price), str(qty)) for price, qty in data['bids']]
        asks = [(str(price), str(qty)) for price, qty in data['asks']]
        return cls(lastUpdateId, bids, asks)