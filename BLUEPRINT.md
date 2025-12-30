# 股票投資監控系統藍圖

## 📊 系統概述

這是一個自動化的股票價格與指標監控系統，用於實時追蹤 QQQ、SMH、TSLA、NVDA 等標的的價格變動、技術指標和市場訊號。

## 🎯 核心功能

### 1. 價格監控
- **實時價格追蹤**: 每分鐘更新股價
- **價格變動警報**: 當價格變動超過設定閾值時發送通知
- **歷史價格記錄**: 保存價格歷史數據供分析

### 2. 技術指標計算
- **移動平均線 (MA)**: 5日、10日、20日、50日、200日
- **相對強弱指標 (RSI)**: 14日RSI
- **MACD**: 12/26/9 參數
- **布林帶 (Bollinger Bands)**: 20日，2標準差
- **成交量分析**: 成交量變化趨勢

### 3. AI 分析與預測
- **趨勢分析**: 使用 AI 分析價格趨勢
- **訊號生成**: 自動生成買入/賣出/持有訊號
- **風險評估**: 評估當前市場風險等級

### 4. 通知與記錄系統
- **Discord 即時通知**: 價格異常、指標突破、AI 訊號時發送到 Discord 頻道
- **Notion 數據記錄**: 將監控數據、指標、AI 分析結果自動記錄到 Notion 數據庫
- **Notion 每日摘要**: 每日收盤後在 Notion 生成總結報告頁面
- **Notion 歷史追蹤**: 所有重要事件和訊號記錄到 Notion 供長期追蹤

### 5. 數據視覺化
- **即時儀表板**: Web 介面顯示當前狀態
- **圖表分析**: 價格走勢圖、指標圖表
- **歷史回顧**: 查看歷史數據和訊號

## 🏗️ 系統架構

```
┌─────────────────────────────────────────────────┐
│              數據收集層 (Data Collection)        │
│  - 股票 API (Yahoo Finance / Alpha Vantage)     │
│  - 數據爬蟲 (備用方案)                           │
└─────────────────┬───────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────┐
│              數據處理層 (Data Processing)        │
│  - 數據清洗與驗證                                │
│  - 技術指標計算引擎                              │
│  - 數據存儲 (SQLite/PostgreSQL)                 │
└─────────────────┬───────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────┐
│              AI 分析層 (AI Analysis)              │
│  - 趨勢預測模型                                  │
│  - 訊號生成邏輯                                  │
│  - 風險評估算法                                  │
└─────────────────┬───────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────┐
│              通知與展示層 (Notification/UI)      │
│  - Discord Webhook (即時通知)                    │
│  - Notion API (數據記錄與摘要)                   │
│  - Web 儀表板 (Flask/FastAPI + React)           │
│  - API 接口                                      │
└─────────────────────────────────────────────────┘
```

## 🛠️ 技術棧建議

### 後端
- **語言**: Python 3.10+
- **框架**: FastAPI (API) + Flask (Web)
- **數據庫**: SQLite (開發) / PostgreSQL (生產)
- **任務調度**: APScheduler (定時任務)
- **數據獲取**: 
  - `yfinance` (Yahoo Finance API)
  - `alpha_vantage` (Alpha Vantage API，備用)
- **技術指標**: `pandas_ta` 或 `ta-lib`
- **AI/ML**: 
  - `scikit-learn` (傳統 ML)
  - `tensorflow` 或 `pytorch` (深度學習，可選)

### 前端
- **框架**: React + TypeScript
- **圖表庫**: Chart.js 或 Recharts
- **UI 框架**: Tailwind CSS 或 Material-UI

### 通知與記錄服務
- **Discord**: `discord.py` 或 Discord Webhook (推薦 Webhook，更簡單)
- **Notion**: `notion-client` (官方 Notion API) 或 `notion-py`

### 部署
- **容器化**: Docker + Docker Compose
- **雲端**: AWS / GCP / Azure (可選)

## 📁 項目結構

```
Stock monitor/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI 主應用
│   │   ├── config.py               # 配置管理
│   │   ├── models/                 # 數據模型
│   │   │   ├── stock.py
│   │   │   └── indicator.py
│   │   ├── services/               # 業務邏輯
│   │   │   ├── data_collector.py   # 數據收集
│   │   │   ├── indicator_calculator.py  # 指標計算
│   │   │   ├── ai_analyzer.py     # AI 分析
│   │   │   ├── discord_notifier.py  # Discord 通知
│   │   │   └── notion_recorder.py   # Notion 記錄
│   │   ├── database/               # 數據庫相關
│   │   │   ├── database.py
│   │   │   └── crud.py
│   │   ├── api/                    # API 路由
│   │   │   ├── stocks.py
│   │   │   ├── indicators.py
│   │   │   └── alerts.py
│   │   └── scheduler/              # 定時任務
│   │       └── tasks.py
│   ├── tests/                      # 測試
│   ├── requirements.txt
│   └── Dockerfile
│
├── frontend/                       # (可選，第二階段)
│   ├── src/
│   ├── package.json
│   └── ...
│
├── data/                           # 數據存儲
│   └── stocks.db                   # SQLite 數據庫
│
├── logs/                           # 日誌文件
│
├── config/                         # 配置文件
│   ├── config.yaml
│   └── stocks.yaml                 # 監控股票列表
│
├── .env                            # 環境變量
├── .gitignore
├── docker-compose.yml
├── README.md
└── BLUEPRINT.md                    # 本文件
```

