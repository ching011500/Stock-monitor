"""
配置管理模組
"""
import os
from pathlib import Path
from typing import Optional, List
from pydantic_settings import BaseSettings


# 獲取項目根目錄（從 backend/app/config.py 向上兩級）
BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_FILE = BASE_DIR / ".env"


class Settings(BaseSettings):
    """應用配置"""
    
    # API Keys
    ALPHA_VANTAGE_API_KEY: Optional[str] = None
    YAHOO_FINANCE_ENABLED: bool = True
    OPENAI_API_KEY: Optional[str] = None
    
    # 數據庫
    DATABASE_URL: str = "sqlite:///./data/stocks.db"
    
    # Discord 通知
    DISCORD_WEBHOOK_URL: Optional[str] = None
    DISCORD_ENABLED: bool = False
    
    # Notion 記錄
    NOTION_API_KEY: Optional[str] = None
    NOTION_DATABASE_ID: Optional[str] = None
    NOTION_DAILY_REPORT_PAGE_ID: Optional[str] = None
    NOTION_ENABLED: bool = False
    
    # GitHub 圖片上傳（用於圖表）
    GITHUB_TOKEN: Optional[str] = None
    GITHUB_REPO_OWNER: Optional[str] = None  # 例如: "username"
    GITHUB_REPO_NAME: Optional[str] = None  # 例如: "stock-monitor"
    GITHUB_BRANCH: str = "main"  # 默認分支
    GITHUB_CHART_PATH: str = "charts"  # 圖表存儲路徑
    
    # 應用配置
    UPDATE_INTERVAL: int = 60  # 秒
    INDICATOR_INTERVAL: int = 300  # 秒
    AI_ANALYSIS_INTERVAL: int = 900  # 秒
    
    # 監控標的
    MONITORED_SYMBOLS: str = "QQQ,SMH,TSLA,NVDA"
    
    class Config:
        env_file = str(ENV_FILE) if ENV_FILE.exists() else ".env"
        env_file_encoding = "utf-8"


settings = Settings()


def get_monitored_symbols() -> List[str]:
    """獲取監控標的列表"""
    return [s.strip() for s in settings.MONITORED_SYMBOLS.split(",") if s.strip()]

