"""
股票相關 API 路由
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timedelta

from app.database.database import get_db
from app.database.crud import (
    get_latest_price,
    get_prices_by_symbol,
    get_all_latest_prices,
    clear_all_data
)
from app.data_collection import DataCollector
from pydantic import BaseModel

router = APIRouter(prefix="/stocks", tags=["stocks"])


# Pydantic 模型
class StockPriceResponse(BaseModel):
    id: int
    symbol: str
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int
    adj_close: float
    
    class Config:
        from_attributes = True


class StockPriceListResponse(BaseModel):
    symbol: str
    prices: List[StockPriceResponse]


@router.get("/", response_model=List[StockPriceResponse])
def get_all_stocks(db: Session = Depends(get_db)):
    """獲取所有標的的最新價格"""
    prices = get_all_latest_prices(db)
    return prices


@router.get("/{symbol}", response_model=StockPriceResponse)
def get_stock_latest(symbol: str, db: Session = Depends(get_db)):
    """獲取指定標的最新價格"""
    price = get_latest_price(db, symbol.upper())
    if not price:
        raise HTTPException(status_code=404, detail=f"Stock {symbol} not found")
    return price


@router.get("/{symbol}/history", response_model=List[StockPriceResponse])
def get_stock_history(symbol: str, days: int = 30, db: Session = Depends(get_db)):
    """獲取指定標的的歷史價格"""
    if days > 365:
        days = 365  # 限制最多 365 天
    prices = get_prices_by_symbol(db, symbol.upper(), days=days)
    return prices


@router.post("/{symbol}/refresh")
def refresh_stock_data(symbol: str):
    """手動刷新指定標的的數據"""
    collector = DataCollector()
    data = collector.fetch_stock_data(symbol.upper())
    
    if not data:
        raise HTTPException(status_code=404, detail=f"Failed to fetch data for {symbol}")
    
    success = collector.save_stock_data(data)
    if not success:
        raise HTTPException(status_code=500, detail=f"Failed to save data for {symbol}")
    
    return {"message": f"Successfully refreshed data for {symbol}", "data": data}


@router.post("/refresh-all")
def refresh_all_stocks():
    """手動刷新所有標的的數據"""
    from app.config import settings
    import logging
    logger = logging.getLogger(__name__)
    
    collector = DataCollector()
    
    # 檢查是否有監控標的
    if not collector.symbols:
        return {
            "message": f"No monitored symbols configured. Current setting: '{settings.MONITORED_SYMBOLS}'",
            "results": {},
            "symbols_count": 0
        }
    
    logger.info(f"開始刷新 {len(collector.symbols)} 個標的: {collector.symbols}")
    results = collector.collect_and_save_all()
    
    success_count = sum(1 for v in results.values() if v)
    total_count = len(results)
    
    return {
        "message": f"Refreshed {success_count}/{total_count} stocks",
        "results": results,
        "symbols_attempted": collector.symbols,
        "symbols_count": len(collector.symbols)
    }


@router.post("/clear-all")
def clear_all_stock_data(db: Session = Depends(get_db)):
    """清空所有股票數據和指標數據"""
    import logging
    logger = logging.getLogger(__name__)
    
    logger.warning("清空所有股票數據和指標數據...")
    result = clear_all_data(db)
    
    return {
        "message": "All stock data cleared",
        "deleted": result
    }


@router.post("/import-history")
def import_historical_data(year: int = None, days: int = None):
    """
    導入歷史數據（用於初始化數據庫）
    
    Args:
        year: 指定年份（例如 2025），如果指定則導入該年的數據
        days: 如果指定年份，則忽略此參數；否則導入過去多少天的數據
    """
    import logging
    from datetime import datetime
    logger = logging.getLogger(__name__)
    
    collector = DataCollector()
    
    if not collector.symbols:
        return {
            "message": "No monitored symbols configured",
            "results": {},
            "symbols_count": 0
        }
    
    # 如果指定了年份，計算該年的日期範圍
    start_date = None
    end_date = None
    if year:
        start_date = datetime(year, 1, 1)
        # 如果今天還在該年內，使用今天；否則使用該年最後一天
        today = datetime.now()
        if today.year == year:
            end_date = today
        else:
            end_date = datetime(year, 12, 31)
        logger.info(f"開始為 {len(collector.symbols)} 個標的導入 {year} 年的歷史數據（{start_date.date()} 到 {end_date.date()}）...")
    else:
        if days is None:
            days = 365
        logger.info(f"開始為 {len(collector.symbols)} 個標的導入歷史數據（{days} 天）...")
    
    results = collector.import_historical_data_for_all(days, start_date, end_date)
    
    total_count = sum(results.values())
    
    return {
        "message": f"Imported historical data for {len(collector.symbols)} symbols",
        "year": year,
        "days": days,
        "start_date": start_date.date().isoformat() if start_date else None,
        "end_date": end_date.date().isoformat() if end_date else None,
        "results": results,
        "total_records": total_count,
        "symbols_attempted": collector.symbols
    }


