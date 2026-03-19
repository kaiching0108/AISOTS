"""Web Interface Flask Application"""
from flask import Flask, render_template
from loguru import logger


def create_web_app(trading_tools, llm_provider=None, data_updater=None, connection_mgr=None, strategy_runner=None):
    """建立 Flask 應用
    
    Args:
        trading_tools: TradingTools 實例
        llm_provider: LLM Provider 實例
        data_updater: DataUpdater 實例（可選）
        connection_mgr: ConnectionManager 實例（可選）
        strategy_runner: StrategyRunner 實例（可選）
        
    Returns:
        Flask 應用
    """
    # 修復 async/await 在 Flask 中的 event loop 問題
    import nest_asyncio
    nest_asyncio.apply()
    
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'aisots-web-secret-key'
    
    # 儲存引用
    app.trading_tools = trading_tools
    app.llm_provider = llm_provider
    app.data_updater = data_updater
    app.connection_mgr = connection_mgr
    app.strategy_runner = strategy_runner
    

    
    # 註冊路由
    from src.web.routes import status, strategies, positions, risk, backtest
    from src.web.routes import create
    from src.web.routes import config
    from src.web.routes import orders
    from src.web.routes import trade_logs
    from src.web.routes import performance
    from src.web.routes import sqlite
    from src.web.routes import chart
    
    app.register_blueprint(status.bp)
    app.register_blueprint(strategies.bp)
    app.register_blueprint(positions.bp)
    app.register_blueprint(risk.bp)
    app.register_blueprint(backtest.bp)
    app.register_blueprint(create.create_bp)
    app.register_blueprint(config.bp)
    app.register_blueprint(orders.bp)
    app.register_blueprint(trade_logs.bp)
    app.register_blueprint(performance.bp)
    app.register_blueprint(sqlite.bp)
    app.register_blueprint(chart.bp)
    
    # 提供 workspace 目录下的文件访问（如回测图表）
    import os
    from flask import send_from_directory
    
    workspace_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'workspace')
    
    @app.route('/workspace/<path:filename>')
    def serve_workspace(filename):
        """提供 workspace 目录下的文件"""
        return send_from_directory(workspace_path, filename)
    
    @app.route('/')
    def index():
        """首頁 - 系統總覽"""
        return render_template('index.html')
    
    @app.route('/strategies')
    def strategies_page():
        """策略列表頁面"""
        return render_template('strategies.html')
    
    @app.route('/positions')
    def positions_page():
        """部位列表頁面"""
        return render_template('positions.html')
    
    @app.route('/orders')
    def orders_page():
        """訂單列表頁面"""
        return render_template('orders.html')
    
    @app.route('/config')
    def config_page():
        """系統配置頁面"""
        return render_template('config.html')
    
    @app.route('/performance')
    def performance_page():
        """績效分析頁面"""
        return render_template('performance.html')
    
    @app.route('/chart')
    def chart_page():
        """K棒圖表頁面"""
        return render_template('chart.html')
    
    logger.info("Flask Web 應用已建立")
    
    return app


def start_web_app(trading_tools, host='127.0.0.1', port=5000):
    """啟動 Web 應用（在獨立執行緒中）
    
    Args:
        trading_tools: TradingTools 實例
        host: 綁定位址
        port: 連接埠
    """
    app = create_web_app(trading_tools)
    
    logger.info(f"啟動 Web 界面: http://{host}:{port}")
    app.run(host=host, port=port, debug=False, use_reloader=False)
