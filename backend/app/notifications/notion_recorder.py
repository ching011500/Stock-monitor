"""
Notion 記錄服務
將監控數據、指標、AI 分析結果記錄到 Notion 數據庫
"""
from notion_client import Client
from typing import Optional, Dict, List
from datetime import datetime
import logging
import requests
import os
import base64
from pathlib import Path

from app.config import settings
from app.notifications.report_generator import ReportGenerator
from app.notifications.chart_generator import ChartGenerator
from app.database.crud import get_prices_by_symbol, get_indicators_by_symbol
from app.database.database import get_db_sync

logger = logging.getLogger(__name__)


class NotionRecorder:
    """Notion 記錄器"""
    
    def __init__(self):
        self.api_key = settings.NOTION_API_KEY
        self.database_id = settings.NOTION_DATABASE_ID
        self.daily_report_page_id = settings.NOTION_DAILY_REPORT_PAGE_ID
        self.enabled = settings.NOTION_ENABLED
        
        if self.enabled and self.api_key:
            try:
                self.client = Client(auth=self.api_key)
                logger.info("Notion 客戶端初始化成功")
            except Exception as e:
                logger.error(f"Notion 客戶端初始化失敗: {str(e)}")
                self.enabled = False
        else:
            self.client = None
            if self.enabled:
                logger.warning("Notion API Key 未配置，Notion 記錄已禁用")
        
        # 初始化報告生成器
        self.report_generator = ReportGenerator()
        # 初始化圖表生成器
        self.chart_generator = ChartGenerator()
    
    def _get_title_property_name(self, database_id: str) -> Optional[str]:
        """
        獲取數據庫的標題屬性名稱
        
        Args:
            database_id: 數據庫 ID
        
        Returns:
            標題屬性名稱，如果未找到則返回 None
        """
        if not self.enabled or not self.client:
            return None
        
        try:
            database = self.client.databases.retrieve(database_id=database_id)
            properties = database.get("properties", {})
            
            # 查找類型為 "title" 的屬性
            for prop_name, prop_info in properties.items():
                if prop_info.get("type") == "title":
                    return prop_name
            
            logger.warning(f"未找到標題類型的屬性，使用第一個屬性")
            # 如果沒找到 title 類型，返回第一個屬性名
            if properties:
                return list(properties.keys())[0]
            
            return None
            
        except Exception as e:
            logger.error(f"獲取數據庫屬性失敗: {str(e)}")
            return None
    
    def _get_or_create_page(self, database_id: str, symbol: str) -> Optional[str]:
        """
        獲取或創建 Notion 頁面
        
        Args:
            database_id: 數據庫 ID
            symbol: 股票代號
        
        Returns:
            頁面 ID
        """
        if not self.enabled or not self.client:
            return None
        
        try:
            # 獲取標題屬性名稱
            title_prop_name = self._get_title_property_name(database_id)
            if not title_prop_name:
                logger.error(f"無法獲取數據庫標題屬性名稱")
                return None
            
            # 查詢現有頁面
            results = self.client.databases.query(
                database_id=database_id,
                filter={
                    "property": title_prop_name,
                    "title": {
                        "equals": symbol
                    }
                }
            )
            
            if results.get("results"):
                return results["results"][0]["id"]
            
            # 創建新頁面
            new_page = self.client.pages.create(
                parent={"database_id": database_id},
                properties={
                    title_prop_name: {
                        "title": [{"text": {"content": symbol}}]
                    }
                }
            )
            
            return new_page["id"]
            
        except Exception as e:
            logger.error(f"獲取或創建 Notion 頁面失敗 ({symbol}): {str(e)}", exc_info=True)
            return None
    
    def _get_database_properties(self, database_id: str) -> Optional[Dict]:
        """
        獲取數據庫的所有屬性名稱和類型
        
        Args:
            database_id: 數據庫 ID
        
        Returns:
            屬性字典 {屬性名: 屬性類型}，如果失敗則返回 None
        """
        if not self.enabled or not self.client:
            return None
        
        try:
            database = self.client.databases.retrieve(database_id=database_id)
            properties = database.get("properties", {})
            
            # 構建屬性名和類型的映射
            prop_map = {}
            for prop_name, prop_info in properties.items():
                prop_map[prop_name] = prop_info.get("type")
            
            return prop_map
            
        except Exception as e:
            logger.error(f"獲取數據庫屬性失敗: {str(e)}")
            return None
    
    def _find_property_name(self, database_id: str, possible_names: List[str], prop_type: str = None) -> Optional[str]:
        """
        根據可能的屬性名稱列表，查找數據庫中實際存在的屬性名稱
        
        Args:
            database_id: 數據庫 ID
            possible_names: 可能的屬性名稱列表
            prop_type: 期望的屬性類型（可選）
        
        Returns:
            找到的屬性名稱，如果未找到則返回 None
        """
        prop_map = self._get_database_properties(database_id)
        if not prop_map:
            return None
        
        # 先嘗試精確匹配
        for name in possible_names:
            if name in prop_map:
                if prop_type is None or prop_map[name] == prop_type:
                    return name
        
        # 如果沒找到，嘗試不區分大小寫匹配
        prop_map_lower = {k.lower(): k for k in prop_map.keys()}
        for name in possible_names:
            if name.lower() in prop_map_lower:
                matched_name = prop_map_lower[name.lower()]
                if prop_type is None or prop_map[matched_name] == prop_type:
                    return matched_name
        
        return None
    
    def update_stock_data(self, symbol: str, price: float, change_percent: float,
                         rsi: Optional[float] = None, ai_signal: Optional[str] = None,
                         risk_level: Optional[str] = None,
                         price_timestamp: Optional[datetime] = None) -> bool:
        """
        更新股票數據到 Notion 數據庫
        
        Args:
            symbol: 股票代號
            price: 當前價格
            change_percent: 價格變動百分比
            rsi: RSI 指標（可選）
            ai_signal: AI 訊號（可選）
            risk_level: 風險等級（可選）
        
        Returns:
            是否成功
        """
        if not self.enabled or not self.client or not self.database_id:
            logger.debug("Notion 記錄未啟用或未配置，跳過更新")
            return False
        
        try:
            page_id = self._get_or_create_page(self.database_id, symbol)
            if not page_id:
                return False
            
            # 動態查找屬性名稱
            price_prop = self._find_property_name(self.database_id, ["Current Price", "價格", "Price", "當前價格"], "number")
            change_prop = self._find_property_name(self.database_id, ["Price Change %", "價格變動", "Change %", "價格變動百分比"], "number")
            updated_prop = self._find_property_name(self.database_id, ["Last Updated", "最後更新", "Updated", "更新時間"], "date")
            rsi_prop = self._find_property_name(self.database_id, ["RSI", "rsi"], "number") if rsi is not None else None
            signal_prop = self._find_property_name(self.database_id, ["AI Signal", "AI訊號", "Signal", "訊號"], "select") if ai_signal else None
            risk_prop = self._find_property_name(self.database_id, ["Risk Level", "風險等級", "Risk", "風險"], "select") if risk_level else None
            
            properties = {}
            
            if price_prop:
                properties[price_prop] = {"number": price}
            else:
                logger.warning(f"未找到價格屬性，跳過更新價格")
            
            if change_prop:
                properties[change_prop] = {"number": change_percent}
            
            if updated_prop:
                # 使用價格記錄的日期（不含時間），避免因時區或 UTC 造成日期顯示錯誤
                if price_timestamp:
                    date_str = price_timestamp.date().isoformat()
                else:
                    # 後備：如果沒有提供 timestamp，就用今天的日期（UTC）
                    date_str = datetime.utcnow().date().isoformat()
                properties[updated_prop] = {
                    "date": {
                        # Notion 日期欄位只需要 YYYY-MM-DD，避免帶入時間
                        "start": date_str
                    }
                }
            
            if rsi is not None and rsi_prop:
                properties[rsi_prop] = {"number": rsi}
            
            if ai_signal and signal_prop:
                properties[signal_prop] = {
                    "select": {
                        "name": ai_signal
                    }
                }
            
            if risk_level and risk_prop:
                properties[risk_prop] = {
                    "select": {
                        "name": risk_level
                    }
                }
            
            # 即使沒有可更新的屬性，頁面也已經創建/找到了，所以返回 True
            if not properties:
                logger.warning(f"未找到任何可更新的屬性，但頁面已創建/找到: {symbol}。請在 Notion 數據庫中添加屬性（Current Price, Price Change %, RSI, AI Signal, Risk Level）")
                return True
            
            self.client.pages.update(
                page_id=page_id,
                properties=properties
            )
            
            logger.info(f"Notion 數據更新成功: {symbol}，更新了 {len(properties)} 個屬性")
            return True
            
        except Exception as e:
            logger.error(f"更新 Notion 數據失敗 ({symbol}): {str(e)}", exc_info=True)
            return False
    
    def create_daily_report(self, date: str, stocks_data: List[Dict]) -> Optional[str]:
        """
        創建每日報告頁面
        
        Args:
            date: 日期（YYYY-MM-DD）
            stocks_data: 股票數據列表
        
        Returns:
            頁面 ID 或 None
        """
        if not self.enabled or not self.client:
            logger.debug("Notion 記錄未啟用，跳過創建日報")
            return None
        
        if not self.daily_report_page_id:
            logger.warning("Notion Daily Report Page ID 未配置，無法創建日報")
            return None
        
        try:
            # 生成分析報告（優先使用 OpenAI，否則使用結構化格式）
            ai_analysis = self.report_generator.generate_daily_analysis(stocks_data, date)
            if not ai_analysis:
                # 如果 OpenAI 不可用，使用結構化報告格式
                ai_analysis = self.report_generator.generate_structured_report(stocks_data, date)
            
            # 構建報告內容
            content_blocks = []
            
            # 標題（已在 properties 中設置，這裡添加一個副標題）
            content_blocks.append({
                "object": "block",
                "type": "heading_2",
                "heading_2": {
                    "rich_text": [{"type": "text", "text": {"content": "市場分析報告"}}]
                }
            })
            
            # AI 生成的市場分析（分段添加，因為可能很長）
            # 將長文本分割成多個段落
            analysis_lines = ai_analysis.split('\n')
            current_symbol = None
            
            for line in analysis_lines:
                line = line.strip()
                if not line:
                    continue
                
                # 檢查是否是標題（以 # 開頭）
                if line.startswith('##'):
                    content_blocks.append({
                        "object": "block",
                        "type": "heading_3",
                        "heading_3": {
                            "rich_text": [{"type": "text", "text": {"content": line.replace('##', '').strip()}}]
                        }
                    })
                elif line.startswith('###'):
                    content_blocks.append({
                        "object": "block",
                        "type": "heading_3",
                        "heading_3": {
                            "rich_text": [{"type": "text", "text": {"content": line.replace('###', '').strip()}}]
                        }
                    })
                elif line.startswith('####'):
                    # 個股標題，提取 symbol
                    current_symbol = line.replace('####', '').strip()
                    content_blocks.append({
                        "object": "block",
                        "type": "heading_3",
                        "heading_3": {
                            "rich_text": [{"type": "text", "text": {"content": line.replace('####', '').strip()}}]
                        }
                    })
                elif line == "【技術圖】" or line.startswith("【技術圖】"):
                    # 生成並上傳圖表
                    if current_symbol:
                        chart_path = self._generate_and_upload_chart(current_symbol, stocks_data, page_id=None)
                        if chart_path:
                            # 圖表會在創建頁面後上傳，這裡先標記
                            content_blocks.append({
                                "object": "block",
                                "type": "paragraph",
                                "paragraph": {
                                    "rich_text": [{"type": "text", "text": {"content": "【技術圖】（圖表已生成）"}}]
                                }
                            })
                        else:
                            content_blocks.append({
                                "object": "block",
                                "type": "paragraph",
                                "paragraph": {
                                    "rich_text": [{"type": "text", "text": {"content": "【技術圖】（圖表生成失敗）"}}]
                                }
                            })
                    else:
                        content_blocks.append({
                            "object": "block",
                            "type": "paragraph",
                            "paragraph": {
                                "rich_text": [{"type": "text", "text": {"content": line}}]
                            }
                        })
                else:
                    content_blocks.append({
                        "object": "block",
                        "type": "paragraph",
                        "paragraph": {
                            "rich_text": [{"type": "text", "text": {"content": line}}]
                        }
                    })
            
            # 分隔線
            content_blocks.append({
                "object": "block",
                "type": "divider",
                "divider": {}
            })
            
            # 創建頁面（先創建基本結構）
            new_page = self.client.pages.create(
                parent={"page_id": self.daily_report_page_id},
                properties={
                    "title": {
                        "title": [{"text": {"content": f"每日報告 - {date}"}}]
                    }
                },
                children=content_blocks  # 添加所有內容區塊
            )
            
            page_id = new_page["id"]
            
            # 為每個標的生成圖表並上傳到 Notion
            # 在「個股分析」區塊中，為每個標的追加圖表
            for stock in stocks_data:
                symbol = stock.get("symbol", "")
                # 生成圖表並上傳（會在函數內部添加到 Notion 頁面）
                self._generate_and_upload_chart(symbol, stocks_data, page_id, date)
            
            # 添加個股詳細數據（以列表形式，因為表格在 Notion API 中較複雜）
            if stocks_data:
                detail_blocks = []
                detail_blocks.append({
                    "object": "block",
                    "type": "heading_3",
                    "heading_3": {
                        "rich_text": [{"type": "text", "text": {"content": "個股詳細數據"}}]
                    }
                })
                
                for stock in stocks_data:
                    symbol = stock.get("symbol", "")
                    price = stock.get("price", 0)
                    change = stock.get("change_percent", 0)
                    signal = stock.get("ai_signal", "HOLD")
                    risk = stock.get("risk_level", "MEDIUM")
                    rsi = stock.get("rsi")
                    
                    # 為每個標的創建一個 bullet list item
                    change_emoji = "📈" if change > 0 else "📉" if change < 0 else "➡️"
                    signal_emoji = "🟢" if signal == "BUY" else "🔴" if signal == "SELL" else "🟡"
                    
                    stock_text = f"{change_emoji} {symbol}: ${price:.2f} ({change:+.2f}%) | {signal_emoji} {signal} | 風險: {risk}"
                    if rsi:
                        stock_text += f" | RSI: {rsi:.2f}"
                    
                    detail_blocks.append({
                        "object": "block",
                        "type": "bulleted_list_item",
                        "bulleted_list_item": {
                            "rich_text": [{"type": "text", "text": {"content": stock_text}}]
                        }
                    })
                
                # 追加詳細數據區塊到頁面
                try:
                    self.client.blocks.children.append(
                        block_id=page_id,
                        children=detail_blocks
                    )
                except Exception as e:
                    logger.warning(f"追加詳細數據區塊失敗: {str(e)}")
            
            logger.info(f"Notion 日報創建成功: {date}")
            return page_id
            
        except Exception as e:
            logger.error(f"創建 Notion 日報失敗: {str(e)}", exc_info=True)
            return None
    
    def _generate_and_upload_chart(self, symbol: str, stocks_data: List[Dict], 
                                   page_id: Optional[str] = None, date: Optional[str] = None) -> Optional[str]:
        """
        生成圖表並上傳到 Notion
        
        Args:
            symbol: 股票代號
            stocks_data: 股票數據列表
            page_id: Notion 頁面 ID（用於上傳圖片）
        
        Returns:
            圖表文件路徑，如果失敗則返回 None
        """
        try:
            # 從數據庫獲取歷史價格和指標數據
            db = get_db_sync()
            try:
                prices = get_prices_by_symbol(db, symbol, days=60)  # 獲取60天數據用於繪圖
                indicators = get_indicators_by_symbol(db, symbol, days=60)
            finally:
                db.close()
            
            if not prices or len(prices) < 2:
                logger.warning(f"{symbol}: 價格數據不足，無法生成圖表")
                return None
            
            # 提取 RSI 值
            rsi_values = None
            if indicators:
                # 將 indicators 按時間戳匹配到 prices
                indicator_dict = {ind.timestamp.date(): ind.rsi for ind in indicators if ind.rsi is not None}
                rsi_values = [indicator_dict.get(p.timestamp.date()) for p in prices]
                # 如果某些日期沒有 RSI，用 None 填充
                rsi_values = [rsi if rsi is not None else None for rsi in rsi_values]
            
            # 生成圖表
            chart_path = self.chart_generator.generate_stock_chart(
                symbol=symbol,
                prices=prices,
                ma20=None,  # 會在圖表中計算
                ma50=None,  # 會在圖表中計算
                rsi_values=rsi_values
            )
            
            if chart_path and page_id:
                # 使用傳入的日期，如果沒有則使用當前日期
                if not date:
                    date = datetime.now().strftime("%Y-%m-%d")
                
                # 嘗試上傳圖片並添加到 Notion
                image_url = self._upload_image_to_notion(chart_path, symbol, date)
                if image_url:
                    # 添加圖片到 Notion 頁面
                    try:
                        self.client.blocks.children.append(
                            block_id=page_id,
                            children=[{
                                "object": "block",
                                "type": "image",
                                "image": {
                                    "type": "external",
                                    "external": {
                                        "url": image_url
                                    }
                                }
                            }]
                        )
                        logger.info(f"{symbol}: 圖表已上傳到 Notion: {image_url}")
                    except Exception as e:
                        logger.warning(f"{symbol}: 上傳圖表到 Notion 失敗: {str(e)}")
                else:
                    logger.info(f"{symbol}: 圖表已生成，路徑: {chart_path}（未上傳，需要配置 GitHub 或 Imgur）")
            
            return chart_path
        except Exception as e:
            logger.error(f"{symbol}: 生成或上傳圖表時發生錯誤: {str(e)}", exc_info=True)
            return None
    
    def _upload_image_to_github(self, image_path: str, symbol: str, date: str) -> Optional[str]:
        """
        上傳圖片到 GitHub repo 並返回公開 URL
        
        Args:
            image_path: 圖片文件路徑
            symbol: 股票代號
            date: 日期（YYYY-MM-DD）
        
        Returns:
            圖片的公開 URL（raw.githubusercontent.com），如果失敗則返回 None
        """
        if not settings.GITHUB_TOKEN or not settings.GITHUB_REPO_OWNER or not settings.GITHUB_REPO_NAME:
            logger.debug("GitHub 配置不完整，跳過圖片上傳")
            return None
        
        try:
            # 讀取圖片文件並轉換為 base64
            with open(image_path, 'rb') as f:
                image_content = base64.b64encode(f.read()).decode('utf-8')
            
            # 構建文件路徑：charts/YYYY-MM-DD/SYMBOL.png
            file_path = f"{settings.GITHUB_CHART_PATH}/{date}/{symbol}.png"
            
            # GitHub API URL
            api_url = f"https://api.github.com/repos/{settings.GITHUB_REPO_OWNER}/{settings.GITHUB_REPO_NAME}/contents/{file_path}"
            
            # 檢查文件是否已存在
            headers = {
                'Authorization': f'token {settings.GITHUB_TOKEN}',
                'Accept': 'application/vnd.github.v3+json'
            }
            
            # 先檢查文件是否存在
            check_response = requests.get(api_url, headers=headers)
            sha = None
            if check_response.status_code == 200:
                # 文件已存在，獲取 SHA 用於更新
                sha = check_response.json().get('sha')
                logger.info(f"{symbol}: 文件已存在，將更新")
            
            # 準備上傳數據
            data = {
                'message': f'Add chart for {symbol} on {date}',
                'content': image_content,
                'branch': settings.GITHUB_BRANCH
            }
            
            if sha:
                data['sha'] = sha
            
            # 上傳文件
            response = requests.put(api_url, headers=headers, json=data)
            
            if response.status_code in [200, 201]:
                # 構建公開 URL
                # 格式: https://raw.githubusercontent.com/owner/repo/branch/path
                public_url = f"https://raw.githubusercontent.com/{settings.GITHUB_REPO_OWNER}/{settings.GITHUB_REPO_NAME}/{settings.GITHUB_BRANCH}/{file_path}"
                logger.info(f"{symbol}: 圖片已上傳到 GitHub: {public_url}")
                return public_url
            else:
                logger.error(f"{symbol}: GitHub 上傳失敗: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"{symbol}: GitHub 上傳失敗: {str(e)}", exc_info=True)
            return None
    
    def _upload_image_to_notion(self, image_path: str, symbol: str, date: str) -> Optional[str]:
        """
        上傳圖片並返回公開 URL
        
        Args:
            image_path: 圖片文件路徑
            symbol: 股票代號
            date: 日期
        
        Returns:
            圖片的公開 URL，如果失敗則返回 None
        """
        # 優先使用 GitHub
        github_url = self._upload_image_to_github(image_path, symbol, date)
        if github_url:
            return github_url
        
        # 備選方案：使用 Imgur（如果配置了）
        imgur_client_id = os.getenv('IMGUR_CLIENT_ID')
        if imgur_client_id:
            try:
                with open(image_path, 'rb') as f:
                    response = requests.post(
                        'https://api.imgur.com/3/image',
                        headers={'Authorization': f'Client-ID {imgur_client_id}'},
                        files={'image': f}
                    )
                    if response.status_code == 200:
                        data = response.json()
                        if data.get('success'):
                            image_url = data['data']['link']
                            logger.info(f"{symbol}: 圖片已上傳到 Imgur: {image_url}")
                            return image_url
            except Exception as e:
                logger.warning(f"Imgur 上傳失敗: {str(e)}")
        
        # 如果都沒有配置，返回 None
        logger.warning(f"{symbol}: 未配置圖片上傳服務，圖表保存在: {image_path}")
        return None
    
    def log_event(self, event_type: str, symbol: str, message: str,
                 severity: str = "INFO", details: Optional[str] = None) -> bool:
        """
        記錄事件到 Notion（如果有事件記錄數據庫）
        
        Args:
            event_type: 事件類型
            symbol: 股票代號
            message: 事件消息
            severity: 嚴重程度
            details: 詳細信息
        
        Returns:
            是否成功
        """
        # 這個功能需要事件記錄數據庫，暫時只記錄日誌
        logger.info(f"事件記錄: [{event_type}] {symbol} - {message} ({severity})")
        # TODO: 實現事件記錄數據庫的更新
        return True

