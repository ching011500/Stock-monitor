#!/usr/bin/env python3
"""
清理數據庫中的重複記錄
"""
import sys
import os

# 添加項目路徑
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.database.database import get_db_sync
from app.database.crud import remove_duplicate_stock_prices, remove_duplicate_indicators
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    """清理重複數據"""
    db = get_db_sync()
    
    try:
        logger.info("開始清理重複的股票價格記錄...")
        price_count = remove_duplicate_stock_prices(db)
        logger.info(f"✓ 已刪除 {price_count} 筆重複的股票價格記錄")
        
        logger.info("開始清理重複的技術指標記錄...")
        indicator_count = remove_duplicate_indicators(db)
        logger.info(f"✓ 已刪除 {indicator_count} 筆重複的技術指標記錄")
        
        logger.info("清理完成！")
        
    except Exception as e:
        logger.error(f"清理過程中發生錯誤: {str(e)}", exc_info=True)
        return 1
    finally:
        db.close()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

