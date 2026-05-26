from datetime import date, timedelta
import threading
import uuid

from fastapi import APIRouter, Query
from typing import Optional
import httpx
import json

from schemas import StockSearchItem, GoldenCrossItem, FullScanStatus
from database import SessionLocal
from models import StockInfo, DailyQuote
from providers.manager import manager as provider_manager
from strategy.engine import StrategyEngine

router = APIRouter(prefix="/api/stocks", tags=["stocks"])

# In-memory full scan state
_scan_states: dict[str, dict] = {}


class _ScanState:
    def __init__(self, total: int):
        self.status = "running"
        self.total = total
        self.processed = 0
        self._seek_target: Optional[int] = None
        self.results: list[GoldenCrossItem] = []
        self._pause_event = threading.Event()
        self._pause_event.set()

    def check_paused(self):
        self._pause_event.wait()

    def pause(self):
        self._pause_event.clear()
        self.status = "paused"

    def resume(self):
        self._pause_event.set()
        self.status = "running"

    def cancel(self):
        self.status = "cancelled"
        self._pause_event.set()

    def is_cancelled(self):
        return self.status == "cancelled"

    def seek(self, index: int):
        self._seek_target = max(0, min(index, self.total))

    def get_seek(self) -> Optional[int]:
        target = self._seek_target
        self._seek_target = None
        return target

    def to_schema(self, scan_id: str) -> FullScanStatus:
        return FullScanStatus(
            scan_id=scan_id,
            status=self.status,
            total=self.total,
            processed=self.processed,
            results=self.results,
        )


import json
import os

SYMBOL_CACHE_FILE = os.path.join(os.path.dirname(__file__), "..", "symbol_cache.json")
_symbol_cache: list[tuple[str, str]] | None = None


