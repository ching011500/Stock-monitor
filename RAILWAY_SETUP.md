# Railway.app 部署指南

使用 Railway 部署股票監控系統，Mac 關機也能運行！

## 🎯 優點

- ✅ **免費額度**：$5/月免費額度（通常足夠使用）
- ✅ **24/7 運行**：不需要 Mac 開機
- ✅ **簡單設置**：幾分鐘即可完成
- ✅ **自動部署**：連接 GitHub 後自動部署
- ✅ **持久化存儲**：數據庫會持久保存

## ⚠️ 注意事項

- 可能會遇到 Yahoo Finance rate limiting（已實施改進策略）
- 免費額度有限，如果超出需要付費

## 設置步驟

### 步驟 1: 註冊 Railway

1. 訪問 https://railway.app
2. 點擊 **Start a New Project**
3. 使用 **GitHub 登錄**（推薦）

### 步驟 2: 創建新項目

1. 點擊 **New Project**
2. 選擇 **Deploy from GitHub repo**
3. 選擇您的 `Stock-monitor` 倉庫
4. Railway 會自動檢測 Python 項目

### 步驟 3: 配置環境變量

在 Railway 項目頁面：

1. 點擊項目 → **Variables** 標籤
2. 添加以下環境變量：

#### 必需的變量：

```
MONITORED_SYMBOLS=QQQ,SMH,TSLA,NVDA
```

#### OpenAI（必需）：

```
OPENAI_API_KEY=your_openai_api_key
```

#### Discord（可選但推薦）：

```
DISCORD_ENABLED=true
DISCORD_WEBHOOK_URL=your_discord_webhook_url
```

#### Notion（可選）：

```
NOTION_ENABLED=true
NOTION_API_KEY=your_notion_api_key
NOTION_DATABASE_ID=your_notion_database_id
NOTION_DAILY_REPORT_PAGE_ID=your_notion_page_id
```

### 步驟 4: 配置構建和啟動

Railway 會自動檢測到 `Procfile` 和配置。

如果沒有自動檢測，在項目設置中：

- **Root Directory**: 留空（項目根目錄）
- **Build Command**: `cd backend && pip install -r requirements.txt`
- **Start Command**: `cd backend && python run.py`

### 步驟 5: 部署

1. Railway 會自動開始構建和部署
2. 查看 **Deployments** 標籤查看部署日誌
3. 等待部署完成（通常 2-5 分鐘）

### 步驟 6: 確認運行

1. 查看 **Logs** 標籤
2. 應該看到：
   - "Initializing database..."
   - "Database initialized"
   - "Scheduled tasks started"
   - "定時任務已設置：執行時間：每天 UTC 22:00 (台灣時間 06:00)"

## 定時任務配置

Railway 會自動運行 FastAPI 應用，定時任務（APScheduler）會在應用啟動時自動設置。

任務會在台灣時間每天早上 6:00（UTC 22:00）自動執行。

## 監控和日誌

### 查看日誌

1. 進入 Railway 項目
2. 點擊 **Logs** 標籤
3. 查看實時日誌

### 查看部署狀態

1. 進入 Railway 項目
2. 點擊 **Deployments** 標籤
3. 查看部署歷史和狀態

## 更新代碼

當您推送代碼到 GitHub 時，Railway 會自動：
1. 檢測到新的提交
2. 重新構建應用
3. 重新部署（零停機時間）

## 數據持久化

Railway 會自動持久化數據庫文件（`backend/data/stocks.db`），數據不會丟失。

## 成本管理

### 免費額度

- **$5/月免費額度**
- 通常足夠運行一個小型 Python 應用

### 監控使用量

1. 進入 Railway 項目
2. 查看 **Usage** 標籤
3. 監控資源使用情況

### 如果超出免費額度

- Railway 會通知您
- 可以選擇升級到付費計劃（$5-20/月）
- 或優化應用以減少資源使用

## 故障排除

### 部署失敗

1. 查看 **Logs** 了解錯誤信息
2. 檢查環境變量是否正確設置
3. 確認 `requirements.txt` 中的依賴正確

### 應用無法啟動

1. 檢查日誌中的錯誤信息
2. 確認所有必需的環境變量已設置
3. 檢查 `run.py` 是否正確配置

### 定時任務沒有執行

1. 查看日誌確認 "Scheduled tasks started" 訊息
2. 確認應用正在運行（不是構建失敗）
3. 等待下一個執行時間（台灣時間早上 6:00）

### Yahoo Finance Rate Limiting

如果遇到 rate limiting：
- 查看日誌中的錯誤訊息
- 已實施的重試機制應該會自動處理
- 如果持續失敗，考慮使用 VPS + 自託管 runner

## 與 GitHub Actions 的區別

| 特性 | Railway | GitHub Actions |
|------|---------|----------------|
| 運行方式 | 持續運行服務 | 定時觸發任務 |
| 數據持久化 | ✅ 自動持久化 | ❌ 每次全新環境 |
| 成本 | $5/月免費額度 | 完全免費 |
| IP 封鎖 | ⚠️ 可能遇到 | ⚠️ 可能遇到 |
| 設置難度 | ⭐ 簡單 | ⭐⭐ 中等 |

## 推薦配置

### 最小配置（推薦）

- **Plan**: Free（免費）
- **資源**: 自動分配（通常足夠）

### 如果需要更多資源

- **Hobby Plan**: $5/月
- 更多資源和優先支持

## 下一步

1. ✅ 部署完成後，等待第一個定時任務執行
2. ✅ 查看日誌確認任務成功執行
3. ✅ 檢查 Discord 通知（如果配置了）
4. ✅ 檢查 Notion 數據更新（如果配置了）

## 參考資源

- [Railway 官方文檔](https://docs.railway.app)
- [Railway 定價](https://railway.app/pricing)
- [Railway 環境變量](https://docs.railway.app/develop/variables)

