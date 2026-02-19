"""Telegram 通知與 Bot"""
import re
import asyncio
import requests
from typing import Optional, Dict, Any
from datetime import datetime

from telegram import BotCommand, Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

from src.logger import logger
from telegram.request import HTTPXRequest


def clean_markdown_for_telegram(text: str) -> str:
    """清理 Markdown 格式，轉換為 Telegram 友好的純文字
    
    處理：
    1. 移除 ** 粗體標記
    2. 移除 * 斜體標記
    3. 移除 ###、##、# 標題標記
    4. 將表格轉換為清單格式
    5. 移除 --- 分隔線，改為統一的符號
    6. 移除多餘空行
    
    Args:
        text: 原始文字（可能包含 Markdown）
        
    Returns:
        清理後的純文字
    """
    if not text:
        return text
        
    # 移除粗體標記 **text** → text
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    
    # 移除斜體標記 *text* → text（但保留 emoji 中的星號）
    # 使用 negative lookbehind 避免匹配 emoji
    text = re.sub(r'(?<![\u263a-\U0001f645])\*(.*?)\*(?![\u263a-\U0001f645])', r'\1', text)
    
    # 移除標題標記 ### → 直接文字
    text = re.sub(r'###\s*', '', text)
    text = re.sub(r'##\s*', '', text)
    text = re.sub(r'#\s*', '', text)
    
    # 將表格行轉換為清單
    lines = text.split('\n')
    cleaned_lines = []
    for line in lines:
        # 跳過表格分隔線
        if line.strip().startswith('|---') or line.strip().startswith('|=='):
            continue
        # 處理表格行 | 欄位1 | 欄位2 |
        if '|' in line and line.count('|') >= 2:
            parts = [p.strip() for p in line.split('|') if p.strip()]
            if len(parts) >= 2:
                # 將表格轉為 • 格式
                cleaned_lines.append(f"• {' | '.join(parts)}")
            elif len(parts) == 1:
                cleaned_lines.append(f"• {parts[0]}")
            else:
                cleaned_lines.append(line)
        else:
            # 移除 --- 或 === 分隔線
            if line.strip() == '---' or line.strip().startswith('===') or line.strip().startswith('---'):
                cleaned_lines.append('─' * 30)  # 改為統一的分隔線
            else:
                cleaned_lines.append(line)
    
    # 重新組合
    text = '\n'.join(cleaned_lines)
    
    # 移除多餘空行
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    return text.strip()