## 📈 監控標的配置

### 初始監控列表
- **QQQ**: Invesco QQQ Trust (納斯達克100 ETF)
- **SMH**: VanEck Semiconductor ETF
- **TSLA**: Tesla Inc.
- **NVDA**: NVIDIA Corporation

### 配置格式
```yaml
stocks:
  - symbol: QQQ
    name: Invesco QQQ Trust
    type: ETF
    alerts:
      price_change_threshold: 2.0  # 2% 價格變動觸發警報
      rsi_oversold: 30
      rsi_overbought: 70
  
  - symbol: SMH
    name: VanEck Semiconductor ETF
    type: ETF
    alerts:
      price_change_threshold: 2.0
      rsi_oversold: 30
      rsi_overbought: 70
  
  - symbol: TSLA
    name: Tesla Inc.
    type: Stock
    alerts:
      price_change_threshold: 3.0
      rsi_oversold: 30
      rsi_overbought: 70
  
  - symbol: NVDA
    name: NVIDIA Corporation
    type: Stock
    alerts:
      price_change_threshold: 3.0
      rsi_oversold: 30
      rsi_overbought: 70
```

## 🔄 數據流程

### 1. 數據收集流程
```
每分鐘執行:
1. 從 API 獲取最新價格數據
2. 驗證數據完整性
3. 存入數據庫
4. 觸發指標計算
```

### 2. 指標計算流程
```
每5分鐘執行:
1. 從數據庫讀取最近 N 天的數據
2. 計算所有技術指標
3. 更新指標數據表
4. 觸發 AI 分析
```

### 3. AI 分析流程
```
每15分鐘執行:
1. 讀取最新價格和指標數據
2. 執行趨勢分析
3. 生成交易訊號
4. 評估風險等級
5. 觸發通知（如需要）
```

### 4. 通知與記錄流程
```
實時觸發:
1. 價格變動超過閾值 → Discord 通知 + Notion 記錄
2. 指標突破關鍵位 → Discord 通知 + Notion 記錄
3. AI 生成買入/賣出訊號 → Discord 通知 + Notion 記錄

定時執行:
4. 每小時 → 更新 Notion 數據庫（價格、指標）
5. 每日收盤後 → 在 Notion 創建日報頁面 + Discord 摘要通知
```

## 🚨 警報規則

### 價格警報
- **大幅變動**: 單日變動 > 設定閾值（如 2-3%）
- **突破關鍵位**: 突破重要支撐/阻力位
- **異常成交量**: 成交量異常放大（> 2倍平均量）

### 指標警報
- **RSI 超買/超賣**: RSI < 30 或 > 70
- **MACD 交叉**: MACD 線與信號線交叉
- **布林帶突破**: 價格突破布林帶上下軌

### AI 訊號
- **買入訊號**: AI 判斷為買入時機
- **賣出訊號**: AI 判斷為賣出時機
- **風險警告**: 風險等級提升

## 📊 數據模型

### Notion 數據庫結構

#### 主監控數據庫 (Stock Monitor Database)
```notion
Properties:
- Symbol (Title): 股票代號
- Name (Text): 股票名稱
- Current Price (Number): 當前價格
- Price Change % (Number): 價格變動百分比
- RSI (Number): RSI 指標
- MACD Signal (Select): MACD 訊號 (Bullish/Bearish/Neutral)
- AI Signal (Select): AI 訊號 (BUY/SELL/HOLD)
- Risk Level (Select): 風險等級 (LOW/MEDIUM/HIGH)
- Last Updated (Date): 最後更新時間
- Status (Select): 狀態 (Active/Monitoring)
```

#### 日報頁面結構 (Daily Report)
```notion
每日自動創建頁面，包含:
- 日期標題
- 市場概覽 (所有標的的整體表現)
- 個股分析 (每個標的的詳細數據)
- 技術指標摘要
- AI 訊號總結
- 重要事件記錄
```

#### 事件記錄數據庫 (Events Log)
```notion
Properties:
- Event Type (Select): 事件類型 (Price Alert/RSI Alert/MACD Signal/AI Signal)
- Symbol (Relation): 關聯到主數據庫
- Severity (Select): 嚴重程度 (INFO/WARNING/CRITICAL)
- Message (Text): 事件描述
- Timestamp (Date): 發生時間
- Details (Text): 詳細信息
```

