"""
定時任務
從 2025/12/31 台灣時間早上 6:00 開始，每個交易日自動收集股票數據
第一天：12/31 台灣時間早上 6 點收集 12/30 美股的數據
"""
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, date
import logging
from typing import List

from app.data_collection import DataCollector
from app.technical_indicators import IndicatorCalculator
from app.ai_analysis import AIAnalyzer
from app.notifications import AlertEngine
from app.config import settings

logger = logging.getLogger(__name__)

# 美國股市交易日（排除節假日）
# 注意：這裡只排除週末，實際節假日需要根據美國股市日曆調整
US_MARKET_HOLIDAYS_2026 = [
    date(2026, 1, 1),   # New Year's Day
    date(2026, 1, 19),  # Martin Luther King Jr. Day
    date(2026, 2, 16),  # Presidents' Day
    date(2026, 4, 3),   # Good Friday
    date(2026, 5, 25),  # Memorial Day
    date(2026, 7, 3),   # Independence Day (observed)
    date(2026, 9, 7),   # Labor Day
    date(2026, 11, 26), # Thanksgiving
    date(2026, 11, 27), # Day after Thanksgiving
    date(2026, 12, 24), # Christmas Eve (early close)
    date(2026, 12, 25), # Christmas Day
]


def is_trading_day(check_date: date) -> bool:
    """
    判斷是否為交易日
    
    Args:
        check_date: 要檢查的日期
    
    Returns:
        True 如果是交易日，False 如果不是
    """
    # 檢查是否為週末（週六=5, 週日=6）
    if check_date.weekday() >= 5:
        return False
    
    # 檢查是否為節假日
    if check_date in US_MARKET_HOLIDAYS_2026:
        return False
    
    return True


