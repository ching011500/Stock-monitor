"""
警報規則引擎
檢測價格變動、指標突破等觸發條件，並發送通知
"""
from typing import Optional, Dict, List
from datetime import datetime, timedelta
import logging

from app.database.database import get_db_sync
from app.database.crud import (
    get_latest_price,
    get_latest_indicator,
    get_latest_signal,
    get_prices_by_symbol
)
from app.notifications.discord_notifier import DiscordNotifier
from app.notifications.notion_recorder import NotionRecorder

logger = logging.getLogger(__name__)


class AlertEngine:
    """警報規則引擎"""
    
    def __init__(self):
        self.discord = DiscordNotifier()
        self.notion = NotionRecorder()
        
        # 警報閾值配置
        self.price_change_threshold = 2.0  # 價格變動閾值（百分比）
        self.volume_spike_threshold = 2.0  # 成交量異常倍數
    
    def check_price_alerts(self, symbol: str, skip_notification: bool = False):
        """
        檢查價格警報
        
        Args:
            symbol: 股票代號
            skip_notification: 是否跳過發送通知（只用於檢查條件）
        
        Returns:
            (alerts: List[str], sent_integrated_notification: bool) - 觸發的警報列表和是否已發送整合通知的標記
        """
        alerts = []
        sent_integrated_notification = False
        db = get_db_sync()
        
        try:
            # 獲取最新價格
            current_price = get_latest_price(db, symbol)
            if not current_price:
                return alerts, sent_integrated_notification
            
            # 獲取前一個價格（同一天或前一天）
            prices = get_prices_by_symbol(db, symbol, days=5)
            if len(prices) < 2:
                return alerts, sent_integrated_notification
            
            # 找到當前價格之前的最新價格
            previous_price = None
            for price in reversed(prices[:-1]):  # 排除最後一個（當前價格）
                if price.timestamp.date() < current_price.timestamp.date():
                    previous_price = price
                    break
            
            if not previous_price:
                previous_price = prices[-2] if len(prices) >= 2 else None
            
            if previous_price:
                change_percent = ((current_price.close - previous_price.close) / previous_price.close) * 100
                
                # 檢查是否超過閾值
                if abs(change_percent) >= self.price_change_threshold:
                    alerts.append(f"價格變動 {change_percent:+.2f}%")
                    
                    if not skip_notification:
                        # 檢查是否有 AI 訊號，如果有則使用整合格式（統一格式）
                        signal = get_latest_signal(db, symbol)
                        if signal:
                            # 如果有 AI 訊號（包括 HOLD），使用整合格式（包含價格和 AI 分析）
                            self.discord.send_ai_signal(
                                symbol=symbol,
                                signal=signal.signal,
                                confidence=signal.confidence,
                                risk_level=signal.risk_level,
                                reasoning=signal.reasoning or "",
                                current_price=current_price.close,
                                change_percent=change_percent,
                                previous_price=previous_price.close
                            )
                            sent_integrated_notification = True
                        else:
                            # 沒有 AI 訊號，只發送價格警報
                            self.discord.send_price_alert(
                                symbol=symbol,
                                current_price=current_price.close,
                                change_percent=change_percent,
                                previous_price=previous_price.close
                            )
            
            # 檢查成交量異常
            if current_price.volume > 0:
                # 計算平均成交量（最近20天）
                recent_prices = get_prices_by_symbol(db, symbol, days=20)
                if len(recent_prices) > 5:
                    avg_volume = sum(p.volume for p in recent_prices) / len(recent_prices)
                    if current_price.volume >= avg_volume * self.volume_spike_threshold:
                        alerts.append(f"成交量異常放大 ({current_price.volume / avg_volume:.1f}x 平均量)")
            
        except Exception as e:
            logger.error(f"檢查價格警報失敗 ({symbol}): {str(e)}", exc_info=True)
        finally:
            db.close()
        
        return alerts, sent_integrated_notification
    
    def check_indicator_alerts(self, symbol: str) -> List[str]:
        """
        檢查指標警報
        
        Args:
            symbol: 股票代號
        
        Returns:
            觸發的警報列表
        """
        alerts = []
        db = get_db_sync()
        
        try:
            indicator = get_latest_indicator(db, symbol)
            if not indicator:
                return alerts
            
            # RSI 警報
            if indicator.rsi is not None:
                if indicator.rsi < 30:
                    alerts.append(f"RSI 超賣 ({indicator.rsi:.2f} < 30)")
                    self.discord.send_indicator_alert(
                        symbol=symbol,
                        indicator_type="RSI",
                        value=indicator.rsi,
                        message=f"RSI 超賣，可能反彈機會 ({indicator.rsi:.2f})"
                    )
                elif indicator.rsi > 70:
                    alerts.append(f"RSI 超買 ({indicator.rsi:.2f} > 70)")
                    self.discord.send_indicator_alert(
                        symbol=symbol,
                        indicator_type="RSI",
                        value=indicator.rsi,
                        message=f"RSI 超買，可能回調風險 ({indicator.rsi:.2f})"
                    )
            
            # MACD 交叉檢測（需要歷史數據，這裡簡化處理）
            # TODO: 實現 MACD 交叉檢測
            
            # 布林帶突破檢測
            price = get_latest_price(db, symbol)
            if price and indicator.bb_upper and indicator.bb_lower:
                if price.close >= indicator.bb_upper:
                    alerts.append(f"價格突破布林帶上軌 (${price.close:.2f} >= ${indicator.bb_upper:.2f})")
                    self.discord.send_indicator_alert(
                        symbol=symbol,
                        indicator_type="Bollinger Bands",
                        value=price.close,
                        message=f"價格突破上軌，可能回調"
                    )
                elif price.close <= indicator.bb_lower:
                    alerts.append(f"價格跌破布林帶下軌 (${price.close:.2f} <= ${indicator.bb_lower:.2f})")
                    self.discord.send_indicator_alert(
                        symbol=symbol,
                        indicator_type="Bollinger Bands",
                        value=price.close,
                        message=f"價格跌破下軌，可能反彈"
                    )
            
        except Exception as e:
            logger.error(f"檢查指標警報失敗 ({symbol}): {str(e)}", exc_info=True)
        finally:
            db.close()
        
        return alerts
    
    def check_ai_signal_alerts(self, symbol: str, skip_if_integrated_sent: bool = False) -> List[str]:
        """
        檢查 AI 訊號警報（整合價格變動資訊）
        
        Args:
            symbol: 股票代號
            skip_if_integrated_sent: 如果已經發送過整合通知，則跳過
        
        Returns:
            觸發的警報列表
        """
        alerts = []
        
        if skip_if_integrated_sent:
            return alerts
        
        db = get_db_sync()
        
        try:
            signal = get_latest_signal(db, symbol)
            if not signal:
                return alerts
            
            # 對所有 AI 訊號發送通知（包括 HOLD，但優先級較低）
            price = get_latest_price(db, symbol)
            if not price:
                return alerts
            
            current_price = price.close
            
            # 獲取價格變動資訊
            change_percent = None
            previous_price = None
            prices = get_prices_by_symbol(db, symbol, days=5)
            if len(prices) >= 2:
                previous_price_obj = prices[-2] if len(prices) >= 2 else None
                if previous_price_obj:
                    previous_price = previous_price_obj.close
                    change_percent = ((current_price - previous_price) / previous_price) * 100
            
            # 只對 BUY 和 SELL 訊號記錄到 alerts（HOLD 不記錄但會發送通知）
            if signal.signal in ["BUY", "SELL"]:
                alerts.append(f"AI 訊號: {signal.signal} (置信度: {signal.confidence*100:.1f}%)")
            
            # 對所有訊號（包括 HOLD）發送 Discord 通知（整合價格資訊和 AI 分析）
            # 這樣即使價格變動不大，也能看到完整的分析報告
            self.discord.send_ai_signal(
                symbol=symbol,
                signal=signal.signal,
                confidence=signal.confidence,
                risk_level=signal.risk_level,
                reasoning=signal.reasoning or "",
                current_price=current_price,
                change_percent=change_percent,
                previous_price=previous_price
            )
            
        except Exception as e:
            logger.error(f"檢查 AI 訊號警報失敗 ({symbol}): {str(e)}", exc_info=True)
        finally:
            db.close()
        
        return alerts
    
    def check_all_alerts(self, symbol: str) -> Dict[str, List[str]]:
        """
        檢查所有類型的警報
        
        Args:
            symbol: 股票代號
        
        Returns:
            各類警報的字典
        """
        # 先檢查價格警報（可能已經包含 AI 訊號通知）
        price_alerts, sent_integrated_notification = self.check_price_alerts(symbol)
        
        # 檢查指標警報
        indicator_alerts = self.check_indicator_alerts(symbol)
        
        # 如果價格警報已經發送了整合通知（價格變動超過閾值且有 AI 訊號），
        # 則跳過 AI 訊號警報，避免重複發送
        ai_signal_alerts = self.check_ai_signal_alerts(symbol, skip_if_integrated_sent=sent_integrated_notification)
        
        return {
            "price": price_alerts,
            "indicator": indicator_alerts,
            "ai_signal": ai_signal_alerts
        }
    
    def update_notion_data(self, symbol: str) -> bool:
        """
        更新 Notion 數據庫
        
        Args:
            symbol: 股票代號
        
        Returns:
            是否成功
        """
        db = get_db_sync()
        
        try:
            price = get_latest_price(db, symbol)
            indicator = get_latest_indicator(db, symbol)
            signal = get_latest_signal(db, symbol)
            
            if not price:
                return False
            
            # 計算價格變動
            change_percent = 0.0
            prices = get_prices_by_symbol(db, symbol, days=5)
            if len(prices) >= 2:
                previous_price = prices[-2] if len(prices) >= 2 else None
                if previous_price:
                    change_percent = ((price.close - previous_price.close) / previous_price.close) * 100
            
            # 更新 Notion，日期使用價格記錄的 timestamp（只取日期部分）
            return self.notion.update_stock_data(
                symbol=symbol,
                price=price.close,
                change_percent=change_percent,
                rsi=indicator.rsi if indicator else None,
                ai_signal=signal.signal if signal else None,
                risk_level=signal.risk_level if signal else None,
                price_timestamp=price.timestamp
            )
            
        except Exception as e:
            logger.error(f"更新 Notion 數據失敗 ({symbol}): {str(e)}", exc_info=True)
            return False
        finally:
            db.close()