def _get_all_symbols() -> list[tuple[str, str]]:
    global _symbol_cache
    if _symbol_cache is not None:
        return _symbol_cache
    # Try loading from file cache
    try:
        with open(SYMBOL_CACHE_FILE, "r", encoding="utf-8") as f:
            cached = json.load(f)
            _symbol_cache = [(s["code"], s["name"]) for s in cached]
            return _symbol_cache
    except Exception:
        pass
    # Fresh load
    _symbol_cache = _load_symbols()
    # Save to file cache
    try:
        with open(SYMBOL_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump([{"code": s, "name": n} for s, n in _symbol_cache], f, ensure_ascii=False)
    except Exception:
        pass
    return _symbol_cache


def _load_symbols() -> list[tuple[str, str]]:
    try:
        import akshare as ak
        df = ak.stock_info_a_code_name()
        return [(str(row["code"]), str(row["name"])) for _, row in df.iterrows()]
    except Exception as e:
        print(f"[_load_symbols] AKShare failed: {e}, falling back to DB")
        db = SessionLocal()
        try:
            rows = db.query(StockInfo.symbol, StockInfo.name).all()
            result = [(r.symbol, r.name or "") for r in rows]
            if result:
                return result
            print("[_load_symbols] DB also empty, no symbols available")
            return []
        finally:
            db.close()


def _run_full_scan(scan_id: str, all_stocks: list[tuple[str, str]]):
    state = _scan_states[scan_id]
    i = 0

    while i < len(all_stocks):
        if state.is_cancelled():
            return
        state.check_paused()
        seek_to = state.get_seek()
        if seek_to is not None:
            i = seek_to
            state.processed = i
            continue

        symbol, name = all_stocks[i]
        try:
            end = date.today()
            start = end - timedelta(days=60)
            df = provider_manager.fetch_daily(symbol, start, end, "forward")
            if df.empty or len(df) < 25:
                i += 1
                state.processed = i
                continue
            engine = StrategyEngine(df)
            signals = engine.get_signals()
            golden = [s for s in signals if s.type == "golden_cross"]
            if golden:
                s = golden[0]
                state.results.append(GoldenCrossItem(
                    symbol=symbol,
                    name=name,
                    price=s.price,
                    date=s.date,
                    description=s.description,
                ))
        except Exception:
            pass
        i += 1
        state.processed = i

    if state.status != "cancelled":
        state.status = "completed"


EM_SEARCH_URL = "https://searchadapter.eastmoney.com/api/suggest/get"


def _search_eastmoney(q: str) -> list[StockSearchItem]:
    try:
        resp = httpx.get(EM_SEARCH_URL, params={"input": q, "type": "14"}, timeout=5)
        if resp.status_code != 200:
            return []
        data = resp.json()
        rows = data.get("QuotationCodeTable", {}).get("Data", [])
        items = []
        for row in rows[:20]:
            code = row.get("Code", "")
            name = row.get("Name", "")
            sec_type = row.get("SecurityTypeName", "")
            exchange_map = {"深A": "深交所", "沪A": "上交所", "深B": "深交所", "沪B": "上交所", "基金": ""}
            exchange = exchange_map.get(sec_type, "")
            if code and name:
                items.append(StockSearchItem(symbol=code, name=name, exchange=exchange))
        return items
    except Exception:
        return []


def _search_akshare(q: str) -> list[StockSearchItem]:
    try:
        import akshare as ak
        df = ak.stock_zh_a_spot_em()
        if q:
            mask = df["代码"].str.contains(q, na=False) | df["名称"].str.contains(q, na=False)
            df = df[mask]
        results = []
        for _, row in df.head(20).iterrows():
            results.append(StockSearchItem(
                symbol=str(row["代码"]),
                name=str(row["名称"]),
                exchange="",
            ))
        return results
    except Exception:
        return []


def _search_local(q: str) -> list[StockSearchItem]:
    db = SessionLocal()
    try:
        query = db.query(StockInfo).filter(
            StockInfo.symbol.contains(q) | StockInfo.name.contains(q)
        ).limit(20)
        return [StockSearchItem(symbol=r.symbol, name=r.name, exchange=r.exchange or "") for r in query]
    finally:
        db.close()


@router.post("/golden-cross/full-scan")
def start_full_scan():
    all_stocks = _get_all_symbols()
    scan_id = str(uuid.uuid4())
    _scan_states[scan_id] = _ScanState(len(all_stocks))
    if all_stocks:
        thread = threading.Thread(target=_run_full_scan, args=(scan_id, all_stocks), daemon=True)
        thread.start()
    else:
        _scan_states[scan_id].status = "completed"
    return {"scan_id": scan_id}


@router.get("/golden-cross/full-scan/{scan_id}")
def get_full_scan_status(scan_id: str):
    state = _scan_states.get(scan_id)
    if not state:
        return {"error": "scan not found"}
    return state.to_schema(scan_id)


@router.post("/golden-cross/full-scan/{scan_id}/pause")
def pause_full_scan(scan_id: str):
    state = _scan_states.get(scan_id)
    if state:
        state.pause()
    return {"status": "ok"}


@router.post("/golden-cross/full-scan/{scan_id}/resume")
def resume_full_scan(scan_id: str):
    state = _scan_states.get(scan_id)
    if state:
        state.resume()
    return {"status": "ok"}


@router.post("/golden-cross/full-scan/{scan_id}/seek")
def seek_full_scan(scan_id: str, index: int = Query(...)):
    state = _scan_states.get(scan_id)
    if state:
        state.seek(index)
    return {"status": "ok"}


@router.get("/golden-cross/full-scan/{scan_id}/exists")
def exists_full_scan(scan_id: str):
    state = _scan_states.get(scan_id)
    if not state:
        return {"exists": False}
    return {"exists": True, "status": state.status}


@router.get("/golden-cross")
def get_golden_cross_stocks():
    db = SessionLocal()
    try:
        sixty_days_ago = date.today() - timedelta(days=60)
        recent_symbols = (
            db.query(DailyQuote.symbol)
            .filter(DailyQuote.trade_date >= sixty_days_ago)
            .distinct()
            .all()
        )
    finally:
        db.close()

    symbols = [s[0] for s in recent_symbols]
    results: list[GoldenCrossItem] = []

    for symbol in symbols:
        try:
            end = date.today()
            start = end - timedelta(days=60)
            df = provider_manager.fetch_daily(symbol, start, end, "forward")
            if df.empty or len(df) < 25:
                continue
            engine = StrategyEngine(df)
            signals = engine.get_signals()
            golden = [s for s in signals if s.type == "golden_cross"]
            if golden:
                s = golden[0]
                info = _get_stock_name(symbol)
                results.append(GoldenCrossItem(
                    symbol=symbol,
                    name=info,
                    price=s.price,
                    date=s.date,
                    description=s.description,
                ))
        except Exception:
            continue

    return results


def _get_stock_name(symbol: str) -> str:
    db = SessionLocal()
    try:
        info = db.query(StockInfo).filter(StockInfo.symbol == symbol).first()
        return info.name if info else ""
    except Exception:
        return ""
    finally:
        db.close()


@router.get("/search")
def search_stocks(q: str = Query("", min_length=1)):
    results = _search_eastmoney(q)
    if results:
        return results
    results = _search_akshare(q)
    if results:
        return results
    return _search_local(q)