"""日誌配置 - 使用 loguru"""

from loguru import logger
import sys
from pathlib import Path

# 移除預設 handler
logger.remove()

# 確保日誌目錄存在
log_dir = Path("workspace/logs")
log_dir.mkdir(parents=True, exist_ok=True)

# 添加 console handler
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
    level="INFO"
)

# 添加 file handler
logger.add(
    "workspace/logs/trading.log",
    rotation="1 day",
    retention="30 days",
    level="DEBUG",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}"
)

__all__ = ["logger"]