class TelegramNotifier:
    """Telegram 通知機器人"""
    
    def __init__(self, config: dict):
        self.enabled = config.get("enabled", True)
        self.bot_token = config.get("bot_token", "")
        self.chat_id = config.get("chat_id", "")
        
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}"
        
        if not self.bot_token or not self.chat_id:
            logger.warning("Telegram 配置不完整")
            self.enabled = False
    
    def send_message(self, text: str, parse_mode: str = None) -> bool:
        """發送訊息
        
        Args:
            text: 訊息內容（會自動清理 Markdown 格式）
            parse_mode: 解析模式，預設為 None（純文字），可選 "Markdown" 或 "HTML"
        """
        if not self.enabled:
            return False
        
        # 自動清理 Markdown 格式
        text = clean_markdown_for_telegram(text)
        
        try:
            url = f"{self.api_url}/sendMessage"
            data = {
                "chat_id": self.chat_id,
                "text": text
            }
            
            # 只有明確指定時才使用 Markdown/HTML 解析
            if parse_mode:
                data["parse_mode"] = parse_mode
            
            response = requests.post(url, json=data, timeout=10)
            result = response.json()
            
            if result.get("ok"):
                return True
            else:
                # 如果發送失敗且使用了 parse_mode，嘗試用純文字重發
                if parse_mode and "parse_mode" in data:
                    logger.warning(f"Telegram 發送失敗（{parse_mode}），嘗試純文字: {result}")
                    data.pop("parse_mode")
                    response = requests.post(url, json=data, timeout=10)
                    result = response.json()
                    return result.get("ok", False)
                logger.error(f"Telegram 發送失敗: {result}")
                return False
                
        except Exception as e:
            logger.error(f"Telegram 發送錯誤: {e}")
            return False
    
    def send_alert(self, title: str, message: str) -> bool:
        """發送警報"""
        text = f"🚨 *{title}*\n\n{message}"
        return self.send_message(text)
    
    def send_system_status(self, status: Dict[str, Any]) -> bool:
        """發送系統狀態"""
        text = f"""
📊 *系統狀態*
────────────
連線: {'✅ 正常' if status.get('connected') else '❌ 異常'}
策略數: {status.get('strategy_count', 0)}
啟用策略: {status.get('enabled_count', 0)}
部位數: {status.get('position_count', 0)}
當日損益: {status.get('daily_pnl', 0):+,.0f}
"""
        return self.send_message(text)
    
    def send_order_notification(self, order_info: Dict[str, Any]) -> bool:
        """發送成交通知"""
        status = order_info.get("status", "")
        
        if status == "Filled":
            emoji = "✅"
            title = "成交通知"
        elif status == "Cancelled":
            emoji = "❌"
            title = "委託取消"
        elif status == "Submitted":
            emoji = "📝"
            title = "委託送出"
        else:
            emoji = "⚠️"
            title = "訂單狀態"
        
        text = f"""
{emoji} *{title}*
────────────
策略: {order_info.get('strategy_name', 'N/A')}
合約: {order_info.get('symbol', 'N/A')}
方向: {order_info.get('action', 'N/A')}
數量: {order_info.get('quantity', 0)}口
{
f"價格: {order_info.get('price', 0)}" if order_info.get('price', 0) > 0 else "價格: 市價"
}
{
f"成交價: {order_info.get('filled_price', 0)}" if order_info.get('filled_price') else ""
}
時間: {order_info.get('timestamp', 'N/A')}
"""
        return self.send_message(text)
    
    def send_position_update(self, positions: list) -> bool:
        """發送部位更新"""
        if not positions:
            text = "📊 *部位更新*\n\n目前無部位"
        else:
            text = "📊 *部位更新*\n────────────\n"
            total_pnl = 0
            
            for pos in positions:
                pnl = pos.get("pnl", 0)
                total_pnl += pnl
                emoji = "🟢" if pnl >= 0 else "🔴"
                
                text += f"""
{emoji} {pos.get('strategy_name', 'N/A')}
  合約: {pos.get('symbol', 'N/A')}
  方向: {pos.get('direction', 'N/A')} {pos.get('quantity', 0)}口
  進場: {pos.get('entry_price', 0)} → 現價: {pos.get('current_price', 0)}
  損益: {pnl:+,.0f}
"""
            
            text += f"\n────────────\n總損益: {total_pnl:+,.0f}"
        
        return self.send_message(text)
    
    def send_performance_report(self, perf: Dict[str, Any]) -> bool:
        """發送績效報表"""
        text = f"""
📈 *績效報表*
────────────
日期: {perf.get('date', 'N/A')}

當日損益: {perf.get('total_pnl', 0):+,.0f}
總交易次數: {perf.get('total_trades', 0)}
勝率: {perf.get('win_rate', 0):.1f}%

{
f"最大回撤: {perf.get('max_drawdown', 0):+,.0f}" if perf.get('max_drawdown') else ""
}
"""
        return self.send_message(text)
    
    def send_error(self, error_message: str) -> bool:
        """發送錯誤訊息"""
        text = f"""
❌ *系統錯誤*
─────────────
{error_message}
時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        return self.send_message(text)
    
    def send_long_message(self, text: str, parse_mode: str = None) -> bool:
        """發送長訊息，自動分段處理 Telegram 字數限制
        
        Telegram 普通訊息上限為 4096 字元，此方法會自動分段發送。
        
        Args:
            text: 要發送的訊息內容（會自動清理 Markdown 格式）
            parse_mode: Markdown 或 HTML，預設為 None（純文字）
            
        Returns:
            bool: 是否全部發送成功
        """
        if not self.enabled:
            return False
        
        # 自動清理 Markdown 格式
        text = clean_markdown_for_telegram(text)
        
        MAX_LENGTH = 4000
        
        if len(text) <= MAX_LENGTH:
            return self.send_message(text, parse_mode)
        
        parts = []
        current_part = ""
        split_markers = ["\n\n", "\n", "。", "；", "，"]
        
        lines = text.split("\n")
        for line in lines:
            test_part = current_part + ("\n" if current_part else "") + line
            
            if len(test_part) > MAX_LENGTH:
                if current_part:
                    parts.append(current_part)
                
                if len(line) > MAX_LENGTH:
                    for marker in split_markers:
                        if marker in line:
                            subparts = line.split(marker)
                            temp = ""
                            for sp in subparts:
                                if len(temp) + len(sp) + len(marker) > MAX_LENGTH:
                                    if temp:
                                        parts.append(temp)
                                    temp = sp
                                else:
                                    temp += marker + sp if temp else sp
                            current_part = temp
                            break
                    else:
                        current_part = line[:MAX_LENGTH]
                else:
                    current_part = line
            else:
                current_part = test_part
        
        if current_part:
            parts.append(current_part)
        
        if not parts:
            return False
        
        summary = parts[0][:500]
        if len(parts[0]) > 500:
            summary += "..."
        
        first_msg = f"📋 *報告過長，分 {len(parts)} 部分發送*\n\n{summary}"
        self.send_message(first_msg, parse_mode)
        
        for i, part in enumerate(parts[1:], 2):
            part_msg = f"--- 第 {i}/{len(parts)} 部分 ---\n\n{part}"
            self.send_message(part_msg, parse_mode)
        
        return True


class TelegramBot:
    """Telegram Bot - 接收用戶命令"""

    BOT_COMMANDS = [
        BotCommand("start", "開始使用"),
        BotCommand("help", "顯示所有命令"),
        BotCommand("new", "開始新對話"),
    ]

    def __init__(self, config: dict, command_handler, clear_history_callback=None):
        self.enabled = config.get("enabled", True)
        self.bot_token = config.get("bot_token", "")
        self.chat_id = config.get("chat_id", "")
        self.command_handler = command_handler
        self.clear_history_callback = clear_history_callback

        self._app = None
        self._running = False

        if not self.bot_token:
            logger.warning("Telegram Bot token 未設定")
            self.enabled = False
        
        if self.enabled and not self.chat_id:
            logger.error("chat_id 未設定，拒絕啟動 Bot 以防止安全風險")
            self.enabled = False

    async def start(self) -> None:
        """啟動 Telegram Bot (Long Polling)"""
        if not self.enabled:
            logger.info("Telegram Bot 未啟用")
            return

        logger.info("正在啟動 Telegram Bot...")

        req = HTTPXRequest(
            connection_pool_size=16,
            pool_timeout=30.0,
            connect_timeout=30.0,
            read_timeout=30.0
        )

        builder = Application.builder().token(self.bot_token).request(req)
        self._app = builder.build()
        self._app.add_error_handler(self._on_error)

        self._app.add_handler(CommandHandler("start", self._on_start))
        self._app.add_handler(CommandHandler("help", self._on_help))
        self._app.add_handler(CommandHandler("new", self._on_new))
        self._app.add_handler(
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                self._on_message
            )
        )

        try:
            await self._app.initialize()
            await self._app.start()
            
            bot_info = await self._app.bot.get_me()
            logger.info(f"Telegram Bot @{bot_info.username} 已連線")
            
            try:
                await self._app.bot.set_my_commands(self.BOT_COMMANDS)
                logger.info("Telegram Bot 命令已註冊")
            except Exception as e:
                logger.warning(f"註冊 Bot 命令失敗: {e}")

            self._running = True
            await self._app.updater.start_polling(
                allowed_updates=["message"],
                drop_pending_updates=True
            )
            
            logger.info("Telegram Bot 已啟動 (Polling 模式)")
        except Exception as e:
            logger.warning(f"Telegram Bot 啟動失敗: {e}")
            self._running = False
            self._app = None

    async def stop(self) -> None:
        """停止 Telegram Bot"""
        self._running = False
        if self._app and self._app.updater:
            logger.info("正在停止 Telegram Bot...")
            try:
                await self._app.updater.stop()
                await self._app.stop()
                await self._app.shutdown()
            except Exception as e:
                logger.warning(f"停止 Telegram Bot 時發生錯誤: {e}")
            self._app = None

    async def _on_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """處理 /start 命令"""
        if not update.message:
            return

        welcome_text = """
