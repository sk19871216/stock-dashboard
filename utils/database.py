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
                next_yang_return TEXT,
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

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS chanlun_signals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT NOT NULL,
                name TEXT,
                signal_type TEXT NOT NULL,
                signal_date TEXT NOT NULL,
                signal_price REAL,
                current_price REAL,
                interval_return REAL,
                next_yang_return TEXT,
                is_new_low TEXT,
                divergence_details TEXT,
                scan_date TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(code, signal_type, signal_date)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS limit_up_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trade_date TEXT NOT NULL,
                code TEXT NOT NULL,
                name TEXT,
                reason TEXT,
                limit_count INTEGER,
                limit_time TEXT,
                sector TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(trade_date, code)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS limit_down_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trade_date TEXT NOT NULL,
                code TEXT NOT NULL,
                name TEXT,
                reason TEXT,
                limit_count INTEGER,
                limit_time TEXT,
                sector TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(trade_date, code)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sector_flow_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trade_date TEXT NOT NULL,
                sector_name TEXT NOT NULL,
                main_net_inflow REAL,
                net_inflow_ratio REAL,
                change_pct REAL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(trade_date, sector_name)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS hot_stocks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trade_date TEXT NOT NULL,
                rank INTEGER NOT NULL,
                rank_change INTEGER DEFAULT 0,
                code TEXT NOT NULL,
                name TEXT,
                change_pct REAL DEFAULT 0,
                attention_ratio TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(trade_date, code)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS industry_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                trade_date TEXT NOT NULL,
                seq INTEGER NOT NULL,
                board_name TEXT NOT NULL,
                change_pct REAL DEFAULT 0,
                volume TEXT DEFAULT '',
                amount TEXT DEFAULT '',
                net_flow TEXT DEFAULT '',
                up_count INTEGER DEFAULT 0,
                down_count INTEGER DEFAULT 0,
                avg_price TEXT DEFAULT '',
                top_stock TEXT DEFAULT '',
                top_price TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(trade_date, board_name)
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS training_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                training_id TEXT NOT NULL,
                code TEXT NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                total_profit REAL DEFAULT 0,
                total_trades INTEGER DEFAULT 0,
                win_rate REAL DEFAULT 0,
                max_drawdown REAL DEFAULT 0,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS trade_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                training_id TEXT NOT NULL,
                trade_date TEXT NOT NULL,
                code TEXT NOT NULL,
                trade_type TEXT NOT NULL,
                price REAL NOT NULL,
                quantity REAL NOT NULL,
                position REAL NOT NULL,
                reason TEXT,
                ai_comment TEXT,
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
                    (code, name, source, trigger_date, price, next_yang_return, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    stock.get('code', ''),
                    stock.get('name', ''),
                    stock.get('source', ''),
                    stock.get('trigger_date', date.today().isoformat()),
                    stock.get('price'),
                    stock.get('next_yang_return', ''),
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

    def save_chanlun_signals(self, signals: List[Dict], scan_date: str = None) -> int:
        """保存缠论买点信号到数据库"""
        if not scan_date:
            scan_date = date.today().isoformat()

        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            saved_count = 0
            for signal in signals:
                cursor.execute("""
                    INSERT OR REPLACE INTO chanlun_signals
                    (code, name, signal_type, signal_date, signal_price, current_price,
                     interval_return, next_yang_return, is_new_low, divergence_details, scan_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    signal.get('股票代码', ''),
                    signal.get('name', ''),
                    signal.get('买点类型', ''),
                    signal.get('买点日期', ''),
                    signal.get('买点价格'),
                    signal.get('当前价格'),
                    signal.get('区间涨幅%'),
                    signal.get('次阳涨幅%', ''),
                    signal.get('是否新低', ''),
                    signal.get('背驰详情', ''),
                    scan_date
                ))
                saved_count += 1

            conn.commit()
            conn.close()
            return saved_count
        except Exception as e:
            print(f"保存缠论信号失败: {e}")
            return 0

    def get_chanlun_signals(self, scan_date: str = None) -> pd.DataFrame:
        """获取缠论买点信号"""
        conn = self._get_connection()
        cursor = conn.cursor()

        if scan_date:
            query = """
                SELECT * FROM chanlun_signals
                WHERE scan_date = ?
                ORDER BY signal_date DESC, code
            """
            df = pd.read_sql(query, conn, params=(scan_date,))
        else:
            query = """
                SELECT * FROM chanlun_signals
                ORDER BY scan_date DESC, signal_date DESC, code
            """
            df = pd.read_sql(query, conn)

        conn.close()
        return df

    def get_latest_chanlun_signals(self) -> pd.DataFrame:
        """获取最新日期的缠论买点信号"""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT scan_date FROM chanlun_signals
            ORDER BY scan_date DESC LIMIT 1
        """)
        result = cursor.fetchone()

        if result:
            latest_date = result[0]
            df = pd.read_sql("""
                SELECT * FROM chanlun_signals
                WHERE scan_date = ?
                ORDER BY signal_date DESC, code
            """, conn, params=(latest_date,))
        else:
            df = pd.DataFrame()

        conn.close()
        return df

    def get_chanlun_signals_count(self) -> int:
        """获取缠论信号数量"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM chanlun_signals")
        count = cursor.fetchone()[0]
        conn.close()
        return count

    def clear_chanlun_signals(self, scan_date: str = None) -> bool:
        """清空缠论信号"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            if scan_date:
                cursor.execute("DELETE FROM chanlun_signals WHERE scan_date = ?", (scan_date,))
            else:
                cursor.execute("DELETE FROM chanlun_signals")

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"清空缠论信号失败: {e}")
            return False

    def save_limit_up_history(self, data: List[Dict], trade_date: str) -> int:
        """保存涨停历史数据"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            saved_count = 0
            for item in data:
                code = item.get('代码', item.get('code', ''))
                name = item.get('名称', item.get('name', ''))
                sector = item.get('所属行业', item.get('sector', ''))

                cursor.execute("""
                    INSERT OR REPLACE INTO limit_up_history
                    (trade_date, code, name, reason, limit_count, limit_time, sector)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    trade_date,
                    code,
                    name,
                    sector,
                    item.get('连板数', 0),
                    item.get('涨停统计', ''),
                    item.get('首次封板时间', '')
                ))
                saved_count += 1

            conn.commit()
            conn.close()
            return saved_count
        except Exception as e:
            print(f"保存涨停历史失败: {e}")
            return 0

    def save_limit_down_history(self, data: List[Dict], trade_date: str) -> int:
        """保存跌停历史数据"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            saved_count = 0
            for item in data:
                code = item.get('代码', item.get('code', ''))
                name = item.get('名称', item.get('name', ''))
                sector = item.get('所属行业', item.get('sector', ''))

                cursor.execute("""
                    INSERT OR REPLACE INTO limit_down_history
                    (trade_date, code, name, reason, limit_count, limit_time, sector)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    trade_date,
                    code,
                    name,
                    sector,
                    item.get('连板数', 0),
                    item.get('涨停统计', ''),
                    item.get('首次封板时间', '')
                ))
                saved_count += 1

            conn.commit()
            conn.close()
            return saved_count
        except Exception as e:
            print(f"保存跌停历史失败: {e}")
            return 0

    def save_sector_flow_history(self, data: pd.DataFrame, trade_date: str) -> int:
        """保存板块资金流向历史数据"""
        try:
            data = data.copy()
            
            if '行业' in data.columns:
                data.rename(columns={'行业': '板块'}, inplace=True)
            
            if '行业-涨跌幅' in data.columns:
                data.rename(columns={'行业-涨跌幅': '涨跌幅'}, inplace=True)
            
            if '净额' in data.columns:
                data.rename(columns={'净额': '主力净流入'}, inplace=True)
            
            cols = data.columns.tolist()
            if len(cols) >= 7 and all(isinstance(c, (int, float)) or (isinstance(c, str) and c.replace('.', '').replace('-', '').isdigit()) for c in cols[:3]):
                expected = ['板块', '涨跌幅', '成交额', '主力净流入', '超大单净流入', '大单净流入', '中单净流入', '小单净流入']
                data.columns = expected[:len(cols)]

            conn = self._get_connection()
            cursor = conn.cursor()

            saved_count = 0
            for _, row in data.iterrows():
                sector_name = row.get('板块', row.get('名称', ''))
                main_inflow = row.get('主力净流入', 0)
                net_ratio = row.get('净流入占比', 0)
                change_pct = row.get('涨跌幅', 0)

                cursor.execute("""
                    INSERT OR REPLACE INTO sector_flow_history
                    (trade_date, sector_name, main_net_inflow, net_inflow_ratio, change_pct)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    trade_date,
                    sector_name,
                    main_inflow,
                    net_ratio,
                    change_pct
                ))
                saved_count += 1

            conn.commit()
            conn.close()
            return saved_count
        except Exception as e:
            print(f"保存板块资金流向历史失败: {e}")
            return 0

    def get_limit_up_history(self, days: int = 1) -> pd.DataFrame:
        """获取涨停历史数据"""
        conn = self._get_connection()
        query = """
            SELECT * FROM limit_up_history
            WHERE trade_date >= date('now', '-' || ? || ' days')
            ORDER BY trade_date DESC, code
        """
        df = pd.read_sql(query, conn, params=(days,))
        conn.close()
        return df

    def get_limit_down_history(self, days: int = 1) -> pd.DataFrame:
        """获取跌停历史数据"""
        conn = self._get_connection()
        query = """
            SELECT * FROM limit_down_history
            WHERE trade_date >= date('now', '-' || ? || ' days')
            ORDER BY trade_date DESC, code
        """
        df = pd.read_sql(query, conn, params=(days,))
        conn.close()
        return df

    def get_sector_flow_history(self, days: int = 1) -> pd.DataFrame:
        """获取板块资金流向历史数据"""
        conn = self._get_connection()
        query = """
            SELECT * FROM sector_flow_history
            WHERE trade_date >= date('now', '-' || ? || ' days')
            ORDER BY trade_date DESC, main_net_inflow DESC
        """
        df = pd.read_sql(query, conn, params=(days,))
        conn.close()
        return df

    def get_limit_up_history_by_date(self, trade_date: str) -> pd.DataFrame:
        """获取指定日期的涨停历史数据"""
        conn = self._get_connection()
        query = """
            SELECT * FROM limit_up_history
            WHERE trade_date = ?
            ORDER BY code
        """
        df = pd.read_sql(query, conn, params=(trade_date,))
        conn.close()
        return df

    def get_limit_down_history_by_date(self, trade_date: str) -> pd.DataFrame:
        """获取指定日期的跌停历史数据"""
        conn = self._get_connection()
        query = """
            SELECT * FROM limit_down_history
            WHERE trade_date = ?
            ORDER BY code
        """
        df = pd.read_sql(query, conn, params=(trade_date,))
        conn.close()
        return df

    def get_sector_flow_history_by_date(self, trade_date: str) -> pd.DataFrame:
        """获取指定日期的板块资金流向历史数据"""
        conn = self._get_connection()
        
        date_formats = [trade_date]
        if len(trade_date) == 8:
            date_formats.append(f"{trade_date[:4]}-{trade_date[4:6]}-{trade_date[6:8]}")
        elif '-' not in trade_date:
            if len(trade_date) == 10:
                date_formats.append(trade_date[:4] + '-' + trade_date[4:6] + '-' + trade_date[6:])
        
        placeholders = ','.join(['?' for _ in date_formats])
        query = f"""
            SELECT * FROM sector_flow_history
            WHERE trade_date IN ({placeholders})
            ORDER BY change_pct DESC
        """
        
        df = pd.read_sql(query, conn, params=tuple(date_formats))
        conn.close()
        return df

    def save_training_record(self, training_id: str, code: str, start_date: str, end_date: str,
                           total_profit: float = 0, total_trades: int = 0, win_rate: float = 0,
                           max_drawdown: float = 0, notes: str = "") -> bool:
        """保存训练记录"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO training_records
                (training_id, code, start_date, end_date, total_profit, total_trades, win_rate, max_drawdown, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (training_id, code, start_date, end_date, total_profit, total_trades, win_rate, max_drawdown, notes))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"保存训练记录失败: {e}")
            return False

    def save_trade_record(self, training_id: str, trade_date: str, code: str, trade_type: str,
                         price: float, quantity: float, position: float, reason: str = "",
                         ai_comment: str = "") -> bool:
        """保存交易记录"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO trade_records
                (training_id, trade_date, code, trade_type, price, quantity, position, reason, ai_comment)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (training_id, trade_date, code, trade_type, price, quantity, position, reason, ai_comment))
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"保存交易记录失败: {e}")
            return False

    def get_training_records(self, limit: int = 100) -> pd.DataFrame:
        """获取训练记录"""
        conn = self._get_connection()
        query = """
            SELECT * FROM training_records
            ORDER BY created_at DESC
            LIMIT ?
        """
        df = pd.read_sql(query, conn, params=(limit,))
        conn.close()
        return df

    def get_trade_records(self, training_id: str) -> pd.DataFrame:
        """获取指定训练ID的交易记录"""
        conn = self._get_connection()
        query = """
            SELECT * FROM trade_records
            WHERE training_id = ?
            ORDER BY trade_date
        """
        df = pd.read_sql(query, conn, params=(training_id,))
        conn.close()
        return df

    def save_hot_stocks(self, data: List[Dict], trade_date: str = None) -> int:
        """保存热门个股数据"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            saved_count = 0
            for item in data:
                code = str(item.get('code', '')).zfill(6)
                if len(code) != 6:
                    continue

                if trade_date is None:
                    trade_date = item.get('trade_date', datetime.now().strftime("%Y-%m-%d"))

                cursor.execute("""
                    INSERT OR REPLACE INTO hot_stocks
                    (trade_date, rank, rank_change, code, name, change_pct, attention_ratio)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    trade_date,
                    item.get('rank', 0),
                    item.get('rank_change', 0),
                    code,
                    item.get('name', ''),
                    item.get('change_pct', 0),
                    item.get('attention_ratio', '')
                ))
                saved_count += 1

            conn.commit()
            conn.close()
            return saved_count
        except Exception as e:
            print(f"保存热门个股数据失败: {e}")
            return 0

    def save_industry_data(self, data: List[Dict]) -> int:
        """保存行业数据"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            saved_count = 0
            for item in data:
                board_name = item.get('board_name', '')
                if not board_name:
                    continue

                trade_date = item.get('trade_date', datetime.now().strftime("%Y-%m-%d"))

                cursor.execute("""
                    INSERT OR REPLACE INTO industry_data
                    (trade_date, seq, board_name, change_pct, volume, amount, net_flow,
                     up_count, down_count, avg_price, top_stock, top_price)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    trade_date,
                    item.get('seq', 0),
                    board_name,
                    item.get('change_pct', 0),
                    item.get('volume', ''),
                    item.get('amount', ''),
                    item.get('net_flow', ''),
                    item.get('up_count', 0),
                    item.get('down_count', 0),
                    item.get('avg_price', ''),
                    item.get('top_stock', ''),
                    item.get('top_price', '')
                ))
                saved_count += 1

            conn.commit()
            conn.close()
            return saved_count
        except Exception as e:
            print(f"保存行业数据失败: {e}")
            return 0

    def get_industry_data(self, trade_date: str = None) -> pd.DataFrame:
        """获取行业数据"""
        conn = self._get_connection()
        cursor = conn.cursor()

        if trade_date:
            query = """
                SELECT * FROM industry_data
                WHERE trade_date = ?
                ORDER BY seq
            """
            df = pd.read_sql(query, conn, params=(trade_date,))
        else:
            query = """
                SELECT * FROM industry_data
                WHERE trade_date = (SELECT MAX(trade_date) FROM industry_data)
                ORDER BY seq
            """
            df = pd.read_sql(query, conn)

        conn.close()
        return df

    def get_industry_data_dates(self) -> List[str]:
        """获取所有有行业数据的日期"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT DISTINCT trade_date FROM industry_data
            ORDER BY trade_date DESC
        """)
        dates = [row[0] for row in cursor.fetchall()]
        conn.close()
        return dates

    def get_hot_stocks(self, trade_date: str = None, limit: int = 100) -> pd.DataFrame:
        """获取热门个股数据"""
        conn = self._get_connection()
        cursor = conn.cursor()

        if trade_date:
            query = """
                SELECT * FROM hot_stocks
                WHERE trade_date = ?
                ORDER BY rank
                LIMIT ?
            """
            df = pd.read_sql(query, conn, params=(trade_date, limit))
        else:
            query = """
                SELECT * FROM hot_stocks
                WHERE trade_date = (SELECT MAX(trade_date) FROM hot_stocks)
                ORDER BY rank
                LIMIT ?
            """
            df = pd.read_sql(query, conn, params=(limit,))

        conn.close()
        return df

    def get_hot_stocks_by_date(self, trade_date: str) -> pd.DataFrame:
        """获取指定日期的热门个股数据"""
        return self.get_hot_stocks(trade_date)

    def get_hot_stocks_dates(self) -> List[str]:
        """获取所有有热门个股数据的日期"""
        conn = self._get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT DISTINCT trade_date FROM hot_stocks
            ORDER BY trade_date DESC
        """)
        dates = [row[0] for row in cursor.fetchall()]
        conn.close()
        return dates

    def get_hot_stocks_count(self, trade_date: str = None) -> int:
        """获取热门个股数量"""
        conn = self._get_connection()
        cursor = conn.cursor()

        if trade_date:
            cursor.execute("SELECT COUNT(*) FROM hot_stocks WHERE trade_date = ?", (trade_date,))
        else:
            cursor.execute("""
                SELECT COUNT(*) FROM hot_stocks
                WHERE trade_date = (SELECT MAX(trade_date) FROM hot_stocks)
            """)

        count = cursor.fetchone()[0]
        conn.close()
        return count

    def clear_hot_stocks(self, trade_date: str = None) -> bool:
        """清空热门个股数据"""
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            if trade_date:
                cursor.execute("DELETE FROM hot_stocks WHERE trade_date = ?", (trade_date,))
            else:
                cursor.execute("DELETE FROM hot_stocks")

            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"清空热门个股数据失败: {e}")
            return False

    def get_training_record_by_id(self, training_id: str) -> pd.DataFrame:
        """根据训练ID获取训练记录"""
        conn = self._get_connection()
        query = """
            SELECT * FROM training_records
            WHERE training_id = ?
        """
        df = pd.read_sql(query, conn, params=(training_id,))
        conn.close()
        return df
