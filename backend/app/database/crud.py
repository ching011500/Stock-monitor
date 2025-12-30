"""
數據庫 CRUD 操作
"""
from datetime import datetime, timedelta
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.stock import StockPrice, TechnicalIndicator, AISignal


# ========== StockPrice CRUD ==========

def create_stock_price(db: Session, symbol: str, open: float, high: float, 
                      low: float, close: float, volume: int, adj_close: float,
                      timestamp: Optional[datetime] = None) -> StockPrice:
    """
    創建股票價格記錄（如果已存在相同 symbol 和 timestamp 的記錄則更新）
    """
    timestamp = timestamp or datetime.utcnow()
    
    # 檢查是否已存在相同 symbol 和 timestamp 的記錄
    existing = db.query(StockPrice).filter(
        StockPrice.symbol == symbol,
        StockPrice.timestamp == timestamp
    ).first()
    
    if existing:
        # 更新現有記錄
        existing.open = open
        existing.high = high
        existing.low = low
        existing.close = close
        existing.volume = volume
        existing.adj_close = adj_close
        db.commit()
        db.refresh(existing)
        return existing
    else:
        # 創建新記錄
        stock_price = StockPrice(
            symbol=symbol,
            timestamp=timestamp,
            open=open,
            high=high,
            low=low,
            close=close,
            volume=volume,
            adj_close=adj_close
        )
        db.add(stock_price)
        db.commit()
        db.refresh(stock_price)
        return stock_price


def get_latest_price(db: Session, symbol: str) -> Optional[StockPrice]:
    """獲取最新價格"""
    return db.query(StockPrice).filter(
        StockPrice.symbol == symbol
    ).order_by(desc(StockPrice.timestamp)).first()


def get_prices_by_symbol(db: Session, symbol: str, days: int = 30) -> List[StockPrice]:
    """獲取指定標的的歷史價格"""
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    return db.query(StockPrice).filter(
        StockPrice.symbol == symbol,
        StockPrice.timestamp >= cutoff_date
    ).order_by(StockPrice.timestamp).all()


def get_all_latest_prices(db: Session) -> List[StockPrice]:
    """獲取所有標的的最新價格"""
    # 如果數據庫為空，返回空列表
    count = db.query(StockPrice).count()
    if count == 0:
        return []
    
    # 使用子查詢獲取每個標的最新記錄
    from sqlalchemy import and_
    subquery = db.query(
        StockPrice.symbol,
        db.func.max(StockPrice.timestamp).label('max_timestamp')
    ).group_by(StockPrice.symbol).subquery()
    
    return db.query(StockPrice).join(
        subquery,
        and_(
            StockPrice.symbol == subquery.c.symbol,
            StockPrice.timestamp == subquery.c.max_timestamp
        )
    ).all()


# ========== TechnicalIndicator CRUD ==========

