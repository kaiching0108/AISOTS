"""AI Agent 交易工具 - 對應 Nanobot Tool 概念"""
import asyncio
import random
from typing import Any, Dict, Optional
from datetime import datetime
from src.logger import logger
from src.trading.strategy_manager import StrategyManager
from src.trading.position_manager import PositionManager
from src.trading.order_manager import OrderManager
from src.risk.risk_manager import RiskManager
from src.notify.telegram import clean_markdown_for_telegram


class TradingTools:
    """交易工具集 - 供 AI Agent 調用"""
    
    def __init__(
        self,
        strategy_manager: StrategyManager,
        position_manager: PositionManager,
        order_manager: OrderManager,
        risk_manager: RiskManager,
        shioaji_client,
        notifier,
        llm_provider=None,
        valid_symbols: list = None
    ):
        self.strategy_mgr = strategy_manager
        self.position_mgr = position_manager
        self.order_mgr = order_manager
        self.risk_mgr = risk_manager
        self.api = shioaji_client
        self.notifier = notifier
        self._llm_provider = llm_provider
        
        # 從 Shioaji 取得可用期貨代碼，若無則使用預設列表
        if valid_symbols:
            self._valid_symbols = valid_symbols
        else:
            self._valid_symbols = ["TXF", "MXF", "TMF", "T5F", "XIF", "TE"]
        
        # 期貨代碼與中文名稱對應表
        self._futures_names: Dict[str, str] = {}
        
        self._pending_strategy: Optional[Dict[str, Any]] = None
        self._awaiting_symbol: bool = False
        self._awaiting_confirm: bool = False
        self._current_goal: Optional[str] = None
        
        # 手動建立策略 Q&A 流程狀態
        self._awaiting_create_input: bool = False
        self._create_step: str = ""  # name, symbol, prompt, timeframe, quantity, stop_loss, take_profit, confirm
        self._pending_create_data: Dict[str, Any] = {}
        
        self._pending_optimization: Optional[Dict[str, Any]] = None
        
        self._signal_recorder = None
        self._performance_analyzer = None
    
    def _get_signal_recorder(self):
        """取得訊號記錄器（lazy loading）"""
        if self._signal_recorder is None:
            from src.analysis.signal_recorder import SignalRecorder
            workspace = self.strategy_mgr.workspace_dir
            self._signal_recorder = SignalRecorder(workspace)
        return self._signal_recorder
    
    def _get_performance_analyzer(self):
        """取得績效分析器（lazy loading）"""
        if self._performance_analyzer is None:
            from src.analysis.performance_analyzer import PerformanceAnalyzer
            self._performance_analyzer = PerformanceAnalyzer(self._get_signal_recorder())
        return self._performance_analyzer
    
    def update_valid_symbols(self, symbols: list = None) -> None:
        """更新可用期貨代碼列表"""
        if symbols:
            self._valid_symbols = symbols
            logger.info(f"已更新可用期貨代碼: {symbols}")
        elif self.api:
            try:
                symbols = self.api.get_available_futures_symbols()
                self._valid_symbols = symbols
                logger.info(f"已從 Shioaji 取得可用期貨代碼: {symbols}")
            except Exception as e:
                logger.warning(f"從 Shioaji 取得期貨代碼失敗: {e}")
        
        # 取得期貨代碼對應的中文名稱
        if self.api:
            try:
                self._futures_names = self.api.get_futures_name_mapping()
                logger.info(f"已取得期貨代碼對應表: {self._futures_names}")
            except Exception as e:
                logger.warning(f"取得期貨代碼對應表失敗: {e}")
                self._futures_names = {
                    "TXF": "臺股期貨",
                    "MXF": "小型臺指",
                    "TMF": "微型臺指期貨",
                    "T5F": "臺灣50期貨",
                    "XIF": "非金電期貨",
                    "TE": "電子期貨"
                }
    
    def get_futures_name(self, symbol: str) -> str:
        """取得期貨代碼的中文名稱"""
        return self._futures_names.get(symbol, symbol)
    
    def get_futures_list_for_llm(self) -> str:
        """取得期貨列表（供 LLM 使用）"""
        if not self._futures_names:
            self.update_valid_symbols()
        
        items = [f"- {code}: {name}" for code, name in self._futures_names.items()]
        return "\n".join(items[:20])  # 限制顯示前20個
    
    # ========== 策略工具 ==========
    
    def get_strategies(self) -> str:
        """取得所有策略"""
        strategies = self.strategy_mgr.get_all_strategies()
        
        if not strategies:
            return "目前沒有任何策略"
        
        text = f"📋 策略列表（共 {len(strategies)} 個）\n"
        text += "────────────────────\n\n"
        
        for s in strategies:
            status = "✅ 啟用" if s.enabled else "❌ 停用"
            
            # 策略名稱和狀態
            text += f"{status} {s.name}\n"
            text += f"• ID: {s.id}\n"
            text += f"• 期貨代碼: {s.symbol}（{self.get_futures_name(s.symbol)}）\n"
            text += f"• 版本: v{s.strategy_version}\n"
            
            # 策略描述（prompt）
            if s.prompt:
                prompt_short = s.prompt[:50] + "..." if len(s.prompt) > 50 else s.prompt
                text += f"• 策略描述: {prompt_short}\n"
            
            # 參數
            params = s.params or {}
            if params.get("timeframe"):
                text += f"• K線週期: {params.get('timeframe')}\n"
            if params.get("quantity"):
                text += f"• 口數: {params.get('quantity')}口\n"
            if params.get("stop_loss"):
                text += f"• 停損: {params.get('stop_loss')}點\n"
            if params.get("take_profit"):
                text += f"• 止盈: {params.get('take_profit')}點\n"
            
            # 目標
            if s.goal:
                unit_names = {"daily": "每日", "weekly": "每週", "monthly": "每月"}
                unit = unit_names.get(s.goal_unit, s.goal_unit)
                goal_val = int(s.goal) if str(s.goal).isdigit() else s.goal
                text += f"• 目標: {unit}賺 {goal_val} 元\n"
            
            text += "\n"
        
        text += "────────────────────\n"
        text += "輸入「策略 <ID>」查看詳細狀態"
        
        return text
    
    def get_strategy_status(self, strategy_id: str) -> str:
        """取得特定策略狀態"""
        strategies = self.strategy_mgr.get_all_strategies()
        
        strategy = strategies.get(strategy_id)
        if not strategy:
            return f"❌ 找不到策略: {strategy_id}"
        
        status = "✅ 執行中" if strategy.is_running else "❌ 已停用"
        pnl = ""
        
        position = self.position_mgr.get_position(strategy_id)
        if position and position.quantity > 0:
            pnl = f"""
部位:
  合約: {position.symbol}
  方向: {position.direction} {position.quantity}口
  進場: {position.entry_price} → 現價: {position.current_price}
  損益: {position.pnl:+,.0f}"""
        
        text = f"""📊 *策略狀態*
─────────────
ID: {strategy.id}
名稱: {strategy.name}
合約: {strategy.symbol}
狀態: {status}
K線週期: {strategy.params.get('timeframe', 'N/A')}
停損: {strategy.params.get('stop_loss', 0)}點
止盈: {strategy.params.get('take_profit', 0)}點
數量: {strategy.params.get('position_size', 1)}口
最後訊號: {strategy.last_signal or 'N/A'}
最後訊號時間: {strategy.last_signal_time or 'N/A'}{pnl}"""
        
        return text
    
    def enable_strategy(self, strategy_id: str) -> str:
        """啟用策略"""
        logger.info(f"Enable strategy called: {strategy_id}")
        
        # 找到要 enable 的策略
        strategy = self.strategy_mgr.get_strategy(strategy_id)
        if not strategy:
            logger.error(f"Strategy not found: {strategy_id}")
            return f"❌ 找不到策略: {strategy_id}"
        
        # 檢查策略是否已通過驗證
        if not strategy.verified:
            if strategy.verification_status == "failed":
                return f"""❌ 無法啟用策略：驗證失敗
────────────────
ID: {strategy_id}
名稱: {strategy.name}
驗證狀態：失敗
原因：{strategy.verification_error}

請重新建立策略或修改策略描述"""
            else:
                return f"""❌ 無法啟用策略：尚未通過驗證
────────────────
ID: {strategy_id}
名稱: {strategy.name}
驗證狀態：{strategy.verification_status}

請稍後再試或重新建立策略"""
        
        logger.info(f"Found strategy: {strategy.name}, current enabled: {strategy.enabled}")
        
        # 檢查同一 symbol 是否有其他版本已 enable
        same_symbol_strategies = [
            s for s in self.strategy_mgr.get_all_strategies()
            if s.symbol == strategy.symbol and s.id != strategy_id and s.enabled
        ]
        
        disabled = []
        for s in same_symbol_strategies:
            self.strategy_mgr.disable_strategy(s.id)
            disabled.append(f"{s.id} ({s.name})")
        
        # enable 當前策略
        success = self.strategy_mgr.enable_strategy(strategy_id)
        logger.info(f"Enable result: {success}")
        
        if success:
            params = strategy.params or {}
            timeframe = params.get("timeframe", "未知")
            quantity = params.get("quantity", 1)
            stop_loss = params.get("stop_loss", 0)
            
            result = f"""✅ *{strategy_id} 策略已啟動！*
────────────────────
📌 策略名稱：{strategy.name}
📌 期貨代碼：{strategy.symbol}（{self.get_futures_name(strategy.symbol)}）
📌 K線週期：{timeframe}
📌 交易口數：{quantity}口
📌 停損：{stop_loss}點

⏰ 系統將在交易時間內自動執行交易

📊 可用指令：
• `status {strategy_id}` - 查看策略狀態
• `positions` - 查看目前部位
• `performance` - 查看當日績效
• `disable {strategy_id}` - 停用策略

────────────────────
✅ 策略已啟動完成，無需其他操作！"""
            if disabled:
                result += f"\n\n⚠️ 已自動停用以下舊版本：\n" + "\n".join(f"  - {d}" for d in disabled)
            return result
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
    
    def _generate_strategy_id(self, symbol: str) -> str:
        """自動生成策略 ID：symbol + 年份後2碼 + 4位數字"""
        from datetime import datetime
        
        symbol = symbol.upper().strip()
        year = str(datetime.now().year)[-2:]
        
        for num in range(10000):
            new_id = f"{symbol}{year}{num:04d}"
            if not self.strategy_mgr.get_strategy(new_id):
                return new_id
        
        import random
        return f"{symbol}{year}{random.randint(0, 9999):04d}"
    
    def create_strategy(
        self,
        name: str,
        symbol: str,
        prompt: str,
        timeframe: str,
        quantity: int = 1,
        stop_loss: int = 0,
        take_profit: int = 0
    ) -> str:
        """建立新策略（自動生成 ID）"""
        from src.trading.strategy import Strategy
        
        # 驗證必要參數
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
        
        # 自動生成策略 ID
        strategy_id = self._generate_strategy_id(symbol)
        
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
        old_version = strategy.strategy_version
        
        # 更新 prompt 並遞增版本
        strategy.prompt = new_prompt
        strategy.strategy_version = old_version + 1
        
        # 歸檔舊版本訊號，建立新版本
        self._get_signal_recorder().archive_to_new_version(
            strategy_id=strategy_id,
            old_version=old_version,
            new_version=strategy.strategy_version
        )
        
        self.strategy_mgr.store.save_strategy(strategy.to_dict())
        
        return f"""
✅ *策略已更新*
────────────
ID: {strategy_id}
名稱: {strategy.name}
舊版本: v{old_version}
新版本: v{strategy.strategy_version}
舊描述: {old_prompt}
新描述: {new_prompt}

策略程式碼將自動重新生成
新版本訊號將記錄到 v{strategy.strategy_version}.json
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
    
    def create_strategy_by_goal(self, goal: str, symbol: Optional[str] = None) -> str:
        """根據用戶目標建立策略（自動推斷參數）
        
        當用戶說「幫我建立策略」時調用此 tool。
        - 若 symbol 為 None，回覆訊息要求用戶指定期貨代碼
        - 若 symbol 已提供，推斷參數並展示，詢問確認
        """
        if symbol is None or symbol.strip() == "":
            self._awaiting_symbol = True
            self._current_goal = goal
            self._pending_strategy = None
            self._awaiting_confirm = False
            return "請問要使用哪個期貨合約？（如 TXF、MXF、EFF）"
        
        symbol = symbol.upper().strip()
        
        if symbol not in self._valid_symbols:
            name = self.get_futures_name(symbol)
            valid_list = [f"{s}({self.get_futures_name(s)})" for s in self._valid_symbols[:10]]
            return f"❌ 無效的期貨代碼：{name}\n可用代碼：{', '.join(valid_list)}"
        
        self._awaiting_symbol = False
        self._awaiting_confirm = True
        self._current_goal = goal
        
        # 先推斷基本參數
        inferred = self._infer_strategy_params(goal, symbol)
        
        # 使用 LLM 設計具體的策略邏輯
        logger.info(f"Attempting to design strategy with LLM. Provider: {self._llm_provider is not None}")
        if self._llm_provider:
            try:
                import asyncio
                import nest_asyncio
                nest_asyncio.apply()
                
                design_prompt = f"""請為以下交易策略設計具體的交易邏輯和進出場條件：

