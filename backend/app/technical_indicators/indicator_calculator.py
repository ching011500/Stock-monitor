"""
技術指標計算服務
實現 MA、RSI、MACD、布林帶等技術指標的計算
"""
import pandas as pd
import numpy as np
from typing import List, Dict, Optional
from datetime import datetime
import logging

from app.database.database import get_db_sync
from app.database.crud import get_prices_by_symbol, create_technical_indicator
from app.models.stock import StockPrice

logger = logging.getLogger(__name__)


class IndicatorCalculator:
    """技術指標計算器"""
    
    @staticmethod
    def calculate_ma(prices: pd.Series, period: int) -> pd.Series:
        """
        計算移動平均線 (Moving Average)
        
        Args:
            prices: 價格序列（通常為收盤價）
            period: 週期
        
        Returns:
            移動平均線序列
        """
        return prices.rolling(window=period).mean()
    
    @staticmethod
    def calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
        """
        計算相對強弱指標 (RSI)
        
        Args:
            prices: 價格序列（通常為收盤價）
            period: 週期，默認14
        
        Returns:
            RSI 序列，範圍 0-100
        """
        delta = prices.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        # 計算 RS，避免除零錯誤（當 loss 為 0 時，RS 為 inf，RSI 為 100）
        rs = gain / loss.replace(0, np.finfo(float).eps)
        rsi = 100 - (100 / (1 + rs))
        return rsi
    
    @staticmethod
    def calculate_macd(prices: pd.Series, fast_period: int = 12, 
                       slow_period: int = 26, signal_period: int = 9) -> Dict[str, pd.Series]:
        """
        計算 MACD 指標
        
        Args:
            prices: 價格序列（通常為收盤價）
            fast_period: 快線週期，默認12
            slow_period: 慢線週期，默認26
            signal_period: 訊號線週期，默認9
        
        Returns:
            包含 macd, signal, hist 的字典
        """
        ema_fast = prices.ewm(span=fast_period, adjust=False).mean()
        ema_slow = prices.ewm(span=slow_period, adjust=False).mean()
        
        macd = ema_fast - ema_slow
        signal = macd.ewm(span=signal_period, adjust=False).mean()
        hist = macd - signal
        
        return {
            'macd': macd,
            'signal': signal,
            'hist': hist
        }
    
    @staticmethod
    def calculate_bollinger_bands(prices: pd.Series, period: int = 20, 
                                  std_dev: int = 2) -> Dict[str, pd.Series]:
        """
        計算布林帶 (Bollinger Bands)
        
        Args:
            prices: 價格序列（通常為收盤價）
            period: 週期，默認20
            std_dev: 標準差倍數，默認2
        
        Returns:
            包含 upper, middle, lower 的字典
        """
        middle = prices.rolling(window=period).mean()
        std = prices.rolling(window=period).std()
        
        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)
        
        return {
            'upper': upper,
            'middle': middle,
            'lower': lower
        }
    
    @staticmethod
    def calculate_volume_average(volumes: pd.Series, period: int = 20) -> pd.Series:
        """
        計算成交量移動平均
        
        Args:
            volumes: 成交量序列
            period: 週期，默認20
        
        Returns:
            成交量移動平均序列
        """
        return volumes.rolling(window=period).mean()
    
    @staticmethod
    def stock_prices_to_dataframe(prices: List[StockPrice]) -> pd.DataFrame:
        """
        將 StockPrice 列表轉換為 pandas DataFrame
        
        Args:
            prices: StockPrice 對象列表
        
        Returns:
            DataFrame，包含 timestamp, open, high, low, close, volume
        """
        data = {
            'timestamp': [p.timestamp for p in prices],
            'open': [p.open for p in prices],
            'high': [p.high for p in prices],
            'low': [p.low for p in prices],
            'close': [p.close for p in prices],
            'volume': [p.volume for p in prices],
        }
        df = pd.DataFrame(data)
        df.set_index('timestamp', inplace=True)
        df.sort_index(inplace=True)
        return df
    
    def calculate_all_indicators(self, symbol: str, min_data_points: int = 5) -> Optional[Dict]:
        """
        計算指定標的的所有技術指標
        
        Args:
            symbol: 股票代號
            min_data_points: 需要的最小數據點數，默認5（用於計算 MA5）
        
        Returns:
            包含所有指標的字典，如果數據不足則返回 None
        """
        try:
            # 從資料庫獲取歷史價格數據
            db = get_db_sync()
            
            try:
                # 獲取足夠的歷史數據（至少需要 200 個交易日來計算 MA200）
                # 考慮到節假日，獲取更多天數的數據
                prices = get_prices_by_symbol(db, symbol, days=365)
            finally:
                db.close()
            
            # 檢查最小數據要求（至少需要 5 個數據點來計算 MA5）
            if len(prices) < min_data_points:
                logger.error(f"{symbol}: 數據點太少 ({len(prices)} < {min_data_points})，無法計算指標")
                return None
            
            logger.info(f"{symbol}: 找到 {len(prices)} 個數據點，開始計算指標")
            
            # 轉換為 DataFrame
            df = self.stock_prices_to_dataframe(prices)
            
            if df.empty:
                logger.error(f"{symbol}: 無法創建 DataFrame")
                return None
            
            # 提取價格和成交量序列
            close_prices = df['close']
            volumes = df['volume']
            
            # 計算移動平均線
            ma5 = self.calculate_ma(close_prices, 5)
            ma10 = self.calculate_ma(close_prices, 10)
            ma20 = self.calculate_ma(close_prices, 20)
            ma50 = self.calculate_ma(close_prices, 50)
            ma200 = self.calculate_ma(close_prices, 200) if len(prices) >= 200 else None
            
            # 計算 RSI
            rsi = self.calculate_rsi(close_prices, 14)
            
            # 計算 MACD
            macd_data = self.calculate_macd(close_prices, 12, 26, 9)
            
            # 計算布林帶
            bb_data = self.calculate_bollinger_bands(close_prices, 20, 2)
            
            # 計算成交量平均
            volume_avg = self.calculate_volume_average(volumes, 20)
            
            # 獲取最新值（最後一行）
            # 使用最後一筆價格數據的 timestamp
            last_timestamp = prices[-1].timestamp if prices else datetime.utcnow()
            
            result = {
                'symbol': symbol,
                'timestamp': last_timestamp,
                'ma5': float(ma5.iloc[-1]) if not pd.isna(ma5.iloc[-1]) else None,
                'ma10': float(ma10.iloc[-1]) if not pd.isna(ma10.iloc[-1]) else None,
                'ma20': float(ma20.iloc[-1]) if not pd.isna(ma20.iloc[-1]) else None,
                'ma50': float(ma50.iloc[-1]) if not pd.isna(ma50.iloc[-1]) else None,
                'ma200': float(ma200.iloc[-1]) if ma200 is not None and not pd.isna(ma200.iloc[-1]) else None,
                'rsi': float(rsi.iloc[-1]) if not pd.isna(rsi.iloc[-1]) else None,
                'macd': float(macd_data['macd'].iloc[-1]) if not pd.isna(macd_data['macd'].iloc[-1]) else None,
                'macd_signal': float(macd_data['signal'].iloc[-1]) if not pd.isna(macd_data['signal'].iloc[-1]) else None,
                'macd_hist': float(macd_data['hist'].iloc[-1]) if not pd.isna(macd_data['hist'].iloc[-1]) else None,
                'bb_upper': float(bb_data['upper'].iloc[-1]) if not pd.isna(bb_data['upper'].iloc[-1]) else None,
                'bb_middle': float(bb_data['middle'].iloc[-1]) if not pd.isna(bb_data['middle'].iloc[-1]) else None,
                'bb_lower': float(bb_data['lower'].iloc[-1]) if not pd.isna(bb_data['lower'].iloc[-1]) else None,
                'volume_avg': float(volume_avg.iloc[-1]) if not pd.isna(volume_avg.iloc[-1]) else None,
            }
            
            logger.info(f"✓ 成功計算 {symbol} 的技術指標")
            return result
            
        except Exception as e:
            logger.error(f"計算 {symbol} 技術指標時發生錯誤: {str(e)}", exc_info=True)
            return None
    
    def calculate_and_save_indicator(self, symbol: str) -> bool:
        """
        計算並保存指定標的的技術指標到資料庫
        
        Args:
            symbol: 股票代號
        
        Returns:
            是否成功
        """
        try:
            indicator_data = self.calculate_all_indicators(symbol)
            if indicator_data is None:
                logger.warning(f"{symbol}: 無法計算指標，跳過保存")
                return False
            
            # 從 indicator_data 中移除 symbol 和 timestamp，因為它們是位置參數
            # timestamp 會在 create_technical_indicator 中從 kwargs 中提取
            data_to_save = {k: v for k, v in indicator_data.items() 
                          if k not in ['symbol']}
            
            db = get_db_sync()
            try:
                create_technical_indicator(db, symbol, **data_to_save)
                logger.info(f"✓ 成功保存 {symbol} 的技術指標")
                return True
            finally:
                db.close()
            
        except Exception as e:
            logger.error(f"保存 {symbol} 技術指標時發生錯誤: {str(e)}", exc_info=True)
            return False
    
    def calculate_and_save_all_indicators(self, symbols: List[str]) -> Dict[str, bool]:
        """
        計算並保存所有指定標的的技術指標
        
        Args:
            symbols: 股票代號列表
        
        Returns:
            每個標的的成功狀態字典
        """
        results = {}
        for symbol in symbols:
            logger.info(f"正在計算 {symbol} 的技術指標...")
            success = self.calculate_and_save_indicator(symbol)
            results[symbol] = success
        return results