def collect_stock_data_job():
    """
    定時任務：收集所有股票數據
    只在交易日執行
    
    時間邏輯：
    - 任務在 UTC 22:00 執行（台灣時間 06:00）
    - 台灣時間早上 6 點時，美國還是前一天
    - 例如：12/31 台灣時間早上 6 點收集 12/30 美股的數據
    """
    from datetime import timezone, timedelta
    
    # 獲取台灣時間（UTC+8）
    taiwan_tz = timezone(timedelta(hours=8))
    taiwan_now = datetime.now(taiwan_tz)
    taiwan_date = taiwan_now.date()
    
    # 台灣時間早上 6:00 時執行，收集的是前一個交易日美股的數據
    # 例如：12/31 台灣時間早上 6 點收集 12/30 美股的數據
    check_date = taiwan_date
    
    logger.info(f"任務執行時間：台灣時間 {taiwan_now.strftime('%Y-%m-%d %H:%M:%S')} (UTC {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')})")
    
    # 計算美股日期（台灣時間早上 6 點時，美國還是前一天）
    # 台灣時間 = UTC+8，美國東部時間 = UTC-5（或 UTC-4，看是否夏令時）
    # 台灣時間早上 6:00 = UTC 22:00（前一天）= 美國時間前一天晚上
    # 例如：台灣時間 12/31 早上 6 點 = 美國時間 12/30 晚上，收集 12/30 的數據
    us_date = (check_date - timedelta(days=1))  # 美股日期是台灣時間的前一天
    
    # 檢查美股日期是否為交易日
    if not is_trading_day(us_date):
        logger.info(f"{us_date} (美股日期) 不是交易日，跳過數據收集")
        return
    
    logger.info(f"開始執行交易日數據收集任務 (台灣時間 {check_date}，收集美股 {us_date} 的數據)...")
    
    try:
        collector = DataCollector()
        results = collector.collect_and_save_all()
        
        success_count = sum(1 for v in results.values() if v)
        total_count = len(results)
        
        logger.info(f"數據收集完成: {success_count}/{total_count} 個標的成功")
        
        # 記錄失敗的標的
        failed = [symbol for symbol, success in results.items() if not success]
        if failed:
            logger.warning(f"以下標的收集失敗: {failed}")
        
        # 收集數據後，自動計算技術指標
        logger.info("開始計算技術指標...")
        try:
            calculator = IndicatorCalculator()
            # 只計算成功收集數據的標的
            successful_symbols = [symbol for symbol, success in results.items() if success]
            if successful_symbols:
                indicator_results = calculator.calculate_and_save_all_indicators(successful_symbols)
                indicator_success_count = sum(1 for v in indicator_results.values() if v)
                logger.info(f"技術指標計算完成: {indicator_success_count}/{len(indicator_results)} 個標的成功")
                
                indicator_failed = [symbol for symbol, success in indicator_results.items() if not success]
                if indicator_failed:
                    logger.warning(f"以下標的指標計算失敗: {indicator_failed}")
                
                # 指標計算完成後，自動進行 AI 分析
                logger.info("開始進行 AI 分析...")
                try:
                    analyzer = AIAnalyzer()
                    # 只分析成功計算指標的標的
                    successful_indicator_symbols = [symbol for symbol, success in indicator_results.items() if success]
                    if successful_indicator_symbols:
                        ai_results = analyzer.analyze_all(successful_indicator_symbols)
                        ai_success_count = sum(1 for v in ai_results.values() if v)
                        logger.info(f"AI 分析完成: {ai_success_count}/{len(ai_results)} 個標的成功")
                        
                        ai_failed = [symbol for symbol, success in ai_results.items() if not success]
                        if ai_failed:
                            logger.warning(f"以下標的 AI 分析失敗: {ai_failed}")
                        
                        # AI 分析完成後，檢查警報、發送 Discord 通知並更新 Notion
                        logger.info("開始檢查警報、發送 Discord 通知並更新 Notion...")
                        try:
                            alert_engine = AlertEngine()
                            # 只處理成功完成 AI 分析的標的
                            successful_ai_symbols = [symbol for symbol, success in ai_results.items() if success]
                            
                            for symbol in successful_ai_symbols:
                                try:
                                    # 檢查所有類型的警報（會自動發送 Discord 通知）
                                    alerts = alert_engine.check_all_alerts(symbol)
                                    
                                    # 更新 Notion 數據
                                    notion_success = alert_engine.update_notion_data(symbol)
                                    if notion_success:
                                        logger.info(f"{symbol}: Notion 數據更新成功")
                                    else:
                                        logger.warning(f"{symbol}: Notion 數據更新失敗")
                                    
                                    # 記錄觸發的警報（Discord 通知已經在 check_all_alerts 中發送）
                                    total_alerts = sum(len(v) for v in alerts.values())
                                    if total_alerts > 0:
                                        logger.info(f"{symbol} 觸發 {total_alerts} 個警報: {alerts}")
                                    else:
                                        logger.info(f"{symbol}: AI 分析完成，Discord 通知已發送，Notion 已更新（無特殊警報）")
                                except Exception as e:
                                    logger.error(f"處理 {symbol} 的警報和通知時發生錯誤: {str(e)}", exc_info=True)
                                    continue
                                
                            logger.info(f"✅ 完成 {len(successful_ai_symbols)} 個標的的警報檢查、Discord 通知和 Notion 更新")
                            
                            # 創建 Notion 每日報告
                            logger.info("開始創建 Notion 每日報告...")
                            try:
                                from app.database.database import get_db_sync
                                from app.database.crud import get_latest_price, get_latest_indicator, get_latest_signal, get_prices_by_symbol
                                from app.notifications.report_generator import ReportGenerator
                                
                                db = get_db_sync()
                                report_generator = ReportGenerator()
                                stocks_data = []
                                
                                try:
                                    for symbol in successful_ai_symbols:
                                        try:
                                            price = get_latest_price(db, symbol)
                                            indicator = get_latest_indicator(db, symbol)
                                            signal = get_latest_signal(db, symbol)
                                            
                                            if price:
                                                # 獲取歷史價格用於計算波動率和價格變動
                                                prices = get_prices_by_symbol(db, symbol, days=30)
                                                
                                                # 計算價格變動（與前一個交易日比較）
                                                change_percent = 0.0
                                                if len(prices) >= 2:
                                                    previous_price = prices[-2] if len(prices) >= 2 else None
                                                    if previous_price:
                                                        change_percent = ((price.close - previous_price.close) / previous_price.close) * 100
                                                
                                                # 計算波動率（20日年化）
                                                volatility = None
                                                if len(prices) >= 20:
                                                    price_list = [p.close for p in prices[-21:]]
                                                    volatility = report_generator.calculate_volatility(price_list, days=20)
                                                
                                                # 檢測技術警報
                                                alerts = report_generator.detect_technical_alerts(
                                                    price=price.close,
                                                    ma20=indicator.ma20 if indicator else None,
                                                    ma50=indicator.ma50 if indicator else None,
                                                    rsi=indicator.rsi if indicator else None,
                                                    volatility=volatility,
                                                    avg_volatility=None
                                                )
                                                
                                                # 檢查警報引擎的警報
                                                alert_result = alert_engine.check_all_alerts(symbol)
                                                all_alerts = []
                                                all_alerts.extend(alert_result.get("price", []))
                                                all_alerts.extend(alert_result.get("indicator", []))
                                                all_alerts.extend(alert_result.get("ai_signal", []))
                                                
                                                # 合併技術警報和引擎警報
                                                if all_alerts:
                                                    alerts.extend([a for a in all_alerts if a not in alerts])
                                                
                                                stocks_data.append({
                                                    "symbol": symbol,
                                                    "price": price.close,
                                                    "change_percent": change_percent,
                                                    "ma20": indicator.ma20 if indicator else None,
                                                    "ma50": indicator.ma50 if indicator else None,
                                                    "rsi": indicator.rsi if indicator else None,
                                                    "volatility": volatility,
                                                    "alerts": alerts,
                                                    "ai_signal": signal.signal if signal else "HOLD",
                                                    "risk_level": signal.risk_level if signal else "MEDIUM",
                                                })
                                        except Exception as e:
                                            logger.error(f"收集標的 {symbol} 的報告數據時發生錯誤: {str(e)}", exc_info=True)
                                            continue
                                    
                                    if stocks_data:
                                        # 計算平均波動率（用於比較）
                                        all_volatilities = [s.get("volatility") for s in stocks_data if s.get("volatility") is not None]
                                        avg_volatility = sum(all_volatilities) / len(all_volatilities) if all_volatilities else None
                                        
                                        # 更新每個標的的平均波動率參考
                                        for stock in stocks_data:
                                            if stock.get("volatility") and avg_volatility:
                                                stock["alerts"] = report_generator.detect_technical_alerts(
                                                    price=stock["price"],
                                                    ma20=stock.get("ma20"),
                                                    ma50=stock.get("ma50"),
                                                    rsi=stock.get("rsi"),
                                                    volatility=stock.get("volatility"),
                                                    avg_volatility=avg_volatility
                                                )
                                        
                                        # 創建每日報告（使用台灣時間日期）
                                        report_date = taiwan_date.strftime("%Y-%m-%d")
                                        page_id = alert_engine.notion.create_daily_report(report_date, stocks_data)
                                        
                                        if page_id:
                                            logger.info(f"✅ Notion 每日報告創建成功 (日期: {report_date}, 頁面 ID: {page_id})")
                                        else:
                                            logger.warning(f"⚠️ Notion 每日報告創建失敗 (日期: {report_date})，請檢查配置")
                                    else:
                                        logger.warning("沒有可用的股票數據，跳過創建每日報告")
                                finally:
                                    db.close()
                            except Exception as e:
                                logger.error(f"創建 Notion 每日報告時發生錯誤: {str(e)}", exc_info=True)
                            
                            # 總結報告
                            logger.info("=" * 60)
                            logger.info(f"📊 交易日數據處理完成總結 (美股日期: {us_date})")
                            logger.info(f"  - 數據收集: {success_count}/{total_count} 成功")
                            logger.info(f"  - 技術指標: {indicator_success_count}/{len(indicator_results)} 成功")
                            logger.info(f"  - AI 分析: {ai_success_count}/{len(ai_results)} 成功")
                            logger.info(f"  - Discord 通知: {len(successful_ai_symbols)} 個標的已發送")
                            logger.info(f"  - Notion 更新: {len(successful_ai_symbols)} 個標的已更新")
                            logger.info(f"  - Notion 每日報告: 已創建")
                            logger.info("=" * 60)
                        except Exception as e:
                            logger.error(f"警報檢查和通知發送失敗: {str(e)}", exc_info=True)
                    else:
                        logger.warning("沒有成功計算指標的標的，跳過 AI 分析")
                except Exception as e:
                    logger.error(f"AI 分析任務執行失敗: {str(e)}", exc_info=True)
            else:
                logger.warning("沒有成功收集數據的標的，跳過指標計算")
        except Exception as e:
            logger.error(f"技術指標計算任務執行失敗: {str(e)}", exc_info=True)
            
    except Exception as e:
        logger.error(f"數據收集任務執行失敗: {str(e)}", exc_info=True)