### Stock Price
```python
{
    symbol: str,
    timestamp: datetime,
    open: float,
    high: float,
    low: float,
    close: float,
    volume: int,
    adj_close: float
}
```

### Technical Indicators
```python
{
    symbol: str,
    timestamp: datetime,
    ma5: float,
    ma10: float,
    ma20: float,
    ma50: float,
    ma200: float,
    rsi: float,
    macd: float,
    macd_signal: float,
    macd_hist: float,
    bb_upper: float,
    bb_middle: float,
    bb_lower: float,
    volume_avg: float
}
```

### AI Signals
```python
{
    symbol: str,
    timestamp: datetime,
    signal: str,  # 'BUY', 'SELL', 'HOLD'
    confidence: float,  # 0-1
    risk_level: str,  # 'LOW', 'MEDIUM', 'HIGH'
    reasoning: str
}
```

## 🔐 安全與配置

### 環境變量
```env
# API Keys
ALPHA_VANTAGE_API_KEY=your_key
YAHOO_FINANCE_ENABLED=true

# 數據庫
DATABASE_URL=sqlite:///data/stocks.db

# Discord 通知
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/your_webhook_url
DISCORD_ENABLED=true

# Notion 記錄
NOTION_API_KEY=secret_your_notion_integration_token
NOTION_DATABASE_ID=your_notion_database_id  # 主數據庫 ID
NOTION_DAILY_REPORT_PAGE_ID=your_daily_report_page_id  # 日報父頁面 ID
NOTION_ENABLED=true

# 應用配置
UPDATE_INTERVAL=60  # 秒
INDICATOR_INTERVAL=300  # 秒
AI_ANALYSIS_INTERVAL=900  # 秒
```

## 📅 開發階段

### 第一階段：基礎架構 (Week 1)
- [ ] 項目結構搭建
- [ ] 數據收集模組
- [ ] 數據庫設計與實現
- [ ] 基礎 API 接口

### 第二階段：指標計算 (Week 2)
- [ ] 技術指標計算引擎
- [ ] 指標數據存儲
- [ ] 指標 API 接口

### 第三階段：通知與記錄系統 (Week 3)
- [ ] Discord Webhook 整合
- [ ] Notion API 整合
- [ ] Notion 數據庫結構設計
- [ ] 即時通知邏輯（Discord）
- [ ] 數據記錄邏輯（Notion）
- [ ] 每日摘要生成（Notion）
- [ ] 警報規則引擎

### 第四階段：AI 分析 (Week 4)
- [ ] 基礎趨勢分析
- [ ] 訊號生成邏輯
- [ ] 風險評估

### 第五階段：前端儀表板 (Week 5-6)
- [ ] Web 界面開發
- [ ] 圖表視覺化
- [ ] 實時數據展示

## 🎯 未來擴展

1. **更多標的**: 支援自定義添加監控標的
2. **策略回測**: 歷史策略回測功能
3. **組合管理**: 投資組合追蹤
4. **新聞分析**: 整合新聞情緒分析
5. **自動交易**: 連接券商 API 實現自動交易（需謹慎）

## 🔗 Discord 與 Notion 整合說明

### Discord 使用場景
- **即時警報**: 價格大幅變動、指標突破時立即發送
- **AI 訊號通知**: 當 AI 生成買入/賣出訊號時通知
- **每日摘要**: 收盤後發送簡要總結
- **系統狀態**: 系統異常或重要事件通知

### Notion 使用場景
- **數據持久化**: 所有監控數據自動記錄到 Notion 數據庫
- **歷史追蹤**: 長期追蹤價格趨勢和指標變化
- **結構化分析**: 使用 Notion 的視圖功能進行數據分析
- **日報生成**: 每日自動生成結構化的市場分析報告
- **協作分享**: 方便與團隊或自己分享投資分析

### 整合優勢
1. **Discord**: 即時性強，適合快速通知和提醒
2. **Notion**: 結構化存儲，適合長期追蹤和分析
3. **互補**: Discord 負責即時通知，Notion 負責數據記錄和歷史分析

## 📝 注意事項

1. **API 限制**: 
   - Discord Webhook: 無嚴格限制，但避免過度頻繁
   - Notion API: 每分鐘約 3 次請求限制，需合理設計更新頻率
2. **數據準確性**: 確保數據來源可靠
3. **風險提示**: AI 訊號僅供參考，不構成投資建議
4. **合規性**: 確保符合相關法規要求
5. **備份**: Notion 數據自動雲端備份，但建議定期導出重要數據
6. **Notion 設置**: 需要先創建 Notion Integration 並獲取 API Key
7. **Discord 設置**: 需要在 Discord 頻道中創建 Webhook

---

**下一步**: 開始實現第一階段的基礎架構