👋 歡迎使用 AI 期貨交易系統！

我可以幫您：
📊 查詢系統狀態
📦 查看目前部位
📈 查看當日績效
📋 管理交易策略
❓ 輸入 help 查看所有命令
"""
        await update.message.reply_text(welcome_text)

    async def _on_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """處理 /help 命令"""
        if not update.message:
            return

        help_text = """
📋 *AI 期貨交易系統 - 命令列表*

🤖 【建立策略】（直接對 AI 說）
• 方式一（手動輸入）:
  例: 建立策略 ID=my_rsi, 名稱=RSI策略, 代碼=TXF, 描述=RSI低於30買入
• 方式二（目標驅動）:
  例: 幫我設計一個每日賺500元的策略
  例: 設計一個 RSI 策略

🔍 【基本查詢】
• status              - 系統狀態
• positions / 部位    - 目前部位
• strategies / 策略   - 所有策略
• performance         - 當日整體績效
• risk / 風控         - 風控狀態
• orders / 訂單       - 訂單歷史

📊 【績效查詢】
• performance <ID> [period]  - 查詢策略績效
  例: performance strategy_001 month
  period: today/week/month/quarter/year/all

🔎 【策略狀態】
• status <ID>         - 查詢特定策略狀態
  例: status strategy_001

