from datetime import date, timedelta
from typing import Optional
import pandas as pd

from providers.base import QuoteProvider, ProviderError
from config import settings


class ThsIfindSdkProvider(QuoteProvider):
    name = "ths_sdk"
    _ifind = None

    def is_configured(self) -> bool:
        return settings.ths_sdk_enabled

    def is_available(self) -> bool:
        if not self.is_configured():
            return False
        try:
            from THS import iFinD
            self._ifind = iFinD
            return True
        except ImportError:
            return False

    def fetch_daily(
        self, symbol: str, start: Optional[date] = None, end: Optional[date] = None, adjust: str = "forward"
    ) -> pd.DataFrame:
        if not self.is_available():
            raise ProviderError("同花顺 iFinD SDK not available", self.name)

        end = end or date.today()
        start = start or (end - timedelta(days=365 * 2))

        adjust_code = {"forward": "1", "backward": "2", "none": "0"}
        adj = adjust_code.get(adjust, "1")

        try:
            df = self._ifind.THS_iFinDData(
                code=symbol,
                indicators="open,high,low,close,volume,amount",
                start=start.strftime("%Y%m%d"),
                end=end.strftime("%Y%m%d"),
                adjust=adj,
            )
            if df is None or df.empty:
                raise ProviderError(f"No data for {symbol} from iFinD SDK", self.name)

            df = df.rename(columns={
                "date": "trade_date",
                "open": "open",
                "high": "high",
                "low": "low",
                "close": "close",
                "volume": "volume",
                "amount": "amount",
            })
            if "trade_date" not in df.columns and "date" in df.columns:
                df = df.rename(columns={"date": "trade_date"})
            df["trade_date"] = pd.to_datetime(df["trade_date"])
            out = df[["trade_date", "open", "high", "low", "close", "volume", "amount"]].copy()
            out["source"] = self.name
            out["adjusted"] = adjust
            out["symbol"] = symbol
            out.drop_duplicates(subset=["trade_date"], inplace=True)
            out.sort_values("trade_date", inplace=True)
            out.reset_index(drop=True, inplace=True)
            return out

        except ProviderError:
            raise
        except Exception as e:
            raise ProviderError(f"iFinD SDK fetch error: {e}", self.name)
