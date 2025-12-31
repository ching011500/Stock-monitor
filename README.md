# 股票投資監控系統

自動化的股票價格與指標監控系統，用於實時追蹤 QQQ、SMH、TSLA、NVDA 等標的的價格變動、技術指標和市場訊號。

## 功能特性

- 📊 **實時價格監控**: 自動收集和存儲股票價格數據
- 📈 **技術指標計算**: MA、RSI、MACD、布林帶等（第二階段）
- 🤖 **AI 分析**: 趨勢預測與交易訊號生成（第四階段）
- 🔔 **Discord 通知**: 即時警報通知（第三階段）
- 📝 **Notion 記錄**: 自動記錄到 Notion 數據庫（第三階段）
- 🌐 **RESTful API**: 完整的 API 接口

## 技術棧

- **後端**: Python 3.10+, FastAPI
- **數據庫**: SQLite (開發) / PostgreSQL (生產)
- **數據獲取**: yfinance (Yahoo Finance)
- **任務調度**: APScheduler

## 快速開始

### 1. 環境設置

```bash
# 創建虛擬環境
python -m venv venv

# 激活虛擬環境
# macOS/Linux:
source venv/bin/activate
# Windows:
venv\Scripts\activate

# 安裝依賴
cd backend
pip install -r requirements.txt
```

### 2. 配置環境變量

```bash
# 複製環境變量模板
cp .env.example .env

# 編輯 .env 文件，填入必要的配置
# 至少需要設置監控標的：
# MONITORED_SYMBOLS=QQQ,SMH,TSLA,NVDA
```

### 3. 初始化數據庫

數據庫會在應用啟動時自動創建。

### 4. 啟動應用

**本地開發**：
```bash
cd backend
python run.py
```

或者直接使用 uvicorn：
```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**雲端部署（推薦）**：

使用 **Railway.app** 部署，請參考 [RAILWAY_SETUP.md](./RAILWAY_SETUP.md)

- ✅ 免費額度 $5/月（通常足夠）
- ✅ Mac 關機也能運行
- ✅ 設置簡單，幾分鐘完成
- ✅ 數據持久化
- ✅ 自動部署（連接 GitHub 後自動部署）

### 5. 訪問 API

- API 文檔: http://localhost:8000/docs
- 健康檢查: http://localhost:8000/health
- 所有股票: http://localhost:8000/stocks/

## API 端點

### 股票相關

- `GET /stocks/` - 獲取所有標的最新價格
- `GET /stocks/{symbol}` - 獲取指定標的最新價格
- `GET /stocks/{symbol}/history?days=30` - 獲取歷史價格
- `POST /stocks/{symbol}/refresh` - 手動刷新指定標的數據
- `POST /stocks/refresh-all` - 手動刷新所有標的數據

### 技術指標（第二階段）

- `GET /indicators/{symbol}` - 獲取最新技術指標
- `GET /indicators/{symbol}/history?days=30` - 獲取歷史指標
- `POST /indicators/{symbol}/calculate` - 手動計算指定標的的技術指標
- `POST /indicators/refresh-all` - 計算所有監控標的的技術指標

### AI 訊號（第三階段）

- `GET /signals/{symbol}` - 獲取最新 AI 訊號
- `GET /signals/{symbol}/history?days=30` - 獲取歷史訊號
- `POST /signals/{symbol}/analyze` - 手動分析指定標的並生成訊號
- `POST /signals/analyze-all` - 分析所有監控標的並生成訊號

### 警報（第四階段）

- `GET /alerts/{symbol}` - 檢查指定標的的所有警報
- `POST /alerts/{symbol}/check` - 手動觸發指定標的的警報檢查
- `POST /alerts/check-all` - 檢查所有監控標的的警報

## 項目結構

```
Stock monitor/
├── backend/
│   ├── app/
│   │   ├── api/              # API 路由
│   │   ├── database/         # 數據庫相關
│   │   ├── models/           # 數據模型
│   │   ├── data_collection/  # 數據收集服務
│   │   ├── technical_indicators/  # 技術指標計算
│   │   ├── ai_analysis/      # AI 分析
│   │   ├── notifications/    # 通知服務（Discord、Notion）
│   │   ├── scheduler/        # 定時任務（APScheduler）
│   │   ├── config.py         # 配置管理
│   │   └── main.py           # FastAPI 主應用
│   ├── data/                 # 數據存儲（本地開發用，Railway 會持久化）
│   ├── cleanup_duplicates.py # 數據庫清理工具（可選）
│   ├── manual_collect.py     # 手動執行腳本（本地測試用）
│   ├── run.py                # 啟動腳本（Railway 使用）
│   └── requirements.txt      # Python 依賴
├── Procfile                  # Railway 啟動配置
├── railway.json              # Railway 配置文件（可選）
├── .gitignore
├── README.md                 # 本文件
└── RAILWAY_SETUP.md         # Railway 部署指南
```

## 開發階段

- ✅ **第一階段**: 基礎架構、數據收集、API 接口
- ✅ **第二階段**: 技術指標計算（MA、RSI、MACD、布林帶）
- ✅ **第三階段**: AI 分析（趨勢分析、訊號生成、風險評估）
- ✅ **第四階段**: Discord + Notion 整合（通知與記錄系統）
- ⏳ **第五階段**: Web 儀表板

## 注意事項

1. **API 限制**: yfinance 沒有嚴格限制，但建議合理控制請求頻率
2. **數據準確性**: 數據來源於 Yahoo Finance，僅供參考
3. **風險提示**: 本系統僅供學習和研究使用，不構成投資建議

## 授權

MIT License

