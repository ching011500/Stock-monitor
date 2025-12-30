"""
AI 分析服務
基於技術指標進行趨勢分析，生成交易訊號和風險評估
"""
from typing import Dict, Optional
from datetime import datetime
import logging

from app.database.database import get_db_sync
from app.database.crud import (
    get_latest_price,
    get_latest_indicator,
    create_ai_signal
)
from app.models.stock import StockPrice, TechnicalIndicator

logger = logging.getLogger(__name__)


class AIAnalyzer:
    """AI 分析器"""
    
    def __init__(self):
        pass
    
    def analyze_trend(self, price: StockPrice, indicator: TechnicalIndicator) -> Dict:
        """
        分析股票趨勢並生成交易訊號
        
        Args:
            price: 最新價格數據
            indicator: 最新技術指標
        
        Returns:
            包含 signal, confidence, risk_level, reasoning 的字典
        """
        if not price or not indicator:
            logger.warning("缺少價格或指標數據，無法進行分析")
            return None
        
        # 收集所有指標數據
        current_price = price.close
        ma5 = indicator.ma5
        ma10 = indicator.ma10
        ma20 = indicator.ma20
        ma50 = indicator.ma50
        ma200 = indicator.ma200
        rsi = indicator.rsi
        macd = indicator.macd
        macd_signal = indicator.macd_signal
        macd_hist = indicator.macd_hist
        bb_upper = indicator.bb_upper
        bb_middle = indicator.bb_middle
        bb_lower = indicator.bb_lower
        
        # 初始化評分系統（-100 到 +100，正數表示看漲，負數表示看跌）
        buy_score = 0
        sell_score = 0
        reasons = []
        
        # 1. 移動平均線分析
        if ma5 and ma10 and ma20:
            # 多頭排列（短期均線 > 中期均線 > 長期均線）
            if ma5 > ma10 > ma20:
                buy_score += 15
                reasons.append("多頭排列：MA5 > MA10 > MA20")
            # 空頭排列
            elif ma5 < ma10 < ma20:
                sell_score += 15
                reasons.append("空頭排列：MA5 < MA10 < MA20")
        
        # 價格與均線關係
        if ma20:
            if current_price > ma20:
                buy_score += 5
                reasons.append(f"價格高於 MA20 ({current_price:.2f} > {ma20:.2f})")
            else:
                sell_score += 5
                reasons.append(f"價格低於 MA20 ({current_price:.2f} < {ma20:.2f})")
        
        if ma50:
            if current_price > ma50:
                buy_score += 10
                reasons.append(f"價格高於 MA50 ({current_price:.2f} > {ma50:.2f})")
            else:
                sell_score += 10
                reasons.append(f"價格低於 MA50 ({current_price:.2f} < {ma50:.2f})")
        
        if ma200:
            if current_price > ma200:
                buy_score += 15
                reasons.append(f"價格高於 MA200 ({current_price:.2f} > {ma200:.2f})")
            else:
                sell_score += 15
                reasons.append(f"價格低於 MA200 ({current_price:.2f} < {ma200:.2f})")
        
        # 2. RSI 分析
        if rsi:
            if rsi < 30:
                buy_score += 20  # 超賣，可能反彈
                reasons.append(f"RSI 超賣 ({rsi:.2f} < 30)")
            elif rsi > 70:
                sell_score += 20  # 超買，可能回調
                reasons.append(f"RSI 超買 ({rsi:.2f} > 70)")
            elif 30 <= rsi <= 50:
                buy_score += 5
                reasons.append(f"RSI 偏低 ({rsi:.2f})")
            elif 50 < rsi <= 70:
                sell_score += 5
                reasons.append(f"RSI 偏高 ({rsi:.2f})")
        
        # 3. MACD 分析
        if macd is not None and macd_signal is not None:
            # MACD 金叉（MACD 線向上穿越信號線）
            if macd > macd_signal:
                buy_score += 15
                reasons.append(f"MACD 多頭 (MACD={macd:.4f} > Signal={macd_signal:.4f})")
            else:
                sell_score += 15
                reasons.append(f"MACD 空頭 (MACD={macd:.4f} < Signal={macd_signal:.4f})")
        
        if macd_hist is not None:
            if macd_hist > 0:
                buy_score += 5
                reasons.append(f"MACD 柱狀圖為正 ({macd_hist:.4f})")
            else:
                sell_score += 5
                reasons.append(f"MACD 柱狀圖為負 ({macd_hist:.4f})")
        
        # 4. 布林帶分析
        if bb_upper and bb_middle and bb_lower:
            # 價格接近下軌（可能反彈）
            if current_price <= bb_lower * 1.02:  # 允許2%的誤差
                buy_score += 15
                reasons.append(f"價格接近布林帶下軌 ({current_price:.2f} ≈ {bb_lower:.2f})")
            # 價格接近上軌（可能回調）
            elif current_price >= bb_upper * 0.98:
                sell_score += 15
                reasons.append(f"價格接近布林帶上軌 ({current_price:.2f} ≈ {bb_upper:.2f})")
            # 價格在中軌附近
            elif bb_middle * 0.98 <= current_price <= bb_middle * 1.02:
                buy_score += 3
                reasons.append(f"價格在布林帶中軌附近 ({current_price:.2f} ≈ {bb_middle:.2f})")
        
        # 計算總分和訊號
        total_score = buy_score - sell_score
        
        # 生成訊號
        if total_score >= 30:
            signal = "BUY"
            confidence = min(0.95, 0.5 + abs(total_score) / 200)  # 轉換為 0-1 的置信度
        elif total_score <= -30:
            signal = "SELL"
            confidence = min(0.95, 0.5 + abs(total_score) / 200)
        else:
            signal = "HOLD"
            confidence = 0.5  # 持有訊號的置信度較低
        
        # 評估風險等級
        risk_level = self._assess_risk(price, indicator, total_score)
        
        # 生成分析理由（限制在 500 字元內）
        reasoning = "; ".join(reasons[:10])  # 最多取前10個理由
        if len(reasoning) > 500:
            reasoning = reasoning[:497] + "..."
        
        return {
            "signal": signal,
            "confidence": round(confidence, 2),
            "risk_level": risk_level,
            "reasoning": reasoning,
            "score": total_score  # 用於調試
        }
    
    def _assess_risk(self, price: StockPrice, indicator: TechnicalIndicator, score: int) -> str:
        """
        評估風險等級
        
        Args:
            price: 價格數據
            indicator: 指標數據
            score: 分析分數
        
        Returns:
            風險等級: 'LOW', 'MEDIUM', 'HIGH'
        """
        risk_factors = 0
        
        # RSI 極端值增加風險
        if indicator.rsi:
            if indicator.rsi < 20 or indicator.rsi > 80:
                risk_factors += 2
            elif indicator.rsi < 30 or indicator.rsi > 70:
                risk_factors += 1
        
        # 價格與長期均線偏離過大增加風險
        if indicator.ma200:
            deviation = abs(price.close - indicator.ma200) / indicator.ma200
            if deviation > 0.2:  # 偏離超過 20%
                risk_factors += 2
            elif deviation > 0.1:  # 偏離超過 10%
                risk_factors += 1
        
        # 布林帶極端值增加風險
        if indicator.bb_upper and indicator.bb_lower and indicator.bb_middle:
            band_width = (indicator.bb_upper - indicator.bb_lower) / indicator.bb_middle
            if band_width > 0.15:  # 帶寬過大，波動性高
                risk_factors += 1
        
        # 訊號強度（分數絕對值）也影響風險
        if abs(score) > 50:
            risk_factors += 1
        
        # 根據風險因子判斷風險等級
        if risk_factors >= 3:
            return "HIGH"
        elif risk_factors >= 1:
            return "MEDIUM"
        else:
            return "LOW"
    
    def analyze_and_save(self, symbol: str) -> bool:
        """
        分析指定標的並保存結果到資料庫
        
        Args:
            symbol: 股票代號
        
        Returns:
            是否成功
        """
        try:
            db = get_db_sync()
            
            # 獲取最新數據
            price = get_latest_price(db, symbol)
            indicator = get_latest_indicator(db, symbol)
            
            if not price:
                logger.warning(f"{symbol}: 沒有找到價格數據")
                db.close()
                return False
            
            if not indicator:
                logger.warning(f"{symbol}: 沒有找到指標數據，跳過 AI 分析")
                db.close()
                return False
            
            # 進行分析
            analysis_result = self.analyze_trend(price, indicator)
            
            if not analysis_result:
                logger.warning(f"{symbol}: 分析失敗")
                db.close()
                return False
            
            # 使用價格的時間戳
            timestamp = price.timestamp
            
            # 保存到資料庫
            create_ai_signal(
                db=db,
                symbol=symbol,
                signal=analysis_result["signal"],
                confidence=analysis_result["confidence"],
                risk_level=analysis_result["risk_level"],
                reasoning=analysis_result["reasoning"],
                timestamp=timestamp
            )
            
            db.close()
            
            logger.info(f"✓ {symbol} AI 分析完成: {analysis_result['signal']} "
                       f"(置信度: {analysis_result['confidence']:.2f}, "
                       f"風險: {analysis_result['risk_level']})")
            return True
            
        except Exception as e:
            logger.error(f"分析 {symbol} 時發生錯誤: {str(e)}", exc_info=True)
            return False
    
    def analyze_all(self, symbols: list) -> Dict[str, bool]:
        """
        分析所有指定標的
        
        Args:
            symbols: 股票代號列表
        
        Returns:
            每個標的的成功狀態字典
        """
        results = {}
        for symbol in symbols:
            logger.info(f"正在分析 {symbol}...")
            success = self.analyze_and_save(symbol)
            results[symbol] = success
        return results

