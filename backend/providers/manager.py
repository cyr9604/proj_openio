from datetime import date, datetime
from typing import Optional
import pandas as pd
from sqlalchemy.orm import Session

from config import settings
from database import SessionLocal
from models import DailyQuote
from providers.base import QuoteProvider, ProviderError
from providers.akshare_provider import AkshareProvider
from providers.baostock_provider import BaostockProvider
from providers.efinance_provider import EfinanceProvider
from providers.ths_http_provider import ThsHttpProvider
from providers.ths_ifind_provider import ThsIfindSdkProvider
from providers.sina_provider import SinaProvider


class ProviderManager:
    def __init__(self):
        self._providers: dict[str, QuoteProvider] = {
            "baostock": BaostockProvider(),
            "efinance": EfinanceProvider(),
            "sina": SinaProvider(),
            "akshare": AkshareProvider(),
            "ths_http": ThsHttpProvider(),
            "ths_sdk": ThsIfindSdkProvider(),
        }
        self._status_cache: dict[str, dict] = {}

    def get_provider_status(self) -> list[dict]:
        results = []
        for name, provider in self._providers.items():
            try:
                avail = provider.is_available()
                configured = provider.is_configured()
            except Exception as e:
                avail = False
                configured = False
            results.append({
                "name": name,
                "available": avail,
                "configured": configured,
                "last_sync": None,
                "error": "",
            })
        return results

    def fetch_daily(
        self, symbol: str, start: Optional[date] = None, end: Optional[date] = None, adjust: str = "forward"
    ) -> pd.DataFrame:
        cached = self.get_cached_daily(symbol, start, end, adjust)
        if not cached.empty:
            latest_cache_date = cached["trade_date"].max().date()
            earliest_cache_date = cached["trade_date"].min().date()
            if end and latest_cache_date >= end and start and earliest_cache_date <= start:
                return cached
        errors = []
        for name in settings.priority:
            provider = self._providers.get(name)
            if not provider:
                continue
            try:
                df = provider.fetch_daily(symbol, start, end, adjust)
                if df is not None and not df.empty:
                    self._save_to_db(symbol, df)
                    full = self.get_cached_daily(symbol, start, end, adjust)
                    if not full.empty:
                        latest = full["trade_date"].max().date()
                        earliest = full["trade_date"].min().date()
                        if (end is None or latest >= end) and (start is None or earliest <= start):
                            return full
                    continue
            except ProviderError as e:
                errors.append(str(e))
                continue
            except Exception as e:
                errors.append(f"{name}: {e}")
                continue
        full = self.get_cached_daily(symbol, start, end, adjust)
        if not full.empty:
            return full
        if not cached.empty:
            return cached
        raise ProviderError(
            f"All providers failed for {symbol}: {'; '.join(errors)}",
            "manager",
        )

    def _save_to_db(self, symbol: str, df: pd.DataFrame):
        db: Session = SessionLocal()
        try:
            for _, row in df.iterrows():
                exists = db.query(DailyQuote).filter(
                    DailyQuote.symbol == symbol,
                    DailyQuote.trade_date == row["trade_date"].date(),
                    DailyQuote.adjusted == row.get("adjusted", "forward"),
                ).first()
                if not exists:
                    q = DailyQuote(
                        symbol=symbol,
                        trade_date=row["trade_date"].date(),
                        open=float(row["open"]),
                        high=float(row["high"]),
                        low=float(row["low"]),
                        close=float(row["close"]),
                        volume=float(row.get("volume", 0)),
                        amount=float(row.get("amount", 0)),
                        source=str(row.get("source", "unknown")),
                        adjusted=str(row.get("adjusted", "forward")),
                    )
                    db.add(q)
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()

    def get_cached_daily(
        self, symbol: str, start: Optional[date] = None, end: Optional[date] = None, adjust: str = "forward"
    ) -> pd.DataFrame:
        db: Session = SessionLocal()
        try:
            query = db.query(DailyQuote).filter(
                DailyQuote.symbol == symbol,
                DailyQuote.adjusted == adjust,
            )
            if start:
                query = query.filter(DailyQuote.trade_date >= start)
            if end:
                query = query.filter(DailyQuote.trade_date <= end)
            rows = query.order_by(DailyQuote.trade_date).all()
            if not rows:
                return pd.DataFrame()
            data = [
                {
                    "trade_date": r.trade_date,
                    "open": r.open,
                    "high": r.high,
                    "low": r.low,
                    "close": r.close,
                    "volume": r.volume,
                    "amount": r.amount,
                    "source": r.source,
                    "adjusted": r.adjusted,
                }
                for r in rows
            ]
            df = pd.DataFrame(data)
            df["trade_date"] = pd.to_datetime(df["trade_date"])
            return df
        finally:
            db.close()


manager = ProviderManager()
