"""
數據庫連接和初始化
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
import os

from app.config import settings
from app.models.stock import Base


# 確保數據目錄存在
db_path = settings.DATABASE_URL.replace("sqlite:///", "")
if db_path != ":memory:":
    db_dir = os.path.dirname(db_path)
    if db_dir:  # 如果有目錄路徑
        os.makedirs(db_dir, exist_ok=True)

# 創建數據庫引擎
if settings.DATABASE_URL.startswith("sqlite"):
    engine = create_engine(
        settings.DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=False
    )
else:
    engine = create_engine(settings.DATABASE_URL, echo=False)

# 創建 SessionLocal 類
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def init_db():
    """初始化數據庫，創建所有表"""
    Base.metadata.create_all(bind=engine)


def get_db() -> Session:
    """獲取數據庫會話"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_db_sync() -> Session:
    """同步獲取數據庫會話（用於非 async 場景）"""
    return SessionLocal()


