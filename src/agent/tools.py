"""AI Agent 交易工具 - 對應 Nanobot Tool 概念"""
from typing import Any, Dict, Optional
import logging
from datetime import datetime
from src.trading.strategy_manager import StrategyManager
from src.trading.position_manager import PositionManager
from src.trading.order_manager import OrderManager
from src.risk.risk_manager import RiskManager

logger = logging.getLogger(__name__)


class TradingTools:
    """交易工具集 - 供 AI Agent 調用"""
    
    def __init__(
        self,
        strategy_manager: StrategyManager,
        position_manager: PositionManager,
        order_manager: OrderManager,
        risk_manager: RiskManager,
        shioaji_client,
        notifier
    ):
        self.strategy_mgr = strategy_manager
        self.position_mgr = position_manager
        self.order_mgr = order_manager
        self.risk_mgr = risk_manager
        self.api = shioaji_client
        self.notifier = notifier
    
    # ========== 策略工具 ==========
    
    def get_strategies(self) -> str:
        """取得所有策略"""
        strategies = self.strategy_mgr.get_all_strategies()
        
        if not strategies:
            return "目前沒有任何策略"
        
        text = "📋 *策略列表*\n\n"
        for s in strategies:
            status = "✅ 啟用" if s.enabled else "❌ 停用"
            text += f"*{s.name}*\n"
            text += f"  ID: {s.id}\n"
            text += f"  合約: {s.symbol}\n"
            text += f"  狀態: {status}\n"
            text += f"  參數: {s.params}\n\n"
        
        return text
    
    def enable_strategy(self, strategy_id: str) -> str:
        """啟用策略"""
        success = self.strategy_mgr.enable_strategy(strategy_id)
        if success:
            return f"✅ 策略已啟用: {strategy_id}"
        return f"❌ 啟用失敗: {strategy_id}"
    
    def disable_strategy(self, strategy_id: str) -> str:
        """停用策略 (含詢問機制)"""
        
        # 先檢查是否有部位
        check = self.strategy_mgr.disable_strategy_with_check(strategy_id, self.position_mgr)
        
        if not check["can_disable"] and check["has_positions"]:
            # 有部位，發送警告並詢問
            pos = check["position"]
            return f"""
⚠️ *警告：策略仍有部位*
─────────────────
策略ID: {strategy_id}
部位: {pos['symbol']} {pos['direction']} {pos['quantity']}口
進場價: {pos['entry_price']}
現價: {pos.get('current_price', pos['entry_price'])}
損益: {pos['pnl']:+,.0f}

請確認是否強制平倉並停用？

輸入: `confirm disable {strategy_id}` 確認停用
輸入: `cancel` 取消
"""
        
        # 無部位，直接停用
        if check["can_disable"]:
            self.strategy_mgr.disable_strategy(strategy_id)
            return f"✅ 策略已停用: {strategy_id}"
        
        return f"❌ 停用失敗: {strategy_id}"
    
    def confirm_disable_strategy(self, strategy_id: str) -> str:
        """確認停用策略 (含強制平倉)"""
        
        # 取得部位
        position = self.position_mgr.get_position(strategy_id)
        
        if position and position.quantity > 0:
            # 取得現價
            contract = self.api.get_contract(position.symbol)
            current_price = contract.last_price if contract else 0
            
            if current_price > 0:
                # 強制平倉
                close_action = "Sell" if position.direction == "Buy" else "Buy"
                
                # 下單平倉
                self.api.place_order(
                    symbol=position.symbol,
                    action=close_action,
                    quantity=position.quantity,
                    price=0  # 市價
                )
                
                # 更新部位
                result = self.position_mgr.close_position(strategy_id, current_price)
                
                pnl = position.pnl
                emoji = "🟢" if pnl >= 0 else "🔴"
                
                # 發送通知
                self.notifier.send_message(
                    f"{emoji} *強制平倉並停用策略*\n"
                    f"─────────────\n"
                    f"策略: {strategy_id}\n"
                    f"平倉價: {current_price}\n"
                    f"損益: {pnl:+,.0f}"
                )
        
        # 停用策略
        self.strategy_mgr.disable_strategy(strategy_id)
        
        return f"✅ 策略已強制平倉並停用: {strategy_id}"
    
    def create_strategy(
        self,
        strategy_id: str,
        name: str,
        symbol: str,
        prompt: str,
        timeframe: str,
        quantity: int = 1,
        stop_loss: int = 0,
        take_profit: int = 0
    ) -> str:
        """建立新策略"""
        from src.trading.strategy import Strategy
        
        # 驗證必要參數
        if not strategy_id or not strategy_id.strip():
            return "❌ 錯誤：請提供策略 ID"
        if not name or not name.strip():
            return "❌ 錯誤：請提供策略名稱"
        if not symbol or not symbol.strip():
            return "❌ 錯誤：請提供期貨代碼 (如 TXF, MXF, EFF)"
        if not prompt or not prompt.strip():
            return "❌ 錯誤：請提供策略描述"
        
        # 驗證 timeframe
        valid_timeframes = ["1m", "5m", "15m", "30m", "60m", "1h", "1d"]
        if not timeframe or timeframe.strip() not in valid_timeframes:
            return f"❌ 錯誤：請提供有效的 K線週期 (1m/5m/15m/30m/60m/1h/1d)"
        
        # 驗證數值參數
        if quantity < 1:
            return "❌ 錯誤：數量必須 >= 1"
        if stop_loss < 0:
            return "❌ 錯誤：停損不能為負數"
        if take_profit < 0:
            return "❌ 錯誤：止盈不能為負數"
        
        # 檢查 ID 是否已存在
        if self.strategy_mgr.get_strategy(strategy_id):
            return f"❌ 策略 ID 已存在: {strategy_id}"
        
        # 建立參數
        params = {
            "timeframe": timeframe,
            "quantity": quantity,
            "stop_loss": stop_loss,
            "take_profit": take_profit
        }
        
        # 建立策略物件
        strategy = Strategy(
            strategy_id=strategy_id,
            name=name,
            symbol=symbol.upper(),
            prompt=prompt,
            params=params,
            enabled=False
        )
        
        # 儲存策略
        self.strategy_mgr.add_strategy(strategy)
        
        return f"""
✅ *策略已建立*
─────────────
ID: {strategy_id}
名稱: {name}
期貨代碼: {symbol.upper()}
策略描述: {prompt}
數量: {quantity}
停損: {stop_loss}
止盈: {take_profit}

請使用 `enable {strategy_id}` 啟用策略
"""
    
    def update_strategy_prompt(
        self,
        strategy_id: str,
        new_prompt: str
    ) -> str:
        """更新策略描述並重新生成程式碼"""
        
        # 取得策略
        strategy = self.strategy_mgr.get_strategy(strategy_id)
        if not strategy:
            return f"❌ 找不到策略: {strategy_id}"
        
        # 記錄舊 prompt
        old_prompt = strategy.prompt
        
        # 更新 prompt
        strategy.prompt = new_prompt
        self.strategy_mgr.store.save_strategy(strategy.to_dict())
        
        return f"""
✅ *策略已更新*
─────────────
ID: {strategy_id}
名稱: {strategy.name}
舊描述: {old_prompt}
新描述: {new_prompt}

策略程式碼將自動重新生成 (v{strategy.strategy_version + 1})
"""
    
    def delete_strategy_tool(self, strategy_id: str) -> str:
        """刪除策略"""
        
        # 檢查是否有部位
        position = self.position_mgr.get_position(strategy_id)
        if position and position.quantity > 0:
            return f"❌ 無法刪除：策略仍有部位 {position.symbol} {position.quantity}口，請先平倉"
        
        # 檢查策略是否存在
        strategy = self.strategy_mgr.get_strategy(strategy_id)
        if not strategy:
            return f"❌ 找不到策略: {strategy_id}"
        
        # 刪除策略
        self.strategy_mgr.delete_strategy(strategy_id)
        
        return f"✅ 策略已刪除: {strategy_id}"
    
    # ========== 部位工具 ==========
    
    def get_positions(self) -> str:
        """取得目前部位"""
        positions = self.position_mgr.get_all_positions()
        
        if not positions:
            return "📊 目前無部位"
        
        summary = self.position_mgr.get_positions_summary()
        
        text = "📊 *目前部位*\n────────────\n"
        
        for pos in summary["positions"]:
            pnl = pos["pnl"]
            emoji = "🟢" if pnl >= 0 else "🔴"
            
            text += f"""
{emoji} *{pos['strategy_name']}*
  合約: {pos['symbol']}
  方向: {pos['direction']} {pos['quantity']}口
  進場: {pos['entry_price']} → 現價: {pos['current_price']}
  損益: {pnl:+,.0f}
"""
        
        text += f"\n────────────\n"
        text += f"總口數: {summary['total_quantity']}\n"
        text += f"總損益: {summary['total_pnl']:+,.0f}"
        
        return text
    
    def get_position_by_strategy(self, strategy_id: str) -> str:
        """取得指定策略的部位"""
        position = self.position_mgr.get_position(strategy_id)
        
        if not position:
            return f"策略 {strategy_id} 目前無部位"
        
        pnl = position.pnl
        emoji = "🟢" if pnl >= 0 else "🔴"
        
        return f"""
{emoji} *部位資訊*
────────────
策略: {position.strategy_name}
合約: {position.symbol}
方向: {position.direction}
數量: {position.quantity}口
進場價: {position.entry_price}
現價: {position.current_price}
損益: {pnl:+,.0f}
停損: {position.stop_loss}
止盈: {position.take_profit}
"""
    
    # ========== 下單工具 ==========
    
    def place_order(
        self,
        strategy_id: str,
        action: str,
        quantity: int,
        price: float = 0,
        reason: str = "",
        stop_loss: int = 0,
        take_profit: int = 0
    ) -> str:
        """下單
        
        Args:
            stop_loss: 停損點數（0=不啟用）
            take_profit: 止盈點數（0=不啟用）
        """
        # 取得策略資訊
        strategy = self.strategy_mgr.get_strategy(strategy_id)
        if not strategy:
            return f"❌ 找不到策略: {strategy_id}"
        
        symbol = strategy.symbol
        strategy_name = strategy.name
        
        # 風控檢查
        current_positions = self.position_mgr.get_total_quantity()
        daily_pnl = self.risk_mgr.daily_pnl
        
        risk_check = self.risk_mgr.check_order(
            symbol=symbol,
            action=action,
            quantity=quantity,
            price=price,
            current_positions=current_positions,
            daily_pnl=daily_pnl
        )
        
        if not risk_check["passed"]:
            msg = f"❌ 風控擋單: {risk_check['reason']}"
            logger.warning(msg)
            return msg
        
        # 建立訂單
        order = self.order_mgr.create_order(
            strategy_id=strategy_id,
            strategy_name=strategy_name,
            symbol=symbol,
            action=action,
            quantity=quantity,
            price=price,
            reason=reason or strategy.prompt[:50]
        )
        
        # 執行下單
        trade = self.api.place_order(
            symbol=symbol,
            action=action,
            quantity=quantity,
            price=price
        )
        
        if trade:
            self.order_mgr.submit_order(order.order_id, trade.order.seqno if hasattr(trade.order, 'seqno') else None)
            
            # 取得成交價
            filled_price = price
            if hasattr(trade, 'price'):
                filled_price = trade.price
            elif price == 0:
                contract = self.api.get_contract(symbol)
                if contract:
                    filled_price = contract.last_price
            
            # 建立部位（帶入停損止盈點數）
            self.position_mgr.open_position(
                strategy_id=strategy_id,
                strategy_name=strategy_name,
                symbol=symbol,
                direction=action,
                quantity=quantity,
                entry_price=filled_price,
                stop_loss_points=stop_loss,
                take_profit_points=take_profit
            )
            
            msg = f"""
✅ *下單成功*
─────────────
策略: {strategy_name}
合約: {symbol}
方向: {action}
數量: {quantity}口
價格: {filled_price}
停損: {stop_loss}點
止盈: {take_profit}點
"""
            self.notifier.send_order_notification({
                "status": "Submitted",
                "strategy_name": strategy_name,
                "symbol": symbol,
                "action": action,
                "quantity": quantity,
                "price": filled_price,
                "timestamp": datetime.now().isoformat()
            })
            
            return msg
        else:
            self.order_mgr.reject_order(order.order_id, "API 下單失敗")
            return "❌ 下單失敗: API 錯誤"
    
    def close_position(self, strategy_id: str, price: float = 0) -> str:
        """平倉"""
        position = self.position_mgr.get_position(strategy_id)
        if not position:
            return f"❌ 策略 {strategy_id} 無部位可平"
        
        # 取得現價
        if price == 0:
            contract = self.api.get_contract(position.symbol)
            price = contract.last_price if contract else 0
        
        if price == 0:
            return "❌ 無法取得現價"
        
        # 平倉
        result = self.position_mgr.close_position(strategy_id, price)
        
        if result:
            # 反向下一口平倉
            close_action = "Sell" if position.direction == "Buy" else "Buy"
            self.api.place_order(
                symbol=position.symbol,
                action=close_action,
                quantity=position.quantity,
                price=price
            )
            
            pnl = result["pnl"]
            emoji = "🟢" if pnl >= 0 else "🔴"
            
            msg = f"""
{emoji} *平倉完成*
─────────────
策略: {result['strategy_name']}
合約: {result['symbol']}
方向: {close_action} {result['quantity']}口
平倉價: {price}
損益: {pnl:+,.0f}
"""
            self.notifier.send_order_notification({
                "status": "Filled",
                "strategy_name": result["strategy_name"],
                "symbol": result["symbol"],
                "action": close_action,
                "quantity": result["quantity"],
                "filled_price": price,
                "timestamp": datetime.now().isoformat()
            })
            
            return msg
        
        return "❌ 平倉失敗"
    
    # ========== 市場數據工具 ==========
    
    def get_market_data(self, symbol: str) -> str:
        """取得市場報價"""
        contract = self.api.get_contract(symbol)
        
        if not contract:
            return f"❌ 找不到合約: {symbol}"
        
        return f"""
📈 *{contract.name}*
────────────
最新價: {contract.last_price}
漲停: {contract.limit_up}
跌停: {contract.limit_down}
參考價: {contract.reference}
"""
    
    def get_order_history(self, strategy_id: str = None) -> str:
        """取得訂單歷史"""
        if strategy_id:
            orders = self.order_mgr.get_orders_by_strategy(strategy_id)
        else:
            orders = self.order_mgr.get_today_orders()
        
        if not orders:
            return "無訂單記錄"
        
        text = "📜 *訂單記錄*\n────────────\n"
        
        for o in orders[-10:]:  # 顯示最近10筆
            status = o.get("status", "Unknown")
            emoji = {
                "Filled": "✅",
                "Cancelled": "❌",
                "Submitted": "📝",
                "Rejected": "🚫"
            }.get(status, "⚪")
            
            text += f"""
{emoji} {o.get('symbol')} {o.get('action')} {o.get('quantity')}口
  狀態: {status}
  時間: {o.get('timestamp', '')[:19]}
"""
        
        return text
    
    # ========== 績效工具 ==========
    
    def get_performance(self, period: str = "today") -> str:
        """取得績效"""
        stats = self.order_mgr.get_order_statistics()
        
        text = f"""
📊 *績效統計*
────────────
日期: {stats['today']}
總委託: {stats['total_orders']}
成交: {stats['filled']}
取消: {stats['cancelled']}
待處理: {stats['pending']}

部位損益: {self.position_mgr.get_positions_summary()['total_pnl']:+,.0f}
當日風控損益: {self.risk_mgr.daily_pnl:+,.0f}
"""
        
        return text
    
    # ========== 風控工具 ==========
    
    def get_risk_status(self) -> str:
        """取得風控狀態"""
        status = self.risk_mgr.get_status()
        
        return f"""
🛡️ *風控狀態*
────────────
當日損益: {status['daily_pnl']:+,.0f}
最大虧損: {status['max_daily_loss']}
最大部位: {status['max_position']}
本分鐘下單: {status['orders_this_minute']}/{status['max_orders_per_minute']}
停損啟用: {'是' if status['stop_loss_enabled'] else '否'}
止盈啟用: {'是' if status['take_profit_enabled'] else '否'}
"""
    
    def get_system_status(self) -> str:
        """取得系統狀態"""
        conn_status = self.api.connected
        
        text = f"""
🔧 *系統狀態*
────────────
Shioaji: {'✅ 連線' if conn_status else '❌ 斷線'}
策略數: {len(self.strategy_mgr.get_all_strategies())}
啟用策略: {len(self.strategy_mgr.get_enabled_strategies())}
部位數: {len(self.position_mgr.get_all_positions())}
待處理訂單: {len(self.order_mgr.get_pending_orders())}
"""
        
        return text
    
    def get_tool_definitions(self) -> list:
        """取得工具定義 (for LLM)"""
        return [
            {
                "type": "function",
                "function": {
                    "name": "get_system_status",
                    "description": "查詢系統狀態，包含連線是否正常、策略數量、已啟用策略數、目前部位數、待處理訂單數等。相當於問「系統好嗎」、「系統怎麼樣」、「status」。",
                    "parameters": {"type": "object", "properties": {}}
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_positions",
                    "description": "查詢目前持有的所有期貨部位，包含各部位的合約、代價、現價、損益等。相當於問「部位」、「持倉」、「現在有什麼部位」、「positions」。",
                    "parameters": {"type": "object", "properties": {}}
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_strategies",
                    "description": "查詢所有已配置的交易策略及其狀態（啟用/停用）。相當於問「有哪些策略」、「策略列表」。",
                    "parameters": {"type": "object", "properties": {}}
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_performance",
                    "description": "查詢當日交易績效，包含當日損益、總委託次數、成交次數、取消次數等。相當於問「今天賺多少」、「今天績效怎麼樣」、「賺了多少」、「performance」。",
                    "parameters": {"type": "object", "properties": {}}
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_risk_status",
                    "description": "查詢風控狀態，包含當日損益、最大虧損限制、最大部位限制、每分鐘下單次數、停損止盈是否啟用等。相當於問「風控怎麼樣」、「risk」。",
                    "parameters": {"type": "object", "properties": {}}
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_order_history",
                    "description": "查詢歷史委託記錄，可查看已成交、已取消的訂單。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "strategy_id": {"type": "string", "description": "策略ID，可選"}
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_market_data",
                    "description": "取得期貨報價",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "symbol": {"type": "string", "description": "期貨代碼，如 TXF, MXF, EFF"}
                        },
                        "required": ["symbol"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "enable_strategy",
                    "description": "啟用策略",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "strategy_id": {"type": "string", "description": "策略ID"}
                        },
                        "required": ["strategy_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "disable_strategy",
                    "description": "停用策略 (若有部位會詢問確認)",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "strategy_id": {"type": "string", "description": "策略ID"}
                        },
                        "required": ["strategy_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_position_by_strategy",
                    "description": "取得指定策略的部位",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "strategy_id": {"type": "string", "description": "策略ID"}
                        },
                        "required": ["strategy_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "create_strategy",
                    "description": "建立新策略，包含策略ID、名稱、期貨代碼、策略描述、K線週期等參數。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "strategy_id": {"type": "string", "description": "策略ID (自定義，如 my_rsi)"},
                            "name": {"type": "string", "description": "策略名稱"},
                            "symbol": {"type": "string", "description": "期貨代碼 (如 TXF, MXF, EFF)"},
                            "prompt": {"type": "string", "description": "策略描述 (如 RSI 低於 30 買入)"},
                            "timeframe": {
                                "type": "string", 
                                "description": "K線週期 (1m/5m/15m/30m/60m/1h/1d)",
                                "enum": ["1m", "5m", "15m", "30m", "60m", "1h", "1d"]
                            },
                            "quantity": {"type": "integer", "description": "每次交易口數，預設 1"},
                            "stop_loss": {"type": "integer", "description": "停損點數，預設 0"},
                            "take_profit": {"type": "integer", "description": "止盈點數，預設 0"}
                        },
                        "required": ["strategy_id", "name", "symbol", "prompt", "timeframe"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "update_strategy_prompt",
                    "description": "更新策略描述，並自動重新生成策略程式碼。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "strategy_id": {"type": "string", "description": "策略ID"},
                            "new_prompt": {"type": "string", "description": "新的策略描述"}
                        },
                        "required": ["strategy_id", "new_prompt"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "delete_strategy",
                    "description": "刪除策略 (若有部位則無法刪除)",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "strategy_id": {"type": "string", "description": "策略ID"}
                        },
                        "required": ["strategy_id"]
                    }
                }
            },
        ]
    
    def execute_tool(self, tool_name: str, arguments: dict) -> str:
        """執行工具"""
        tool_map = {
            "get_system_status": lambda: self.get_system_status(),
            "get_positions": lambda: self.get_positions(),
            "get_strategies": lambda: self.get_strategies(),
            "get_performance": lambda: self.get_performance(),
            "get_risk_status": lambda: self.get_risk_status(),
            "get_order_history": lambda: self.get_order_history(arguments.get("strategy_id")),
            "get_market_data": lambda: self.get_market_data(arguments.get("symbol", "")),
            "enable_strategy": lambda: self.enable_strategy(arguments.get("strategy_id", "")),
            "disable_strategy": lambda: self.disable_strategy(arguments.get("strategy_id", "")),
            "get_position_by_strategy": lambda: self.get_position_by_strategy(arguments.get("strategy_id", "")),
            "create_strategy": lambda: self.create_strategy(
                strategy_id=arguments.get("strategy_id", ""),
                name=arguments.get("name", ""),
                symbol=arguments.get("symbol", ""),
                prompt=arguments.get("prompt", ""),
                timeframe=arguments.get("timeframe", ""),
                quantity=arguments.get("quantity", 1),
                stop_loss=arguments.get("stop_loss", 0),
                take_profit=arguments.get("take_profit", 0)
            ),
            "update_strategy_prompt": lambda: self.update_strategy_prompt(
                strategy_id=arguments.get("strategy_id", ""),
                new_prompt=arguments.get("new_prompt", "")
            ),
            "delete_strategy": lambda: self.delete_strategy_tool(arguments.get("strategy_id", "")),
        }
        
        tool = tool_map.get(tool_name)
        if tool:
            try:
                return tool()
            except Exception as e:
                logger.error(f"執行工具失敗 {tool_name}: {e}")
                return f"執行失敗: {e}"
        
        return f"未知工具: {tool_name}"
