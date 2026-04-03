import os
from pathlib import Path

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

DB_PATH = DATA_DIR / "stock_data.db"
CACHE_DIR = DATA_DIR / "cache"
CACHE_DIR.mkdir(exist_ok=True)

LOG_DIR = DATA_DIR / "logs"
LOG_DIR.mkdir(exist_ok=True)

STOCK_DATA_DIR = DATA_DIR / "stock_data"
STOCK_DATA_DIR.mkdir(exist_ok=True)

MARKET_CONFIG = {
    "默认": "上海和深圳",
    "上海证券交易所": "sh",
    "深圳证券交易所": "sz",
    "上海A股": "sh",
    "上海B股": "sh",
    "深圳A股": "sz",
    "深圳B股": "sz",
}

TIMEZONE = "Asia/Shanghai"

TRADING_HOURS = {
    "上午": ("09:30", "11:30"),
    "下午": ("13:00", "15:00"),
}

COLOR_CONFIG = {
    "上涨": "#FF0000",
    "下跌": "#00FF00",
    "平盘": "#FFFFFF",
    "背景": "#0E1117",
    "文字": "#CFD8DC",
}
