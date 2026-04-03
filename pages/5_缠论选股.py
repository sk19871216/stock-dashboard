import streamlit as st
import pandas as pd
import sys
from pathlib import Path
from datetime import datetime
import sqlite3
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.database import StockDatabase
from chanlun.analyzer import ChanlunAnalyzer


def get_all_stock_codes():
    """获取所有股票代码"""
    try:
        db_path = Path(__file__).parent.parent / "data" / "stock_data.db"
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute('SELECT DISTINCT code FROM daily ORDER BY code')
        codes = [row[0] for row in cursor.fetchall()]
        conn.close()
        return codes
    except:
        return []


def scan_single_stock(code, days, db, analyzer):
    """扫描单个股票，返回买点信号"""
    try:
        kline_data = db.get_kline_data(code, days=days)

        if kline_data.empty or len(kline_data) < 60:
            return None

        result = analyzer.analyze(kline_data, code)

        if not result['success']:
            return None

        latest_price = kline_data.iloc[-1]['close']
        signals = []

        for fb in result['first_buys']:
            signals.append({
                '股票代码': code,
                '买点类型': '一买',
                '买点日期': fb['date'],
                '买点价格': fb['price'],
                '当前价格': latest_price,
                '区间涨幅%': round(((latest_price - fb['price']) / fb['price'] * 100), 2) if fb['price'] > 0 else 0,
                '次阳涨幅%': fb.get('次日阳线涨幅%', '0%'),
                '是否新低': fb.get('是否新低', '否')
            })

        for sb in result['second_buys']:
            signals.append({
                '股票代码': code,
                '买点类型': '二买',
                '买点日期': sb['date'],
                '买点价格': sb['price'],
                '当前价格': latest_price,
                '区间涨幅%': round(((latest_price - sb['price']) / sb['price'] * 100), 2) if sb['price'] > 0 else 0,
                '次阳涨幅%': sb.get('次日阳线涨幅%', '0%'),
                '是否新低': '否'
            })

        return signals
    except Exception as e:
        return None


st.header("🎯 缠论选股")

st.warning("⚠️ **免责声明**: 选股结果仅供参考，不构成投资建议。股市有风险，投资需谨慎！")

db = StockDatabase()
analyzer = ChanlunAnalyzer()

st.subheader("全市场缠论扫描")

col1, col2 = st.columns([1, 1])
with col1:
    scan_limit = st.number_input("扫描股票数量", min_value=10, max_value=500, value=100)

with col2:
    scan_days = st.number_input("分析天数", min_value=60, max_value=365, value=180)

if st.button("🚀 开始扫描", type="primary"):
    all_codes = get_all_stock_codes()

    if not all_codes:
        st.error("无法获取股票列表，请先更新数据")
    else:
        scan_codes = all_codes[:scan_limit]
        st.info(f"即将扫描 {len(scan_codes)} 只股票，使用线程池并发执行...")

        all_signals = []
        progress_bar = st.progress(0)
        status_text = st.empty()
        completed = 0

        with ThreadPoolExecutor(max_workers=5) as executor:
            future_to_code = {
                executor.submit(scan_single_stock, code, scan_days, db, analyzer): code
                for code in scan_codes
            }

            for future in as_completed(future_to_code):
                code = future_to_code[future]
                try:
                    signals = future.result()
                    if signals:
                        all_signals.extend(signals)
                except Exception as e:
                    pass

                completed += 1
                progress = completed / len(scan_codes)
                progress_bar.progress(progress)
                status_text.text(f"已扫描 {completed}/{len(scan_codes)} 只股票...")

        if all_signals:
            signals_df = pd.DataFrame(all_signals)
            signals_df = signals_df.sort_values('买点日期', ascending=False)

            st.success(f"扫描完成！找到 {len(signals_df)} 个买点信号")

            st.markdown("### 买点信号列表")

            col1, col2, col3 = st.columns(3)
            with col1:
                first_buy_count = len(signals_df[signals_df['买点类型'] == '一买'])
                st.metric("一买信号", first_buy_count)
            with col2:
                second_buy_count = len(signals_df[signals_df['买点类型'] == '二买'])
                st.metric("二买信号", second_buy_count)
            with col3:
                unique_stocks = signals_df['股票代码'].nunique()
                st.metric("涉及股票", unique_stocks)

            st.dataframe(signals_df, use_container_width=True)

            col1, col2 = st.columns([1, 1])
            with col1:
                csv_data = signals_df.to_csv(index=False)
                st.download_button(
                    "📥 下载扫描结果",
                    csv_data,
                    f"chanlun_screening_{datetime.now().strftime('%Y%m%d')}.csv",
                    "text/csv"
                )

            with col2:
                if st.button("📤 导入到触发指标"):
                    db.clear_triggered_stocks()
                    for _, row in signals_df.iterrows():
                        db.add_to_triggered(
                            code=row['股票代码'],
                            name=row['买点类型'],
                            source=row['买点类型'],
                            trigger_date=row['买点日期'],
                            price=row['买点价格']
                        )
                    st.success(f"已将 {len(signals_df)} 条信号导入到触发指标")

            st.markdown("---")
            st.markdown("### 一买信号")
            first_df = signals_df[signals_df['买点类型'] == '一买']
            if not first_df.empty:
                st.dataframe(first_df, use_container_width=True)
            else:
                st.info("未找到一买信号")

            st.markdown("---")
            st.markdown("### 二买信号")
            second_df = signals_df[signals_df['买点类型'] == '二买']
            if not second_df.empty:
                st.dataframe(second_df, use_container_width=True)
            else:
                st.info("未找到二买信号")

        else:
            st.warning("扫描完成，未找到任何买点信号")

st.markdown("---")
st.markdown("""
### 📖 选股说明

**一买（第一买点）**:
- 下降趋势结束时的底背驰买点
- 满足背驰条件（A/B/C任一）
- 通常是较强的买入信号

**二买（第二买点）**:
- 一买后上升回调、不破一买的买点
- 相对一买更安全

### 💡 使用建议

1. 优先关注近期出现的一买信号（距今15天内）
2. 关注"是否新低"字段，为"是"的是真一买
3. 关注次阳涨幅，较大的次阳涨幅说明买点有效
""")
