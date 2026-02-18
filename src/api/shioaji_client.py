"""Shioaji API 封裝"""
import shioaji as sj
from shioaji.constant import Action, FuturesPriceType, OrderType, FuturesOCType
from typing import Optional, List, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class ShioajiClient:
    """Shioaji API 客戶端封裝"""
    
    def __init__(self, api_key: str, secret_key: str, simulation: bool = True, skip_login: bool = False):
        self.api_key = api_key
        self.secret_key = secret_key
        self.simulation = simulation
        self.skip_login = skip_login
        self.api = sj.Shioaji(simulation=simulation)
        self.futopt_account = None
        self.connected = False
        
        # 合約快取
        self._contracts_cache: Dict[str, Any] = {}
        
        # 模擬資料
        self._mock_positions: List[Dict[str, Any]] = []
        self._mock_orders: List[Dict[str, Any]] = []
        self._order_id_counter = 1000
    
    def login(self) -> bool:
        """登入 Shioaji"""
        # 跳過登入（模擬模式）
        if self.skip_login:
            logger.info("模擬模式：跳過 API 登入")
            self.connected = True
            self.futopt_account = "SIMULATE_ACCOUNT"
            return True
        
        try:
            logger.info("正在登入 Shioaji...")
            accounts = self.api.login(
                api_key=self.api_key,
                secret_key=self.secret_key,
                contracts_timeout=10000,
            )
            
            # 取得期貨帳戶
            for acc in accounts:
                if hasattr(acc, "account_id") and acc.account_id:
                    self.futopt_account = acc
                    break
            
            if not self.futopt_account:
                logger.warning("未找到期貨帳戶")
            
            self.connected = True
            logger.info(f"登入成功 - 帳戶: {self.futopt_account}")
            return True
            
        except Exception as e:
            logger.error(f"登入失敗: {e}")
            self.connected = False
            return False
    
    def logout(self) -> bool:
        """登出"""
        try:
            self.api.logout()
            self.connected = False
            logger.info("已登出")
            return True
        except Exception as e:
            logger.error(f"登出失敗: {e}")
            return False
    
    def get_contract(self, symbol: str) -> Optional[Any]:
        """取得期貨合約"""
        if symbol in self._contracts_cache:
            return self._contracts_cache[symbol]
        
        try:
            # 嘗試解析合約代碼
            # 例如: TXF202301 -> TXF, 202301
            category = symbol[:3]
            month = symbol[3:]
            
            # 從 Shioaji 取得合約
            contracts = getattr(self.api.Contracts.Futures, category, None)
            if contracts:
                contract = getattr(contracts, symbol, None)
                if contract:
                    self._contracts_cache[symbol] = contract
                    return contract
            
            return None
            
        except Exception as e:
            logger.error(f"取得合約失敗 {symbol}: {e}")
            return None
    
    def get_contracts_by_category(self, category: str) -> List[Any]:
        """取得某類別的所有期貨合約"""
        try:
            contracts = getattr(self.api.Contracts.Futures, category, None)
            if contracts:
                return [c for c in contracts]
            return []
        except Exception as e:
            logger.error(f"取得合約列表失敗 {category}: {e}")
            return []
    
    def place_order(
        self,
        symbol: str,
        action: str,
        quantity: int,
        price: float = 0,
        price_type: str = "LMT",
        order_type: str = "ROD",
        octype: str = "Auto",
        timeout: int = 0,
        callback=None
    ) -> Optional[Any]:
        """下單"""
        if not self.connected:
            logger.error("未連線，無法下單")
            return None
        
        # 離線模式：模擬下單
        if self.skip_login:
            order_id = f"OFFLINE_{self._order_id_counter}"
            self._order_id_counter += 1
            
            mock_trade = type('MockTrade', (), {
                'order_id': order_id,
                'status': 'F',
                'action': action,
                'symbol': symbol,
                'quantity': quantity,
                'price': price,
                'filled_price': price if price > 0 else 18500,
                'filled_quantity': quantity,
                'order_type': order_type,
                'price_type': price_type,
            })()
            
            self._mock_orders.append({
                'order_id': order_id,
                'action': action,
                'symbol': symbol,
                'quantity': quantity,
                'price': price,
                'filled_price': mock_trade.filled_price,
                'status': 'filled',
                'timestamp': datetime.now().isoformat()
            })
            
            # 模擬部位
            existing = next((p for p in self._mock_positions if p['symbol'] == symbol), None)
            if action == "Buy":
                if existing:
                    existing['quantity'] += quantity
                else:
                    self._mock_positions.append({
                        'symbol': symbol,
                        'quantity': quantity,
                        'avg_price': mock_trade.filled_price,
                        'action': 'Long'
                    })
            else:  # Sell
                if existing:
                    existing['quantity'] -= quantity
                    if existing['quantity'] <= 0:
                        self._mock_positions.remove(existing)
            
            logger.info(f"離線模擬下單: {symbol} {action} {quantity} @ {mock_trade.filled_price}")
            return mock_trade
        
        contract = self.get_contract(symbol)
        if not contract:
            logger.error(f"找不到合約: {symbol}")
            return None
        
        try:
            order = self.api.Order(
                action=Action.Buy if action == "Buy" else Action.Sell,
                price=price,
                quantity=quantity,
                price_type=FuturesPriceType[price_type],
                order_type=OrderType[order_type],
                octype=FuturesOCType[octype],
                account=self.futopt_account
            )
            
            # 非阻塞下單
            trade = self.api.place_order(
                contract,
                order,
                timeout=timeout,
                cb=callback
            )
            
            logger.info(f"下單成功: {symbol} {action} {quantity} @ {price}")
            return trade
            
        except Exception as e:
            logger.error(f"下單失敗: {e}")
            return None
    
    def cancel_order(self, trade: Any) -> bool:
        """取消訂單"""
        if not self.connected:
            logger.error("未連線，無法取消")
            return False
        
        # 離線模式：模擬取消
        if self.skip_login:
            logger.info(f"離線模擬取消訂單")
            return True
        
        try:
            self.api.cancel_order(trade)
            logger.info(f"取消訂單成功")
            return True
        except Exception as e:
            logger.error(f"取消訂單失敗: {e}")
            return False
    
    def get_positions(self) -> List[Any]:
        """取得目前部位"""
        if not self.connected:
            return []
        
        # 離線模式：返回模擬部位
        if self.skip_login:
            return self._mock_positions
        
        try:
            positions = self.api.list_positions(self.futopt_account)
            return positions
        except Exception as e:
            logger.error(f"取得部位失敗: {e}")
            return []
    
    def get_profit_loss(self, begin_date: str = None, end_date: str = None) -> List[Any]:
        """取得已實現損益"""
        if not self.connected:
            return []
        
        # 離線模式：返回模擬損益
        if self.skip_login:
            mock_pnl = []
            for order in self._mock_orders:
                if order.get('status') == 'filled' and order.get('pnl') is not None:
                    mock_pnl.append(order)
            return mock_pnl
        
        try:
            if not begin_date:
                begin_date = datetime.now().strftime("%Y-%m-%d")
            if not end_date:
                end_date = datetime.now().strftime("%Y-%m-%d")
            
            profit_loss = self.api.list_profit_loss(
                self.futopt_account,
                begin_date=begin_date,
                end_date=end_date
            )
            return profit_loss
        except Exception as e:
            logger.error(f"取得損益失敗: {e}")
            return []
    
    def get_margin(self) -> Optional[Any]:
        """取得帳戶保證金資訊"""
        if not self.connected:
            return None
        
        try:
            margin = self.api.margin(self.futopt_account)
            return margin
        except Exception as e:
            logger.error(f"取得保證金失敗: {e}")
            return None
    
    def get_daily_pnl(self) -> float:
        """取得當日損益"""
        profit_loss = self.get_profit_loss()
        total_pnl = sum(p.pnl for p in profit_loss)
        return total_pnl
    
    def subscribe_quote(self, symbol: str, quote_type: str = "tick") -> bool:
        """訂閱報價"""
        if not self.connected:
            return False
        
        contract = self.get_contract(symbol)
        if not contract:
            return False
        
        try:
            self.api.quote.subscribe(
                contract,
                quote_type=sj.constant.QuoteType[quote_type.upper()],
                version=sj.constant.QuoteVersion.v1
            )
            return True
        except Exception as e:
            logger.error(f"訂閱報價失敗: {e}")
            return False
    
    def unsubscribe_quote(self, symbol: str, quote_type: str = "tick") -> bool:
        """取消訂閱報價"""
        if not self.connected:
            return False
        
        contract = self.get_contract(symbol)
        if not contract:
            return False
        
        try:
            self.api.quote.unsubscribe(
                contract,
                quote_type=quote_type
            )
            return True
        except Exception as e:
            logger.error(f"取消訂閱失敗: {e}")
            return False
    
    def set_order_callback(self, callback) -> None:
        """設置訂單回調"""
        self.api.set_order_callback(callback)
    
    def set_quote_callback(self, callback) -> None:
        """設置報價回調"""
        self.api.quote.set_on_tick_fop_v1_callback(callback)
    
    def get_usage(self) -> Optional[Any]:
        """取得流量使用量"""
        try:
            return self.api.usage()
        except Exception as e:
            logger.error(f"取得流量失敗: {e}")
            return None