def create_technical_indicator(db: Session, symbol: str, **kwargs) -> TechnicalIndicator:
    """
    創建技術指標記錄（如果已存在相同 symbol 和 timestamp 的記錄則更新）
    """
    timestamp = kwargs.get('timestamp', datetime.utcnow())
    
    # 檢查是否已存在相同 symbol 和 timestamp 的記錄
    existing = db.query(TechnicalIndicator).filter(
        TechnicalIndicator.symbol == symbol,
        TechnicalIndicator.timestamp == timestamp
    ).first()
    
    if existing:
        # 更新現有記錄
        existing.ma5 = kwargs.get('ma5')
        existing.ma10 = kwargs.get('ma10')
        existing.ma20 = kwargs.get('ma20')
        existing.ma50 = kwargs.get('ma50')
        existing.ma200 = kwargs.get('ma200')
        existing.rsi = kwargs.get('rsi')
        existing.macd = kwargs.get('macd')
        existing.macd_signal = kwargs.get('macd_signal')
        existing.macd_hist = kwargs.get('macd_hist')
        existing.bb_upper = kwargs.get('bb_upper')
        existing.bb_middle = kwargs.get('bb_middle')
        existing.bb_lower = kwargs.get('bb_lower')
        existing.volume_avg = kwargs.get('volume_avg')
        db.commit()
        db.refresh(existing)
        return existing
    else:
        # 創建新記錄
        indicator = TechnicalIndicator(
            symbol=symbol,
            timestamp=timestamp,
            ma5=kwargs.get('ma5'),
            ma10=kwargs.get('ma10'),
            ma20=kwargs.get('ma20'),
            ma50=kwargs.get('ma50'),
            ma200=kwargs.get('ma200'),
            rsi=kwargs.get('rsi'),
            macd=kwargs.get('macd'),
            macd_signal=kwargs.get('macd_signal'),
            macd_hist=kwargs.get('macd_hist'),
            bb_upper=kwargs.get('bb_upper'),
            bb_middle=kwargs.get('bb_middle'),
            bb_lower=kwargs.get('bb_lower'),
            volume_avg=kwargs.get('volume_avg')
        )
        db.add(indicator)
        db.commit()
        db.refresh(indicator)
        return indicator


def get_latest_indicator(db: Session, symbol: str) -> Optional[TechnicalIndicator]:
    """獲取最新技術指標"""
    return db.query(TechnicalIndicator).filter(
        TechnicalIndicator.symbol == symbol
    ).order_by(desc(TechnicalIndicator.timestamp)).first()


def get_indicators_by_symbol(db: Session, symbol: str, days: int = 30) -> List[TechnicalIndicator]:
    """獲取指定標的的歷史指標"""
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    return db.query(TechnicalIndicator).filter(
        TechnicalIndicator.symbol == symbol,
        TechnicalIndicator.timestamp >= cutoff_date
    ).order_by(TechnicalIndicator.timestamp).all()


# ========== Database Management ==========

def remove_duplicate_stock_prices(db: Session) -> int:
    """
    刪除重複的股票價格記錄（保留每個 symbol + timestamp 組合的第一筆記錄）
    
    Returns:
        刪除的重複記錄數量
    """
    from sqlalchemy import func
    
    # 查找所有重複的記錄（symbol + timestamp 組合出現多次）
    duplicates = db.query(
        StockPrice.symbol,
        StockPrice.timestamp,
        func.min(StockPrice.id).label('min_id'),
        func.count(StockPrice.id).label('count')
    ).group_by(
        StockPrice.symbol,
        StockPrice.timestamp
    ).having(func.count(StockPrice.id) > 1).all()
    
    deleted_count = 0
    for dup in duplicates:
        # 保留 ID 最小的記錄，刪除其他重複記錄
        db.query(StockPrice).filter(
            StockPrice.symbol == dup.symbol,
            StockPrice.timestamp == dup.timestamp,
            StockPrice.id != dup.min_id
        ).delete()
        deleted_count += dup.count - 1  # 減去保留的那一筆
    
    db.commit()
    return deleted_count


def remove_duplicate_indicators(db: Session) -> int:
    """
    刪除重複的技術指標記錄（保留每個 symbol + timestamp 組合的第一筆記錄）
    
    Returns:
        刪除的重複記錄數量
    """
    from sqlalchemy import func
    
    # 查找所有重複的記錄（symbol + timestamp 組合出現多次）
    duplicates = db.query(
        TechnicalIndicator.symbol,
        TechnicalIndicator.timestamp,
        func.min(TechnicalIndicator.id).label('min_id'),
        func.count(TechnicalIndicator.id).label('count')
    ).group_by(
        TechnicalIndicator.symbol,
        TechnicalIndicator.timestamp
    ).having(func.count(TechnicalIndicator.id) > 1).all()
    
    deleted_count = 0
    for dup in duplicates:
        # 保留 ID 最小的記錄，刪除其他重複記錄
        db.query(TechnicalIndicator).filter(
            TechnicalIndicator.symbol == dup.symbol,
            TechnicalIndicator.timestamp == dup.timestamp,
            TechnicalIndicator.id != dup.min_id
        ).delete()
        deleted_count += dup.count - 1  # 減去保留的那一筆
    
    db.commit()
    return deleted_count


