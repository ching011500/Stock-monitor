"""
報告生成服務
生成專業的每日市場監控報告
"""
from typing import List, Dict, Optional
import logging
import math
from datetime import datetime
from app.config import settings

logger = logging.getLogger(__name__)


class ReportGenerator:
    """報告生成器"""
    
    def __init__(self):
        self.api_key = settings.OPENAI_API_KEY
        self.enabled = bool(self.api_key)
        
        if self.enabled:
            try:
                from openai import OpenAI
                self.client = OpenAI(api_key=self.api_key)
                logger.info("OpenAI 客戶端初始化成功")
            except Exception as e:
                logger.error(f"OpenAI 客戶端初始化失敗: {str(e)}")
                self.enabled = False
                self.client = None
        else:
            self.client = None
            logger.warning("OpenAI API Key 未配置，將使用結構化報告格式")
    
    def calculate_volatility(self, prices: List[float], days: int = 20) -> Optional[float]:
        """
        計算年化波動率（20日）
        
        Args:
            prices: 價格列表（最近N天的收盤價）
            days: 計算天數，默認20
        
        Returns:
            年化波動率（百分比），如果數據不足則返回 None
        """
        if len(prices) < 2:
            return None
        
        # 計算日報酬率
        returns = []
        for i in range(1, min(len(prices), days + 1)):
            if prices[i-1] > 0:
                daily_return = (prices[i] - prices[i-1]) / prices[i-1]
                returns.append(daily_return)
        
        if len(returns) < 2:
            return None
        
        # 計算標準差
        mean_return = sum(returns) / len(returns)
        variance = sum((r - mean_return) ** 2 for r in returns) / (len(returns) - 1)
        std_dev = math.sqrt(variance)
        
        # 年化波動率（假設252個交易日）
        annualized_volatility = std_dev * math.sqrt(252) * 100
        
        return annualized_volatility
    
    def detect_technical_alerts(self, price: float, ma20: Optional[float], ma50: Optional[float], 
                               rsi: Optional[float], volatility: Optional[float], 
                               avg_volatility: Optional[float] = None) -> List[str]:
        """
        檢測技術警報
        
        Args:
            price: 當前價格
            ma20: MA20 值
            ma50: MA50 值
            rsi: RSI 值
            volatility: 當前波動率
            avg_volatility: 平均波動率（用於比較）
        
        Returns:
            警報列表
        """
        alerts = []
        
        # MA20 跌破/突破
        if ma20 is not None:
            if price < ma20:
                alerts.append("跌破 MA20")
            elif price > ma20 * 1.02:  # 明顯突破
                alerts.append("突破 MA20")
        
        # MA50 跌破/突破
        if ma50 is not None:
            if price < ma50:
                alerts.append("跌破 MA50")
            elif price > ma50 * 1.02:
                alerts.append("突破 MA50")
        
        # RSI 過熱/過冷
        if rsi is not None:
            if rsi > 70:
                alerts.append("RSI 過熱")
            elif rsi < 30:
                alerts.append("RSI 超賣")
        
        # 異常波動
        if volatility is not None and avg_volatility is not None:
            if volatility > avg_volatility * 1.5:
                alerts.append("異常波動")
        
        return alerts
    
    def generate_daily_analysis(self, stocks_data: List[Dict], date: str) -> Optional[str]:
        """
        生成每日市場分析報告（使用 OpenAI，如果可用）
        
        Args:
            stocks_data: 股票數據列表（包含完整技術指標）
            date: 日期
        
        Returns:
            生成的報告文本，如果失敗則返回 None
        """
        if not self.enabled or not self.client:
            return None
        
        try:
            # 構建提示詞
            prompt = self._build_analysis_prompt(stocks_data, date)
            
            # 調用 OpenAI API
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "你是一位專業的量化投資分析助理，擅長用繁體中文撰寫簡潔、專業、量化的市場監控報告。報告風格冷靜、客觀，偏向市場狀態監控而非交易建議。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.3,  # 降低溫度以獲得更一致的輸出
                max_tokens=2000
            )
            
            analysis = response.choices[0].message.content
            logger.info("OpenAI 分析報告生成成功")
            return analysis
            
        except Exception as e:
            logger.error(f"生成 OpenAI 分析報告失敗: {str(e)}", exc_info=True)
            return None
    
    def _build_analysis_prompt(self, stocks_data: List[Dict], date: str) -> str:
        """構建分析提示詞（符合用戶規格）"""
        stocks_summary = []
        for stock in stocks_data:
            symbol = stock.get("symbol", "")
            price = stock.get("price", 0)
            change = stock.get("change_percent", 0)
            ma20 = stock.get("ma20")
            ma50 = stock.get("ma50")
            rsi = stock.get("rsi")
            volatility = stock.get("volatility")
            alerts = stock.get("alerts", [])
            signal = stock.get("ai_signal", "HOLD")
            risk = stock.get("risk_level", "MEDIUM")
            
            summary = f"{symbol}: 價格 ${price:.2f} ({change:+.2f}%)"
            if ma20:
                summary += f", MA20: ${ma20:.2f}"
            if ma50:
                summary += f", MA50: ${ma50:.2f}"
            if rsi:
                summary += f", RSI: {rsi:.2f}"
            if volatility:
                summary += f", 波動率: {volatility:.2f}%"
            if alerts:
                summary += f", 警報: {', '.join(alerts)}"
            summary += f", AI訊號: {signal}, 風險: {risk}"
            stocks_summary.append(summary)
        
        prompt = f"""請為 {date} 生成一份專業的每日市場監控報告，嚴格遵守以下格式：

### 📊 今日市場狀態總覽
（3 行以內，量化 + 定性混合）
- 市場狀態：（例如：🟡 偏保守 / 🟢 偏多 / 🔴 高風險）
- 廣度：{{BUY 訊號數}} / {{總標的數}}
- 波動概況：相較 20 日均值（偏高 / 正常 / 偏低）

### 🚨 今日警報摘要（若無重大警報請明確寫出）
- 列出「有觸發警報的標的 + 警報類型」
- 若無，請寫：「今日無重大技術異常，市場維持常態波動」

### 📈 個股分析（每檔一個區塊，格式一致）

#### {{Ticker}}

【文字解讀（固定四行）】
- 價格表現：{{今日漲跌幅}}，相對市場（強 / 中性 / 弱）
- 趨勢結構：價格相對 MA20 / MA50 的位置與意義
- 動能狀態：RSI 水準（過熱 / 中性 / 偏弱）
- 綜合結論：{{BUY / HOLD / WATCH}}，風險等級（Low / Medium / High）

⚠️ 請避免使用投資建議用語（如「適合買進」），僅做監控與風險描述。

### 🧠 AI 監控備註（給未來回顧 / Agent 使用）
- 用 2–3 句描述「今日市場的主要特徵」
- 說明哪些標的值得後續持續追蹤，以及原因（基於指標）

監控標的的數據：
{chr(10).join(stocks_summary)}

請用繁體中文撰寫，保持專業、冷靜、量化的風格，避免情緒化用語。"""
        
        return prompt
    
    def generate_structured_report(self, stocks_data: List[Dict], date: str) -> str:
        """
        生成結構化的每日市場監控報告（不使用 OpenAI，符合用戶規格）
        
        Args:
            stocks_data: 股票數據列表（需包含完整技術指標）
            date: 日期
        
        Returns:
            格式化的報告文本
        """
        lines = []
        
        # 計算市場整體狀態
        buy_signals = sum(1 for s in stocks_data if s.get("ai_signal") == "BUY")
        total_symbols = len(stocks_data)
        avg_change = sum(s.get("change_percent", 0) for s in stocks_data) / total_symbols if stocks_data else 0
        
        # 計算平均波動率
        volatilities = [s.get("volatility") for s in stocks_data if s.get("volatility") is not None]
        avg_volatility = sum(volatilities) / len(volatilities) if volatilities else None
        
        # 判斷市場狀態
        if avg_change > 0.5 and buy_signals >= total_symbols * 0.5:
            market_status = "🟢 偏多"
        elif avg_change < -0.5 or buy_signals == 0:
            market_status = "🔴 高風險"
        else:
            market_status = "🟡 中性"
        
        # 波動概況
        volatility_status = "正常"
        if avg_volatility:
            # 這裡可以根據歷史平均波動率判斷，暫時簡化
            if avg_volatility > 30:
                volatility_status = "偏高"
            elif avg_volatility < 15:
                volatility_status = "偏低"
        
        # 📊 今日市場狀態總覽
        lines.append("### 📊 今日市場狀態總覽")
        lines.append(f"- 市場狀態：{market_status}")
        lines.append(f"- 廣度：{buy_signals} / {total_symbols}")
        lines.append(f"- 波動概況：相較 20 日均值（{volatility_status}）")
        lines.append("")
        
        # 🚨 今日警報摘要
        lines.append("### 🚨 今日警報摘要")
        all_alerts = []
        for stock in stocks_data:
            symbol = stock.get("symbol", "")
            alerts = stock.get("alerts", [])
            if alerts:
                all_alerts.append(f"- {symbol}: {', '.join(alerts)}")
        
        if all_alerts:
            lines.extend(all_alerts)
        else:
            lines.append("- 今日無重大技術異常，市場維持常態波動")
        lines.append("")
        
        # 📈 個股分析
        lines.append("### 📈 個股分析")
        lines.append("")
        
        for stock in stocks_data:
            symbol = stock.get("symbol", "")
            price = stock.get("price", 0)
            change = stock.get("change_percent", 0)
            ma20 = stock.get("ma20")
            ma50 = stock.get("ma50")
            rsi = stock.get("rsi")
            signal = stock.get("ai_signal", "HOLD")
            risk = stock.get("risk_level", "MEDIUM")
            
            lines.append(f"#### {symbol}")
            lines.append("【文字解讀】")
            
            # 價格表現
            market_relative = "強" if change > avg_change * 1.2 else "弱" if change < avg_change * 0.8 else "中性"
            lines.append(f"- 價格表現：{change:+.2f}%，相對市場（{market_relative}）")
            
            # 趨勢結構
            trend_desc = []
            if ma20 and ma50:
                if price > ma20 and price > ma50:
                    trend_desc.append(f"價格位於 MA20 (${ma20:.2f}) 和 MA50 (${ma50:.2f}) 上方，呈現多頭排列")
                elif price < ma20 and price < ma50:
                    trend_desc.append(f"價格位於 MA20 (${ma20:.2f}) 和 MA50 (${ma50:.2f}) 下方，呈現空頭排列")
                elif price > ma20 and price < ma50:
                    trend_desc.append(f"價格位於 MA20 (${ma20:.2f}) 上方但 MA50 (${ma50:.2f}) 下方，短期偏多但中期偏弱")
                else:
                    trend_desc.append(f"價格位於 MA20 (${ma20:.2f}) 下方但 MA50 (${ma50:.2f}) 上方，短期偏弱但中期偏多")
            elif ma20:
                if price > ma20:
                    trend_desc.append(f"價格位於 MA20 (${ma20:.2f}) 上方")
                else:
                    trend_desc.append(f"價格位於 MA20 (${ma20:.2f}) 下方")
            elif ma50:
                if price > ma50:
                    trend_desc.append(f"價格位於 MA50 (${ma50:.2f}) 上方")
                else:
                    trend_desc.append(f"價格位於 MA50 (${ma50:.2f}) 下方")
            trend_text = "，".join(trend_desc) if trend_desc else "數據不足"
            lines.append(f"- 趨勢結構：{trend_text}")
            
            # 動能狀態
            if rsi:
                if rsi > 70:
                    momentum = "過熱"
                elif rsi < 30:
                    momentum = "偏弱"
                else:
                    momentum = "中性"
                lines.append(f"- 動能狀態：RSI {rsi:.2f}（{momentum}）")
            else:
                lines.append("- 動能狀態：RSI 數據不足")
            
            # 綜合結論
            signal_map = {"BUY": "BUY", "SELL": "WATCH", "HOLD": "HOLD"}
            conclusion_signal = signal_map.get(signal, "HOLD")
            risk_map = {"LOW": "Low", "MEDIUM": "Medium", "HIGH": "High"}
            conclusion_risk = risk_map.get(risk, "Medium")
            lines.append(f"- 綜合結論：{conclusion_signal}，風險等級（{conclusion_risk}）")
            lines.append("")
        
        # 🧠 AI 監控備註
        lines.append("### 🧠 AI 監控備註")
        if buy_signals > 0:
            buy_symbols = [s.get("symbol") for s in stocks_data if s.get("ai_signal") == "BUY"]
            lines.append(f"- 今日市場呈現 {market_status.lower()}態勢，{buy_signals} 檔標的出現 BUY 訊號（{', '.join(buy_symbols)}）")
        else:
            lines.append(f"- 今日市場呈現 {market_status.lower()}態勢，無明顯買入訊號")
        
        if avg_volatility:
            lines.append(f"- 整體波動率 {avg_volatility:.2f}%，處於{volatility_status}水平")
        
        # 找出值得追蹤的標的
        watch_symbols = []
        for stock in stocks_data:
            symbol = stock.get("symbol", "")
            alerts = stock.get("alerts", [])
            rsi = stock.get("rsi")
            if alerts or (rsi and (rsi > 70 or rsi < 30)):
                watch_symbols.append(symbol)
        
        if watch_symbols:
            lines.append(f"- 值得後續追蹤的標的：{', '.join(watch_symbols)}（基於技術指標異常或警報觸發）")
        else:
            lines.append("- 所有標的技術指標均處於正常範圍，無需特別關注")
        
        return "\n".join(lines)

