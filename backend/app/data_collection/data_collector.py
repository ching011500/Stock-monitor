"""
股票數據收集服務
使用 yfinance 獲取股票數據
"""
import yfinance as yf
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import logging
import pandas as pd
import time

from app.config import settings
from app.database.database import get_db_sync
from app.database.crud import create_stock_price, get_latest_price

logger = logging.getLogger(__name__)

# 設置 yfinance 日誌級別，減少不必要的警告
yf_logger = logging.getLogger('yfinance')
yf_logger.setLevel(logging.ERROR)


class DataCollector:
    """數據收集器"""
    
    def __init__(self):
        self.symbols = settings.MONITORED_SYMBOLS.split(",")
        self.symbols = [s.strip() for s in self.symbols if s.strip()]
    
    def fetch_stock_data(self, symbol: str, retry_count: int = 3, delay: float = 2.0) -> Optional[Dict]:
        """
        獲取單個股票的當前數據（帶重試機制）
        
        Args:
            symbol: 股票代號
            retry_count: 重試次數
            delay: 重試延遲（秒），用於避免 429 錯誤
        
        Returns:
            Dict with stock data or None if failed
        """
        for attempt in range(retry_count):
            try:
                if attempt > 0:
                    # 重試前等待，避免 429 錯誤
                    wait_time = delay * (attempt + 1)  # 遞增延遲
                    logger.info(f"等待 {wait_time:.1f} 秒後重試 {symbol} (嘗試 {attempt + 1}/{retry_count})...")
                    time.sleep(wait_time)
                
                logger.info(f"開始獲取 {symbol} 的數據... (嘗試 {attempt + 1}/{retry_count})")
                
                # 方法1: 使用 Ticker.history（優先，因為更簡單可靠）
                try:
                    logger.debug(f"使用 Ticker.history 方法獲取 {symbol} 數據...")
                    ticker = yf.Ticker(symbol)
                    
                    # 嘗試不同的時間範圍
                    data = None
                    for period in ["5d", "1mo", "3mo"]:
                        try:
                            data = ticker.history(period=period, interval="1d")
                            if not data.empty:
                                logger.info(f"✓ history 方法成功獲取 {symbol} 數據 (period={period})")
                                break
                        except Exception as e:
                            logger.debug(f"period={period} 失敗: {str(e)}")
                            continue
                    
                    if data is None or data.empty:
                        raise ValueError("All history periods failed or returned empty")
                        
                except Exception as hist_error:
                    logger.warning(f"history 方法失敗: {str(hist_error)}")
                    # 方法2: 回退到 yf.download
                    try:
                        logger.debug(f"嘗試使用 download 方法...")
                        end_date = datetime.now()
                        start_date = end_date - timedelta(days=30)
                        
                        # 設置 yfinance 日誌級別以避免警告
                        yf_logger = logging.getLogger('yfinance')
                        original_level = yf_logger.level
                        yf_logger.setLevel(logging.ERROR)
                        
                        try:
                            data = yf.download(
                                symbol, 
                                start=start_date.strftime('%Y-%m-%d'),
                                end=end_date.strftime('%Y-%m-%d'),
                                progress=False,
                                timeout=20
                            )
                        finally:
                            yf_logger.setLevel(original_level)
                        
                        # 處理多層索引
                        if isinstance(data.columns, pd.MultiIndex):
                            if symbol in data.columns.levels[1]:
                                data = data.xs(symbol, axis=1, level=1)
                            else:
                                data = data.iloc[:, 0].to_frame()
                        
                        if data.empty:
                            raise ValueError("Download returned empty data")
                        
                        logger.info(f"✓ download 方法成功獲取 {symbol} 數據")
                        
                    except Exception as download_error:
                        logger.warning(f"download 方法也失敗: {str(download_error)}")
                        raise  # 重新拋出異常以觸發重試
                
                # 如果成功獲取數據，處理並返回
                if data.empty:
                    raise ValueError("Data is empty")
                
                # 確保數據是 DataFrame
                if isinstance(data, pd.Series):
                    data = data.to_frame().T
                
                # 獲取最新一筆數據（最後一行）
                latest = data.iloc[-1]
                latest_date = data.index[-1]  # 獲取數據的日期索引
                logger.debug(f"{symbol} 獲取到 {len(data)} 條記錄，使用最新一筆（日期: {latest_date}）")
                
                # 獲取當前價格（使用收盤價）
                current_price = float(latest['Close'])
                
                # 將日期轉換為 datetime 對象
                if hasattr(latest_date, 'to_pydatetime'):
                    # pandas Timestamp 對象
                    data_timestamp = latest_date.to_pydatetime()
                    # 如果是時區感知的，轉換為 UTC naive
                    if data_timestamp.tzinfo is not None:
                        data_timestamp = data_timestamp.replace(tzinfo=None)
                elif isinstance(latest_date, datetime):
                    data_timestamp = latest_date
                    if data_timestamp.tzinfo is not None:
                        data_timestamp = data_timestamp.replace(tzinfo=None)
                else:
                    # 如果無法解析，使用當前時間（UTC 的今天）
                    data_timestamp = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
                
                # 構建返回數據
                result_data = {
                    'symbol': symbol,
                    'timestamp': data_timestamp,
                    'open': float(latest['Open']),
                    'high': float(latest['High']),
                    'low': float(latest['Low']),
                    'close': float(current_price),
                    'volume': int(latest['Volume']),
                    'adj_close': float(latest['Close'])
                }
                
                logger.info(f"✓ 成功獲取 {symbol} 數據: ${current_price:.2f}")
                return result_data
                
            except Exception as e:
                if attempt == retry_count - 1:
                    # 最後一次嘗試失敗
                    logger.error(f"所有方法都失敗，已重試 {retry_count} 次: {str(e)}")
                    return None
                else:
                    # 繼續重試
                    logger.warning(f"獲取 {symbol} 失敗，將重試: {str(e)}")
                    continue
        
        # 如果所有重試都失敗
        return None
    
    def fetch_all_stocks(self) -> List[Dict]:
        """獲取所有監控標的的數據（帶延遲以避免 429 錯誤）"""
        results = []
        for i, symbol in enumerate(self.symbols):
            # 在每個請求之間添加延遲，避免觸發 429 錯誤
            if i > 0:
                delay = 3.0  # 3秒延遲
                logger.debug(f"等待 {delay} 秒以避免速率限制...")
                time.sleep(delay)
            
            logger.info(f"正在獲取 {symbol} 的數據 ({i+1}/{len(self.symbols)})...")
            data = self.fetch_stock_data(symbol)
            if data:
                logger.info(f"成功獲取 {symbol} 的數據: ${data['close']:.2f}")
                results.append(data)
            else:
                logger.warning(f"無法獲取 {symbol} 的數據")
        return results
    
    def save_stock_data(self, data: Dict) -> bool:
        """保存股票數據到數據庫"""
        try:
            db = get_db_sync()
            create_stock_price(
                db=db,
                symbol=data['symbol'],
                open=data['open'],
                high=data['high'],
                low=data['low'],
                close=data['close'],
                volume=data['volume'],
                adj_close=data['adj_close'],
                timestamp=data['timestamp']
            )
            db.close()
            return True
        except Exception as e:
            logger.error(f"Error saving data for {data['symbol']}: {str(e)}")
            return False
    
    def collect_and_save_all(self) -> Dict[str, bool]:
        """
        收集並保存所有標的的數據
        
        Returns:
            Dict mapping symbol to success status
        """
        results = {}
        logger.info(f"開始收集 {len(self.symbols)} 個標的的數據: {self.symbols}")
        all_data = self.fetch_all_stocks()
        logger.info(f"成功獲取 {len(all_data)} 個標的的數據")
        
        if len(all_data) == 0:
            logger.warning(f"沒有獲取到任何數據，檢查網絡連接或標的是否正確")
        
        for data in all_data:
            symbol = data['symbol']
            success = self.save_stock_data(data)
            results[symbol] = success
            if success:
                logger.info(f"Successfully collected and saved data for {symbol}")
            else:
                logger.error(f"Failed to save data for {symbol}")
        
        return results
    
    def fetch_and_save_historical_data(self, symbol: str, days: int = 365, 
                                       start_date: datetime = None, 
                                       end_date: datetime = None) -> int:
        """
        獲取並保存歷史數據
        
        Args:
            symbol: 股票代號
            days: 要獲取的天數，默認365天（如果指定了 start_date 和 end_date 則忽略）
            start_date: 開始日期（可選）
            end_date: 結束日期（可選，默認為今天）
        
        Returns:
            成功保存的數據點數量
        """
        try:
            import yfinance as yf
            from datetime import datetime, timedelta
            
            # 如果指定了日期範圍，使用指定的範圍
            if start_date and end_date:
                logger.info(f"開始獲取 {symbol} 的歷史數據（{start_date.date()} 到 {end_date.date()}）...")
            elif start_date:
                end_date = datetime.now()
                logger.info(f"開始獲取 {symbol} 的歷史數據（從 {start_date.date()} 到 {end_date.date()}）...")
            else:
                # 計算日期範圍
                end_date = datetime.now()
                start_date = end_date - timedelta(days=days)
                logger.info(f"開始獲取 {symbol} 的歷史數據（{days} 天）...")
            
            # 獲取歷史數據
            ticker = yf.Ticker(symbol)
            hist = ticker.history(start=start_date.strftime('%Y-%m-%d'), 
                                 end=(end_date + timedelta(days=1)).strftime('%Y-%m-%d'),  # +1 天以包含結束日期
                                 interval='1d')
            
            if hist.empty:
                logger.warning(f"{symbol}: 無法獲取歷史數據")
                return 0
            
            logger.info(f"{symbol}: 獲取到 {len(hist)} 條歷史數據")
            
            # 先獲取現有記錄的日期集合（用於去重）
            db = get_db_sync()
            from app.models.stock import StockPrice
            from sqlalchemy import func
            existing_dates = set()
            existing_records = db.query(
                func.date(StockPrice.timestamp).label('date')
            ).filter(StockPrice.symbol == symbol).all()
            existing_dates = {record.date for record in existing_records}
            
            # 保存每一筆數據
            saved_count = 0
            skipped_count = 0
            
            for date, row in hist.iterrows():
                try:
                    # 轉換時區感知的時間戳為 naive datetime
                    if hasattr(date, 'to_pydatetime'):
                        timestamp = date.to_pydatetime()
                        # 如果是時區感知的，轉換為 UTC naive
                        if timestamp.tzinfo is not None:
                            timestamp = timestamp.replace(tzinfo=None)
                    else:
                        timestamp = datetime.utcnow()
                    
                    # 檢查是否已存在（使用日期部分）
                    date_only = timestamp.date()
                    if date_only in existing_dates:
                        skipped_count += 1
                        continue
                    
                    create_stock_price(
                        db=db,
                        symbol=symbol,
                        open=float(row['Open']),
                        high=float(row['High']),
                        low=float(row['Low']),
                        close=float(row['Close']),
                        volume=int(row['Volume']),
                        adj_close=float(row['Close']),
                        timestamp=timestamp
                    )
                    existing_dates.add(date_only)  # 添加到已存在集合
                    saved_count += 1
                except Exception as e:
                    # 可能是其他錯誤，記錄但繼續
                    logger.debug(f"{symbol} {date}: 跳過: {str(e)}")
                    skipped_count += 1
                    continue
            
            db.close()
            logger.info(f"✓ {symbol}: 成功保存 {saved_count} 筆新數據，跳過 {skipped_count} 筆重複數據")
            return saved_count
            
        except Exception as e:
            logger.error(f"獲取 {symbol} 歷史數據時發生錯誤: {str(e)}", exc_info=True)
            return 0
    
    def import_historical_data_for_all(self, days: int = 365, 
                                       start_date: datetime = None,
                                       end_date: datetime = None) -> Dict[str, int]:
        """
        為所有監控標的導入歷史數據
        
        Args:
            days: 要獲取的天數，默認365天（如果指定了 start_date 和 end_date 則忽略）
            start_date: 開始日期（可選）
            end_date: 結束日期（可選，默認為今天）
        
        Returns:
            每個標的保存的數據點數量字典
        """
        results = {}
        for symbol in self.symbols:
            count = self.fetch_and_save_historical_data(symbol, days, start_date, end_date)
            results[symbol] = count
            # 在每個請求之間添加延遲
            if symbol != self.symbols[-1]:  # 不是最後一個
                time.sleep(2)  # 2秒延遲避免速率限制
        return results
    
    def get_price_change_percent(self, symbol: str) -> Optional[float]:
        """
        計算價格變動百分比（與上一次記錄比較）
        
        Returns:
            Price change percentage or None
        """
        try:
            db = get_db_sync()
            latest = get_latest_price(db, symbol)
            db.close()
            
            if not latest:
                return None
            
            # 獲取當前價格
            current_data = self.fetch_stock_data(symbol)
            if not current_data:
                return None
            
            current_price = current_data['close']
            previous_price = latest.close
            
            if previous_price == 0:
                return None
            
            change_percent = ((current_price - previous_price) / previous_price) * 100
            return change_percent
            
        except Exception as e:
            logger.error(f"Error calculating price change for {symbol}: {str(e)}")
            return None
