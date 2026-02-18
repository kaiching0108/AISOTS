"""Telegram 通知與 Bot"""
import re
import asyncio
import logging
import requests
from typing import Optional, Dict, Any
from datetime import datetime

from telegram import BotCommand, Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.request import HTTPXRequest

logger = logging.getLogger(__name__)


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
    
    def send_message(self, text: str, parse_mode: str = "Markdown") -> bool:
        """發送訊息"""
        if not self.enabled:
            return False
        
        try:
            url = f"{self.api_url}/sendMessage"
            data = {
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": parse_mode
            }
            
            response = requests.post(url, json=data, timeout=10)
            result = response.json()
            
            if result.get("ok"):
                return True
            else:
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
    
    def send_long_message(self, text: str, parse_mode: str = "Markdown") -> bool:
        """發送長訊息，自動分段處理 Telegram 字數限制
        
        Telegram 普通訊息上限為 4096 字元，此方法會自動分段發送。
        
        Args:
            text: 要發送的訊息內容
            parse_mode: Markdown 或 HTML
            
        Returns:
            bool: 是否全部發送成功
        """
        if not self.enabled:
            return False
        
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

    def __init__(self, config: dict, command_handler):
        self.enabled = config.get("enabled", True)
        self.bot_token = config.get("bot_token", "")
        self.chat_id = config.get("chat_id", "")
        self.command_handler = command_handler

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

🔍 【查詢類】
• status / 系統狀態 - 系統狀態
• positions / 部位 - 目前部位
• strategies / 策略 - 所有策略
• performance / 績效 - 當日績效
• risk / 風控 - 風控狀態
• orders / 訂單 - 訂單歷史
• price <代碼> - 查詢報價
  例: price TXF

📦 【策略管理】
• enable <ID> - 啟用策略
  例: enable strategy_001
• disable <ID> - 停用策略
  例: disable strategy_001
• 透過 AI 建立/更新/刪除策略

❓ 【其他】
• help / ? - 顯示此列表
• new - 開始新對話
• cancel - 取消操作
"""
        await update.message.reply_text(help_text, parse_mode="Markdown")

    async def _on_new(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """處理 /new 命令"""
        if not update.message:
            return

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
            result = self.command_handler(user_text)
            await message.reply_text(result, parse_mode="Markdown")
        except Exception as e:
            logger.error(f"處理命令失敗: {e}")
            await message.reply_text(f"❌ 處理命令時發生錯誤: {e}")

    async def _on_error(self, update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        """處理錯誤"""
        logger.error(f"Telegram Bot 錯誤: {context.error}")