目標：{goal}
商品：{symbol}
停損：{inferred['stop_loss']}點
止盈：{inferred['take_profit']}點

請設計一個完整的交易策略，包含：
1. 使用的技術指標（如RSI、MACD、均線等）
2. 具體的買入條件
3. 具體的賣出條件
4. 停損止盈的執行邏輯

請用繁體中文回答，直接描述策略邏輯即可，不需要代碼。"""
                
                logger.info(f"Calling LLM to design strategy...")
                messages = [{"role": "user", "content": design_prompt}]
                
                # 使用 nest_asyncio 來支持在已有 event loop 中運行
                loop = asyncio.get_event_loop()
                response = loop.run_until_complete(
                    self._llm_provider.chat(messages, temperature=0.7)
                )
                
                designed_prompt = response.strip()
                logger.info(f"LLM designed prompt: {designed_prompt[:100]}...")
                
                if designed_prompt:
                    inferred['prompt'] = designed_prompt
                    logger.info("Strategy prompt updated with LLM design")
            except Exception as e:
                logger.warning(f"LLM 設計策略失敗，使用預設描述: {e}")
                import traceback
                logger.warning(traceback.format_exc())
        else:
            logger.warning("LLM provider not available, using default prompt")
        
        self._pending_strategy = inferred
        
        return self._format_strategy_confirmation(inferred)
    
    def _infer_strategy_params(self, goal: str, symbol: str) -> Dict[str, Any]:
        """根據目標推斷策略參數"""
        import random
        import hashlib
        import re
        
        goal_lower = goal.lower()
        
        # 從目標描述中提取數字（如「每日賺2000元」提取 2000）
        goal_value = None
        # 匹配數字（支持千分位逗號）
        numbers = re.findall(r'(\d{1,3}(?:,\d{3})*|\d+)', goal)
        if numbers:
            # 取最後一個數字（通常是目標金額）
            goal_value = int(numbers[-1].replace(',', ''))
        
        # 根據用戶輸入推斷策略類型和參數
        # 注意：prompt 是描述性的，讓 LLM 去發揮生成具體策略代碼
        
        if "rsi" in goal_lower:
            name = f"RSI策略_{symbol}"
            prompt = f"使用RSI指標在{symbol}上交易，目標"
            timeframe = "15m"
            stop_loss = 30
            take_profit = 50
        elif "macd" in goal_lower or "金叉" in goal_lower or "死叉" in goal_lower:
            name = f"MACD策略_{symbol}"
            prompt = f"使用MACD指標在{symbol}上交易，目標"
            timeframe = "15m"
            stop_loss = 40
            take_profit = 60
        elif "均線" in goal_lower:
            name = f"均線策略_{symbol}"
            prompt = f"使用均線系統在{symbol}上交易，目標"
            timeframe = "15m"
            stop_loss = 30
            take_profit = 50
        elif "突破" in goal_lower:
            name = f"突破策略_{symbol}"
            prompt = f"使用突破策略在{symbol}上交易，目標"
            timeframe = "15m"
            stop_loss = 40
            take_profit = 80
        elif "布林" in goal_lower:
            name = f"布林帶策略_{symbol}"
            prompt = f"使用布林帶指標在{symbol}上交易，目標"
            timeframe = "15m"
            stop_loss = 35
            take_profit = 70
        elif "動量" in goal_lower:
            name = f"動量策略_{symbol}"
            prompt = f"使用動量指標在{symbol}上交易，目標"
            timeframe = "1h"
            stop_loss = 50
            take_profit = 100
        else:
            name = f"收益策略_{symbol}"
            prompt = f"設計一個交易策略在{symbol}上執行，目標"
            timeframe = "15m"
            stop_loss = 30
            take_profit = 50
        
        # 將用戶的原始目標描述附加到 prompt
        if goal_value:
            prompt += f"每日獲利{goal_value}元，停損{stop_loss}點，止盈{take_profit}點。請根據此目標設計完整的交易邏輯和進出場條件。"
        else:
            prompt += f"：{goal}。請根據此目標設計完整的交易邏輯和進出場條件。"
        
        return {
            "name": name,
            "symbol": symbol,
            "prompt": prompt,
            "timeframe": timeframe,
            "quantity": 1,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "goal": goal_value  # 存數字而不是文字描述
        }
    
    def _clean_markdown_for_telegram(self, text: str) -> str:
        """清理 Markdown 格式，轉換為 Telegram 友好的純文字
        
        調用全域函數進行清理
        """
        return clean_markdown_for_telegram(text)
    
    def _format_strategy_confirmation(self, params: Dict[str, Any]) -> str:
        """格式化策略確認訊息"""
        # 清理策略描述中的 Markdown
        clean_prompt = self._clean_markdown_for_telegram(params['prompt'])
        
        # 顯示完整策略描述，不截斷
        display_prompt = clean_prompt
        
        return f"""📋 策略參數確認
{'='*30}

