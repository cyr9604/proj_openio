from fastapi import APIRouter, HTTPException
from datetime import date, timedelta

from providers.manager import manager as provider_manager
from strategy.backtest import BacktestEngine
from strategy.registry import get_all_strategies, get_strategy_detail
from schemas import BacktestRequest, BacktestResponse, StrategyDetail, StrategySummary
from database import SessionLocal
from models import BacktestResult
import json

router = APIRouter(prefix="/api/backtest", tags=["backtest"])
strategy_router = APIRouter(prefix="/api/strategies", tags=["strategies"])


@router.post("")
def run_backtest(req: BacktestRequest):
    end_date = date.fromisoformat(req.end_date) if "-" in req.end_date else date.today()
    start_date = date.fromisoformat(req.start_date) if "-" in req.start_date else (end_date.replace(year=end_date.year - 2))

    df = provider_manager.fetch_daily(
        req.symbol, start_date, end_date, req.adjust
    )
    engine = BacktestEngine(df, req)
    result = engine.run()
    engine.save_result(result)
    return result


@router.get("/history")
def list_backtest_history():
    db = SessionLocal()
    try:
        results = db.query(BacktestResult).order_by(BacktestResult.created_at.desc()).limit(20).all()
        out = []
        for r in results:
            out.append({
                "id": r.id,
                "symbol": r.symbol,
                "start_date": str(r.start_date),
                "end_date": str(r.end_date),
                "total_return": r.total_return,
                "max_drawdown": r.max_drawdown,
                "win_rate": r.win_rate,
                "total_trades": r.total_trades,
                "created_at": str(r.created_at),
            })
        return out
    finally:
        db.close()


@router.get("/history/{result_id}")
def get_backtest_detail(result_id: int):
    db = SessionLocal()
    try:
        r = db.query(BacktestResult).filter(BacktestResult.id == result_id).first()
        if not r:
            return {"error": "not found"}
        return {
            "symbol": r.symbol,
            "start_date": str(r.start_date),
            "end_date": str(r.end_date),
            "initial_capital": r.initial_capital,
            "total_return": r.total_return,
            "annual_return": r.annual_return,
            "max_drawdown": r.max_drawdown,
            "win_rate": r.win_rate,
            "total_trades": r.total_trades,
            "total_fees": r.total_fees,
            "trades": json.loads(r.details) if r.details else [],
        }
    finally:
        db.close()


@strategy_router.get("")
def list_strategies() -> dict[str, StrategySummary]:
    return get_all_strategies()


@strategy_router.get("/{name}")
def get_strategy(name: str) -> StrategyDetail:
    detail = get_strategy_detail(name)
    if not detail:
        raise HTTPException(status_code=404, detail=f"策略 '{name}' 不存在")
    return StrategyDetail(**detail)
