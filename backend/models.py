from sqlalchemy import Column, String, Float, Integer, Date, Text, DateTime, func
from database import Base


class DailyQuote(Base):
    __tablename__ = "daily_quotes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(16), nullable=False, index=True)
    trade_date = Column(Date, nullable=False)
    open = Column(Float)
    high = Column(Float)
    low = Column(Float)
    close = Column(Float)
    volume = Column(Float)
    amount = Column(Float)
    source = Column(String(32), default="akshare")
    adjusted = Column(String(16), default="none")
    created_at = Column(DateTime, server_default=func.now())

    __table_args__ = {"sqlite_autoincrement": True}


class Watchlist(Base):
    __tablename__ = "watchlist"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(16), nullable=False, unique=True, index=True)
    name = Column(String(64), default="")
    added_at = Column(DateTime, server_default=func.now())


class BacktestResult(Base):
    __tablename__ = "backtest_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(16), nullable=False)
    start_date = Column(Date)
    end_date = Column(Date)
    initial_capital = Column(Float, default=100000)
    adjust = Column(String(16), default="forward")
    total_return = Column(Float)
    annual_return = Column(Float)
    max_drawdown = Column(Float)
    win_rate = Column(Float)
    total_trades = Column(Integer)
    total_fees = Column(Float)
    details = Column(Text)
    created_at = Column(DateTime, server_default=func.now())


class StockInfo(Base):
    __tablename__ = "stock_info"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(String(16), nullable=False, unique=True, index=True)
    name = Column(String(64), default="")
    exchange = Column(String(16), default="")
    updated_at = Column(DateTime, server_default=func.now())
