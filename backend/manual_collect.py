"""
手動執行數據收集任務
用於本地測試或補抓數據

注意：Railway 部署時不需要此腳本，定時任務會自動執行
"""
import sys
import os

# 添加項目根目錄到 Python 路徑
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.scheduler.tasks import collect_stock_data_job
from app.config import settings
import logging

# 配置日誌（輸出到 stdout，這樣 GitHub Actions 可以看到）
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)  # 確保輸出到 stdout
    ]
)

if __name__ == "__main__":
    logger = logging.getLogger(__name__)
    
    print("=" * 60)
    print("開始執行股票監控任務...")
    print("=" * 60)
    
    # 輸出配置狀態（不輸出敏感信息）
    logger.info("配置檢查:")
    logger.info(f"  監控標的: {settings.MONITORED_SYMBOLS}")
    logger.info(f"  Discord 啟用: {settings.DISCORD_ENABLED}")
    logger.info(f"  Discord Webhook: {'已配置' if settings.DISCORD_WEBHOOK_URL else '未配置'}")
    logger.info(f"  Notion 啟用: {settings.NOTION_ENABLED}")
    logger.info(f"  OpenAI API Key: {'已配置' if settings.OPENAI_API_KEY else '未配置'}")
    print("-" * 60)
    
    try:
        collect_stock_data_job()
        print("=" * 60)
        print("✅ 數據收集任務完成！")
        print("=" * 60)
    except Exception as e:
        logger.error(f"❌ 任務執行失敗: {str(e)}", exc_info=True)
        print("=" * 60)
        print("❌ 任務執行失敗，請查看上面的錯誤信息")
        print("=" * 60)
        sys.exit(1)