📌 基本資訊
名稱: {params['name']}
期貨: {params['symbol']}
K線週期: {params['timeframe']}
口數: {params['quantity']}

📊 風險控制
停損: {params['stop_loss']}點
止盈: {params['take_profit']}點

📝 策略描述
{display_prompt}

{'='*30}
輸入「確認」建立策略
或修改參數（如「停損改成50點」）"""
    
    def modify_strategy_params(self, modifications: str) -> str:
        """修改待確認的策略參數，並重新生成策略 prompt"""
        if not self._pending_strategy or not self._awaiting_confirm:
            return "❌ 沒有待確認的策略，請先說「幫我建立策略」"
        
        modifications_lower = modifications.lower()
        params = self._pending_strategy
        modified = False
        
        if "停損" in modifications and "改成" in modifications:
            try:
                new_stop_loss = int(modifications.split("改成")[1].split("點")[0].strip())
                params["stop_loss"] = new_stop_loss
                modified = True
            except (ValueError, IndexError):
                return "❌ 無法解析停損參數，請使用格式「停損改成XX點」"
        
        if "止盈" in modifications and "改成" in modifications:
            try:
                new_take_profit = int(modifications.split("改成")[1].split("點")[0].strip())
                params["take_profit"] = new_take_profit
                modified = True
            except (ValueError, IndexError):
                return "❌ 無法解析止盈參數，請使用格式「止盈改成XX點」"
        
        if "週期" in modifications and "改成" in modifications:
            new_timeframe = modifications.split("改成")[1].strip()
            valid_timeframes = ["1m", "5m", "15m", "30m", "60m", "1h", "1d"]
            if new_timeframe in valid_timeframes:
                params["timeframe"] = new_timeframe
                modified = True
            else:
                return f"❌ 無效的K線週期，請使用 {', '.join(valid_timeframes)}"
        
        if "口數" in modifications and "改成" in modifications:
            try:
                new_quantity = int(modifications.split("改成")[1].strip())
                if new_quantity >= 1:
                    params["quantity"] = new_quantity
                    modified = True
                else:
                    return "❌ 口數必須 >= 1"
            except ValueError:
                return "❌ 無法解析口數參數，請使用格式「口數改成X」"
        
        if "期貨代碼" in modifications and "改成" in modifications:
            new_symbol = modifications.split("改成")[1].strip().upper()
            if new_symbol in self._valid_symbols:
                params["symbol"] = new_symbol
                modified = True
            else:
                valid_list = [f"{s}({self.get_futures_name(s)})" for s in self._valid_symbols[:10]]
                return f"❌ 無效的期貨代碼，請使用 {', '.join(valid_list)}"
        
        if not modified:
            return "❌ 無法解析修改內容，請使用格式如「停損改成50點」或「止盈改成100點」"
        
        prompt_addition = ""
        if params["stop_loss"] > 40:
            prompt_addition += "，嚴格執行停損"
        if params["take_profit"] > params["stop_loss"] * 2:
            prompt_addition += "，採用移動停損保護獲利"
        
        if prompt_addition:
            params["prompt"] = params["prompt"] + prompt_addition
        
        self._pending_strategy = params
        
        return f"""
