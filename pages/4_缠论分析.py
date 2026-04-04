import streamlit as st
import pandas as pd
import sys
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import sqlite3

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.database import StockDatabase
from utils.styles import highlight_yangxian
from chanlun.analyzer import ChanlunAnalyzer


def format_amount(value):
    """格式化金额为万、亿单位"""
    if value is None or value == '':
        return '0'
    try:
        val = float(value)
        if val >= 100000000:
            return f'{val/100000000:.2f}亿'
        elif val >= 10000:
            return f'{val/10000:.2f}万'
        else:
            return f'{val:.2f}'
    except (ValueError, TypeError):
        return str(value)


@st.cache_data(ttl=300)
def get_watchlist_cached():
    db = StockDatabase()
    return db.get_watchlist()


def get_all_stock_codes_cached():
    try:
        db_path = Path(__file__).parent.parent / "data" / "stock_data.db"
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT DISTINCT code FROM daily WHERE LENGTH(code) = 6 ORDER BY code')
        codes = []
        for row in cursor.fetchall():
            code = row[0]
            codes.append(str(code))
        conn.close()
        return codes
    except Exception as e:
        print(f"Error getting codes: {e}")
        return []


def scan_single_stock(code, days, db, analyzer):
    try:
        kline_data = db.get_kline_data(code, days=days)
        if kline_data.empty or len(kline_data) < 30:
            return None

        result = analyzer.analyze(kline_data, code)
        if not result['success']:
            return None

        latest_price = float(kline_data.iloc[-1]['close'])
        signals = []

        for fb in result['first_buys']:
            fb_price = float(fb.get('price', 0))
            signal = {
                '序号': '',
                '股票代码': str(code),
                '买点类型': '一买',
                '买点日期': str(fb.get('date', '')),
                '买点价格': fb_price,
                '当前价格': latest_price,
                '区间涨幅%': round(((latest_price - fb_price) / fb_price * 100), 2) if fb_price > 0 else 0,
                '次阳涨幅%': str(fb.get('次日阳线涨幅%', '0%')),
                '是否新低': str(fb.get('是否新低', '否'))
            }
            signals.append(signal)

        for sb in result['second_buys']:
            sb_price = float(sb.get('price', 0))
            signal = {
                '序号': '',
                '股票代码': str(code),
                '买点类型': '二买',
                '买点日期': str(sb.get('date', '')),
                '买点价格': sb_price,
                '当前价格': latest_price,
                '区间涨幅%': round(((latest_price - sb_price) / sb_price * 100), 2) if sb_price > 0 else 0,
                '次阳涨幅%': str(sb.get('次日阳线涨幅%', '0%')),
                '是否新低': '否'
            }
            signals.append(signal)

        return signals
    except Exception as e:
        print(f"Error scanning {code}: {e}")
        return None


st.header("📊 缠论分析")

st.warning("⚠️ **免责声明**: 缠论分析仅供参考，不构成投资建议。股市有风险，投资需谨慎！")

db = StockDatabase()
analyzer = ChanlunAnalyzer()
watchlist = get_watchlist_cached()

tab1, tab2 = st.tabs(["🔍 单股分析", "🎯 全市场扫描"])

