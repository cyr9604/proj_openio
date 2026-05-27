from datetime import date, datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field


class StockSearchItem(BaseModel):
    symbol: str
    name: str
    exchange: str = ""


class WatchlistAddRequest(BaseModel):
    symbol: str
    name: str = ""


class WatchlistItem(BaseModel):
    symbol: str
    name: str
    added_at: datetime

    class Config:
        from_attributes = True


class DailyBar(BaseModel):
    trade_date: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    amount: float = 0


class TrendInfo(BaseModel):
    direction: str
    description: str


class SignalPoint(BaseModel):
    date: str
    type: str
    description: str
    price: float = 0


class WatchlistSignalItem(BaseModel):
    symbol: str
    name: str
    signals: list[SignalPoint]


class GoldenCrossItem(BaseModel):
    symbol: str
    name: str
    price: float
    date: str
    signal_type: str = "golden_cross"
    description: str


class FullScanStatus(BaseModel):
    scan_id: str
    status: str
    total: int
    processed: int
    results: list[GoldenCrossItem]


class PositionAdvice(BaseModel):
    recommended_pct: float = 0
    max_pct: float = 50
    advice_text: str = ""


class RiskWarning(BaseModel):
    stop_loss: Optional[float] = None
    stop_loss_desc: str = ""
    risk_level: str = "low"


class AnalysisResponse(BaseModel):
    symbol: str
    name: str = ""
    last_date: str
    last_close: float
    trend: TrendInfo
    signals: list[SignalPoint] = []
    position: PositionAdvice
    risk: RiskWarning
    chart_data: list[dict] = []


class BacktestRequest(BaseModel):
    symbol: str
    start_date: str
    end_date: str
    initial_capital: float = 100000
    fee_rate: float = 0.00025
    min_fee: float = 5
    adjust: str = "forward"
    strategy: str = "ma520"


class StrategyRule(BaseModel):
    type: str = ""
    condition: str
    action: str
    priority: int = 0


class StrategyDetail(BaseModel):
    name: str
    description: str
    buy_rules: list[StrategyRule] = []
    sell_rules: list[StrategyRule] = []
    add_rules: list[StrategyRule] = []


class StrategySummary(BaseModel):
    name: str
    description: str


class BacktestTrade(BaseModel):
    date: str
    action: str
    price: float
    shares: int
    amount: float
    reason: str = ""


class BacktestResponse(BaseModel):
    symbol: str
    start_date: str
    end_date: str
    initial_capital: float
    final_capital: float
    total_return: float
    annual_return: float
    max_drawdown: float
    win_rate: float
    total_trades: int
    total_fees: float
    trades: list[BacktestTrade] = []
    equity_curve: list[dict] = []


class ProviderStatus(BaseModel):
    name: str
    available: bool
    configured: bool
    last_sync: Optional[str] = None
    error: str = ""


class ProviderStatusResponse(BaseModel):
    providers: list[ProviderStatus]
    current_priority: list[str]


class ProviderSettingsRequest(BaseModel):
    priority: list[str] = Field(default=["ths_http", "ths_sdk", "sina", "akshare"])
    ths_http_token: str = ""
    ths_http_refresh_token: str = ""
    ths_sdk_enabled: bool = False
    default_adjust: str = "forward"
