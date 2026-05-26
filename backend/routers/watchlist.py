from datetime import date, timedelta, datetime

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from database import get_db
from models import Watchlist
from schemas import WatchlistAddRequest, WatchlistItem, WatchlistSignalItem
from providers.manager import manager as provider_manager
from strategy.engine import StrategyEngine

router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])


@router.get("/signals")
def get_watchlist_signals(db: Session = Depends(get_db)):
    items = db.query(Watchlist).order_by(Watchlist.added_at.desc()).all()
    results: list[WatchlistSignalItem] = []
    three_days_ago = date.today() - timedelta(days=3)
    for item in items:
        try:
            end = date.today()
            start = end - timedelta(days=60)
            df = provider_manager.fetch_daily(item.symbol, start, end, "forward")
            if df.empty:
                continue
            engine = StrategyEngine(df)
            all_signals = engine.get_historical_signals()
            recent = [
                s for s in all_signals
                if datetime.strptime(s.date, "%Y-%m-%d").date() >= three_days_ago
            ]
            if recent:
                results.append(WatchlistSignalItem(symbol=item.symbol, name=item.name, signals=recent))
        except Exception:
            continue
    return results


@router.get("")
def list_watchlist(db: Session = Depends(get_db)):
    items = db.query(Watchlist).order_by(Watchlist.added_at.desc()).all()
    return [WatchlistItem(symbol=w.symbol, name=w.name, added_at=w.added_at) for w in items]


@router.post("")
def add_watchlist(req: WatchlistAddRequest, db: Session = Depends(get_db)):
    exists = db.query(Watchlist).filter(Watchlist.symbol == req.symbol).first()
    if not exists:
        item = Watchlist(symbol=req.symbol, name=req.name)
        db.add(item)
        db.commit()
        return {"status": "ok", "symbol": req.symbol}
    return {"status": "exists", "symbol": req.symbol}


@router.delete("/{symbol}")
def remove_watchlist(symbol: str, db: Session = Depends(get_db)):
    db.query(Watchlist).filter(Watchlist.symbol == symbol).delete()
    db.commit()
    return {"status": "ok", "symbol": symbol}
