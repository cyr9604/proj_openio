from datetime import date, timedelta
from typing import Optional
import pandas as pd
import httpx

from providers.base import QuoteProvider, ProviderError
from config import settings


class ThsHttpProvider(QuoteProvider):
    name = "ths_http"
    _token: str = ""
    _refresh_token: str = ""
    _token_expire: float = 0

    TOKEN_URL = "https://quantapi.10jqka.com.cn/api/v1/token/refresh"
    QUOTE_URL = "https://quantapi.10jqka.com.cn/api/v1/quote/daily"

    def is_configured(self) -> bool:
        return bool(settings.ths_http_refresh_token)

    def is_available(self) -> bool:
        return self.is_configured()

    def _refresh_access_token(self) -> str:
        if not settings.ths_http_refresh_token:
            raise ProviderError("refresh_token not configured", self.name)
        try:
            resp = httpx.post(
                self.TOKEN_URL,
                json={"refresh_token": settings.ths_http_refresh_token},
                timeout=10,
            )
            data = resp.json()
            if data.get("code") == 0:
                self._token = data["data"]["access_token"]
                return self._token
            raise ProviderError(f"Token refresh failed: {data}", self.name)
        except Exception as e:
            raise ProviderError(f"Token refresh error: {e}", self.name)

    def fetch_daily(
        self, symbol: str, start: Optional[date] = None, end: Optional[date] = None, adjust: str = "forward"
    ) -> pd.DataFrame:
        if not self.is_configured():
            raise ProviderError("同花顺 HTTP not configured (missing refresh_token)", self.name)

        token = self._refresh_access_token()
        end = end or date.today()
        start = start or (end - timedelta(days=365 * 2))

        adjust_map = {"forward": "1", "backward": "2", "none": "0"}
        adj = adjust_map.get(adjust, "1")

        try:
            resp = httpx.get(
                self.QUOTE_URL,
                params={
                    "symbol": symbol,
                    "start_date": start.strftime("%Y%m%d"),
                    "end_date": end.strftime("%Y%m%d"),
                    "adjust": adj,
                    "access_token": token,
                },
                timeout=30,
            )
            data = resp.json()
            if data.get("code") != 0:
                raise ProviderError(f"同花顺 API error: {data}", self.name)

            records = data.get("data", {}).get("list", [])
            if not records:
                raise ProviderError(f"No data for {symbol}", self.name)

            rows = []
            for r in records:
                rows.append({
                    "date": r["date"],
                    "open": float(r["open"]),
                    "high": float(r["high"]),
                    "low": float(r["low"]),
                    "close": float(r["close"]),
                    "volume": float(r.get("volume", 0)),
                    "amount": float(r.get("amount", 0)),
                })
            df = pd.DataFrame(rows)
            df["date"] = pd.to_datetime(df["date"])
            df = self.normalize(df, self.name, adjust)
            return df

        except ProviderError:
            raise
        except Exception as e:
            raise ProviderError(f"同花顺 HTTP fetch error: {e}", self.name)