with tab1:
    st.subheader("单只股票缠论分析")

    col1, col2 = st.columns([1, 1])
    with col1:
        analyze_code = st.text_input("股票代码", placeholder="例如: 000006", key="analyze_code")

    if not watchlist.empty:
        watchlist_codes = watchlist['code'].tolist()
        selected = st.selectbox("或从自选股选择", [""] + watchlist_codes, key="analyze_select")
        if selected:
            analyze_code = selected

    col1, col2 = st.columns([1, 1])
    with col1:
        days = st.number_input("分析天数", min_value=60, max_value=730, value=180, step=30, key="analyze_days")

    if st.button("🔍 开始分析", type="primary"):
        if analyze_code:
            kline_data = db.get_kline_data(analyze_code, days=days)

            if kline_data.empty:
                st.error("暂无数据，请先更新数据")
            else:
                with st.spinner("正在分析..."):
                    result = analyzer.analyze(kline_data, analyze_code)

                    if result['success']:
                        st.success("分析完成！")

                        st.markdown("---")
                        st.markdown(f"### {analyze_code} 分析结果")

                        col1, col2, col3, col4 = st.columns(4)
                        with col1:
                            st.metric("数据条数", result['data_count'])
                        with col2:
                            st.metric("识别分型", result['fenxing_count'])
                        with col3:
                            st.metric("识别趋势", result['trend_count'])
                        with col4:
                            total_signals = len(result['first_buys']) + len(result['second_buys'])
                            st.metric("买点信号", total_signals)

                        st.markdown("---")

                        col1, col2 = st.columns(2)
                        with col1:
                            st.markdown("#### 一买信号")
                            if result['first_buys']:
                                for fb in result['first_buys']:
                                    is_new_low = fb.get('是否新低', '否')
                                    low_emoji = "🟢" if is_new_low == '是' else "🟡"
                                    st.markdown(f"📌 **{fb['date']}** @ {fb['price']:.2f} {low_emoji} 新低:{is_new_low}")
                                    with st.expander("🔍 查看详情"):
                                        st.write(f"**是否新低**: {is_new_low}")
                                        st.write(f"**次日阳线涨幅**: {fb.get('次日阳线涨幅%', '0%')}")
                                        st.write(f"**是否背驰**: {fb.get('是否背驰', '未知')}")
                                        cond_a = fb.get('面积A', '否')
                                        cond_b = fb.get('面积B', '否')
                                        cond_c = fb.get('面积C', '否')
                                        st.write(f"**条件A(面积减少)**: {cond_a}")
                                        st.write(f"**条件B(高度降低)**: {cond_b}")
                                        st.write(f"**条件C(力度减弱)**: {cond_c}")
                                        if fb.get('在中枢内') == '是':
                                            st.write("✅ 在中枢内")
                                        st.write(f"**价格差%**: {fb.get('价格差%', 'N/A')}")
                                        st.write(f"**绿柱面积**: {fb.get('绿柱面积', 'N/A')}")
                                        st.write(f"**绿柱高度**: {fb.get('绿柱高度', 'N/A')}")
                                        st.write(f"**力度**: {fb.get('力度', 'N/A')}")
                            else:
                                st.info("未识别到一买信号")

                        with col2:
                            st.markdown("#### 二买信号")
                            if result['second_buys']:
                                for sb in result['second_buys']:
                                    st.markdown(f"📌 **{sb['date']}** @ {sb['price']:.2f}")
                                    with st.expander("🔍 查看详情"):
                                        st.write(f"**次日阳线涨幅**: {sb.get('次日阳线涨幅%', '0%')}")
                                        if sb.get('对应1买日期'):
                                            st.write(f"**对应一买日期**: {sb['对应1买日期']}")
                                            st.write(f"**对应一买价格**: {sb.get('对应1买价格', 'N/A')}")
                                        st.write(f"**回调幅度%**: {sb.get('回调幅度%', 'N/A')}")
                                        st.write(f"**绿柱面积**: {sb.get('绿柱面积', 'N/A')}")
                                        st.write(f"**力度**: {sb.get('力度', 'N/A')}")
                            else:
                                st.info("未识别到二买信号")

                        st.markdown("---")

                        summary_df = analyzer.get_buy_signals_summary(result)
                        if not summary_df.empty:
                            st.markdown("#### 买点信号汇总")

                            styled_df = summary_df.style.map(
                                highlight_yangxian,
                                subset=['次阳涨幅%']
                            )
                            st.dataframe(styled_df, use_container_width=True)

                        st.markdown("---")
                        st.markdown("#### 分型列表")
                        if result.get('fenxing_list'):
                            fx_data = []
                            for idx, ftype, kline in result['fenxing_list']:
                                fx_type = "🔴 顶" if ftype == '顶' else "🟢 底"
                                fx_data.append({
                                    '序号': idx,
                                    '分型': fx_type,
                                    '日期': str(kline['date'])[:10],
                                    '最高价': f"{kline['high']:.2f}",
                                    '最低价': f"{kline['low']:.2f}"
                                })
                            fx_df = pd.DataFrame(fx_data)
                            st.dataframe(fx_df, use_container_width=True)
                    else:
                        st.error(f"分析失败: {result.get('error', '未知错误')}")
        else:
            st.warning("请输入股票代码或选择自选股")

with tab2:
    st.subheader("全市场缠论扫描")

    all_codes = get_all_stock_codes_cached()
    total_stocks = len(all_codes) if all_codes else 0
    st.metric("股票总数", total_stocks)

    scan_limit = 5191

    col1, col2 = st.columns([1, 1])
    with col1:
        st.info(f"扫描股票数量: {scan_limit}")

    with col2:
        scan_days = st.number_input("分析天数", min_value=60, max_value=365, value=180, key="scan_days_input")

    if st.button("🚀 开始扫描", type="primary"):
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
                signals_df = signals_df.reset_index(drop=True)

                col_order = ['序号', '股票代码', '买点类型', '买点日期', '买点价格', '当前价格', '区间涨幅%', '次阳涨幅%', '是否新低']
                for col in col_order:
                    if col not in signals_df.columns:
                        signals_df[col] = ''
                signals_df = signals_df[col_order]
                signals_df['序号'] = range(1, len(signals_df) + 1)
                signals_df = signals_df.sort_values('买点日期', ascending=False)

                st.success(f"扫描完成！找到 {len(signals_df)} 个买点信号")

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

                st.markdown("### 一买信号列表")
                first_df = signals_df[signals_df['买点类型'] == '一买']
                if not first_df.empty:
                    st.dataframe(first_df, use_container_width=True)

                st.markdown("### 二买信号列表")
                second_df = signals_df[signals_df['买点类型'] == '二买']
                if not second_df.empty:
                    st.dataframe(second_df, use_container_width=True)

                st.markdown("### 全部买点信号")
                st.dataframe(signals_df, use_container_width=True)

                col1, col2 = st.columns([1, 1])
                with col1:
                    download_df = signals_df.copy()
                    download_df['股票代码'] = '=' + download_df['股票代码']
                    download_df['买点价格'] = download_df['买点价格'].apply(format_amount)
                    download_df['当前价格'] = download_df['当前价格'].apply(format_amount)
                    csv_data = download_df.to_csv(index=False, encoding='gbk')
                    st.download_button(
                        "📥 下载扫描结果",
                        csv_data,
                        f"chanlun_scan_{datetime.now().strftime('%Y%m%d')}.csv",
                        "text/csv"
                    )
            else:
                st.info("未找到任何买点信号")
