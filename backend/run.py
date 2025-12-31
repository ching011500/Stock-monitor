"""
啟動腳本
"""
import uvicorn
import os

if __name__ == "__main__":
    # Railway 和其他平台會設置 PORT 環境變量
    port = int(os.environ.get("PORT", 8000))
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=False  # 生產環境禁用自動重載
    )


