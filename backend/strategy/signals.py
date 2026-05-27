import pandas as pd
import numpy as np
from datetime import datetime
from typing import Optional

from schemas import SignalPoint


class SignalDetector:
    def __init__(self, df: pd.DataFrame):
        self.df = df

    def _trend_up(self, row) -> bool:
        slope = row["ma20_slope"]
        return pd.notna(slope) and slope > 0.5

    def detect_all(self) -> list[SignalPoint]:
        signals = []
        signals.extend(self._detect_golden_cross())
        signals.extend(self._detect_pullback())
        signals.extend(self._detect_convergence())
        signals.extend(self._detect_macd_plus())
        signals.extend(self._detect_combined_gc_macd())
        signals.extend(self._detect_stop_loss())
        signals.extend(self._detect_take_profit())
        return signals

    def _deduplicate_consecutive(self, signals: list[SignalPoint]) -> list[SignalPoint]:
        if not signals:
            return signals
        sorted_sigs = sorted(signals, key=lambda s: s.date)
        result = [sorted_sigs[0]]
        for s in sorted_sigs[1:]:
            last = result[-1]
            if s.type == last.type:
                s_date = datetime.strptime(s.date, "%Y-%m-%d").date()
                last_date = datetime.strptime(last.date, "%Y-%m-%d").date()
                if (s_date - last_date).days <= 1:
                    continue
            result.append(s)
        return result

    def scan_history(self) -> list[SignalPoint]:
        all_signals = []
        min_required = 25
        for i in range(min_required, len(self.df)):
            orig_df = self.df
            self.df = self.df.iloc[: i + 1]
            try:
                day_signals = self.detect_all()
                all_signals.extend(day_signals)
            finally:
                self.df = orig_df
        return self._deduplicate_consecutive(all_signals)

    def _detect_golden_cross(self) -> list[SignalPoint]:
        signals = []
        if len(self.df) < 21:
            return signals
        prev = self.df.iloc[-2]
        curr = self.df.iloc[-1]
        if not (pd.notna(prev["ma5"]) and pd.notna(prev["ma20"]) and pd.notna(curr["ma5"]) and pd.notna(curr["ma20"])):
            return signals
        if prev["ma5"] <= prev["ma20"] and curr["ma5"] > curr["ma20"]:
            reasons = []
            if not self._trend_up(curr):
                reasons.append("20日线未向上")
            if pd.notna(curr["volume_ratio"]) and curr["volume_ratio"] < 1.5:
                reasons.append("成交量不足1.5倍")
            if pd.notna(curr["ma20"]) and curr["close"] < curr["ma20"]:
                reasons.append("股价未站上20日线")
            desc = "5日线上穿20日线，形成金叉"
            if reasons:
                desc += "，但条件不满足: " + "; ".join(reasons)
                desc += "，谨慎对待"
            else:
                desc += "，成交量放大，确认有效买入信号"
            signals.append(SignalPoint(
                date=str(curr["trade_date"].date()),
                type="golden_cross",
                description=desc,
                price=round(float(curr["close"]), 2),
            ))
        return signals

    def _detect_pullback(self) -> list[SignalPoint]:
        signals = []
        if len(self.df) < 25:
            return signals
        curr = self.df.iloc[-1]
        recent = self.df.iloc[-10:]
        golden_crossed = False
        gc_idx = -1
        for i in range(1, len(recent)):
            if (pd.notna(recent.iloc[i-1]["ma5"]) and pd.notna(recent.iloc[i-1]["ma20"])
                    and pd.notna(recent.iloc[i]["ma5"]) and pd.notna(recent.iloc[i]["ma20"])):
                if recent.iloc[i-1]["ma5"] <= recent.iloc[i-1]["ma20"] and recent.iloc[i]["ma5"] > recent.iloc[i]["ma20"]:
                    golden_crossed = True
                    gc_idx = len(self.df) - 10 + i
                    break
        if not golden_crossed or gc_idx is None or not pd.notna(curr["ma20"]) or not pd.notna(curr["close"]):
            return signals
        pullback_pct = (curr["close"] - curr["ma20"]) / curr["ma20"] * 100
        if not (0 <= pullback_pct <= 3):
            return signals
        reasons = []
        if not self._trend_up(curr):
            reasons.append("20日线未向上")
        pullback_bars = self.df.iloc[gc_idx:]
        if len(pullback_bars) >= 3:
            max_vol = pullback_bars["volume"].max()
            avg_vol = pullback_bars["volume"].mean()
            vol_ratio = avg_vol / max_vol if max_vol > 0 else 1
            if vol_ratio > 0.7:
                reasons.append(f"回调缩量不足(均量/最大量={vol_ratio:.0%})")
        if pd.notna(curr["volume_ratio"]) and curr["volume_ratio"] >= 1.0 and curr["close"] > curr["ma5"]:
            pass
        else:
            reasons.append("未出现带量阳线站上5日线")
        desc = f"回踩20日线（偏离{pullback_pct:.1f}%）"
        if reasons:
            desc += "，但: " + "; ".join(reasons)
        else:
            desc += "，缩量回踩后带量站上5日线，确认回踩买点"
        signals.append(SignalPoint(
            date=str(curr["trade_date"].date()),
            type="pullback",
            description=desc,
            price=round(float(curr["close"]), 2),
        ))
        return signals

    def _detect_convergence(self) -> list[SignalPoint]:
        signals = []
        if len(self.df) < 25:
            return signals
        recent = self.df.iloc[-10:]
        ma5_vals = recent["ma5"].dropna()
        ma20_vals = recent["ma20"].dropna()
        if len(ma5_vals) < 5 or len(ma20_vals) < 5:
            return signals
        gap_pct = ((ma5_vals - ma20_vals).abs() / ma20_vals * 100)
        avg_gap = gap_pct.mean()
        last_gap = gap_pct.iloc[-1]
        if avg_gap >= 1.5 or last_gap >= 1.5:
            return signals
        curr = self.df.iloc[-1]
        reasons = []
        if pd.notna(curr["volume_ratio"]) and curr["volume_ratio"] < 1.5:
            reasons.append("放量不足(量比<1.5)")
        lookback = 20
        if len(self.df) >= lookback:
            recent_high = self.df.iloc[-lookback:-1]["high"].max()
            if pd.notna(curr["close"]) and curr["close"] <= recent_high:
                reasons.append("未突破前期震荡区间")
        desc = "5日线与20日线粘合"
        if reasons:
            desc += "，但: " + "; ".join(reasons)
        else:
            desc += "，放量发散突破区间，确认粘合发散买点"
        signals.append(SignalPoint(
            date=str(curr["trade_date"].date()),
            type="convergence",
            description=desc,
            price=round(float(curr["close"]), 2),
        ))
        return signals

    def _detect_macd_plus(self) -> list[SignalPoint]:
        signals = []
        if len(self.df) < 27:
            return signals
        prev = self.df.iloc[-2]
        curr = self.df.iloc[-1]
        if pd.notna(prev["macd"]) and pd.notna(curr["macd"]):
            if prev["macd"] < 0 and curr["macd"] >= 0:
                signals.append(SignalPoint(
                    date=str(curr["trade_date"].date()),
                    type="macd_plus",
                    description="MACD由负转正，零轴上方确认，趋势转多",
                    price=round(float(curr["close"]), 2),
                ))
        return signals

    def _detect_combined_gc_macd(self) -> list[SignalPoint]:
        signals = []
        if len(self.df) < 27:
            return signals
        recent = self.df.iloc[-6:]
        gc_dates = []
        mp_dates = []
        for j in range(1, len(recent)):
            rp = recent.iloc[j - 1]
            rc = recent.iloc[j]
            if pd.notna(rp["ma5"]) and pd.notna(rp["ma20"]) and pd.notna(rc["ma5"]) and pd.notna(rc["ma20"]):
                if rp["ma5"] <= rp["ma20"] and rc["ma5"] > rc["ma20"]:
                    gc_dates.append(rc["trade_date"])
            if pd.notna(rp["macd"]) and pd.notna(rc["macd"]):
                if rp["macd"] < 0 and rc["macd"] >= 0:
                    mp_dates.append(rc["trade_date"])
        curr = self.df.iloc[-1]
        for gd in gc_dates:
            for md in mp_dates:
                diff = abs((gd - md).days)
                if diff <= 5:
                    later = max(gd, md)
                    if later == recent.iloc[-1]["trade_date"] or later == recent.iloc[-2]["trade_date"]:
                        signals.append(SignalPoint(
                            date=str(curr["trade_date"].date()),
                            type="combined_gc_macd",
                            description=f"金叉+MACD+双信号{diff}日内共振确认，强买入信号",
                            price=round(float(curr["close"]), 2),
                        ))
                        return signals
        return signals

    def _detect_stop_loss(self) -> list[SignalPoint]:
        signals = []
        if len(self.df) < 6:
            return signals
        curr = self.df.iloc[-1]
        prev = self.df.iloc[-2]
        prev2 = self.df.iloc[-3]
        if pd.notna(curr["ma5"]) and pd.notna(prev["close"]) and pd.notna(curr["close"]) and pd.notna(prev2["close"]):
            if prev2["close"] < prev2["ma5"] and prev["close"] < prev["ma5"] and curr["close"] < curr["ma5"]:
                signals.append(SignalPoint(
                    date=str(curr["trade_date"].date()),
                    type="stop_loss_ma5",
                    description="连续三日收盘跌破5日线，立即止损，最大亏损控制在5%以内",
                    price=round(float(curr["close"]), 2),
                ))
        if pd.notna(curr["ma20"]) and pd.notna(curr["close"]) and pd.notna(curr["volume_ratio"]):
            if curr["close"] < curr["ma20"] and curr["volume_ratio"] > 1.5:
                signals.append(SignalPoint(
                    date=str(curr["trade_date"].date()),
                    type="stop_loss_ma20",
                    description="放量跌破20日线，收盘收不回，无条件清仓",
                    price=round(float(curr["close"]), 2),
                ))
        return signals

    def _detect_take_profit(self) -> list[SignalPoint]:
        signals = []
        if len(self.df) < 2:
            return signals
        curr = self.df.iloc[-1]
        if pd.notna(curr["ma5"]) and pd.notna(curr["ma20"]):
            if curr["ma5"] < curr["ma20"]:
                signals.append(SignalPoint(
                    date=str(curr["trade_date"].date()),
                    type="death_cross",
                    description="5日线下穿20日线形成死叉，强势趋势结束，清仓止盈/止损",
                    price=round(float(curr["close"]), 2),
                ))
        # --- 最小止盈: 收盘价从上方跌破MA20，盈利3-5% ---
        if len(self.df) >= 3:
            prev = self.df.iloc[-2]
            prev_close = float(prev["close"])
            prev_ma20 = float(prev["ma20"]) if pd.notna(prev["ma20"]) else None
            curr_close = float(curr["close"])
            curr_ma20 = float(curr["ma20"]) if pd.notna(curr["ma20"]) else None
            if prev_ma20 is not None and curr_ma20 is not None and prev_close > prev_ma20 and curr_close <= curr_ma20:
                entry = float(self.df.iloc[-5]["close"]) if len(self.df) >= 5 else prev_close
                pnl_pct = (curr_close - entry) / entry * 100
                if 3 <= pnl_pct <= 5:
                    signals.append(SignalPoint(
                        date=str(curr["trade_date"].date()),
                        type="take_profit_mini",
                        description=f"收盘价跌破MA20({curr_ma20:.2f})，估算盈利{pnl_pct:.1f}%，建议卖出止盈锁定3%-5%利润",
                        price=round(float(curr["close"]), 2),
                    ))
        if len(self.df) >= 5:
            last5 = self.df.iloc[-5:]
            entry_price = last5["close"].iloc[0]
            current_price = last5["close"].iloc[-1]
            pnl_pct = (current_price - entry_price) / entry_price * 100
            if 10 <= pnl_pct <= 20:
                signals.append(SignalPoint(
                    date=str(curr["trade_date"].date()),
                    type="take_profit_normal",
                    description=f"盈利{pnl_pct:.1f}%，达到10%-20%止盈目标，建议卖出落袋为安",
                    price=round(float(curr["close"]), 2),
                ))
        return signals
