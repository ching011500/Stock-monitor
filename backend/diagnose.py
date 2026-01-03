"""
診斷腳本：檢查系統配置和狀態
用於排查自動化任務未執行的問題
"""
import os
import sys
from pathlib import Path

# 添加項目路徑
sys.path.insert(0, str(Path(__file__).parent))

from app.config import settings
from datetime import datetime, timezone, timedelta, date
from app.scheduler.tasks import is_trading_day

def check_config():
    """檢查配置"""
    print("=" * 60)
    print("📋 配置檢查")
    print("=" * 60)
    
    issues = []
    
    # Discord 配置
    print(f"\n🔔 Discord 通知:")
    print(f"  - 啟用狀態: {settings.DISCORD_ENABLED}")
    print(f"  - Webhook URL: {'已配置' if settings.DISCORD_WEBHOOK_URL else '❌ 未配置'}")
    
    if not settings.DISCORD_ENABLED:
        issues.append("⚠️ Discord 通知未啟用，即使任務執行也不會發送通知")
    elif not settings.DISCORD_WEBHOOK_URL:
        issues.append("❌ Discord Webhook URL 未配置，無法發送通知")
    
    # Notion 配置
    print(f"\n📝 Notion 記錄:")
    print(f"  - 啟用狀態: {settings.NOTION_ENABLED}")
    print(f"  - API Key: {'已配置' if settings.NOTION_API_KEY else '❌ 未配置'}")
    print(f"  - Database ID: {'已配置' if settings.NOTION_DATABASE_ID else '❌ 未配置'}")
    
    # API Keys
    print(f"\n🔑 API Keys:")
    print(f"  - Alpha Vantage: {'已配置' if settings.ALPHA_VANTAGE_API_KEY else '未配置（可選）'}")
    print(f"  - OpenAI: {'已配置' if settings.OPENAI_API_KEY else '❌ 未配置（AI 分析需要）'}")
    
    if not settings.OPENAI_API_KEY:
        issues.append("❌ OpenAI API Key 未配置，AI 分析功能無法使用")
    
    # 監控標的
    print(f"\n📊 監控標的: {settings.MONITORED_SYMBOLS}")
    
    return issues

def check_date_logic():
    """檢查日期邏輯"""
    print("\n" + "=" * 60)
    print("📅 日期邏輯檢查")
    print("=" * 60)
    
    # 獲取台灣時間
    taiwan_tz = timezone(timedelta(hours=8))
    taiwan_now = datetime.now(taiwan_tz)
    taiwan_date = taiwan_now.date()
    
    # 計算美股日期
    us_date = taiwan_date - timedelta(days=1)
    
    print(f"\n當前時間:")
    print(f"  - 台灣時間: {taiwan_now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"  - 台灣日期: {taiwan_date}")
    print(f"  - 美股日期: {us_date}")
    
    # 檢查交易日
    is_trading = is_trading_day(us_date)
    print(f"\n交易日檢查:")
    print(f"  - {us_date} 是交易日: {'✅ 是' if is_trading else '❌ 否'}")
    
    if not is_trading:
        weekday = us_date.weekday()
        if weekday >= 5:
            print(f"  - 原因: 週末（{'週六' if weekday == 5 else '週日'}）")
        else:
            print(f"  - 原因: 美國股市節假日")
    
    # 檢查任務執行時間
    print(f"\n任務執行時間:")
    print(f"  - 調度時間: 每天 UTC 22:00 (台灣時間 06:00)")
    current_hour_tw = taiwan_now.hour
    if current_hour_tw < 6:
        print(f"  - 當前時間: 台灣時間 {current_hour_tw:02d}:00，任務將在 06:00 執行")
    elif current_hour_tw == 6:
        print(f"  - 當前時間: 台灣時間 06:00，任務應該正在執行或剛執行完")
    else:
        print(f"  - 當前時間: 台灣時間 {current_hour_tw:02d}:00，今天的任務應該已經執行（如果今天是交易日）")
    
    return is_trading

def main():
    """主函數"""
    print("\n" + "=" * 60)
    print("🔍 股票監控系統診斷工具")
    print("=" * 60)
    
    issues = check_config()
    is_trading = check_date_logic()
    
    print("\n" + "=" * 60)
    print("💡 建議")
    print("=" * 60)
    
    if issues:
        print("\n發現的問題:")
        for issue in issues:
            print(f"  {issue}")
    else:
        print("\n✅ 配置檢查通過")
    
    if not is_trading:
        print("\n⚠️ 今天不是美股交易日，任務不會執行")
        print("   這是正常的，任務只會在交易日執行")
    else:
        print("\n✅ 今天是交易日，任務應該會執行")
    
    print("\n📌 下一步:")
    print("  1. 確保應用正在運行（檢查 Railway 或本地服務器）")
    print("  2. 檢查應用日誌以查看任務執行情況")
    print("  3. 使用 API 端點手動觸發任務:")
    print("     POST /scheduler/trigger-manual")
    print("  4. 檢查調度器狀態:")
    print("     GET /scheduler/status")
    print("  5. 獲取完整診斷信息:")
    print("     GET /diagnostics")
    print("  6. 測試 Discord 通知:")
    print("     POST /alerts/test-discord")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    main()

