"""
手動執行數據收集任務
用於測試或補抓數據
"""
import sys
import os

# 添加項目根目錄到 Python 路徑
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.scheduler.tasks import collect_stock_data_job
import logging

# 配置日誌
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

if __name__ == "__main__":
    print("開始手動執行數據收集任務...")
    collect_stock_data_job()
    print("數據收集任務完成！")