✏️ *參數已更新*
────────────────
{self._format_strategy_confirmation(params)}

────────────────
輸入「確認」建立策略，或繼續修改參數
"""
    
    def confirm_create_strategy(self, confirmed: bool) -> str:
        """確認或取消建立策略"""
        logger.info(f"confirm_create_strategy: confirmed={confirmed}, pending={self._pending_strategy is not None}, awaiting={self._awaiting_confirm}")
        
        if not self._pending_strategy:
            self._clear_pending()
            return "❌ 沒有待確認的策略，請先說「幫我建立策略」"
        
        if not confirmed:
            self._clear_pending()
            return "❌ 已取消建立策略"
        
        # 確保處於確認狀態
        self._awaiting_confirm = True
        params = self._pending_strategy
        
        # 使用新的 ID 生成系統
        strategy_id = self._generate_strategy_id(params["symbol"])
        
        from src.trading.strategy import Strategy
        
        strategy = Strategy(
            strategy_id=strategy_id,
            name=params["name"],
            symbol=params["symbol"],
            prompt=params["prompt"],
            params={
                "timeframe": params["timeframe"],
                "quantity": params["quantity"],
                "stop_loss": params["stop_loss"],
                "take_profit": params["take_profit"]
            },
            enabled=False,
            goal=params.get("goal"),
            goal_unit=params.get("goal_unit", "daily")
        )
        
        self.strategy_mgr.add_strategy(strategy)
        
        verify_result = asyncio.run(self._verify_strategy_at_creation(strategy))
        
        self.strategy_mgr.store.save_strategy(strategy.to_dict())
        
        goal_text = ""
        if params.get("goal"):
            unit_names = {
                "daily": "每日",
                "weekly": "每週", 
                "monthly": "每月",
                "quarterly": "每季",
                "yearly": "每年"
            }
            unit = params.get("goal_unit", "daily")
            goal_val = params['goal']
            # 處理目標值可能是數字或字串的情況
            if isinstance(goal_val, (int, float)):
                goal_text = f"目標: {unit_names.get(unit, unit)}賺 {goal_val:,} 元\n"
            else:
                goal_text = f"目標: {unit_names.get(unit, unit)}賺 {goal_val} 元\n"
        
        # 清理策略描述中的 Markdown 格式
        clean_prompt = self._clean_markdown_for_telegram(params['prompt'])
        
        # 限制顯示長度
        if len(clean_prompt) > 400:
            display_prompt = clean_prompt[:400] + "\n...(完整內容請查看策略詳情)"
        else:
            display_prompt = clean_prompt
        
        if verify_result["passed"]:
            verification_text = f"✅ 驗證狀態：通過"
        else:
            verification_text = f"❌ 驗證狀態：失敗\n原因：{verify_result.get('error', '未知錯誤')}"
        
        result = f"""✅ 策略已建立（停用中）
{'='*30}

📌 基本資訊
ID: {strategy_id}
名稱: {params['name']}
期貨: {params['symbol']}
K線週期: {params['timeframe']}
口數: {params['quantity']}

📊 風險控制
停損: {params['stop_loss']}點
止盈: {params['take_profit']}點
{goal_text}
📝 策略描述
{display_prompt}

{'='*30}
{verification_text}

{'='*30}
⚠️ 策略已建立但尚未啟用！
請說「啟用 {strategy_id}」開始交易"""
        
        self._clear_pending()
        return result
    
    def _clear_pending(self) -> None:
        """清除待確認的策略狀態"""
        self._pending_strategy = None
        self._awaiting_symbol = False
        self._awaiting_confirm = False
        self._current_goal = None
        self._clear_create_flow()
    
    def _clear_create_flow(self) -> None:
        """清除手動建立策略 Q&A 流程狀態"""
        self._awaiting_create_input = False
        self._create_step = ""
        self._pending_create_data = {}
    
    def start_create_flow(self) -> str:
        """開始手動建立策略 Q&A 流程"""
        self._awaiting_create_input = True
        self._create_step = "name"
        self._pending_create_data = {}
        return """📝 *手動建立策略*
────────────────
請依序輸入以下資訊：

*第一步：策略名稱*
請輸入策略名稱（如：RSI策略、均線策略）
        
輸入「取消」可中止建立流程"""
    
    def handle_create_input(self, user_input: str) -> str:
        """處理手動建立策略的輸入
        
        Args:
            user_input: 用戶輸入
            
        Returns:
            str: 回應訊息
        """
        user_input = user_input.strip()
        
        if user_input in ["取消", "cancel", "abort"]:
            self._clear_create_flow()
            return "❌ 已取消建立策略"
        
        if self._create_step == "name":
            self._pending_create_data["name"] = user_input
            self._create_step = "symbol"
            return """📝 *第二步：期貨代碼*
────────────────
請輸入期貨代碼：
TXF - 臺股期貨
MXF - 小型臺指
TMF - 微型臺指
T5F - 臺灣50期貨
XIF - 非金電期貨
TE - 電子期貨
        