def remove_duplicate_ai_signals(db: Session) -> int:
    """
    刪除重複的 AI 訊號記錄（保留每個 symbol + timestamp 組合的第一筆記錄）
    
    Returns:
        刪除的重複記錄數量
    """
    from sqlalchemy import func
    
    # 查找所有重複的記錄（symbol + timestamp 組合出現多次）
    duplicates = db.query(
        AISignal.symbol,
        AISignal.timestamp,
        func.min(AISignal.id).label('min_id'),
        func.count(AISignal.id).label('count')
    ).group_by(
        AISignal.symbol,
        AISignal.timestamp
    ).having(func.count(AISignal.id) > 1).all()
    
    deleted_count = 0
    for dup in duplicates:
        # 保留 ID 最小的記錄，刪除其他重複記錄
        db.query(AISignal).filter(
            AISignal.symbol == dup.symbol,
            AISignal.timestamp == dup.timestamp,
            AISignal.id != dup.min_id
        ).delete()
        deleted_count += dup.count - 1  # 減去保留的那一筆
    
    db.commit()
    return deleted_count


def clear_all_stock_prices(db: Session) -> int:
    """清空所有股票價格數據"""
    count = db.query(StockPrice).count()
    db.query(StockPrice).delete()
    db.commit()
    return count


def clear_all_indicators(db: Session) -> int:
    """清空所有技術指標數據"""
    count = db.query(TechnicalIndicator).count()
    db.query(TechnicalIndicator).delete()
    db.commit()
    return count


def clear_all_data(db: Session) -> dict:
    """清空所有數據（價格和指標）"""
    price_count = clear_all_stock_prices(db)
    indicator_count = clear_all_indicators(db)
    # AISignal 也可以清空，但暫時保留
    return {
        "stock_prices_deleted": price_count,
        "indicators_deleted": indicator_count
    }


# ========== AISignal CRUD ==========

def create_ai_signal(db: Session, symbol: str, signal: str, confidence: float,
                     risk_level: str, reasoning: Optional[str] = None,
                     timestamp: Optional[datetime] = None) -> AISignal:
    """
    創建 AI 訊號記錄（如果已存在相同 symbol 和 timestamp 的記錄則更新）
    """
    timestamp = timestamp or datetime.utcnow()
    
    # 檢查是否已存在相同 symbol 和 timestamp 的記錄
    existing = db.query(AISignal).filter(
        AISignal.symbol == symbol,
        AISignal.timestamp == timestamp
    ).first()
    
    if existing:
        # 更新現有記錄
        existing.signal = signal
        existing.confidence = confidence
        existing.risk_level = risk_level
        existing.reasoning = reasoning
        db.commit()
        db.refresh(existing)
        return existing
    else:
        # 創建新記錄
        ai_signal = AISignal(
            symbol=symbol,
            timestamp=timestamp,
            signal=signal,
            confidence=confidence,
            risk_level=risk_level,
            reasoning=reasoning
        )
        db.add(ai_signal)
        db.commit()
        db.refresh(ai_signal)
        return ai_signal


def get_latest_signal(db: Session, symbol: str) -> Optional[AISignal]:
    """獲取最新 AI 訊號"""
    return db.query(AISignal).filter(
        AISignal.symbol == symbol
    ).order_by(desc(AISignal.timestamp)).first()


def get_signals_by_symbol(db: Session, symbol: str, days: int = 30) -> List[AISignal]:
    """獲取指定標的的歷史訊號"""
    cutoff_date = datetime.utcnow() - timedelta(days=days)
    return db.query(AISignal).filter(
        AISignal.symbol == symbol,
        AISignal.timestamp >= cutoff_date
    ).order_by(AISignal.timestamp).all()


