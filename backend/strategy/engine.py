from datetime import date
from typing import Optional
import pandas as pd
import numpy as np

from strategy.signals import SignalDetector
from schemas import (
    DailyBar, TrendInfo, SignalPoint, PositionAdvice, RiskWarning, AnalysisResponse,
)


class StrategyEngine:
    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()
        self._prepare()

    def _prepare(self):
        if self.df.empty:
            return
        self.df.sort_values("trade_date", inplace=True)
        self.df.reset_index(drop=True, inplace=True)
        self.df["ma5"] = self.df["close"].rolling(window=5).mean()
        self.df["ma20"] = self.df["close"].rolling(window=20).mean()
        self.df["ma20_slope"] = self.df["ma20"].diff(5) / self.df["ma20"].shift(5) * 100
        self.df["volume_ma5"] = self.df["volume"].rolling(5).mean()
        self.df["volume_ratio"] = self.df["volume"] / self.df["volume_ma5"]
        self.df["ema12"] = self.df["close"].ewm(span=12, adjust=False).mean()
        self.df["ema26"] = self.df["close"].ewm(span=26, adjust=False).mean()
        self.df["macd"] = self.df["ema12"] - self.df["ema26"]

    def get_last_row(self):
        if self.df.empty:
            return None
        return self.df.iloc[-1]

    def get_trend(self) -> TrendInfo:
        row = self.get_last_row()
        if row is None:
            return TrendInfo(direction="unknown", description="无数据")
        slope = row["ma20_slope"]
        if pd.isna(slope):
            return TrendInfo(direction="unknown", description="数据不足，无法判断趋势")
        if slope > 0.5:
            return TrendInfo(direction="up", description="20日线向上，趋势偏多")
        elif slope < -0.5:
            return TrendInfo(direction="down", description="20日线向下，趋势偏空")
        else:
            return TrendInfo(direction="flat", description="20日线走平，趋势待变")

    def get_signals(self) -> list[SignalPoint]:
        detector = SignalDetector(self.df)
        return detector.detect_all()

    def get_historical_signals(self) -> list[SignalPoint]:
        detector = SignalDetector(self.df)
        return detector.scan_history()

    def get_position_advice(self, signals: list[SignalPoint]) -> PositionAdvice:
        has_golden = any(s.type == "golden_cross" for s in signals)
        has_pullback = any(s.type == "pullback" for s in signals)
        has_convergence = any(s.type == "convergence" for s in signals)
        has_macd_plus = any(s.type == "macd_plus" for s in signals)
        trend = self.get_trend().direction

        full_conditions = [
            "无缩量问题" not in s.description and "未满足" not in s.description
            for s in signals if s.type in ("golden_cross", "pullback", "convergence")
        ]
        all_full = any(full_conditions)

        if trend == "down":
            return PositionAdvice(
                recommended_pct=0, max_pct=50,
                advice_text="20日线向下，中期空头，坚决不进场，管住手避开80%深套风险",
            )
        if trend == "flat":
            return PositionAdvice(
                recommended_pct=0, max_pct=50,
                advice_text="20日线走平，震荡市，观望为主，不买不卖避免来回止损",
            )

        if has_macd_plus and trend == "up":
            return PositionAdvice(
                recommended_pct=30, max_pct=50,
                advice_text="MACD+买点：MACD由负转正+20日线向上，3成仓试探，回踩确认加仓至5成",
            )
        if has_golden and trend == "up" and all_full:
            return PositionAdvice(
                recommended_pct=30, max_pct=50,
                advice_text="金叉买点：20日线向上+放量金叉+站上均线，首次3成仓试探，回踩确认再加2成至最高5成",
            )
        if has_pullback and trend == "up" and all_full:
            return PositionAdvice(
                recommended_pct=30, max_pct=50,
                advice_text="回踩买点：金叉后缩量回踩20日线，确认后买入3成，再加仓至最高5成",
            )
        if has_convergence and trend == "up" and all_full:
            return PositionAdvice(
                recommended_pct=40, max_pct=40,
                advice_text="粘合发散买点：放量突破+均线发散，4成仓快进快出，不贪多",
            )

        if has_golden or has_pullback or has_convergence or has_macd_plus:
            return PositionAdvice(
                recommended_pct=20, max_pct=30,
                advice_text="有买点信号但部分条件不满足（检查成交量/趋势/均线位置），建议轻仓或等待确认",
            )

        return PositionAdvice(
            recommended_pct=0, max_pct=50,
            advice_text="无明确买点信号，建议空仓观望",
        )

    def get_risk_warning(self) -> RiskWarning:
        signals = self.get_signals()
        has_stop = any(s.type in ("stop_loss_ma5", "stop_loss_ma20") for s in signals)
        if has_stop:
            return RiskWarning(
                stop_loss=self.get_last_row()["close"] if self.get_last_row() is not None else None,
                stop_loss_desc="已触发止损信号，建议及时止损",
                risk_level="high",
            )
        trend = self.get_trend().direction
        if trend == "down":
            return RiskWarning(
                risk_level="high",
                stop_loss_desc="趋势向下，注意控制风险",
            )
        elif trend == "flat":
            return RiskWarning(
                risk_level="medium",
                stop_loss_desc="趋势走平，注意方向选择",
            )
        return RiskWarning(risk_level="low", stop_loss_desc="风险可控")

    def to_chart_data(self) -> list[dict]:
        data = []
        for _, row in self.df.iterrows():
            item = {
                "trade_date": row["trade_date"].strftime("%Y-%m-%d") if hasattr(row["trade_date"], "strftime") else str(row["trade_date"]),
                "open": round(float(row["open"]), 2),
                "high": round(float(row["high"]), 2),
                "low": round(float(row["low"]), 2),
                "close": round(float(row["close"]), 2),
                "volume": float(row["volume"]),
                "ma5": round(float(row["ma5"]), 2) if pd.notna(row["ma5"]) else None,
                "ma20": round(float(row["ma20"]), 2) if pd.notna(row["ma20"]) else None,
            }
            data.append(item)
        return data

    def analyze(self, symbol: str, name: str = "") -> AnalysisResponse:
        row = self.get_last_row()
        trend = self.get_trend()
        signals = self.get_signals()
        position = self.get_position_advice(signals)
        risk = self.get_risk_warning()
        chart = self.to_chart_data()
        historical_signals = self.get_historical_signals()

        return AnalysisResponse(
            symbol=symbol,
            name=name,
            last_date=str(row["trade_date"].date()) if row is not None else "",
            last_close=round(float(row["close"]), 2) if row is not None else 0,
            trend=trend,
            signals=historical_signals,
            position=position,
            risk=risk,
            chart_data=chart,
        )