請輸入代碼（如：TXF）"""
        
        elif self._create_step == "symbol":
            symbol = user_input.upper()
            valid_symbols = ["TXF", "MXF", "TMF", "T5F", "XIF", "TE"]
            if symbol not in valid_symbols:
                return f"❌ 無效的期貨代碼，請輸入：{', '.join(valid_symbols)}"
            self._pending_create_data["symbol"] = symbol
            self._create_step = "prompt"
            return """📝 *第三步：策略描述*
────────────────
請輸入策略描述（例如：RSI低於30買入高於70賣出）"""
        
        elif self._create_step == "prompt":
            self._pending_create_data["prompt"] = user_input
            self._create_step = "timeframe"
            return """📝 *第四步：K線週期*
────────────────
請輸入K線週期：
1m  - 1分鐘
5m  - 5分鐘
15m - 15分鐘
30m - 30分鐘
60m - 60分鐘
1h  - 1小時
1d  - 1天
        
請輸入週期（如：15m）"""
        
        elif self._create_step == "timeframe":
            timeframe = user_input.lower().strip()
            valid_timeframes = ["1m", "5m", "15m", "30m", "60m", "1h", "1d"]
            if timeframe not in valid_timeframes:
                return f"❌ 無效的K線週期，請輸入：{', '.join(valid_timeframes)}"
            self._pending_create_data["timeframe"] = timeframe
            self._create_step = "quantity"
            return """📝 *第五步：交易口數*
────────────────
請輸入每次交易的口數（預設：1）"""
        
        elif self._create_step == "quantity":
            try:
                quantity = int(user_input)
                if quantity < 1:
                    return "❌ 數量必須 >= 1，請重新輸入"
                self._pending_create_data["quantity"] = quantity
            except ValueError:
                return "❌ 請輸入有效的數字"
            self._create_step = "stop_loss"
            return """📝 *第六步：停損點數*
────────────────
請輸入停損點數（設為 0 表示不啟用停損）"""
        
        elif self._create_step == "stop_loss":
            try:
                stop_loss = int(user_input)
                if stop_loss < 0:
                    return "❌ 停損不能為負數，請重新輸入"
                self._pending_create_data["stop_loss"] = stop_loss
            except ValueError:
                return "❌ 請輸入有效的數字"
            self._create_step = "take_profit"
            return """📝 *第七步：止盈點數*
────────────────
請輸入止盈點數（設為 0 表示不啟用止盈）"""
        
        elif self._create_step == "take_profit":
            try:
                take_profit = int(user_input)
                if take_profit < 0:
                    return "❌ 止盈不能為負數，請重新輸入"
                self._pending_create_data["take_profit"] = take_profit
            except ValueError:
                return "❌ 請輸入有效的數字"
            self._create_step = "confirm"
            return self._get_create_confirm_message()
        
        elif self._create_step == "confirm":
            if user_input in ["確認", "yes", "y", "確定", "好", "ok"]:
                return self._execute_create_strategy()
            elif user_input in ["取消", "no", "n", "不要"]:
                self._clear_create_flow()
                return "❌ 已取消建立策略"
            else:
                return "請輸入「確認」建立策略，或「取消」放棄"
        
        return "❌ 發生錯誤，請重新輸入「create」開始"
    
    def _get_create_confirm_message(self) -> str:
        """取得建立策略確認訊息"""
        data = self._pending_create_data
        return f"""📝 *第八步：確認建立*
────────────────
請確認以下資訊：

📌 策略名稱：{data.get('name', 'N/A')}
📌 期貨代碼：{data.get('symbol', 'N/A')}
📌 策略描述：{data.get('prompt', 'N/A')}
📌 K線週期：{data.get('timeframe', 'N/A')}
📌 交易口數：{data.get('quantity', 1)}
📌 停損點數：{data.get('stop_loss', 0)}
📌 止盈點數：{data.get('take_profit', 0)}

────────────────
請輸入「確認」建立策略，或「取消」放棄"""
    
    def _execute_create_strategy(self) -> str:
        """執行建立策略"""
        import asyncio
        from src.trading.strategy import Strategy
        
        data = self._pending_create_data
        strategy_id = self._generate_strategy_id(data["symbol"])
        
        strategy = Strategy(
            strategy_id=strategy_id,
            name=data["name"],
            symbol=data["symbol"],
            prompt=data["prompt"],
            params={
                "timeframe": data["timeframe"],
                "quantity": data["quantity"],
                "stop_loss": data["stop_loss"],
                "take_profit": data["take_profit"]
            },
            enabled=False
        )
        
        self.strategy_mgr.add_strategy(strategy)
        
        verify_result = asyncio.run(self._verify_strategy_at_creation(strategy))
        
        self.strategy_mgr.store.save_strategy(strategy.to_dict())
        
        self._clear_create_flow()
        
        if verify_result["passed"]:
            verification_text = f"✅ 驗證狀態：通過"
        else:
            verification_text = f"❌ 驗證狀態：失敗\n原因：{verify_result.get('error', '未知錯誤')}"
        
        return f"""✅ 策略已建立（停用中）
{'='*30}

📌 基本資訊
ID: {strategy_id}
名稱: {data['name']}
期貨: {data['symbol']}
K線週期: {data['timeframe']}
口數: {data['quantity']}

📊 風險控制
停損: {data['stop_loss']}點
止盈: {data['take_profit']}點

📝 策略描述
{data['prompt']}

{'='*30}
{verification_text}