def setup_scheduler() -> BackgroundScheduler:
    """
    設置定時任務調度器
    
    Returns:
        配置好的調度器
    """
    scheduler = BackgroundScheduler()
    
    # 設置任務：台灣時間早上 6:00 執行
    # 台灣時間 (UTC+8) 早上 6:00 = UTC 22:00 (前一天晚上)
    # 例如：台灣時間 2026/1/2 06:00 = UTC 2026/1/1 22:00
    scheduler.add_job(
        collect_stock_data_job,
        trigger=CronTrigger(
            day_of_week='mon-fri',  # 週一到週五
            hour=22,  # UTC 22:00 = 台灣時間 06:00 (第二天早上)
            minute=0,
            timezone='UTC'
            # 不設置 start_date，讓任務立即開始運行（根據 day_of_week 和 hour 自動計算下次執行時間）
        ),
        id='collect_stocks_daily',
        name='收集股票數據（台灣時間早上 6:00）',
        replace_existing=True
    )
    
    logger.info("定時任務已設置：")
    logger.info("  - 執行時間：每個工作日 UTC 22:00 (台灣時間 06:00)")
    logger.info("  - 自動跳過週末和節假日")
    
    # 顯示下次執行時間（需要先啟動調度器才能計算）
    # 注意：這裡不顯示，因為調度器還沒啟動，會在 main.py 啟動後顯示
    
    return scheduler
