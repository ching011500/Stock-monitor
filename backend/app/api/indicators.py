"""
技術指標相關 API 路由
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.database.database import get_db
from app.database.crud import (
    get_latest_indicator,
    get_indicators_by_symbol
)
from app.technical_indicators import IndicatorCalculator
from app.config import get_monitored_symbols
from pydantic import BaseModel
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/indicators", tags=["indicators"])


class TechnicalIndicatorResponse(BaseModel):
    id: int
    symbol: str
    timestamp: datetime
    ma5: float | None
    ma10: float | None
    ma20: float | None
    ma50: float | None
    ma200: float | None
    rsi: float | None
    macd: float | None
    macd_signal: float | None
    macd_hist: float | None
    bb_upper: float | None
    bb_middle: float | None
    bb_lower: float | None
    volume_avg: float | None
    
    class Config:
        from_attributes = True


@router.get("/{symbol}", response_model=TechnicalIndicatorResponse)
def get_stock_indicator(symbol: str, db: Session = Depends(get_db)):
    """獲取指定標的最新技術指標"""
    indicator = get_latest_indicator(db, symbol.upper())
    if not indicator:
        raise HTTPException(status_code=404, detail=f"Indicator for {symbol} not found")
    return indicator


@router.get("/{symbol}/history", response_model=List[TechnicalIndicatorResponse])
def get_indicator_history(symbol: str, days: int = 30, db: Session = Depends(get_db)):
    """獲取指定標的的歷史指標"""
    if days > 365:
        days = 365
    indicators = get_indicators_by_symbol(db, symbol.upper(), days=days)
    return indicators


@router.post("/{symbol}/calculate")
def calculate_indicator(symbol: str, db: Session = Depends(get_db)):
    """手動計算並保存指定標的的技術指標"""
    calculator = IndicatorCalculator()
    success = calculator.calculate_and_save_indicator(symbol.upper())
    
    if not success:
        raise HTTPException(
            status_code=400, 
            detail=f"Failed to calculate indicator for {symbol}. Check if there's enough historical data."
        )
    
    # 返回最新計算的指標
    indicator = get_latest_indicator(db, symbol.upper())
    return {
        "message": f"Indicator calculated successfully for {symbol}",
        "indicator": indicator
    }


@router.post("/refresh-all")
def calculate_all_indicators(db: Session = Depends(get_db)):
    """計算並保存所有監控標的的技術指標"""
    symbols = get_monitored_symbols()
    calculator = IndicatorCalculator()
    results = calculator.calculate_and_save_all_indicators(symbols)
    
    success_count = sum(1 for v in results.values() if v)
    failed = [symbol for symbol, success in results.items() if not success]
    
    return {
        "message": f"Calculated indicators for {success_count}/{len(symbols)} symbols",
        "results": results,
        "failed": failed
    }