{'='*30}
⚠️ 策略已建立但尚未啟用！
請說「啟用 {strategy_id}」開始交易"""
    
    async def _verify_strategy_at_creation(self, strategy) -> dict:
        """策略建立時自動驗證
        
        Args:
            strategy: 策略物件
            
        Returns:
            dict: {'passed': bool, 'error': str}
        """
        from src.engine.llm_generator import LLMGenerator
        
        if not self._llm_provider:
            logger.warning("No LLM provider, skipping verification")
            return {"passed": True, "error": None}
        
        try:
            llm_generator = LLMGenerator(self._llm_provider)
            
            logger.info(f"Starting verification for strategy: {strategy.id}")
            
            code = await llm_generator.generate(strategy.prompt)
            
            if not code:
                error_msg = "無法生成策略程式碼"
                strategy.set_verification_failed(error_msg)
                return {"passed": False, "error": error_msg}
            
            class_name = llm_generator.extract_class_name(code)
            if not class_name:
                error_msg = "無法解析類別名稱"
                strategy.set_verification_failed(error_msg)
                return {"passed": False, "error": error_msg}
            
            strategy.set_strategy_code(code, class_name)
            
            timeframe = strategy.params.get("timeframe", "15m")
            verify_result = await llm_generator.verify_strategy(
                prompt=strategy.prompt,
                code=code,
                symbol=strategy.symbol,
                timeframe=timeframe,
                max_attempts=3
            )
            
            if verify_result["passed"]:
                strategy.set_verification_passed()
                logger.info(f"Strategy {strategy.id} verified successfully")
                return {"passed": True, "error": None}
            else:
                strategy.set_verification_failed(verify_result["error"])
                logger.warning(f"Strategy {strategy.id} verification failed: {verify_result['error']}")
                return {"passed": False, "error": verify_result["error"]}
                
        except Exception as e:
            error_msg = f"驗證過程發生錯誤: {str(e)}"
            logger.error(f"Verification error for {strategy.id}: {e}")
            strategy.set_verification_failed(error_msg)
            return {"passed": False, "error": error_msg}
    
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
            signal_action = "buy" if action == "Buy" else "sell"
            signal_id = self._get_signal_recorder().record_signal(
                strategy_id=strategy_id,
                strategy_version=strategy.strategy_version,
                signal=signal_action,
                price=filled_price,
                indicators={}
            )
            
            self.position_mgr.open_position(
                strategy_id=strategy_id,
                strategy_name=strategy_name,
                symbol=symbol,
                direction=action,
                quantity=quantity,
                entry_price=filled_price,
                stop_loss_points=stop_loss,
                take_profit_points=take_profit,
                signal_id=signal_id,
                strategy_version=strategy.strategy_version
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
            signal_id = position.signal_id
            strategy_version = position.strategy_version
            
            # 判斷出场原因
            exit_reason = "signal_reversal"
            if position.stop_loss and price <= position.stop_loss:
                exit_reason = "stop_loss"
            elif position.take_profit and price >= position.take_profit:
                exit_reason = "take_profit"
            
            # 更新訊號記錄
            if signal_id:
                self._get_signal_recorder().update_result(
                    signal_id=signal_id,
                    strategy_id=strategy_id,
                    strategy_version=strategy_version,
                    status="filled",
                    exit_price=price,
                    exit_reason=exit_reason,
                    pnl=result["pnl"],
                    filled_at=datetime.now().isoformat(),
                    filled_quantity=result["quantity"]
                )
            
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
──────────────
日期: {stats['today']}
總委託: {stats['total_orders']}
成交: {stats['filled']}
取消: {stats['cancelled']}
待處理: {stats['pending']}

部位損益: {self.position_mgr.get_positions_summary()['total_pnl']:+,.0f}
當日風控損益: {self.risk_mgr.daily_pnl:+,.0f}
"""
        
        return text
    
    def get_strategy_performance(self, strategy_id: str, period: str = "all") -> str:
        """取得特定策略的績效
        
        Args:
            strategy_id: 策略 ID
            period: 查詢週期 (today/week/month/quarter/year/all)
            
        Returns:
            str: 績效報告
        """
        strategy = self.strategy_mgr.get_strategy(strategy_id)
        if not strategy:
            return f"❌ 找不到策略: {strategy_id}"
        
        return self._get_performance_analyzer().format_performance_report(strategy_id, period)
    
    def review_strategy(self, strategy_id: str) -> str:
        """讓 LLM 審查策略並給出修改建議
        
        Args:
            strategy_id: 策略 ID
            
        Returns:
            str: LLM 審查結果
        """
        strategy = self.strategy_mgr.get_strategy(strategy_id)
        if not strategy:
            return f"❌ 找不到策略: {strategy_id}"
        
        if not hasattr(self, '_strategy_reviewer'):
            from src.analysis.strategy_reviewer import StrategyReviewer
            self._strategy_reviewer = StrategyReviewer(
                llm_provider=self._llm_provider,
                performance_analyzer=self._get_performance_analyzer()
            )
        
        strategy_info = {
            "name": strategy.name,
            "symbol": strategy.symbol,
            "prompt": strategy.prompt,
            "goal": strategy.goal,
            "goal_unit": strategy.goal_unit,
            "params": strategy.params
        }
        
        return self._strategy_reviewer.review(strategy_id, strategy_info)
    
    def optimize_strategy(self, strategy_id: str) -> str:
        """優化策略 - 檢查目標達成情況並根據需要進行優化
        
        Args:
            strategy_id: 策略 ID
            
        Returns:
            str: 優化建議或確認訊息
        """
        strategy = self.strategy_mgr.get_strategy(strategy_id)
        if not strategy:
            return f"❌ 找不到策略: {strategy_id}"
        
        goal = strategy.goal
        goal_unit = strategy.goal_unit
        
        if not goal or goal <= 0:
            return f"""
⚠️ 策略 {strategy_id} 尚未設定目標。

請先設定目標後再進行優化：
set_goal {strategy_id} <目標金額> <單位>

例如：
- set_goal {strategy_id} 500 daily (每日賺500元)
- set_goal {strategy_id} 10000 monthly (每月賺10000元)
"""
        
        period_map = {
            "daily": "today",
            "weekly": "week", 
            "monthly": "month",
            "quarterly": "quarter",
            "yearly": "year"
        }
        period = period_map.get(goal_unit, "month")
        
        analysis = self._performance_analyzer.analyze(strategy_id, period)
        stats = analysis.get("signal_stats", {})
        
        from datetime import date, timedelta
        period_days = 1
        if goal_unit == "daily":
            period_days = 1
        elif goal_unit == "weekly":
            period_days = 7
        elif goal_unit == "monthly":
            period_days = 30
        elif goal_unit == "quarterly":
            period_days = 90
        elif goal_unit == "yearly":
            period_days = 365
        
        period_profit = stats.get("total_pnl", 0)
        
        achieved = self._performance_analyzer.check_goal_achieved(
            goal=goal,
            goal_unit=goal_unit,
            period_profit=period_profit,
            period_days=period_days
        )
        
        unit_names = {
            "daily": "每日",
            "weekly": "每週", 
            "monthly": "每月",
            "quarterly": "每季",
            "yearly": "每年"
        }
        unit_name = unit_names.get(goal_unit, "")
        
        if achieved:
            return f"""
🎉 *目標已達成！*

策略: {strategy_id} ({strategy.name})
目標: {unit_name}賺 {goal:,} 元
實際: {unit_name}賺 {period_profit:+,.0f} 元

✅ 策略表現優異，無需優化！
"""
        
        deficit = goal * period_days if goal_unit == "daily" else goal - period_profit
        if goal_unit == "weekly":
            deficit = goal - (period_profit / 7 * 30) if period_profit < goal else 0
        elif goal_unit == "daily":
            deficit = goal - period_profit if period_days == 1 else goal * period_days - period_profit
        
        self._pending_optimization = {
            "strategy_id": strategy_id,
            "strategy_name": strategy.name,
            "goal": goal,
            "goal_unit": goal_unit,
            "unit_name": unit_name,
            "period_profit": period_profit,
            "deficit": deficit,
            "stats": stats,
            "stage": "review"
        }
        
        return f"""
📊 *策略優化分析*

策略: {strategy_id} ({strategy.name})
目標: {unit_name}賺 {goal:,} 元
實際: {unit_name}賺 {period_profit:+,.0f} 元
差距: {deficit:+,.0f} 元

─ 交易統計 ─
總訊號: {stats.get('total_signals', 0)}
成交次數: {stats.get('filled_signals', 0)}
勝率: {stats.get('win_rate', 0):.1f}%
平均損益: {stats.get('avg_pnl', 0):+,.0f} 元
停損觸發: {stats.get('stop_loss_count', 0)} 次
止盈觸發: {stats.get('take_profit_count', 0)} 次

─ 執行優化 ─
正在進行 LLM 策略審查，請稍候...
"""
    
    def _process_optimization_review(self) -> str:
        """處理 LLM 審查結果"""
        if not self._pending_optimization:
            return "❌ 沒有待處理的優化"
        
        opt = self._pending_optimization
        strategy_id = opt["strategy_id"]
        
        strategy = self.strategy_mgr.get_strategy(strategy_id)
        if not strategy:
            self._clear_optimization()
            return f"❌ 找不到策略: {strategy_id}"
        
        if not hasattr(self, '_strategy_reviewer'):
            from src.analysis.strategy_reviewer import StrategyReviewer
            self._strategy_reviewer = StrategyReviewer(
                llm_provider=self._llm_provider,
                performance_analyzer=self._get_performance_analyzer()
            )
        
        strategy_info = {
            "name": strategy.name,
            "symbol": strategy.symbol,
            "prompt": strategy.prompt,
            "goal": opt["goal"],
            "goal_unit": opt["goal_unit"],
            "params": strategy.params
        }
        
        try:
            review_result = self._strategy_reviewer.review(strategy_id, strategy_info)
            
            opt["review_result"] = review_result
            opt["stage"] = "confirm"
            
            return f"""
📋 *LLM 審查結果*

策略: {strategy_id}

{review_result}

─ 下一步 ─

請選擇要執行的修改：

1. 確認修改 - 輸入「確認優化」或「confirm optimize」
2. 取消 - 輸入「cancel」

或許你想：
- 修改參數 - 輸入「停損改成XX」「止盈改成XX」
- 只想查看績效 - 輸入「performance {strategy_id}」
"""
        except Exception as e:
            return f"❌ LLM 審查失敗: {str(e)}"
    
    def confirm_optimize(self, confirmed: bool = True) -> str:
        """確認或取消策略優化
        
        Args:
            confirmed: True 表示確認執行修改，False 表示取消
            
        Returns:
            str: 執行結果
        """
        if not self._pending_optimization:
            return "❌ 沒有待處理的優化，請先輸入「optimize <策略ID>」"
        
        opt = self._pending_optimization
        strategy_id = opt["strategy_id"]
        
        if not confirmed:
            self._clear_optimization()
            return "❌ 已取消策略優化"
        
        strategy = self.strategy_mgr.get_strategy(strategy_id)
        if not strategy:
            self._clear_optimization()
            return f"❌ 找不到策略: {strategy_id}"
        
        review_result = opt.get("review_result", "")
        
        modification_text = ""
        
        lines = review_result.split("\n")
        suggestion_type = None
        specific_changes = []
        capture = False
        
        for line in lines:
            line = line.strip()
            if "## 建議類型" in line:
                capture = True
                continue
            if "## 具體建議" in line:
                capture = False
                continue
            if capture and line:
                suggestion_type = line.strip()
        
        capture = False
        for line in lines:
            line = line.strip()
            if "## 具體建議" in line:
                capture = True
                continue
            if capture and line:
                specific_changes.append(line)
        
        if "參數" in suggestion_type or "parameter" in suggestion_type.lower():
            for change in specific_changes:
                if "停損" in change and "改成" in change:
                    try:
                        new_sl = int(change.split("改成")[1].split("點")[0].strip())
                        strategy.params["stop_loss"] = new_sl
                        modification_text += f"• 停損調整為 {new_sl} 點\n"
                    except:
                        pass
                if "止盈" in change and "改成" in change:
                    try:
                        new_tp = int(change.split("改成")[1].split("點")[0].strip())
                        strategy.params["take_profit"] = new_tp
                        modification_text += f"• 止盈調整為 {new_tp} 點\n"
                    except:
                        pass
                if "數量" in change and "改成" in change:
                    try:
                        new_qty = int(change.split("改成")[1].strip())
                        strategy.params["position_size"] = new_qty
                        modification_text += f"• 交易口數調整為 {new_qty} 口\n"
                    except:
                        pass
        
        elif "Prompt" in suggestion_type or "prompt" in suggestion_type.lower():
            new_prompt = "\n".join(specific_changes[:3])
            if new_prompt:
                old_prompt = strategy.prompt
                strategy.prompt = new_prompt
                modification_text += f"• 策略 Prompt 已更新\n"
        
        elif "重新設計" in suggestion_type or "redesign" in suggestion_type.lower():
            modification_text = "• 策略需要重新設計，請建立新策略\n"
        
        if modification_text and modification_text != "• 策略需要重新設計，請建立新策略\n":
            old_version = strategy.strategy_version
            strategy.strategy_version = old_version + 1
            self._get_signal_recorder().archive_to_new_version(
                strategy_id=strategy_id,
                old_version=old_version,
                new_version=strategy.strategy_version
            )
            modification_text += f"• 版本: v{old_version} → v{strategy.strategy_version}\n"
        
        self.strategy_mgr.store.save_strategy(strategy.to_dict())
        
        self._clear_optimization()
        
        return f"""
✅ *策略已優化*

策略: {strategy_id} ({strategy.name})
修改內容：
{modification_text or "無"}

修改已儲存，策略將在下次執行時使用新參數。
"""
    
    def set_strategy_goal(self, strategy_id: str, goal: float, goal_unit: str) -> str:
        """設定策略目標
        
        Args:
            strategy_id: 策略 ID
            goal: 目標金額
            goal_unit: 目標單位 (daily/weekly/monthly/quarterly/yearly)
            
        Returns:
            str: 設定結果
        """
        strategy = self.strategy_mgr.get_strategy(strategy_id)
        if not strategy:
            return f"❌ 找不到策略: {strategy_id}"
        
        valid_units = ["daily", "weekly", "monthly", "quarterly", "yearly"]
        if goal_unit not in valid_units:
            return f"❌ 無效的目標單位，請使用: {', '.join(valid_units)}"
        
        if goal <= 0:
            return "❌ 目標金額必須大於 0"
        
        strategy.goal = goal
        strategy.goal_unit = goal_unit
        
        self.strategy_mgr.store.save_strategy(strategy.to_dict())
        
        unit_names = {
            "daily": "每日",
            "weekly": "每週", 
            "monthly": "每月",
            "quarterly": "每季",
            "yearly": "每年"
        }
        
        return f"""
✅ *目標已設定*

策略: {strategy_id}
目標: {unit_names[goal_unit]}賺 {goal:,} 元

輸入「optimize {strategy_id}」開始優化分析
"""
    
    def _clear_optimization(self) -> None:
        """清除待處理的優化狀態"""
        self._pending_optimization = None
    
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
                    "description": "查詢所有已配置的策略，包含名稱、ID、合約、狀態、策略描述(prompt)、參數(K線週期/口數/停損/止盈)、目標。當用戶問「策略有哪些」「策略列表」「strategies」「策略」時**必須**呼叫此工具。",
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
                    "name": "get_strategy_performance",
                    "description": "查詢特定策略的績效統計，包含已實現損益、勝率、交易次數、停損止盈觸發次數等。支援查詢週期 (today/week/month/quarter/year/all)。相當於問「strategy_001 表現如何」、「這個策略賺多少」。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "strategy_id": {"type": "string", "description": "策略 ID"},
                            "period": {
                                "type": "string", 
                                "enum": ["today", "week", "month", "quarter", "year", "all"],
                                "description": "查詢週期"
                            }
                        },
                        "required": ["strategy_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "review_strategy",
                    "description": "讓 LLM 審查策略並給出修改建議。會分析策略的績效、找出問題，並建議應該調整參數還是修改交易邏輯。相當於問「幫我看看這個策略怎麼樣」、「review strategy_001」。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "strategy_id": {"type": "string", "description": "策略 ID"}
                        },
                        "required": ["strategy_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "optimize_strategy",
                    "description": "優化策略 - 檢查目標達成情況，若未達成則觸發 LLM 審查並提供修改建議。相當於問「optimize strategy_001」、「優化策略 strategy_001」。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "strategy_id": {"type": "string", "description": "策略 ID"}
                        },
                        "required": ["strategy_id"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "confirm_optimize",
                    "description": "確認執行策略優化修改。當用戶說「確認優化」或「confirm optimize」時調用。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "confirmed": {"type": "boolean", "description": "True 表示確認執行修改，False 表示取消"}
                        },
                        "required": ["confirmed"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "set_strategy_goal",
                    "description": "設定策略的獲利目標。當用戶說「設定目標」或「set goal」時調用。目標單位支援 daily(每日)、weekly(每週)、monthly(每月)、quarterly(每季)、yearly(每年)。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "strategy_id": {"type": "string", "description": "策略 ID"},
                            "goal": {"type": "number", "description": "目標金額"},
                            "goal_unit": {"type": "string", "description": "目標單位 (daily/weekly/monthly/quarterly/yearly)"}
                        },
                        "required": ["strategy_id", "goal", "goal_unit"]
                    }
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
                    "name": "confirm_disable_strategy",
                    "description": "確認停用策略 (當用戶說「確認停用」或「confirm disable」時調用，若有部位會強制平倉)",
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
                    "description": "建立新策略（ID會自動生成）。需要提供名稱、期貨代碼、策略描述、K線週期等參數。",
                    "parameters": {
                        "type": "object",
                        "properties": {
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
                        "required": ["name", "symbol", "prompt", "timeframe"]
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
            {
                "type": "function",
                "function": {
                    "name": "create_strategy_by_goal",
                    "description": "根據用戶目標自動推斷參數並建立策略。當用戶說「幫我建立策略」時調用。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "goal": {"type": "string", "description": "用戶的目標描述（如「幫我建立RSI策略」「設計一個每日賺500元的策略」）"},
                            "symbol": {"type": "string", "description": "期貨代碼（如 TXF、MXF、TMF）。若不提供，系統會詢問用戶"}
                        },
                        "required": ["goal"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "modify_strategy_params",
                    "description": "修改待確認的策略參數（如停損、止盈、K線週期等），並重新生成策略描述。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "modifications": {"type": "string", "description": "修改內容（如「停損改成50點」「止盈改成100點」或「K線週期改成30m」）"}
                        },
                        "required": ["modifications"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "confirm_create_strategy",
                    "description": "確認或取消建立策略。當用戶說「確認」或「取消」時調用。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "confirmed": {"type": "boolean", "description": "True 表示確認建立，False 表示取消"}
                        },
                        "required": ["confirmed"]
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
            "get_strategy_performance": lambda: self.get_strategy_performance(
                strategy_id=arguments.get("strategy_id", ""),
                period=arguments.get("period", "all")
            ),
            "review_strategy": lambda: self.review_strategy(
                strategy_id=arguments.get("strategy_id", "")
            ),
            "optimize_strategy": lambda: self.optimize_strategy(
                strategy_id=arguments.get("strategy_id", "")
            ),
            "confirm_optimize": lambda: self.confirm_optimize(
                confirmed=arguments.get("confirmed", True)
            ),
            "set_strategy_goal": lambda: self.set_strategy_goal(
                strategy_id=arguments.get("strategy_id", ""),
                goal=arguments.get("goal", 0),
                goal_unit=arguments.get("goal_unit", "daily")
            ),
            "get_risk_status": lambda: self.get_risk_status(),
            "get_order_history": lambda: self.get_order_history(arguments.get("strategy_id")),
            "get_market_data": lambda: self.get_market_data(arguments.get("symbol", "")),
            "enable_strategy": lambda: self.enable_strategy(arguments.get("strategy_id", "")),
            "disable_strategy": lambda: self.disable_strategy(arguments.get("strategy_id", "")),
            "confirm_disable_strategy": lambda: self.confirm_disable_strategy(arguments.get("strategy_id", "")),
            "get_position_by_strategy": lambda: self.get_position_by_strategy(arguments.get("strategy_id", "")),
            "create_strategy": lambda: self.create_strategy(
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
            "create_strategy_by_goal": lambda: self.create_strategy_by_goal(
                goal=arguments.get("goal", ""),
                symbol=arguments.get("symbol")
            ),
            "modify_strategy_params": lambda: self.modify_strategy_params(
                modifications=arguments.get("modifications", "")
            ),
            "confirm_create_strategy": lambda: self.confirm_create_strategy(
                confirmed=arguments.get("confirmed", False)
            ),
        }
        
        tool = tool_map.get(tool_name)
        if tool:
            try:
                return tool()
            except Exception as e:
                logger.error(f"執行工具失敗 {tool_name}: {e}")
                return f"執行失敗: {e}"
        
        return f"未知工具: {tool_name}"
