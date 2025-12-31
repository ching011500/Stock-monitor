# GitHub Actions 設置指南

使用 GitHub Actions 定時任務來執行股票監控，**不需要服務器一直運行**！

## 🎯 優點

- ✅ **完全免費**：GitHub Actions 免費方案通常足夠使用
- ✅ **不需要服務器**：不需要電腦一直開著
- ✅ **自動執行**：每天自動運行
- ✅ **易於管理**：在 GitHub 上就可以查看執行歷史和日誌

## ⚠️ 注意事項

1. **數據庫不持久化**：每次運行都是全新的環境，數據庫不會保留
   - 但這沒關係，因為我們每次都會從 API 重新獲取數據
   - 歷史數據會存儲在 Notion 中（如果啟用了 Notion）

2. **執行時間限制**：免費方案每次運行最多 60 分鐘

3. **執行頻率**：免費方案每月有 2000 分鐘額度（每天運行一次，每月約 30 次 × 5-10 分鐘 = 150-300 分鐘，足夠使用）

## 📋 設置步驟

### 1. 將代碼推送到 GitHub

```bash
git add .
git commit -m "Add GitHub Actions workflow"
git push
```

### 2. 設置 GitHub Secrets

在您的 GitHub 倉庫中：
1. 進入 **Settings** → **Secrets and variables** → **Actions**
2. 點擊 **New repository secret**
3. 添加以下 secrets：

#### 必需的 Secrets：

- **`MONITORED_SYMBOLS`**
  - 值：`QQQ,SMH,TSLA,NVDA`（用逗號分隔）

- **`OPENAI_API_KEY`**
  - 值：您的 OpenAI API Key

#### 可選的 Secrets：

- **Discord 通知（可選）**
  - **`DISCORD_ENABLED`**: `true` 或 `false`
  - **`DISCORD_WEBHOOK_URL`**: Discord Webhook URL

- **Notion 同步（可選）**
  - **`NOTION_ENABLED`**: `true` 或 `false`
  - **`NOTION_API_KEY`**: Notion Integration API Key
  - **`NOTION_DATABASE_ID`**: Notion Database ID
  - **`NOTION_DAILY_REPORT_PAGE_ID`**: Notion Daily Report Page ID

- **GitHub 圖表上傳（可選）**
  - `GITHUB_TOKEN` 會自動提供，不需要設置
  - 如果需要在同一個倉庫上傳圖表，可以設置自定義 token

### 3. 驗證 Workflow 文件

確保 `.github/workflows/daily-stock-monitor.yml` 文件存在並且正確。

### 4. 手動測試（可選）

1. 進入 GitHub 倉庫的 **Actions** 標籤頁
2. 選擇 **每日股票監控任務** workflow
3. 點擊 **Run workflow** → **Run workflow**（手動觸發）

### 5. 查看執行結果

執行完成後：
- 點擊 workflow run 查看詳細日誌
- 檢查是否成功執行
- 如果配置了 Discord，檢查是否收到通知

## 🕐 執行時間

- **定時執行**：台灣時間每天早上 6:00（UTC 22:00）
- **執行頻率**：週一到週五（交易日）
- **手動觸發**：隨時可以在 Actions 頁面手動運行

## 🔧 自定義設置

### 修改執行時間

編輯 `.github/workflows/daily-stock-monitor.yml`：

```yaml
schedule:
  - cron: '0 22 * * 1-5'  # 修改這個時間
```

Cron 格式：`分鐘 小時 日 月 星期`
- `0 22 * * 1-5` = 每週一到週五 UTC 22:00（台灣時間 06:00）
- `0 23 * * *` = 每天 UTC 23:00（台灣時間 07:00）

### 修改監控標的

在 GitHub Secrets 中修改 `MONITORED_SYMBOLS` 的值。

### 禁用某些功能

在 GitHub Secrets 中設置：
- `DISCORD_ENABLED=false`（禁用 Discord 通知）
- `NOTION_ENABLED=false`（禁用 Notion 同步）

## 📊 執行歷史

在 GitHub 倉庫的 **Actions** 標籤頁可以查看：
- 所有執行歷史
- 執行狀態（成功/失敗）
- 詳細日誌
- 執行時間和耗時

## 🐛 故障排除

### Workflow 沒有執行

1. 檢查 workflow 文件是否在正確的位置：`.github/workflows/`
2. 確保文件已提交並推送到 GitHub
3. 檢查 cron 語法是否正確

### 執行失敗

1. 查看 Actions 日誌找出錯誤
2. 檢查所有必需的 secrets 是否已設置
3. 確認 API keys 是否有效

### 沒有收到通知

1. 檢查 `DISCORD_ENABLED` 是否設置為 `true`
2. 檢查 `DISCORD_WEBHOOK_URL` 是否正確
3. 查看執行日誌確認是否有錯誤

## 💡 最佳實踐

1. **定期檢查執行歷史**：確保 workflow 正常運行
2. **監控執行時間**：如果執行時間過長，考慮優化
3. **備份重要數據**：雖然數據庫不持久化，但 Notion 中的數據會保留
4. **設置通知**：可以在 Discord 中監控執行狀態

## 🆚 與服務器部署的對比

| 特性 | GitHub Actions | 服務器部署 |
|------|---------------|------------|
| 成本 | 免費 | $5-20/月 |
| 電腦需要開著 | ❌ 不需要 | ✅ 需要（本地）或 ❌ 不需要（雲端） |
| 數據持久化 | ❌ 不持久 | ✅ 持久 |
| 設置難度 | 簡單 | 中等 |
| 執行歷史 | ✅ 有 | 需要自己設置日誌 |
| 手動觸發 | ✅ 容易 | 需要訪問服務器 |

## 📚 相關資源

- [GitHub Actions 文檔](https://docs.github.com/en/actions)
- [Cron 語法說明](https://crontab.guru/)
- [GitHub Actions 限制](https://docs.github.com/en/actions/learn-github-actions/usage-limits-billing-and-administration)

