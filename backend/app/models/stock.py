"""
股票數據模型
"""
from datetime import datetime
from sqlalchemy import Column, String, Float, Integer, DateTime, Index
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class StockPrice(Base):
    """股票價格數據表"""
    __tablename__ = "stock_prices"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(10), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Integer, nullable=False)
    adj_close = Column(Float, nullable=False)
    
    # 創建複合索引以提高查詢效率
    __table_args__ = (
        Index('idx_symbol_timestamp', 'symbol', 'timestamp'),
    )
    
    def __repr__(self):
        return f"<StockPrice(symbol={self.symbol}, timestamp={self.timestamp}, close={self.close})>"


class TechnicalIndicator(Base):
    """技術指標數據表"""
    __tablename__ = "technical_indicators"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(10), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    # 移動平均線
    ma5 = Column(Float, nullable=True)
    ma10 = Column(Float, nullable=True)
    ma20 = Column(Float, nullable=True)
    ma50 = Column(Float, nullable=True)
    ma200 = Column(Float, nullable=True)
    
    # RSI
    rsi = Column(Float, nullable=True)
    
    # MACD
    macd = Column(Float, nullable=True)
    macd_signal = Column(Float, nullable=True)
    macd_hist = Column(Float, nullable=True)
    
    # 布林帶
    bb_upper = Column(Float, nullable=True)
    bb_middle = Column(Float, nullable=True)
    bb_lower = Column(Float, nullable=True)
    
    # 成交量
    volume_avg = Column(Float, nullable=True)
    
    # 創建複合索引
    __table_args__ = (
        Index('idx_indicator_symbol_timestamp', 'symbol', 'timestamp'),
    )
    
    def __repr__(self):
        return f"<TechnicalIndicator(symbol={self.symbol}, timestamp={self.timestamp}, rsi={self.rsi})>"


class AISignal(Base):
    """AI 訊號數據表"""
    __tablename__ = "ai_signals"
    
    id = Column(Integer, primary_key=True, index=True)
    symbol = Column(String(10), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)
    signal = Column(String(10), nullable=False)  # 'BUY', 'SELL', 'HOLD'
    confidence = Column(Float, nullable=False)  # 0-1
    risk_level = Column(String(10), nullable=False)  # 'LOW', 'MEDIUM', 'HIGH'
    reasoning = Column(String(500), nullable=True)
    
    # 創建複合索引
    __table_args__ = (
        Index('idx_signal_symbol_timestamp', 'symbol', 'timestamp'),
    )
    
    def __repr__(self):
        return f"<AISignal(symbol={self.symbol}, signal={self.signal}, confidence={self.confidence})>"


