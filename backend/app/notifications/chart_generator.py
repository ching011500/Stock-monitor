"""
技術圖表生成服務
生成價格 + MA + RSI 圖表
"""
import matplotlib
matplotlib.use('Agg')  # 使用非交互式後端
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.figure import Figure
from typing import List, Optional, Tuple
from datetime import datetime
import io
import base64
import logging
import tempfile
import os

from app.models.stock import StockPrice

logger = logging.getLogger(__name__)


class ChartGenerator:
    """圖表生成器"""
    
    def __init__(self):
        # 設置中文字體（如果可用）
        plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'DejaVu Sans', 'sans-serif']
        plt.rcParams['axes.unicode_minus'] = False
    
    def generate_stock_chart(self, symbol: str, prices: List[StockPrice], 
                            ma20: Optional[float] = None, ma50: Optional[float] = None,
                            rsi_values: Optional[List[float]] = None) -> Optional[str]:
        """
        生成股票技術圖表（價格 + MA + RSI）
        
        Args:
            symbol: 股票代號
            prices: 價格數據列表
            ma20: MA20 值（最新）
            ma50: MA50 值（最新）
            rsi_values: RSI 值列表（與 prices 對應）
        
        Returns:
            圖表文件的臨時路徑，如果失敗則返回 None
        """
        if not prices or len(prices) < 2:
            logger.warning(f"{symbol}: 價格數據不足，無法生成圖表")
            return None
        
        try:
            # 創建圖表（上下兩個子圖）
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), height_ratios=[2, 1])
            fig.suptitle(f'{symbol} 技術分析圖表', fontsize=16, fontweight='bold')
            
            # 提取數據
            dates = [p.timestamp for p in prices]
            closes = [p.close for p in prices]
            
            # 上圖：價格 + MA
            ax1.plot(dates, closes, label='收盤價', color='#1f77b4', linewidth=2)
            
            # 如果有 MA20 和 MA50，計算並繪製
            if len(prices) >= 20:
                # 計算 MA20
                ma20_values = []
                for i in range(len(prices)):
                    if i < 19:
                        ma20_values.append(None)
                    else:
                        ma20_avg = sum(p.close for p in prices[i-19:i+1]) / 20
                        ma20_values.append(ma20_avg)
                
                # 只繪製有值的部分
                ma20_dates = [dates[i] for i in range(len(dates)) if ma20_values[i] is not None]
                ma20_plot = [ma20_values[i] for i in range(len(dates)) if ma20_values[i] is not None]
                if ma20_plot:
                    ax1.plot(ma20_dates, ma20_plot, label='MA20', color='#ff7f0e', linewidth=1.5, linestyle='--')
            
            if len(prices) >= 50:
                # 計算 MA50
                ma50_values = []
                for i in range(len(prices)):
                    if i < 49:
                        ma50_values.append(None)
                    else:
                        ma50_avg = sum(p.close for p in prices[i-49:i+1]) / 50
                        ma50_values.append(ma50_avg)
                
                ma50_dates = [dates[i] for i in range(len(dates)) if ma50_values[i] is not None]
                ma50_plot = [ma50_values[i] for i in range(len(dates)) if ma50_values[i] is not None]
                if ma50_plot:
                    ax1.plot(ma50_dates, ma50_plot, label='MA50', color='#2ca02c', linewidth=1.5, linestyle='--')
            
            ax1.set_ylabel('價格 ($)', fontsize=12)
            ax1.legend(loc='upper left', fontsize=10)
            ax1.grid(True, alpha=0.3)
            ax1.set_title('價格走勢與移動平均線', fontsize=12)
            
            # 格式化日期
            ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
            ax1.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, len(dates)//10)))
            plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha='right')
            
            # 下圖：RSI
            if rsi_values and len(rsi_values) == len(prices):
                ax2.plot(dates, rsi_values, label='RSI(14)', color='#9467bd', linewidth=2)
                ax2.axhline(y=70, color='r', linestyle='--', alpha=0.5, label='超買線 (70)')
                ax2.axhline(y=50, color='gray', linestyle='--', alpha=0.3, label='中線 (50)')
                ax2.axhline(y=30, color='g', linestyle='--', alpha=0.5, label='超賣線 (30)')
                ax2.fill_between(dates, 30, 70, alpha=0.1, color='gray')
            else:
                # 如果沒有 RSI 數據，顯示提示
                ax2.text(0.5, 0.5, 'RSI 數據不足', 
                        horizontalalignment='center', verticalalignment='center',
                        transform=ax2.transAxes, fontsize=12, color='gray')
            
            ax2.set_ylabel('RSI', fontsize=12)
            ax2.set_xlabel('日期', fontsize=12)
            ax2.set_ylim(0, 100)
            ax2.legend(loc='upper left', fontsize=9)
            ax2.grid(True, alpha=0.3)
            ax2.set_title('RSI 相對強弱指標', fontsize=12)
            
            # 格式化日期
            ax2.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
            ax2.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, len(dates)//10)))
            plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45, ha='right')
            
            plt.tight_layout()
            
            # 保存到臨時文件
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
            temp_path = temp_file.name
            fig.savefig(temp_path, dpi=150, bbox_inches='tight', facecolor='white')
            plt.close(fig)
            
            logger.info(f"{symbol}: 圖表生成成功，保存至 {temp_path}")
            return temp_path
            
        except Exception as e:
            logger.error(f"生成 {symbol} 圖表失敗: {str(e)}", exc_info=True)
            plt.close('all')  # 確保關閉所有圖表
            return None
    
    def generate_chart_base64(self, symbol: str, prices: List[StockPrice],
                             ma20: Optional[float] = None, ma50: Optional[float] = None,
                             rsi_values: Optional[List[float]] = None) -> Optional[str]:
        """
        生成圖表並返回 base64 編碼的字符串
        
        Returns:
            base64 編碼的圖片字符串，如果失敗則返回 None
        """
        if not prices or len(prices) < 2:
            return None
        
        try:
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8), height_ratios=[2, 1])
            fig.suptitle(f'{symbol} 技術分析圖表', fontsize=16, fontweight='bold')
            
            dates = [p.timestamp for p in prices]
            closes = [p.close for p in prices]
            
            # 上圖：價格 + MA
            ax1.plot(dates, closes, label='收盤價', color='#1f77b4', linewidth=2)
            
            if len(prices) >= 20:
                ma20_values = []
                for i in range(len(prices)):
                    if i < 19:
                        ma20_values.append(None)
                    else:
                        ma20_avg = sum(p.close for p in prices[i-19:i+1]) / 20
                        ma20_values.append(ma20_avg)
                
                ma20_dates = [dates[i] for i in range(len(dates)) if ma20_values[i] is not None]
                ma20_plot = [ma20_values[i] for i in range(len(dates)) if ma20_values[i] is not None]
                if ma20_plot:
                    ax1.plot(ma20_dates, ma20_plot, label='MA20', color='#ff7f0e', linewidth=1.5, linestyle='--')
            
            if len(prices) >= 50:
                ma50_values = []
                for i in range(len(prices)):
                    if i < 49:
                        ma50_values.append(None)
                    else:
                        ma50_avg = sum(p.close for p in prices[i-49:i+1]) / 50
                        ma50_values.append(ma50_avg)
                
                ma50_dates = [dates[i] for i in range(len(dates)) if ma50_values[i] is not None]
                ma50_plot = [ma50_values[i] for i in range(len(dates)) if ma50_values[i] is not None]
                if ma50_plot:
                    ax1.plot(ma50_dates, ma50_plot, label='MA50', color='#2ca02c', linewidth=1.5, linestyle='--')
            
            ax1.set_ylabel('價格 ($)', fontsize=12)
            ax1.legend(loc='upper left', fontsize=10)
            ax1.grid(True, alpha=0.3)
            ax1.set_title('價格走勢與移動平均線', fontsize=12)
            ax1.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
            ax1.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, len(dates)//10)))
            plt.setp(ax1.xaxis.get_majorticklabels(), rotation=45, ha='right')
            
            # 下圖：RSI
            if rsi_values and len(rsi_values) == len(prices):
                ax2.plot(dates, rsi_values, label='RSI(14)', color='#9467bd', linewidth=2)
                ax2.axhline(y=70, color='r', linestyle='--', alpha=0.5, label='超買線 (70)')
                ax2.axhline(y=50, color='gray', linestyle='--', alpha=0.3, label='中線 (50)')
                ax2.axhline(y=30, color='g', linestyle='--', alpha=0.5, label='超賣線 (30)')
                ax2.fill_between(dates, 30, 70, alpha=0.1, color='gray')
            else:
                ax2.text(0.5, 0.5, 'RSI 數據不足', 
                        horizontalalignment='center', verticalalignment='center',
                        transform=ax2.transAxes, fontsize=12, color='gray')
            
            ax2.set_ylabel('RSI', fontsize=12)
            ax2.set_xlabel('日期', fontsize=12)
            ax2.set_ylim(0, 100)
            ax2.legend(loc='upper left', fontsize=9)
            ax2.grid(True, alpha=0.3)
            ax2.set_title('RSI 相對強弱指標', fontsize=12)
            ax2.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
            ax2.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, len(dates)//10)))
            plt.setp(ax2.xaxis.get_majorticklabels(), rotation=45, ha='right')
            
            plt.tight_layout()
            
            # 轉換為 base64
            buf = io.BytesIO()
            fig.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='white')
            buf.seek(0)
            img_base64 = base64.b64encode(buf.read()).decode('utf-8')
            plt.close(fig)
            
            return img_base64
            
        except Exception as e:
            logger.error(f"生成 {symbol} 圖表失敗: {str(e)}", exc_info=True)
            plt.close('all')
            return None


