from datetime import date, timedelta
from typing import Optional
import pandas as pd

from providers.base import QuoteProvider, ProviderError


class EfinanceProvider(QuoteProvider):
    name = "efinance"

    def is_available(self) -> bool:
        try:
            import efinance
            return True
        except ImportError:
            return False

    def is_configured(self) -> bool:
        return self.is_available()

    def fetch_daily(
        self, symbol: str, start: Optional[date] = None, end: Optional[date] = None, adjust: str = "forward"
    ) -> pd.DataFrame:
        import efinance as ef

        end = end or date.today()
        start = start or (end - timedelta(days=365 * 2))

        adjust_map = {"forward": "qfq", "backward": "hfq", "none": ""}
        adj = adjust_map.get(adjust, "qfq")

        try:
            kwargs = {"stock_code": symbol, "beg": start.strftime("%Y%m%d"), "end": end.strftime("%Y%m%d")}
            if adj:
                kwargs["adjust"] = adj
            df = ef.stock.get_quote_history(**kwargs)

            if df is None or df.empty:
                raise ProviderError(f"No data for {symbol} from Efinance", self.name)

            df = df.rename(columns={
                "日期": "date",
                "开盘": "open",
                "收盘": "close",
                "最高": "high",
                "最低": "low",
                "成交量": "volume",
                "成交额": "amount",
            })
            df["date"] = pd.to_datetime(df["date"])
            df = self.normalize(df, self.name, adjust)
            return df

        except ProviderError:
            raise
        except Exception as e:
            raise ProviderError(f"Efinance fetch failed: {e}", self.name)
