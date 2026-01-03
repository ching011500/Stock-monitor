"""
FastAPI 主應用
"""
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import traceback

from app.config import settings
from app.database.database import init_db
from app.api import stocks, indicators, alerts, signals
from app.scheduler.tasks import setup_scheduler

# 配置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 創建 FastAPI 應用
app = FastAPI(
    title="Stock Monitor API",
    description="股票投資監控系統 API",
    version="1.0.0"
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生產環境應設置具體的域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 註冊路由
app.include_router(stocks.router)
app.include_router(indicators.router)
app.include_router(signals.router)
app.include_router(alerts.router)


# 全局異常處理
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """全局異常處理器"""
    logger.error(f"未處理的異常: {str(exc)}")
    logger.error(traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": str(exc),
            "path": str(request.url)
        }
    )


# 全局調度器
scheduler = None


@app.on_event("startup")
async def startup_event():
    """應用啟動時執行"""
    global scheduler
    
    logger.info("Initializing database...")
    init_db()
    logger.info("Database initialized")
    logger.info(f"Monitoring symbols: {settings.MONITORED_SYMBOLS}")
    
    # 設置定時任務
    logger.info("Setting up scheduled tasks...")
    scheduler = setup_scheduler()
    scheduler.start()
    logger.info("Scheduled tasks started")
    
    # 顯示下次執行時間
    jobs = scheduler.get_jobs()
    if jobs:
        job = jobs[0]
        # 使用 hasattr 檢查屬性是否存在，因為在調度器啟動後才會計算
        if hasattr(job, 'next_run_time') and job.next_run_time:
            logger.info(f"Next scheduled run: {job.next_run_time} (UTC)")


@app.on_event("shutdown")
async def shutdown_event():
    """應用關閉時執行"""
    global scheduler
    if scheduler:
        logger.info("Shutting down scheduler...")
        scheduler.shutdown()
        logger.info("Scheduler shut down")


@app.get("/")
def root():
    """根路徑"""
    return {
        "message": "Stock Monitor API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
def health_check():
    """健康檢查"""
    return {"status": "healthy"}


@app.get("/scheduler/status")
def get_scheduler_status():
    """檢查調度器狀態"""
    global scheduler
    
    if not scheduler:
        return {
            "status": "not_initialized",
            "message": "調度器尚未初始化",
            "running": False
        }
    
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "name": job.name,
            "next_run_time": str(job.next_run_time) if job.next_run_time else None,
            "trigger": str(job.trigger)
        })
    
    return {
        "status": "running" if scheduler.running else "stopped",
        "running": scheduler.running,
        "jobs": jobs,
        "jobs_count": len(jobs)
    }


@app.post("/scheduler/trigger-manual")
def trigger_manual_job():
    """手動觸發完整的自動化任務（用於測試和診斷）"""
    from app.scheduler.tasks import collect_stock_data_job
    import threading
    
    # 在後台線程中執行，避免阻塞 API
    thread = threading.Thread(target=collect_stock_data_job, daemon=True)
    thread.start()
    
    return {
        "message": "手動任務已觸發，正在後台執行",
        "status": "started",
        "note": "請查看日誌以獲取執行結果"
    }


@app.get("/scheduler/recent-activity")
def get_recent_activity():
    """檢查最近的任務執行情況（通過檢查數據庫中的最新數據）"""
    from app.database.database import get_db_sync
    from app.database.crud import get_latest_price, get_latest_signal, get_latest_indicator
    from app.config import get_monitored_symbols
    from datetime import datetime, timezone, timedelta
    
    db = get_db_sync()
    symbols = get_monitored_symbols()
    
    # 獲取台灣時間
    taiwan_tz = timezone(timedelta(hours=8))
    taiwan_now = datetime.now(taiwan_tz)
    today = taiwan_now.date()
    
    activity = {}
    
    try:
        for symbol in symbols:
            price = get_latest_price(db, symbol)
            signal = get_latest_signal(db, symbol)
            indicator = get_latest_indicator(db, symbol)
            
            symbol_activity = {
                "symbol": symbol,
                "has_price_data": price is not None,
                "has_signal_data": signal is not None,
                "has_indicator_data": indicator is not None
            }
            
            if price:
                price_date = price.timestamp.date()
                hours_ago = (taiwan_now.date() - price_date).days
                symbol_activity["latest_price_date"] = str(price_date)
                symbol_activity["latest_price"] = price.close
                symbol_activity["price_age_days"] = hours_ago
                symbol_activity["price_is_today"] = price_date == today or price_date == (today - timedelta(days=1))
            
            if signal:
                signal_date = signal.timestamp.date()
                symbol_activity["latest_signal_date"] = str(signal_date)
                symbol_activity["latest_signal"] = signal.signal
                symbol_activity["signal_age_days"] = (taiwan_now.date() - signal_date).days
                symbol_activity["signal_is_today"] = signal_date == today or signal_date == (today - timedelta(days=1))
            
            if indicator:
                indicator_date = indicator.timestamp.date()
                symbol_activity["latest_indicator_date"] = str(indicator_date)
                symbol_activity["indicator_age_days"] = (taiwan_now.date() - indicator_date).days
                symbol_activity["indicator_is_today"] = indicator_date == today or indicator_date == (today - timedelta(days=1))
            
            activity[symbol] = symbol_activity
        
        # 計算整體狀態
        all_have_data = all(a["has_price_data"] for a in activity.values())
        all_recent = all(
            a.get("price_is_today", False) or a.get("signal_is_today", False) 
            for a in activity.values() 
            if a["has_price_data"] or a["has_signal_data"]
        )
        
        return {
            "current_time": taiwan_now.strftime("%Y-%m-%d %H:%M:%S %Z"),
            "today": str(today),
            "all_symbols_have_data": all_have_data,
            "all_data_is_recent": all_recent,
            "activity": activity,
            "summary": {
                "total_symbols": len(symbols),
                "symbols_with_price": sum(1 for a in activity.values() if a["has_price_data"]),
                "symbols_with_signal": sum(1 for a in activity.values() if a["has_signal_data"]),
                "symbols_with_recent_data": sum(1 for a in activity.values() if a.get("price_is_today", False) or a.get("signal_is_today", False))
            }
        }
    finally:
        db.close()


