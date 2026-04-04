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

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stock_list (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL UNIQUE,
                name TEXT,
                market TEXT DEFAULT 'A股',
                list_date TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS update_failed_stocks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL UNIQUE,
                name TEXT,
                fail_date TEXT,
                error_msg TEXT,
                retry_count INTEGER DEFAULT 0,
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

    def save_stock_list(self, stocks: pd.DataFrame) -> int:
        """保存股票列表到数据库"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            rows = []
            skipped = 0
            for _, row in stocks.iterrows():
                code = str(row['code'])
                if len(code) != 6:
                    skipped += 1
                    continue
                rows.append((code, row['name'], 'A股', date.today().isoformat()))

            if skipped > 0:
                print(f"跳过 {skipped} 个无效股票代码（长度不为6）")

            if not rows:
                return 0

            cursor.executemany("""
                INSERT OR REPLACE INTO stock_list (code, name, market, list_date)
                VALUES (?, ?, ?, ?)
            """, rows)

            conn.commit()
            count = cursor.rowcount
            conn.close()
            return len(rows)
        except Exception as e:
            print(f"保存股票列表失败: {e}")
            return 0

    def get_stock_list(self) -> pd.DataFrame:
        """获取股票列表"""
        conn = self._get_connection()
        df = pd.read_sql("SELECT * FROM stock_list ORDER BY code", conn)
        conn.close()
        return df

    def get_stock_list_count(self) -> int:
        """获取股票列表数量"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM stock_list")
        count = cursor.fetchone()[0]
        conn.close()
        return count

    def save_failed_stock(self, code: str, name: str = None, error_msg: str = "") -> bool:
        """保存更新失败的股票"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO update_failed_stocks
                (code, name, fail_date, error_msg, retry_count)
                VALUES (?, ?, ?, ?, COALESCE((SELECT retry_count FROM update_failed_stocks WHERE code = ?), 0) + 1)
            """, (code, name, date.today().isoformat(), error_msg, code))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"保存失败股票失败: {e}")
            return False

    def remove_failed_stock(self, code: str) -> bool:
        """移除失败记录（更新成功后调用）"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM update_failed_stocks WHERE code = ?", (code,))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"移除失败记录失败: {e}")
            return False

    def get_failed_stocks(self) -> pd.DataFrame:
        """获取更新失败的股票列表"""
        conn = self._get_connection()
        df = pd.read_sql("SELECT * FROM update_failed_stocks ORDER BY retry_count DESC, created_at DESC", conn)
        conn.close()
        return df

    def get_failed_stocks_count(self) -> int:
        """获取失败股票数量"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM update_failed_stocks")
        count = cursor.fetchone()[0]
        conn.close()
        return count

    def clear_failed_stocks(self) -> bool:
        """清空失败记录"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("DELETE FROM update_failed_stocks")
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"清空失败记录失败: {e}")
            return False

    def save_kline_data(self, code: str, data: pd.DataFrame):
        if len(code) != 6:
            print(f"跳过无效股票代码: {code} (长度 {len(code)})")
            return
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            rows = []
            for _, row in data.iterrows():
                volume = row['volume'] if pd.notna(row['volume']) else 0
                if volume < 1:
                    continue

                date = row['date']
                open_price = row['open']
                close = row['close']
                high = row['high']
                low = row['low']
                amount = row['amount']

                prev_close = row.get('prev_close', None)
                if pd.isna(prev_close) or prev_close == 0:
                    pct_chg = 0.0
                    chg = 0.0
                else:
                    pct_chg = (close - prev_close) / prev_close * 100
                    chg = close - prev_close

                if low != 0:
                    amplitude = (high - low) / low * 100
                else:
                    amplitude = 0.0

                turnover = amount / volume / close * 100 if (volume > 0 and close > 0) else 0.0

                rows.append((
                    date, code, open_price, close, high, low, volume, amount,
                    amplitude, pct_chg, chg, turnover, 1
                ))

            cursor.executemany("""
                INSERT OR REPLACE INTO daily
                (date, code, open, close, high, low, volume, amount,
                 amplitude, pct_chg, chg, turnover, valid_data)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, rows)

            conn.commit()
            conn.close()
        except Exception as e:
            print(f"保存K线数据失败: {e}")

    def get_kline_data(self, code: str, days: int = 365) -> pd.DataFrame:
        conn = self._get_connection()
        cursor = conn.cursor()

        query = """
            SELECT date, open, close, high, low, volume, amount,
                   amplitude, pct_chg, chg, turnover, valid_data
            FROM daily
            WHERE code = ?
            ORDER BY date DESC
            LIMIT ?
        """
        df = pd.read_sql(query, conn, params=(code, days))

        conn.close()

        if not df.empty:
            df = df.sort_values('date').reset_index(drop=True)
            df['prev_close'] = df['close'].shift(1).fillna(df['close'])

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
            cursor.execute("SELECT DISTINCT code FROM daily WHERE LENGTH(code) = 6 ORDER BY code")
            codes = [row[0] for row in cursor.fetchall()]

        if not codes:
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='stock_list'")
            has_stock_list = cursor.fetchone() is not None

            if has_stock_list:
                cursor.execute("SELECT DISTINCT code FROM stock_list WHERE LENGTH(code) = 6 ORDER BY code")
                codes = [row[0] for row in cursor.fetchall()]

        conn.close()
        return codes
