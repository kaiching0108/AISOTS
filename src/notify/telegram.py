"""Telegram 通知"""
import requests
import logging
from typing import Optional, Dict, Any
from datetime import datetime

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
────────────
{error_message}
時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        return self.send_message(text)
