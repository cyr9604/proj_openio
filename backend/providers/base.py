from abc import ABC, abstractmethod
from datetime import date
from typing import Optional, Any
import pandas as pd


class QuoteProvider(ABC):
    name: str = "base"

    @abstractmethod
    def fetch_daily(
        self, symbol: str, start: Optional[date] = None, end: Optional[date] = None, adjust: str = "forward"
    ) -> pd.DataFrame:
        ...

    @abstractmethod
    def is_available(self) -> bool:
        ...

    @abstractmethod
    def is_configured(self) -> bool:
        ...

    def normalize(self, df: pd.DataFrame, source: str, adjust: str) -> pd.DataFrame:
        required = {"date", "open", "high", "low", "close", "volume"}
        if not required.issubset(df.columns):
            missing = required - set(df.columns)
            raise ValueError(f"Missing columns: {missing}")
        out = df.rename(columns={"date": "trade_date"}).copy()
        out["trade_date"] = pd.to_datetime(out["trade_date"])
        out["source"] = source
        out["adjusted"] = adjust
        out["amount"] = out.get("amount", 0.0)
        out["symbol"] = out.get("symbol", "")
        out.drop_duplicates(subset=["trade_date"], inplace=True)
        out.sort_values("trade_date", inplace=True)
        out.reset_index(drop=True, inplace=True)
        return out


class ProviderError(Exception):
    def __init__(self, message: str, provider: str):
        self.provider = provider
        self.message = message
        super().__init__(f"[{provider}] {message}")
