"""
檢查通知狀態的腳本
診斷為什麼沒有收到通知
"""
import sys
from pathlib import Path

# 添加項目路徑
sys.path.insert(0, str(Path(__file__).parent))

from app.database.database import get_db_sync
from app.database.crud import get_latest_price, get_latest_signal, get_latest_indicator
from app.config import settings
from app.notifications.alert_engine import AlertEngine
from datetime import datetime, timedelta

def check_notification_status():
    """檢查通知狀態"""
    print("=" * 60)
    print("🔔 通知狀態檢查")
    print("=" * 60)
    
    # 檢查 Discord 配置
    print("\n1. Discord 配置檢查:")
    print(f"   - DISCORD_ENABLED: {settings.DISCORD_ENABLED}")
    print(f"   - DISCORD_WEBHOOK_URL: {'已配置' if settings.DISCORD_WEBHOOK_URL else '❌ 未配置'}")
    
    if not settings.DISCORD_ENABLED:
        print("   ⚠️  Discord 通知未啟用！這是沒有收到通知的主要原因。")
        return
    
    if not settings.DISCORD_WEBHOOK_URL:
        print("   ❌ Discord Webhook URL 未配置！無法發送通知。")
        return
    
    # 檢查數據庫中的數據
    print("\n2. 數據庫狀態檢查:")
    db = get_db_sync()
    
    try:
        symbols = [s.strip() for s in settings.MONITORED_SYMBOLS.split(",") if s.strip()]
        print(f"   監控標的: {', '.join(symbols)}")
        
        has_data = False
        has_signals = False
        
        for symbol in symbols:
            price = get_latest_price(db, symbol)
            signal = get_latest_signal(db, symbol)
            indicator = get_latest_indicator(db, symbol)
            
            if price:
                has_data = True
                price_age = datetime.utcnow() - price.timestamp.replace(tzinfo=None)
                print(f"\n   {symbol}:")
                print(f"     - 最新價格: ${price.close:.2f} (時間: {price.timestamp})")
                print(f"     - 數據年齡: {price_age}")
                
                if signal:
                    has_signals = True
                    signal_age = datetime.utcnow() - signal.timestamp.replace(tzinfo=None)
                    print(f"     - ✅ AI 訊號: {signal.signal} (置信度: {signal.confidence*100:.1f}%)")
                    print(f"     - 訊號時間: {signal.timestamp} (年齡: {signal_age})")
                else:
                    print(f"     - ❌ 沒有 AI 訊號（這是沒有通知的主要原因）")
                
                if indicator:
                    print(f"     - RSI: {indicator.rsi:.2f}" if indicator.rsi else "     - RSI: 無數據")
                else:
                    print(f"     - 技術指標: 無數據")
            else:
                print(f"\n   {symbol}: ❌ 沒有價格數據")
        
        if not has_data:
            print("\n   ⚠️  數據庫中沒有任何價格數據")
            print("   建議: 運行數據收集任務或手動收集數據")
            return
        
        if not has_signals:
            print("\n   ⚠️  數據庫中沒有任何 AI 訊號")
            print("   可能原因:")
            print("   1. AI 分析未執行")
            print("   2. AI 分析失敗（檢查 OpenAI API Key）")
            print("   3. 任務未運行")
            return
        
        # 測試通知邏輯
        print("\n3. 通知邏輯測試:")
        alert_engine = AlertEngine()
        
        for symbol in symbols:
            signal = get_latest_signal(db, symbol)
            if signal:
                print(f"\n   {symbol}:")
                print(f"     - AI 訊號: {signal.signal}")
                
                # 檢查是否會發送通知
                # 根據代碼邏輯，如果沒有 signal，check_ai_signal_alerts 會返回空列表且不發送通知
                # 如果有 signal（包括 HOLD），應該會發送通知
                
                if signal.signal == "HOLD":
                    print(f"     - 📢 應該會發送通知（HOLD 訊號也會發送）")
                else:
                    print(f"     - 📢 應該會發送通知（{signal.signal} 訊號）")
        
    finally:
        db.close()
    
    print("\n" + "=" * 60)
    print("💡 診斷結論")
    print("=" * 60)
    print("\n如果 Discord 已啟用且有 AI 訊號，但還是沒收到通知，可能原因：")
    print("1. Discord Webhook URL 無效或已過期")
    print("2. 網絡問題導致發送失敗")
    print("3. Discord 服務器問題")
    print("\n建議:")
    print("- 使用 API 端點測試 Discord: POST /alerts/test-discord")
    print("- 檢查應用日誌中的錯誤訊息")
    print("- 手動觸發通知測試: POST /alerts/{symbol}/check")

if __name__ == "__main__":
    check_notification_status()

