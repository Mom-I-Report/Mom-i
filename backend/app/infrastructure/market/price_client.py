import httpx
from typing import Dict, List
from app.core.config import settings


class PriceClient:
    """
    외부 시장 데이터 API 클라이언트.
    MARKET_API_KEY 없으면 더미 가격으로 fallback — 실제 API 연동 전 전체 로직 테스트 가능.
    """

    _DUMMY_PRICES: Dict[str, float] = {
        "SPY":    520.50,
        "QQQ":    430.20,
        "TLT":     92.10,
        "GLD":    220.80,
        "069500": 28450.0,   # KODEX 200
        "360750": 15320.0,   # TIGER 미국S&P500
    }

    def __init__(self):
        self._base_url = getattr(settings, "MARKET_API_URL", "")
        self._api_key  = getattr(settings, "MARKET_API_KEY", "")

    def fetch_prices(self, tickers: List[str]) -> Dict[str, float]:
        """tickers 리스트의 현재 시장가 반환. API 키 없으면 더미 데이터."""
        if not self._api_key:
            return {t: self._DUMMY_PRICES.get(t, 100.0) for t in tickers}

        with httpx.Client(timeout=10.0) as client:
            resp = client.get(
                f"{self._base_url}/prices",
                params={"tickers": ",".join(tickers)},
                headers={"Authorization": f"Bearer {self._api_key}"},
            )
            resp.raise_for_status()
            return resp.json()


price_client = PriceClient()
