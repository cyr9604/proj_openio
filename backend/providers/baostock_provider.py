from datetime import date, timedelta, datetime
from typing import Optional
import pandas as pd

from providers.base import QuoteProvider, ProviderError


class BaostockProvider(QuoteProvider):
    name = "baostock"

    def _convert_symbol(self, symbol: str) -> str:
        if symbol.startswith("6"):
            return f"sh.{symbol}"
        elif symbol.startswith(("0", "3")):
            return f"sz.{symbol}"
        elif symbol.startswith(("8", "4")):
            return f"bj.{symbol}"
        return f"sz.{symbol}"

    def is_available(self) -> bool:
        try:
            import baostock as bs
            lg = bs.login()
            ok = lg.error_code == "0"
            bs.logout()
            return ok
        except Exception:
            return False

    def is_configured(self) -> bool:
        return self.is_available()

    def fetch_daily(
        self, symbol: str, start: Optional[date] = None, end: Optional[date] = None, adjust: str = "forward"
    ) -> pd.DataFrame:
        import baostock as bs

        end = end or date.today()
        start = start or (end - timedelta(days=365 * 2))
        bs_symbol = self._convert_symbol(symbol)

        adjust_map = {"forward": "1", "backward": "2", "none": "3"}
        adj = adjust_map.get(adjust, "1")

        try:
            lg = bs.login()
            if lg.error_code != "0":
                raise ProviderError(f"Baostock login failed: {lg.error_msg}", self.name)

            rs = bs.query_history_k_data_plus(
                bs_symbol,
                fields="date,open,high,low,close,volume,amount",
                start_date=start.strftime("%Y-%m-%d"),
                end_date=end.strftime("%Y-%m-%d"),
                frequency="d",
                adjustflag=adj,
            )
            if rs.error_code != "0":
                raise ProviderError(f"Baostock query failed: {rs.error_msg}", self.name)

            rows = []
            while rs.next():
                row = rs.get_row_data()
                if row[0] is None:
                    continue
                d = row[0]
                try:
                    rows.append({
                        "date": d,
                        "open": float(row[1]),
                        "high": float(row[2]),
                        "low": float(row[3]),
                        "close": float(row[4]),
                        "volume": float(row[5]),
                        "amount": float(row[6]),
                    })
                except (ValueError, TypeError):
                    continue

            bs.logout()

            if not rows:
                raise ProviderError(f"No data for {symbol} from Baostock", self.name)

            df = pd.DataFrame(rows)
            df["date"] = pd.to_datetime(df["date"])
            df = self.normalize(df, self.name, adjust)
            return df

        except ProviderError:
            raise
        except Exception as e:
            raise ProviderError(f"Baostock fetch failed: {e}", self.name)
