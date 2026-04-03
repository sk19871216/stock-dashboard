"""
获取股票日线数据并存入数据库
使用 mootdx 库连接通达信行情服务器
"""

import sqlite3
import pandas as pd
from mootdx.quotes import Quotes
import time
from pathlib import Path


def get_db_path():
    """获取数据库路径"""
    base_dir = Path(__file__).parent.parent
    return base_dir / "data" / "stock_data.db"


def create_client():
    """创建行情客户端"""
    print("正在连接行情服务器...")
    client = Quotes.factory(market='std', server=('120.76.1.198', 7709))
    print("连接成功!")
    return client


def get_stock_list():
    """获取股票列表"""
    db_path = get_db_path()
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT code FROM stock_list')
        stocks = [row[0] for row in cursor.fetchall()]
    except:
        stocks = []
    conn.close()
    return stocks


def calculate_fields(df):
    """计算 amplitude, pct_chg, chg, turnover 等字段"""
    df = df.sort_index()

    df['chg'] = df['close'].diff()
    df['pct_chg'] = df['close'].pct_change() * 100
    df['amplitude'] = (df['high'] - df['low']) / df['close'].shift(1) * 100
    df['turnover'] = 0.0

    return df


def fetch_and_store_data(client, stock_code, conn):
    """获取单只股票的数据并存储"""
    try:
        df = client.bars(symbol=stock_code)

        if df is None or df.empty:
            return 0

        df_2026 = df[df.index >= '2026-01-01'].copy()

        if df_2026.empty:
            return 0

        df_2026 = calculate_fields(df_2026)

        cursor = conn.cursor()
        inserted_count = 0

        for idx, row in df_2026.iterrows():
            if row['volume'] < 1:
                continue

            date_str = idx.strftime('%Y-%m-%d')

            amplitude = row['amplitude'] if pd.notna(row['amplitude']) else 0.0
            pct_chg = row['pct_chg'] if pd.notna(row['pct_chg']) else 0.0
            chg = row['chg'] if pd.notna(row['chg']) else 0.0

            try:
                cursor.execute('''
                    INSERT OR REPLACE INTO daily
                    (date, code, open, close, high, low, volume, amount,
                     amplitude, pct_chg, chg, turnover, valid_data)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    date_str,
                    stock_code,
                    row['open'],
                    row['close'],
                    row['high'],
                    row['low'],
                    row['vol'],
                    row['amount'],
                    amplitude,
                    pct_chg,
                    chg,
                    0.0,
                    1
                ))
                inserted_count += 1
            except Exception as e:
                print(f"  插入数据失败 {stock_code} {date_str}: {e}")

        return inserted_count

    except Exception as e:
        print(f"  获取 {stock_code} 数据失败: {e}")
        return 0


def main():
    print("=" * 50)
    print("股票数据获取程序 - 2026年至今")
    print("=" * 50)

    db_path = get_db_path()
    conn = sqlite3.connect(str(db_path))
    print(f"数据库连接成功: {db_path}")

    client = create_client()

    stocks = get_stock_list()
    print(f"共有 {len(stocks)} 只股票")

    total_inserted = 0
    failed_stocks = []
    skip_count = 0

    for i, stock_code in enumerate(stocks):
        if (i + 1) % 100 == 0:
            print(f"\n进度: {i + 1}/{len(stocks)}")

        try:
            count = fetch_and_store_data(client, stock_code, conn)
            if count > 0:
                total_inserted += count
                print(f"  {stock_code}: 获取 {count} 条数据")
            else:
                skip_count += 1
        except Exception as e:
            failed_stocks.append((stock_code, str(e)))
            print(f"  {stock_code}: 失败 - {e}")

        if (i + 1) % 50 == 0:
            conn.commit()

        time.sleep(0.1)

    conn.commit()
    conn.close()

    print("\n" + "=" * 50)
    print("数据获取完成!")
    print(f"成功插入: {total_inserted} 条")
    print(f"无数据股票: {skip_count} 只")
    if failed_stocks:
        print(f"失败股票: {len(failed_stocks)} 只")
        for code, err in failed_stocks[:10]:
            print(f"  {code}: {err}")


if __name__ == "__main__":
    main()
