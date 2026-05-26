from datetime import date, timedelta
from typing import Optional
import pandas as pd
import akshare as ak

from providers.base import QuoteProvider, ProviderError


class AkshareProvider(QuoteProvider):
    name = "akshare"

    def is_available(self) -> bool:
        try:
            import akshare
            return True
        except ImportError:
            return False

    def is_configured(self) -> bool:
        return self.is_available()

    def fetch_daily(
        self, symbol: str, start: Optional[date] = None, end: Optional[date] = None, adjust: str = "forward"
    ) -> pd.DataFrame:
        end = end or date.today()
        start = start or (end - timedelta(days=365 * 2))

        try:
            adjust_map = {"forward": "qfq", "backward": "hfq", "none": ""}
            adj = adjust_map.get(adjust, "")
            df = ak.stock_zh_a_hist(
                symbol=symbol,
                period="daily",
                start_date=start.strftime("%Y%m%d"),
                end_date=end.strftime("%Y%m%d"),
                adjust=adj,
            )
            if df.empty:
                raise ProviderError(f"No data for {symbol} from AKShare", self.name)

            df = df.rename(columns={
                "日期": "date",
                "开盘": "open",
                "最高": "high",
                "最低": "low",
                "收盘": "close",
                "成交量": "volume",
                "成交额": "amount",
            })
            df["date"] = pd.to_datetime(df["date"])
            df = self.normalize(df, self.name, adjust)
            return df

        except ProviderError:
            raise
        except Exception as e:
            raise ProviderError(f"AKShare fetch failed: {e}", self.name)
