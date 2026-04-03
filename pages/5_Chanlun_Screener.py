import streamlit as st
import pandas as pd
import sys
from pathlib import Path
from datetime import datetime
import sqlite3

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


st.header("🎯 缠论选股")

st.warning("⚠️ **免责声明**: 选股结果仅供参考，不构成投资建议。")

db = StockDatabase()
analyzer = ChanlunAnalyzer()

tab1, tab2 = st.tabs(["📊 全市场扫描", "📈 扫描结果"])

    with tab1:
        st.subheader("全市场缠论扫描")

        st.info("⚠️ 全市场扫描需要较长时间，请耐心等待")

        col1, col2 = st.columns([1, 1])
        with col1:
            scan_limit = st.number_input("扫描股票数量", min_value=10, max_value=500, value=100)

        with col2:
            scan_days = st.number_input("分析天数", min_value=60, max_value=365, value=180)

        if st.button("🚀 开始全市场扫描", type="primary"):
            with st.spinner(f"正在扫描前 {scan_limit} 只股票..."):
                all_codes = get_all_stock_codes()

                if not all_codes:
                    st.error("无法获取股票列表")
                else:
                    scan_codes = all_codes[:scan_limit]

                    all_first_buys = []
                    all_second_buys = []
                    progress_bar = st.progress(0)

                    for i, code in enumerate(scan_codes):
                        kline_data = db.get_kline_data(code, days=scan_days)

                        if kline_data.empty or len(kline_data) < 60:
                            progress_bar.progress((i + 1) / len(scan_codes))
                            continue

                        result = analyzer.analyze(kline_data, code)

                        if result['success']:
                            latest_price = kline_data.iloc[-1]['close']
                            latest_date = kline_data.iloc[-1]['date']

                            for fb in result['first_buys']:
                                all_first_buys.append({
                                    '股票代码': code,
                                    '买点日期': fb['date'],
                                    '买点价格': fb['price'],
                                    '当前价格': latest_price,
                                    '区间涨幅%': ((latest_price - fb['price']) / fb['price'] * 100) if fb['price'] > 0 else 0,
                                    '次阳涨幅%': fb['next_day_yangxian_pct'],
                                    '验证': '是' if fb['verified'] else '否'
                                })

                            for sb in result['second_buys']:
                                all_second_buys.append({
                                    '股票代码': code,
                                    '买点日期': sb['date'],
                                    '买点价格': sb['price'],
                                    '当前价格': latest_price,
                                    '区间涨幅%': ((latest_price - sb['price']) / sb['price'] * 100) if sb['price'] > 0 else 0,
                                    '次阳涨幅%': sb['next_day_yangxian_pct'],
                                    '验证': '是' if sb['verified'] else '否'
                                })

                        progress_bar.progress((i + 1) / len(scan_codes))

                    st.session_state['first_buys_df'] = pd.DataFrame(all_first_buys) if all_first_buys else pd.DataFrame()
                    st.session_state['second_buys_df'] = pd.DataFrame(all_second_buys) if all_second_buys else pd.DataFrame()

                    st.success(f"扫描完成！")
                    st.info(f"找到一买信号: {len(all_first_buys)} 个, 二买信号: {len(all_second_buys)} 个")
                    st.info("请切换到「扫描结果」标签页查看详细结果")

    with tab2:
        st.subheader("扫描结果")

        has_results = False

        if 'first_buys_df' in st.session_state and not st.session_state['first_buys_df'].empty:
            has_results = True
            st.markdown("### 一买信号列表")
            st.dataframe(st.session_state['first_buys_df'], use_container_width=True)

            csv1 = st.session_state['first_buys_df'].to_csv(index=False)
            col1, col2 = st.columns([1, 1])
            with col1:
                st.download_button(
                    "📥 下载一买结果",
                    csv1,
                    f"first_buy_{datetime.now().strftime('%Y%m%d')}.csv",
                    "text/csv",
                    key="download_first"
                )
            with col2:
                if st.button("📤 导入到触发指标（一买）", key="import_first"):
                    all_results = st.session_state['first_buys_df'].to_dict('records')
                    for record in all_results:
                        record['名称'] = record.get('股票代码', '')
                    st.session_state['triggered_stocks'] = all_results
                    st.success(f"已将 {len(all_results)} 只一买股票导入到触发指标")

        if 'second_buys_df' in st.session_state and not st.session_state['second_buys_df'].empty:
            has_results = True
            st.markdown("---")
            st.markdown("### 二买信号列表")
            st.dataframe(st.session_state['second_buys_df'], use_container_width=True)

            csv2 = st.session_state['second_buys_df'].to_csv(index=False)
            col1, col2 = st.columns([1, 1])
            with col1:
                st.download_button(
                    "📥 下载二买结果",
                    csv2,
                    f"second_buy_{datetime.now().strftime('%Y%m%d')}.csv",
                    "text/csv",
                    key="download_second"
                )
            with col2:
                if st.button("📤 导入到触发指标（二买）", key="import_second"):
                    all_results = st.session_state['second_buys_df'].to_dict('records')
                    for record in all_results:
                        record['名称'] = record.get('股票代码', '')
                    st.session_state['triggered_stocks'] = all_results
                    st.success(f"已将 {len(all_results)} 只二买股票导入到触发指标")

        if 'first_buys_df' in st.session_state and 'second_buys_df' in st.session_state:
            first_df = st.session_state.get('first_buys_df', pd.DataFrame())
            second_df = st.session_state.get('second_buys_df', pd.DataFrame())

            if not first_df.empty and not second_df.empty:
                st.markdown("---")
                st.markdown("### 全部买点信号")

                all_signals_df = pd.concat([first_df, second_df], ignore_index=True)
                all_signals_df = all_signals_df.sort_values('买点日期', ascending=False)

                st.dataframe(all_signals_df, use_container_width=True)

                if st.button("📤 导入全部到触发指标", key="import_all"):
                    all_results = all_signals_df.to_dict('records')
                    for record in all_results:
                        record['名称'] = record.get('股票代码', '')
                    st.session_state['triggered_stocks'] = all_results
                    st.success(f"已将 {len(all_results)} 只股票导入到触发指标")

                    csv_all = all_signals_df.to_csv(index=False)
                    st.download_button(
                        "📥 下载全部结果",
                        csv_all,
                        f"all_buy_signals_{datetime.now().strftime('%Y%m%d')}.csv",
                        "text/csv",
                        key="download_all"
                    )

        if not has_results:
            st.info("暂无扫描结果，请先进行全市场扫描")

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
    - 可能是更好的买入机会

    ### 💡 使用建议

    1. 优先关注近期出现的一买信号（距今15天内）
    2. 验证状态为"已验证"的信号更可靠
    3. 关注次阳涨幅，较大的次阳涨幅说明买点有效
    4. 结合作者技术面和基本面综合判断
    """)
