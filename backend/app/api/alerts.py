"""
警報相關 API 路由
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, List
from pydantic import BaseModel

from app.database.database import get_db
from app.database.crud import get_latest_price, get_latest_indicator, get_latest_signal, get_prices_by_symbol
from app.notifications import AlertEngine
from app.config import get_monitored_symbols
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/alerts", tags=["alerts"])


class AlertResponse(BaseModel):
    symbol: str
    price_alerts: List[str]
    indicator_alerts: List[str]
    ai_signal_alerts: List[str]


@router.get("/{symbol}", response_model=AlertResponse)
def check_stock_alerts(symbol: str, db: Session = Depends(get_db)):
    """檢查指定標的的所有警報"""
    alert_engine = AlertEngine()
    alerts = alert_engine.check_all_alerts(symbol.upper())
    
    return AlertResponse(
        symbol=symbol.upper(),
        price_alerts=alerts.get("price", []),
        indicator_alerts=alerts.get("indicator", []),
        ai_signal_alerts=alerts.get("ai_signal", [])
    )


@router.post("/{symbol}/check")
def trigger_alert_check(symbol: str, db: Session = Depends(get_db)):
    """手動觸發指定標的的警報檢查"""
    alert_engine = AlertEngine()
    alerts = alert_engine.check_all_alerts(symbol.upper())
    
    # 更新 Notion 數據
    alert_engine.update_notion_data(symbol.upper())
    
    total_alerts = sum(len(v) for v in alerts.values())
    
    return {
        "message": f"Alert check completed for {symbol}",
        "symbol": symbol.upper(),
        "total_alerts": total_alerts,
        "alerts": alerts
    }


@router.post("/check-all")
def check_all_alerts(db: Session = Depends(get_db)):
    """檢查所有監控標的的警報"""
    symbols = get_monitored_symbols()
    alert_engine = AlertEngine()
    
    results = {}
    total_alerts_count = 0
    
    for symbol in symbols:
        alerts = alert_engine.check_all_alerts(symbol)
        total = sum(len(v) for v in alerts.values())
        total_alerts_count += total
        
        results[symbol] = {
            "total": total,
            "alerts": alerts
        }
        
        # 更新 Notion 數據
        alert_engine.update_notion_data(symbol)
    
    return {
        "message": f"Checked alerts for {len(symbols)} symbols",
        "total_alerts": total_alerts_count,
        "results": results
    }


@router.post("/test-discord")
def test_discord():
    """測試 Discord 通知連接"""
    from app.notifications.discord_notifier import DiscordNotifier
    from app.config import settings
    
    notifier = DiscordNotifier()
    
    if not settings.DISCORD_ENABLED:
        return {
            "success": False,
            "message": "Discord 未啟用。請在 .env 文件中設置 DISCORD_ENABLED=true",
            "enabled": False,
            "webhook_configured": bool(settings.DISCORD_WEBHOOK_URL)
        }
    
    if not settings.DISCORD_WEBHOOK_URL:
        return {
            "success": False,
            "message": "Discord Webhook URL 未配置",
            "enabled": True,
            "webhook_configured": False
        }
    
    # 發送測試消息
    success = notifier.send_message(
        content="🔔 **測試通知**\n這是來自股票監控系統的測試消息。如果你看到這條消息，說明 Discord 通知配置成功！"
    )
    
    return {
        "success": success,
        "message": "測試消息已發送" if success else "發送失敗，請檢查日誌",
        "enabled": True,
        "webhook_configured": True
    }


@router.post("/create-daily-report")
def create_daily_report(db: Session = Depends(get_db)):
    """創建 Notion 每日報告頁面（包含完整技術指標和警報）"""
    try:
        from app.notifications import AlertEngine, ReportGenerator
        from app.config import get_monitored_symbols
        from datetime import datetime
        
        alert_engine = AlertEngine()
        report_generator = ReportGenerator()
        symbols = get_monitored_symbols()
        
        # 收集所有標的的完整數據
        stocks_data = []
        all_prices_list = {}  # 用於計算波動率
        
        for symbol in symbols:
            try:
                price = get_latest_price(db, symbol)
                indicator = get_latest_indicator(db, symbol)
                signal = get_latest_signal(db, symbol)
                
                if price:
                    # 獲取歷史價格用於計算波動率和價格變動
                    prices = get_prices_by_symbol(db, symbol, days=30)
                    all_prices_list[symbol] = [p.close for p in prices]
                    
                    # 計算價格變動（與前一個交易日比較）
                    change_percent = 0.0
                    if len(prices) >= 2:
                        previous_price = prices[-2] if len(prices) >= 2 else None
                        if previous_price:
                            change_percent = ((price.close - previous_price.close) / previous_price.close) * 100
                    
                    # 計算波動率（20日年化）
                    volatility = None
                    if len(prices) >= 20:
                        price_list = [p.close for p in prices[-21:]]  # 需要21個數據點計算20個收益率
                        volatility = report_generator.calculate_volatility(price_list, days=20)
                    
                    # 檢測技術警報
                    alerts = report_generator.detect_technical_alerts(
                        price=price.close,
                        ma20=indicator.ma20 if indicator else None,
                        ma50=indicator.ma50 if indicator else None,
                        rsi=indicator.rsi if indicator else None,
                        volatility=volatility,
                        avg_volatility=None  # 可以後續計算整體平均波動率
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
                logger.error(f"處理標的 {symbol} 時發生錯誤: {str(e)}", exc_info=True)
                continue
        
        if not stocks_data:
            return {
                "success": False,
                "message": "沒有可用的股票數據，請確保數據庫中有價格數據",
                "date": datetime.now().strftime("%Y-%m-%d")
            }
        
        # 計算平均波動率（用於比較）
        all_volatilities = [s.get("volatility") for s in stocks_data if s.get("volatility") is not None]
        avg_volatility = sum(all_volatilities) / len(all_volatilities) if all_volatilities else None
        
        # 更新每個標的的平均波動率參考
        for stock in stocks_data:
            if stock.get("volatility") and avg_volatility:
                # 重新檢測警報，這次包含平均波動率
                stock["alerts"] = report_generator.detect_technical_alerts(
                    price=stock["price"],
                    ma20=stock.get("ma20"),
                    ma50=stock.get("ma50"),
                    rsi=stock.get("rsi"),
                    volatility=stock.get("volatility"),
                    avg_volatility=avg_volatility
                )
        
        # 創建每日報告
        today = datetime.now().strftime("%Y-%m-%d")
        page_id = alert_engine.notion.create_daily_report(today, stocks_data)
        
        if page_id:
            return {
                "success": True,
                "message": f"每日報告創建成功",
                "date": today,
                "page_id": page_id,
                "stocks_count": len(stocks_data)
            }
        else:
            return {
                "success": False,
                "message": "每日報告創建失敗，請檢查 Notion Daily Report Page ID 是否配置正確",
                "date": today
            }
    except Exception as e:
        logger.error(f"創建每日報告時發生錯誤: {str(e)}", exc_info=True)
        return {
            "success": False,
            "message": f"創建每日報告失敗: {str(e)}",
            "error": str(e)
        }


@router.get("/test-notion/database-properties")
def get_notion_database_properties():
    """獲取 Notion 數據庫的所有屬性名稱和類型（用於調試）"""
    from app.notifications.notion_recorder import NotionRecorder
    from app.config import settings
    
    if not settings.NOTION_ENABLED:
        return {
            "success": False,
            "message": "Notion 未啟用",
            "enabled": False
        }
    
    if not settings.NOTION_API_KEY or not settings.NOTION_DATABASE_ID:
        return {
            "success": False,
            "message": "Notion API Key 或 Database ID 未配置",
            "api_key_configured": bool(settings.NOTION_API_KEY),
            "database_id_configured": bool(settings.NOTION_DATABASE_ID)
        }
    
    try:
        recorder = NotionRecorder()
        props = recorder._get_database_properties(settings.NOTION_DATABASE_ID)
        
        if props:
            return {
                "success": True,
                "database_id": settings.NOTION_DATABASE_ID,
                "properties": props,
                "property_names": list(props.keys()),
                "title_property": recorder._get_title_property_name(settings.NOTION_DATABASE_ID)
            }
        else:
            return {
                "success": False,
                "message": "無法獲取數據庫屬性"
            }
    except Exception as e:
        import traceback
        return {
            "success": False,
            "message": f"獲取屬性失敗: {str(e)}",
            "traceback": traceback.format_exc()
        }


@router.post("/update-notion-all")
def update_all_to_notion(db: Session = Depends(get_db)):
    """更新所有監控標的的數據到 Notion"""
    from app.notifications import AlertEngine
    from app.config import get_monitored_symbols
    
    symbols = get_monitored_symbols()
    alert_engine = AlertEngine()
    
    results = {}
    success_count = 0
    
    for symbol in symbols:
        success = alert_engine.update_notion_data(symbol)
        results[symbol] = success
        if success:
            success_count += 1
    
    return {
        "message": f"更新 {success_count}/{len(symbols)} 個標的到 Notion",
        "results": results,
        "total": len(symbols),
        "success": success_count,
        "failed": len(symbols) - success_count
    }


@router.post("/test-notion/{symbol}")
def test_notion(symbol: str, db: Session = Depends(get_db)):
    """測試 Notion 記錄功能"""
    from app.notifications import AlertEngine
    from app.config import settings
    import logging
    
    logger = logging.getLogger(__name__)
    
    if not settings.NOTION_ENABLED:
        return {
            "success": False,
            "message": "Notion 未啟用。請在 .env 文件中設置 NOTION_ENABLED=true",
            "enabled": False
        }
    
    if not settings.NOTION_API_KEY or not settings.NOTION_DATABASE_ID:
        return {
            "success": False,
            "message": "Notion API Key 或 Database ID 未配置",
            "enabled": True,
            "api_key_configured": bool(settings.NOTION_API_KEY),
            "database_id_configured": bool(settings.NOTION_DATABASE_ID)
        }
    
    # 測試更新 Notion 數據
    try:
        alert_engine = AlertEngine()
        success = alert_engine.update_notion_data(symbol.upper())
        
        error_msg = "未知錯誤"
        if not success:
            # 嘗試獲取更詳細的錯誤信息
            try:
                # 直接測試 NotionRecorder
                from app.notifications.notion_recorder import NotionRecorder
                recorder = NotionRecorder()
                # 測試獲取數據庫屬性
                props = recorder._get_database_properties(settings.NOTION_DATABASE_ID)
                if props:
                    error_msg = f"更新失敗，數據庫屬性: {list(props.keys())[:5]}"
                else:
                    error_msg = "無法獲取數據庫屬性"
            except Exception as e:
                error_msg = f"錯誤: {str(e)}"
        
        return {
            "success": success,
            "message": f"Notion 數據更新{'成功' if success else '失敗: ' + error_msg}",
            "symbol": symbol.upper(),
            "enabled": True
        }
    except Exception as e:
        logger.error(f"測試 Notion 記錄時發生錯誤: {str(e)}", exc_info=True)
        import traceback
        return {
            "success": False,
            "message": f"測試失敗: {str(e)}",
            "symbol": symbol.upper(),
            "enabled": True,
            "traceback": traceback.format_exc()
        }