📦 【策略管理】
• enable <ID>        - 啟用策略
  例: enable strategy_001
• disable <ID>       - 停用策略
  例: disable strategy_001

🎯 【目標與優化】
• goal <ID> <金額> <單位>  - 設定策略目標
  例: goal strategy_001 500 daily
  單位: daily/weekly/monthly/quarterly/yearly
• review <ID>        - LLM 審查策略
• optimize <ID>       - 執行完整優化流程
• confirm optimize   - 確認執行優化修改（需先執行 optimize）

📈 【市場資料】
• price <代碼>        - 查詢報價
  例: price TXF

❓ 【其他】
• help / ?           - 顯示此列表
• new                - 開始新對話
"""
        await update.message.reply_text(help_text, parse_mode="Markdown")

    async def _on_new(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """處理 /new 命令"""
        if not update.message:
            return

        if self.clear_history_callback:
            self.clear_history_callback()
        
        await update.message.reply_text("🔄 已開始新對話，請輸入您的問題或指令。")

    async def _on_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """處理一般訊息"""
        if not update.message:
            return

        message = update.message
        chat_id = str(message.chat_id)

        if self.chat_id and chat_id != self.chat_id:
            logger.warning(f"收到未授權用戶的訊息: {chat_id}")
            return

        user_text = message.text
        if not user_text:
            return

        logger.info(f"收到命令: {user_text}")

        try:
            result = await self.command_handler(user_text)
            # 清理 Markdown 格式後發送
            cleaned_result = clean_markdown_for_telegram(result)
            await message.reply_text(cleaned_result, parse_mode=None)
        except Exception as e:
            logger.error(f"處理命令失敗: {e}")
            error_msg = clean_markdown_for_telegram(f"❌ 處理命令時發生錯誤: {e}")
            await message.reply_text(error_msg, parse_mode=None)

    async def _on_error(self, update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        """處理錯誤"""
        logger.error(f"Telegram Bot 錯誤: {context.error}")
