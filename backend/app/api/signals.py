"""
AI 訊號相關 API 路由
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from pydantic import BaseModel
from datetime import datetime

from app.database.database import get_db
from app.database.crud import (
    get_latest_signal,
    get_signals_by_symbol
)
from app.ai_analysis import AIAnalyzer
from app.config import get_monitored_symbols
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/signals", tags=["signals"])


class AISignalResponse(BaseModel):
    id: int
    symbol: str
    timestamp: datetime
    signal: str
    confidence: float
    risk_level: str
    reasoning: str | None
    
    class Config:
        from_attributes = True


@router.get("/{symbol}", response_model=AISignalResponse)
def get_stock_signal(symbol: str, db: Session = Depends(get_db)):
    """獲取指定標的最新 AI 訊號"""
    signal = get_latest_signal(db, symbol.upper())
    if not signal:
        raise HTTPException(status_code=404, detail=f"Signal for {symbol} not found")
    return signal


@router.get("/{symbol}/history", response_model=List[AISignalResponse])
def get_signal_history(symbol: str, days: int = 30, db: Session = Depends(get_db)):
    """獲取指定標的的歷史訊號"""
    if days > 365:
        days = 365
    signals = get_signals_by_symbol(db, symbol.upper(), days=days)
    return signals


@router.post("/{symbol}/analyze")
def analyze_stock(symbol: str, db: Session = Depends(get_db)):
    """手動分析指定標的並生成 AI 訊號"""
    analyzer = AIAnalyzer()
    success = analyzer.analyze_and_save(symbol.upper())
    
    if not success:
        raise HTTPException(
            status_code=400,
            detail=f"Failed to analyze {symbol}. Check if there's enough price and indicator data."
        )
    
    # 返回最新生成的訊號
    signal = get_latest_signal(db, symbol.upper())
    return {
        "message": f"Analysis completed for {symbol}",
        "signal": signal
    }


@router.post("/analyze-all")
def analyze_all_stocks(db: Session = Depends(get_db)):
    """分析所有監控標的並生成 AI 訊號"""
    symbols = get_monitored_symbols()
    analyzer = AIAnalyzer()
    results = analyzer.analyze_all(symbols)
    
    success_count = sum(1 for v in results.values() if v)
    failed = [symbol for symbol, success in results.items() if not success]
    
    return {
        "message": f"Analyzed {success_count}/{len(symbols)} symbols",
        "results": results,
        "failed": failed
    }


