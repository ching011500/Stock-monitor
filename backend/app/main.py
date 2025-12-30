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


