from fastapi import APIRouter, Query
from datetime import date, timedelta
from typing import Optional

from providers.manager import manager as provider_manager
from strategy.engine import StrategyEngine
from schemas import AnalysisResponse
from database import SessionLocal
from models import StockInfo

router = APIRouter(prefix="/api/analysis", tags=["analysis"])


@router.get("/{symbol}")
def analyze_stock(
    symbol: str,
    start: Optional[str] = Query(None),
    end: Optional[str] = Query(None),
    adjust: str = Query("forward"),
):
    end_date = date.fromisoformat(end) if end else date.today()
    start_date = date.fromisoformat(start) if start else (end_date - timedelta(days=365 * 2))

    df = provider_manager.fetch_daily(symbol, start_date, end_date, adjust)
    engine = StrategyEngine(df)
    name = _get_stock_name(symbol)
    return engine.analyze(symbol, name)


def _get_stock_name(symbol: str) -> str:
    db = SessionLocal()
    try:
        info = db.query(StockInfo).filter(StockInfo.symbol == symbol).first()
        return info.name if info else ""
    finally:
        db.close()
