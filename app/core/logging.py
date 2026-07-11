"""
Centralized logging. Import `logger` anywhere instead of using print().
"""
import sys
from loguru import logger

logger.remove()
logger.add(
    sys.stdout,
    colorize=True,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | "
           "<cyan>{module}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="INFO",
)
logger.add(
    "storage/logs/app.log",
    rotation="10 MB",
    retention="30 days",
    level="DEBUG",
    backtrace=True,
    diagnose=False,
)

__all__ = ["logger"]