@app.get("/diagnostics")
def get_diagnostics():
    """獲取系統診斷信息"""
    from datetime import datetime, timezone, timedelta
    from app.config import settings
    from app.scheduler.tasks import is_trading_day
    
    # 獲取台灣時間
    taiwan_tz = timezone(timedelta(hours=8))
    taiwan_now = datetime.now(taiwan_tz)
    taiwan_date = taiwan_now.date()
    
    # 計算美股日期
    us_date = taiwan_date - timedelta(days=1)
    
    # 檢查調度器狀態
    global scheduler
    scheduler_status = {
        "initialized": scheduler is not None,
        "running": scheduler.running if scheduler else False,
        "jobs_count": len(scheduler.get_jobs()) if scheduler else 0
    }
    
    # 檢查配置
    config_status = {
        "discord_enabled": settings.DISCORD_ENABLED,
        "discord_webhook_configured": bool(settings.DISCORD_WEBHOOK_URL),
        "notion_enabled": settings.NOTION_ENABLED,
        "notion_api_key_configured": bool(settings.NOTION_API_KEY),
        "notion_database_id_configured": bool(settings.NOTION_DATABASE_ID),
        "monitored_symbols": settings.MONITORED_SYMBOLS,
        "alpha_vantage_key_configured": bool(settings.ALPHA_VANTAGE_API_KEY),
        "openai_key_configured": bool(settings.OPENAI_API_KEY)
    }
    
    # 檢查日期和交易日
    date_info = {
        "taiwan_time": taiwan_now.strftime("%Y-%m-%d %H:%M:%S %Z"),
        "taiwan_date": str(taiwan_date),
        "us_date": str(us_date),
        "is_us_trading_day": is_trading_day(us_date),
        "start_date": "已移除（任務會持續運行）",
        "is_after_start_date": True
    }
    
    # 檢查任務是否應該執行
    should_run = (
        date_info["is_after_start_date"] and
        date_info["is_us_trading_day"] and
        scheduler_status["running"]
    )
    
    return {
        "timestamp": datetime.now().isoformat(),
        "scheduler": scheduler_status,
        "config": config_status,
        "date_info": date_info,
        "should_run_today": should_run,
        "recommendations": _get_recommendations(config_status, scheduler_status, date_info, should_run)
    }


def _get_recommendations(config_status, scheduler_status, date_info, should_run):
    """生成診斷建議"""
    recommendations = []
    
    if not scheduler_status["initialized"]:
        recommendations.append("❌ 調度器未初始化，請重啟應用")
    elif not scheduler_status["running"]:
        recommendations.append("❌ 調度器未運行，請檢查應用日誌")
    
    if not config_status["discord_enabled"]:
        recommendations.append("⚠️ Discord 通知未啟用，即使任務執行也不會發送通知")
    elif not config_status["discord_webhook_configured"]:
        recommendations.append("❌ Discord Webhook URL 未配置，無法發送通知")
    
    if not date_info["is_after_start_date"]:
        recommendations.append(f"ℹ️ 當前日期早於開始日期 {date_info['start_date']}，任務不會執行")
    
    if not date_info["is_us_trading_day"]:
        recommendations.append(f"ℹ️ {date_info['us_date']} 不是美股交易日，任務會跳過")
    
    if not should_run and scheduler_status["running"]:
        recommendations.append("💡 使用 POST /scheduler/trigger-manual 手動觸發任務進行測試")
    
    if not recommendations:
        recommendations.append("✅ 系統配置正常，任務應該會自動執行")
    
    return recommendations


