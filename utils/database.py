import sqlite3
from datetime import datetime, date
from pathlib import Path
from typing import List, Dict, Optional
import pandas as pd
from config import DB_PATH


class StockDatabase:
    def __init__(self, db_path: str = str(DB_PATH)):
        self.db_path = db_path
        self._init_database()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _init_database(self):
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS watchlist (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL UNIQUE,
                name TEXT,
                market TEXT DEFAULT 'A股',
                added_date TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stock_kline (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL,
                date TEXT NOT NULL,
                open REAL,
                high REAL,
                low REAL,
                close REAL,
                volume REAL,
                amount REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(code, date)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL,
                predict_date TEXT NOT NULL,
                predicted_price REAL,
                predicted_direction TEXT,
                actual_price REAL,
                accuracy REAL,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(code, predict_date)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS market_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data_type TEXT NOT NULL,
                date TEXT NOT NULL,
                data TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(data_type, date)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS review_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL,
                review_date TEXT NOT NULL,
                prediction TEXT,
                actual_result TEXT,
                analysis TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS triggered_stocks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL UNIQUE,
                name TEXT,
                source TEXT,
                trigger_date TEXT,
                price REAL,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        conn.commit()
        conn.close()

    def add_to_watchlist(self, code: str, name: str = None, market: str = "A股", notes: str = "") -> bool:
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "INSERT OR REPLACE INTO watchlist (code, name, market, added_date, notes) VALUES (?, ?, ?, ?, ?)",
                (code, name, market, date.today().isoformat(), notes)
            )
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"添加自选股失败: {e}")
            return False

    def remove_from_watchlist(self, code: str) -> bool:
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM watchlist WHERE code = ?", (code,))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"删除自选股失败: {e}")
            return False

    def get_watchlist(self) -> pd.DataFrame:
        conn = self._get_connection()
        df = pd.read_sql("SELECT * FROM watchlist ORDER BY created_at DESC", conn)
        conn.close()
        return df

    def add_to_triggered(self, code: str, name: str = None, source: str = None,
                         trigger_date: str = None, price: float = None, notes: str = "") -> bool:
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO triggered_stocks
                (code, name, source, trigger_date, price, notes)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (code, name, source, trigger_date, price, notes))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"添加触发指标失败: {e}")
            return False

    def remove_from_triggered(self, code: str) -> bool:
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM triggered_stocks WHERE code = ?", (code,))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"删除触发指标失败: {e}")
            return False

    def get_triggered_stocks(self) -> pd.DataFrame:
        conn = self._get_connection()
        df = pd.read_sql("SELECT * FROM triggered_stocks ORDER BY created_at DESC", conn)
        conn.close()
        return df

    def clear_triggered_stocks(self) -> bool:
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM triggered_stocks")
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"清空触发指标失败: {e}")
            return False

    def batch_add_to_triggered(self, stocks: List[Dict]) -> int:
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            for stock in stocks:
                cursor.execute("""
                    INSERT OR REPLACE INTO triggered_stocks
                    (code, name, source, trigger_date, price, notes)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    stock.get('code', ''),
                    stock.get('name', ''),
                    stock.get('source', ''),
                    stock.get('trigger_date', date.today().isoformat()),
                    stock.get('price'),
                    stock.get('notes', '')
                ))
            conn.commit()
            conn.close()
            return len(stocks)
        except Exception as e:
            print(f"批量添加触发指标失败: {e}")
            return 0

    def save_kline_data(self, code: str, data: pd.DataFrame):
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            rows = [
                (code, row['date'], row['open'], row['high'], row['low'],
                 row['close'], row['volume'], row['amount'])
                for _, row in data.iterrows()
            ]

            cursor.executemany("""
                INSERT OR REPLACE INTO stock_kline
                (code, date, open, high, low, close, volume, amount)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, rows)

            conn.commit()
            conn.close()
        except Exception as e:
            print(f"保存K线数据失败: {e}")

    def get_kline_data(self, code: str, days: int = 365) -> pd.DataFrame:
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='daily'")
        has_daily_table = cursor.fetchone() is not None

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='stock_kline'")
        has_stock_kline_table = cursor.fetchone() is not None

        df = pd.DataFrame()

        if has_daily_table:
            query = """
                SELECT date, open, close, high, low, volume, amount
                FROM daily
                WHERE code = ?
                ORDER BY date DESC
                LIMIT ?
            """
            df = pd.read_sql(query, conn, params=(code, days))

        if df.empty and has_stock_kline_table:
            query = """
                SELECT date, open, high, low, close, volume, amount
                FROM stock_kline
                WHERE code = ?
                ORDER BY date DESC
                LIMIT ?
            """
            df = pd.read_sql(query, conn, params=(code, days))

        conn.close()

        if not df.empty:
            df = df.sort_values('date')
            if 'open' not in df.columns or 'close' not in df.columns:
                if 'open' in df.columns and 'close' not in df.columns:
                    df['close'] = df['open']
                elif 'close' in df.columns and 'open' not in df.columns:
                    df['open'] = df['close']

        return df

    def save_prediction(self, code: str, predict_date: str, predicted_price: float,
                       predicted_direction: str, notes: str = "") -> bool:
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO predictions
                (code, predict_date, predicted_price, predicted_direction, notes)
                VALUES (?, ?, ?, ?, ?)
            """, (code, predict_date, predicted_price, predicted_direction, notes))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"保存预测失败: {e}")
            return False

    def update_prediction_result(self, code: str, predict_date: str, actual_price: float):
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE predictions
                SET actual_price = ?,
                    accuracy = CASE
                        WHEN predicted_price > 0 THEN
                            1 - ABS(actual_price - predicted_price) / predicted_price
                        ELSE NULL
                    END
                WHERE code = ? AND predict_date = ?
            """, (actual_price, code, predict_date))
            conn.commit()
            conn.close()
        except Exception as e:
            print(f"更新预测结果失败: {e}")

    def get_predictions(self, code: str = None, days: int = 30) -> pd.DataFrame:
        conn = self._get_connection()
        if code:
            query = """
                SELECT * FROM predictions
                WHERE code = ?
                ORDER BY predict_date DESC
                LIMIT ?
            """
            df = pd.read_sql(query, conn, params=(code, days))
        else:
            query = """
                SELECT * FROM predictions
                ORDER BY predict_date DESC
                LIMIT ?
            """
            df = pd.read_sql(query, conn, params=(days,))
        conn.close()
        return df

    def save_market_data(self, data_type: str, date: str, data: str) -> bool:
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO market_data (data_type, date, data)
                VALUES (?, ?, ?)
            """, (data_type, date, data))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"保存市场数据失败: {e}")
            return False

    def get_market_data(self, data_type: str, date: str = None) -> Optional[str]:
        conn = self._get_connection()
        cursor = conn.cursor()
        if date:
            cursor.execute("SELECT data FROM market_data WHERE data_type = ? AND date = ?",
                          (data_type, date))
        else:
            cursor.execute("SELECT data FROM market_data WHERE data_type = ? ORDER BY date DESC LIMIT 1",
                          (data_type,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None

    def save_review(self, code: str, review_date: str, prediction: str,
                   actual_result: str, analysis: str) -> bool:
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO review_log
                (code, review_date, prediction, actual_result, analysis)
                VALUES (?, ?, ?, ?, ?)
            """, (code, review_date, prediction, actual_result, analysis))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"保存复盘记录失败: {e}")
            return False

    def get_reviews(self, code: str = None, days: int = 30) -> pd.DataFrame:
        conn = self._get_connection()
        if code:
            query = """
                SELECT * FROM review_log
                WHERE code = ?
                ORDER BY review_date DESC
                LIMIT ?
            """
            df = pd.read_sql(query, conn, params=(code, days))
        else:
            query = """
                SELECT * FROM review_log
                ORDER BY review_date DESC
                LIMIT ?
            """
            df = pd.read_sql(query, conn, params=(days,))
        conn.close()
        return df

    def get_all_stock_codes(self) -> List[str]:
        """获取所有有数据的股票代码"""
        conn = self._get_connection()
        cursor = conn.cursor()

        codes = []

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='daily'")
        has_daily = cursor.fetchone() is not None

        if has_daily:
            cursor.execute("SELECT DISTINCT code FROM daily ORDER BY code")
            codes = [row[0] for row in cursor.fetchall()]

        if not codes:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='stock_list'")
            has_stock_list = cursor.fetchone() is not None

            if has_stock_list:
                cursor.execute("SELECT DISTINCT code FROM stock_list ORDER BY code")
                codes = [row[0] for row in cursor.fetchall()]

        conn.close()
        return codes
