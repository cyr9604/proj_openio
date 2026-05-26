from datetime import date, timedelta
from typing import Optional
import pandas as pd
import httpx

from providers.base import QuoteProvider, ProviderError


class SinaProvider(QuoteProvider):
    name = "sina"
    BASE_URL = "https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData"

    def is_available(self) -> bool:
        try:
            resp = httpx.get(
                "https://money.finance.sina.com.cn/quotes_service/api/json_v2.php/CN_MarketData.getKLineData",
                params={"symbol": "sh000001", "scale": "240", "datalen": "1"},
                timeout=10,
            )
            return resp.status_code == 200
        except Exception:
            return False

    def is_configured(self) -> bool:
        return True

    def _convert_symbol(self, symbol: str) -> str:
        if symbol.startswith("6"):
            return f"sh{symbol}"
        elif symbol.startswith("0") or symbol.startswith("3") or symbol.startswith("1"):
            return f"sz{symbol}"
        elif symbol.startswith("8") or symbol.startswith("4"):
            return f"bj{symbol}"
        return f"sh{symbol}"

    def fetch_daily(
        self, symbol: str, start: Optional[date] = None, end: Optional[date] = None, adjust: str = "forward"
    ) -> pd.DataFrame:
        sina_symbol = self._convert_symbol(symbol)
        end = end or date.today()
        start = start or (end - timedelta(days=365 * 2))
        days = max((end - start).days, 30)
        datalen = min(days + 30, 800)

        try:
            resp = httpx.get(
                self.BASE_URL,
                params={"symbol": sina_symbol, "scale": "240", "datalen": str(datalen)},
                timeout=15,
            )
            if resp.status_code != 200:
                raise ProviderError(f"Sina API returned {resp.status_code}", self.name)

            text = resp.text.strip()
            if not text or text == "null":
                raise ProviderError(f"No data for {symbol} from Sina", self.name)

            import json
            records = json.loads(text)
            if not isinstance(records, list) or len(records) == 0:
                raise ProviderError(f"Empty data for {symbol} from Sina", self.name)

            rows = []
            for r in records:
                d = r.get("day", "")
                if not d:
                    continue
                rows.append({
                    "date": d,
                    "open": float(r.get("open", 0)),
                    "high": float(r.get("high", 0)),
                    "low": float(r.get("low", 0)),
                    "close": float(r.get("close", 0)),
                    "volume": float(r.get("volume", 0)),
                    "amount": float(r.get("ma_volume", 0)) if "ma_volume" in r else 0.0,
                })

            df = pd.DataFrame(rows)
            df["date"] = pd.to_datetime(df["date"])
            df = df[df["date"] >= pd.Timestamp(start)]
            df = df[df["date"] <= pd.Timestamp(end)]

            if df.empty:
                raise ProviderError(f"No data in range for {symbol} from Sina", self.name)

            df = self.normalize(df, self.name, adjust)
            return df

        except ProviderError:
            raise
        except Exception as e:
            raise ProviderError(f"Sina fetch failed: {e}", self.name)