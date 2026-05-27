import pandas as pd
import numpy as np
from datetime import date, datetime
from typing import Optional
from sqlalchemy.orm import Session

from schemas import BacktestRequest, BacktestResponse, BacktestTrade
from strategy.signals import SignalDetector
from database import SessionLocal
from models import BacktestResult
import json


class BacktestEngine:
    def __init__(self, df: pd.DataFrame, request: BacktestRequest):
        self.df = df.copy()
        self.request = request
        self.fee_rate = request.fee_rate
        self.min_fee = request.min_fee
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

    def run(self) -> BacktestResponse:
        capital = self.request.initial_capital
        initial_capital = capital
        position = 0
        cost = 0
        trades: list[BacktestTrade] = []
        equity_curve = []
        peak = capital
        max_drawdown = 0
        wins = 0
        losses = 0
        total_fees = 0
        in_position = False
        buy_triggered = False
        buy_type = ""
        last_gc_idx = -1
        last_macd_plus_idx = -1

        min_rows = 25
        if len(self.df) < min_rows:
            return BacktestResponse(
                symbol=self.request.symbol,
                start_date=self.request.start_date,
                end_date=self.request.end_date,
                initial_capital=initial_capital,
                final_capital=capital,
                total_return=0,
                annual_return=0,
                max_drawdown=0,
                win_rate=0,
                total_trades=0,
                total_fees=0,
                trades=[],
                equity_curve=[{"date": str(self.df.iloc[-1]["trade_date"].date()) if not self.df.empty else "", "equity": capital, "position": 0}],
            )

        for i in range(20, len(self.df)):
            row = self.df.iloc[i]
            prev = self.df.iloc[i - 1]
            date_str = str(row["trade_date"].date())
            price = float(row["close"])
            volume_ratio = float(row["volume_ratio"]) if pd.notna(row["volume_ratio"]) else 1.0

            ma5 = float(row["ma5"]) if pd.notna(row["ma5"]) else None
            ma20 = float(row["ma20"]) if pd.notna(row["ma20"]) else None
            prev_ma5 = float(prev["ma5"]) if pd.notna(prev["ma5"]) else None
            prev_ma20 = float(prev["ma20"]) if pd.notna(prev["ma20"]) else None

            if ma5 is None or ma20 is None or prev_ma5 is None or prev_ma20 is None:
                equity_curve.append({"date": date_str, "equity": round(capital, 2), "position": 0})
                continue

            trend_up = row["ma20_slope"] > 0.5 if pd.notna(row["ma20_slope"]) else False
            trend_down = row["ma20_slope"] < -0.5 if pd.notna(row["ma20_slope"]) else False

            # --- Buy signals (规则: 20日线向下/走平不进场) ---
            golden_cross = False
            if trend_up:
                if prev_ma5 <= prev_ma20 and ma5 > ma20:
                    if volume_ratio >= 1.5:
                        if price > ma20:
                            golden_cross = True

            # Track raw MA5 crossover (regardless of trend/volume) for combined signal detection
            raw_gc = False
            if all(x is not None for x in [prev_ma5, prev_ma20, ma5, ma20]):
                if prev_ma5 <= prev_ma20 and ma5 > ma20:
                    raw_gc = True

            pullback = False
            if trend_up and ma20 is not None:
                pullback_pct = (price - ma20) / ma20 * 100
                if 0 <= pullback_pct <= 3:
                    gc_found = False
                    for j in range(max(0, i - 10), i):
                        if (pd.notna(self.df.iloc[j-1]["ma5"]) and pd.notna(self.df.iloc[j-1]["ma20"])
                                and pd.notna(self.df.iloc[j]["ma5"]) and pd.notna(self.df.iloc[j]["ma20"])):
                            if self.df.iloc[j-1]["ma5"] <= self.df.iloc[j-1]["ma20"] and self.df.iloc[j]["ma5"] > self.df.iloc[j]["ma20"]:
                                gc_found = True
                                break
                    if gc_found:
                        gc_bars = self.df.iloc[max(0, i-10):i+1]
                        max_vol = gc_bars["volume"].max()
                        avg_vol = gc_bars["volume"].mean()
                        vol_ratio = avg_vol / max_vol if max_vol > 0 else 1
                        if vol_ratio <= 0.7:
                            if volume_ratio >= 1.0 and price > ma5:
                                pullback = True

            convergence = False
            if i >= 10:
                recent = self.df.iloc[i-9:i+1]
                gap_pct = ((recent["ma5"] - recent["ma20"]).abs() / recent["ma20"] * 100).dropna()
                if len(gap_pct) >= 5 and gap_pct.mean() < 1.5 and gap_pct.iloc[-1] < 1.5:
                    if volume_ratio >= 1.5:
                        lookback_high = self.df.iloc[i-19:i]["high"].max() if i >= 19 else self.df.iloc[:i]["high"].max()
                        if price > lookback_high:
                            convergence = True

            # --- MACD+ detection ---
            macd_plus = False
            if i >= 26:
                prev_macd = float(prev["macd"]) if pd.notna(prev["macd"]) else None
                curr_macd = float(row["macd"]) if pd.notna(row["macd"]) else None
                if prev_macd is not None and curr_macd is not None and prev_macd < 0 and curr_macd >= 0:
                    macd_plus = True

            if raw_gc:
                last_gc_idx = i
            if macd_plus:
                last_macd_plus_idx = i

            # Combined golden_cross + macd_plus signal
            combined = False
            if last_gc_idx >= 0 and last_macd_plus_idx >= 0:
                if abs(last_gc_idx - last_macd_plus_idx) <= 5 and i == max(last_gc_idx, last_macd_plus_idx):
                    combined = True

            # --- Sell signals ---
            death_cross = (prev_ma5 >= prev_ma20 and ma5 < ma20)
            stop_ma5 = (i >= 2
                and float(self.df.iloc[i-2]["close"]) < float(self.df.iloc[i-2]["ma5"])
                and float(self.df.iloc[i-1]["close"]) < float(self.df.iloc[i-1]["ma5"])
                and price < ma5
                and price < cost)
            stop_ma20 = (price < ma20 and volume_ratio > 1.5)

            # --- Take profit: 常规10%-20%止盈 ---
            take_profit_normal = False
            if in_position and buy_triggered:
                buy_price = cost
                pnl_pct = (price - buy_price) / buy_price * 100
                if 10 <= pnl_pct <= 20:
                    take_profit_normal = True

            # --- Take profit: 最小止盈(跌破MA20, 3%-5%) ---
            take_profit_mini = False
            if in_position and buy_triggered and i >= 1:
                buy_price = cost
                pnl_pct = (price - buy_price) / buy_price * 100
                prev_close = float(self.df.iloc[i-1]["close"])
                prev_ma20 = float(self.df.iloc[i-1]["ma20"])
                if 3 <= pnl_pct <= 5 and prev_close > prev_ma20 and price <= ma20:
                    take_profit_mini = True

            if not in_position:
                buy_pct = 0.3
                buy_reason = ""
                if combined:
                    buy_pct = 0.5
                    buy_reason = "金叉+MACD+双信号共振(5日内，半仓买入)"
                elif golden_cross:
                    buy_pct = 0.3
                    buy_reason = "金叉买入(放量+趋势向上+站上均线)"
                elif pullback:
                    buy_pct = 0.3
                    buy_reason = "回踩买入(缩量回踩+带量站上5日线)"
                elif convergence:
                    buy_pct = 0.4
                    buy_reason = "粘合发散买入(4成仓快进快出)"

                if buy_reason:
                    buy_amount = capital * buy_pct
                    shares = int(buy_amount / (price * 100)) * 100
                    if shares > 0:
                        cost_amount = shares * price
                        fee = max(cost_amount * self.fee_rate, self.min_fee)
                        total_fees += fee
                        if cost_amount + fee <= capital:
                            position = shares
                            cost = price
                            capital -= (cost_amount + fee)
                            in_position = True
                            buy_triggered = True
                            buy_type = buy_reason
                            trades.append(BacktestTrade(
                                date=date_str, action="买入", price=round(price, 2),
                                shares=shares, amount=round(cost_amount, 2),
                                reason=buy_reason,
                            ))
            else:
                should_sell = False
                sell_reason = ""
                if take_profit_normal:
                    should_sell = True
                    sell_reason = "常规止盈(10%-20%落袋为安)"
                elif take_profit_mini:
                    should_sell = True
                    sell_reason = "最小止盈(跌破MA20，锁定3%-5%利润)"
                elif death_cross:
                    should_sell = True
                    sell_reason = "死叉卖出(强势趋势结束)"
                elif stop_ma5:
                    should_sell = True
                    sell_reason = "连续三日跌破5日线止损(价格低于买入价)"
                elif stop_ma20:
                    should_sell = True
                    sell_reason = "放量跌破20日线止损(无条件清仓)"

                if should_sell:
                    sell_amount = position * price
                    fee = max(sell_amount * self.fee_rate, self.min_fee)
                    total_fees += fee
                    pnl = sell_amount - fee - position * cost
                    if pnl > 0:
                        wins += 1
                    else:
                        losses += 1
                    capital += (sell_amount - fee)
                    trades.append(BacktestTrade(
                        date=date_str, action="卖出", price=round(price, 2),
                        shares=position, amount=round(sell_amount, 2),
                        reason=sell_reason,
                    ))
                    position = 0
                    in_position = False
                    buy_triggered = False

                elif buy_triggered and position > 0 and position * cost < capital * 0.5:
                    add_amount = capital * 0.2
                    add_shares = int(add_amount / (price * 100)) * 100
                    if add_shares > 0 and trend_up and price > cost:
                        add_cost = add_shares * price
                        fee = max(add_cost * self.fee_rate, self.min_fee)
                        total_fees += fee
                        if add_cost + fee <= capital:
                            total_shares_value = position * cost + add_shares * price
                            total_shares = position + add_shares
                            cost = total_shares_value / total_shares
                            position = total_shares
                            capital -= (add_cost + fee)
                            trades.append(BacktestTrade(
                                date=date_str, action="加仓", price=round(price, 2),
                                shares=add_shares, amount=round(add_cost, 2),
                                reason="趋势向上+盈利状态，加仓2成(最高5成)",
                            ))

            equity = capital + position * price
            peak = max(peak, equity)
            dd = (peak - equity) / peak * 100
            max_drawdown = max(max_drawdown, dd)
            equity_curve.append({"date": date_str, "equity": round(equity, 2), "position": position})

        if position > 0:
            last_price = float(self.df.iloc[-1]["close"])
            sell_amount = position * last_price
            fee = max(sell_amount * self.fee_rate, self.min_fee)
            total_fees += fee
            capital += (sell_amount - fee)
            trades.append(BacktestTrade(
                date=str(self.df.iloc[-1]["trade_date"].date()),
                action="平仓", price=round(last_price, 2),
                shares=position, amount=round(sell_amount, 2),
                reason="回测结束强制平仓",
            ))

        total_return = (capital - initial_capital) / initial_capital * 100
        days = (self.df.iloc[-1]["trade_date"] - self.df.iloc[20]["trade_date"]).days
        annual_return = ((1 + total_return / 100) ** (365 / max(days, 1)) - 1) * 100 if days > 0 else 0
        total_trades = len(trades)
        win_rate = wins / max(wins + losses, 1) * 100

        return BacktestResponse(
            symbol=self.request.symbol,
            start_date=self.request.start_date,
            end_date=self.request.end_date,
            initial_capital=initial_capital,
            final_capital=round(capital, 2),
            total_return=round(total_return, 2),
            annual_return=round(annual_return, 2),
            max_drawdown=round(max_drawdown, 2),
            win_rate=round(win_rate, 2),
            total_trades=total_trades,
            total_fees=round(total_fees, 2),
            trades=trades,
            equity_curve=equity_curve,
        )

    def save_result(self, response: BacktestResponse):
        db: Session = SessionLocal()
        try:
            result = BacktestResult(
                symbol=response.symbol,
                start_date=datetime.strptime(response.start_date, "%Y-%m-%d").date() if "-" in response.start_date else datetime.strptime(response.start_date, "%Y%m%d").date(),
                end_date=datetime.strptime(response.end_date, "%Y-%m-%d").date() if "-" in response.end_date else datetime.strptime(response.end_date, "%Y%m%d").date(),
                initial_capital=response.initial_capital,
                adjust=self.request.adjust,
                total_return=response.total_return,
                annual_return=response.annual_return,
                max_drawdown=response.max_drawdown,
                win_rate=response.win_rate,
                total_trades=response.total_trades,
                total_fees=response.total_fees,
                details=json.dumps([t.model_dump() for t in response.trades], ensure_ascii=False),
            )
            db.add(result)
            db.commit()
        except Exception:
            db.rollback()
        finally:
            db.close()
