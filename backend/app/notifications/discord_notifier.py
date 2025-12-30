"""
Discord 通知服務
使用 Webhook 發送通知到 Discord 頻道
"""
import requests
from typing import Optional, Dict
import logging

from app.config import settings

logger = logging.getLogger(__name__)


class DiscordNotifier:
    """Discord 通知器"""
    
    def __init__(self):
        self.webhook_url = settings.DISCORD_WEBHOOK_URL
        self.enabled = settings.DISCORD_ENABLED
    
    def send_message(self, content: str, embed: Optional[Dict] = None) -> bool:
        """
        發送消息到 Discord
        
        Args:
            content: 消息內容
            embed: 可選的嵌入對象（富文本格式）
        
        Returns:
            是否成功
        """
        if not self.enabled:
            logger.debug("Discord 通知未啟用，跳過發送")
            return False
        
        if not self.webhook_url:
            logger.warning("Discord Webhook URL 未配置，無法發送通知")
            return False
        
        try:
            payload = {"content": content}
            if embed:
                payload["embeds"] = [embed]
            
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 204:
                logger.debug("Discord 通知發送成功")
                return True
            else:
                logger.warning(f"Discord 通知發送失敗: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"發送 Discord 通知時發生錯誤: {str(e)}", exc_info=True)
            return False
    
    def send_price_alert(self, symbol: str, current_price: float, 
                        change_percent: float, previous_price: float) -> bool:
        """
        發送價格變動警報（僅價格變動超過閾值時使用）
        
        Args:
            symbol: 股票代號
            current_price: 當前價格
            change_percent: 變動百分比
            previous_price: 前一價格
        
        Returns:
            是否成功
        """
        emoji = "🟢" if change_percent > 0 else "🔴"
        direction = "上漲" if change_percent > 0 else "下跌"
        
        embed = {
            "title": f"{emoji} {symbol} 價格警報",
            "description": f"價格大幅**{direction}** {abs(change_percent):.2f}%",
            "color": 0x00ff00 if change_percent > 0 else 0xff0000,
            "fields": [
                {
                    "name": "💰 當前價格",
                    "value": f"**${current_price:.2f}**",
                    "inline": True
                },
                {
                    "name": "📊 變動",
                    "value": f"**{change_percent:+.2f}%**",
                    "inline": True
                },
                {
                    "name": "前一價格",
                    "value": f"${previous_price:.2f}",
                    "inline": True
                }
            ]
        }
        
        content = f"**{symbol}** {emoji} {direction} **{abs(change_percent):.2f}%** | ${current_price:.2f}"
        return self.send_message(content, embed)
    
    def send_indicator_alert(self, symbol: str, indicator_type: str, 
                           value: float, message: str) -> bool:
        """
        發送指標警報
        
        Args:
            symbol: 股票代號
            indicator_type: 指標類型（如 RSI、MACD 等）
            value: 指標值
            message: 警報訊息
        
        Returns:
            是否成功
        """
        embed = {
            "title": f"📊 {symbol} {indicator_type} 警報",
            "description": message,
            "color": 0xffa500,
            "fields": [
                {
                    "name": "指標值",
                    "value": f"{value:.2f}",
                    "inline": True
                }
            ],
            "timestamp": None
        }
        
        content = f"**{symbol}** {indicator_type} 警報: {message}"
        return self.send_message(content, embed)
    
    def send_ai_signal(self, symbol: str, signal: str, confidence: float,
                      risk_level: str, reasoning: str, current_price: float,
                      change_percent: float = None, previous_price: float = None) -> bool:
        """
        發送 AI 訊號通知（整合價格資訊和分析）
        
        Args:
            symbol: 股票代號
            signal: 訊號類型 (BUY/SELL/HOLD)
            confidence: 置信度 (0-1)
            risk_level: 風險等級 (LOW/MEDIUM/HIGH)
            reasoning: 分析理由
            current_price: 當前價格
            change_percent: 價格變動百分比（可選）
            previous_price: 前一價格（可選）
        
        Returns:
            是否成功
        """
        signal_emoji = {
            "BUY": "🟢",
            "SELL": "🔴",
            "HOLD": "🟡"
        }
        signal_color = {
            "BUY": 0x00ff00,
            "SELL": 0xff0000,
            "HOLD": 0xffff00
        }
        
        emoji = signal_emoji.get(signal, "📊")
        color = signal_color.get(signal, 0x808080)
        
        risk_emoji = {
            "LOW": "🟢",
            "MEDIUM": "🟡",
            "HIGH": "🔴"
        }
        risk_emoji_icon = risk_emoji.get(risk_level, "⚪")
        
        # 構建價格資訊字段
        fields = [
            {
                "name": "💰 當前價格",
                "value": f"**${current_price:.2f}**",
                "inline": True
            }
        ]
        
        # 如果有價格變動資訊，添加到字段中
        if change_percent is not None:
            change_emoji = "📈" if change_percent > 0 else "📉" if change_percent < 0 else "➡️"
            fields.append({
                "name": f"{change_emoji} 價格變動",
                "value": f"**{change_percent:+.2f}%**",
                "inline": True
            })
            if previous_price is not None:
                fields.append({
                    "name": "前一價格",
                    "value": f"${previous_price:.2f}",
                    "inline": True
                })
        
        # AI 分析資訊
        fields.extend([
            {
                "name": "🤖 AI 訊號",
                "value": f"**{emoji} {signal}**",
                "inline": True
            },
            {
                "name": "📊 置信度",
                "value": f"**{confidence * 100:.1f}%**",
                "inline": True
            },
            {
                "name": "⚠️ 風險等級",
                "value": f"{risk_emoji_icon} **{risk_level}**",
                "inline": True
            }
        ])
        
        # 格式化分析理由（每行一個要點，限制長度）
        reasoning_lines = reasoning.split(';') if reasoning else []
        formatted_reasoning = "\n".join([f"• {line.strip()}" for line in reasoning_lines[:8]])  # 最多顯示8個要點
        if len(reasoning_lines) > 8:
            formatted_reasoning += f"\n• ...（還有 {len(reasoning_lines) - 8} 個要點）"
        
        embed = {
            "title": f"{emoji} {symbol} 市場分析報告",
            "description": f"**AI 訊號: {signal}** | 置信度: {confidence * 100:.1f}% | 風險: {risk_emoji_icon} {risk_level}",
            "color": color,
            "fields": fields,
            "footer": {
                "text": "技術分析理由"
            }
        }
        
        # 添加詳細的分析理由（如果有）
        if formatted_reasoning:
            embed["fields"].append({
                "name": "📋 分析理由",
                "value": formatted_reasoning[:1024],  # Discord embed field 最大 1024 字符
                "inline": False
            })
        
        content = f"**{symbol}** {emoji} **{signal}** | ${current_price:.2f}"
        if change_percent is not None:
            content += f" ({change_percent:+.2f}%)"
        content += f" | 置信度: {confidence*100:.1f}%"
        
        return self.send_message(content, embed)
    
    def send_daily_summary(self, summary_data: Dict) -> bool:
        """
        發送每日摘要
        
        Args:
            summary_data: 摘要數據字典，包含標的列表和統計信息
        
        Returns:
            是否成功
        """
        symbols = summary_data.get("symbols", [])
        date = summary_data.get("date", "")
        
        content_lines = [f"## 📊 每日市場摘要 - {date}\n"]
        
        for symbol_data in symbols:
            symbol = symbol_data.get("symbol", "")
            price = symbol_data.get("price", 0)
            change = symbol_data.get("change_percent", 0)
            signal = symbol_data.get("ai_signal", "HOLD")
            
            emoji = "🟢" if change > 0 else "🔴" if change < 0 else "⚪"
            content_lines.append(f"{emoji} **{symbol}**: ${price:.2f} ({change:+.2f}%) - AI: {signal}")
        
        content = "\n".join(content_lines)
        return self.send_message(content)
    
    def send_system_message(self, title: str, message: str, level: str = "INFO") -> bool:
        """
        發送系統消息
        
        Args:
            title: 標題
            message: 消息內容
            level: 級別 (INFO/WARNING/ERROR)
        
        Returns:
            是否成功
        """
        level_emoji = {
            "INFO": "ℹ️",
            "WARNING": "⚠️",
            "ERROR": "❌"
        }
        level_color = {
            "INFO": 0x3498db,
            "WARNING": 0xf39c12,
            "ERROR": 0xe74c3c
        }
        
        embed = {
            "title": f"{level_emoji.get(level, '📢')} {title}",
            "description": message,
            "color": level_color.get(level, 0x808080),
            "timestamp": None
        }
        
        return self.send_message(f"**{title}**\n{message}", embed)

