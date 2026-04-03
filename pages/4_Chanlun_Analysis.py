import streamlit as st
import pandas as pd
import sys
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.database import StockDatabase
from chanlun.analyzer import ChanlunAnalyzer

st.header("📊 缠论分析")

st.warning("⚠️ **免责声明**: 缠论分析仅供参考，不构成投资建议。股市有风险，投资需谨慎！")

db = StockDatabase()
analyzer = ChanlunAnalyzer()

tab1, tab2, tab3 = st.tabs(["🔍 单股分析", "📈 MACD分析", "📋 历史买点"])

with tab1:
    st.subheader("单只股票缠论分析")

    col1, col2 = st.columns([1, 1])
    with col1:
        analyze_code = st.text_input("股票代码", placeholder="例如: 000006", key="analyze_code")

    watchlist = db.get_watchlist()
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

                            def highlight_yangxian(val):
                                if isinstance(val, str) and '%' in val:
                                    pct = float(val.replace('%', ''))
                                    if pct > 3:
                                        return 'color: red; font-weight: bold'
                                return ''

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
    st.subheader("MACD指标分析")

    col1, col2 = st.columns([1, 1])
    with col1:
        macd_code = st.text_input("股票代码", placeholder="例如: 000006", key="macd_code")

    if not watchlist.empty:
        watchlist_codes = watchlist['code'].tolist()
        selected = st.selectbox("或从自选股选择", [""] + watchlist_codes, key="macd_select")
        if selected:
            macd_code = selected

    col1, col2 = st.columns([1, 1])
    with col1:
        macd_days = st.number_input("分析天数", min_value=60, max_value=730, value=120, step=30, key="macd_days")

    if st.button("📈 分析MACD", type="primary"):
        if macd_code:
            kline_data = db.get_kline_data(macd_code, days=macd_days)

            if kline_data.empty:
                st.error("暂无数据，请先更新数据")
            else:
                from chanlun.macd import add_macd_to_dataframe
                df_with_macd = add_macd_to_dataframe(kline_data)

                st.success("MACD分析完成")

                latest = df_with_macd.iloc[-1]

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("DIF", f"{latest['dif']:.3f}")
                with col2:
                    st.metric("DEA", f"{latest['dea']:.3f}")
                with col3:
                    macd_color = "🔴" if latest['macd_hist'] > 0 else "🟢"
                    st.metric("MACD柱", f"{latest['macd_hist']:.3f}", macd_color)

                st.markdown("### 近期MACD柱状图")
                chart_data = df_with_macd.tail(60)[['date', 'macd_hist']].copy()
                chart_data = chart_data.set_index('date')
                st.bar_chart(chart_data)

                st.markdown("### DIF和DEA走势")
                line_data = df_with_macd.tail(60)[['date', 'dif', 'dea']].copy()
                line_data = line_data.set_index('date')
                st.line_chart(line_data)
        else:
            st.warning("请输入股票代码")

with tab3:
    st.subheader("历史买点查询")

    col1, col2 = st.columns([1, 1])
    with col1:
        history_code = st.text_input("股票代码", placeholder="例如: 000006", key="history_code")

    if not watchlist.empty:
        watchlist_codes = watchlist['code'].tolist()
        selected = st.selectbox("或从自选股选择", [""] + watchlist_codes, key="history_select")
        if selected:
            history_code = selected

    col1, col2 = st.columns([1, 1])
    with col1:
        history_days = st.number_input("查询天数", min_value=30, max_value=365, value=90, step=30, key="history_days")

    if st.button("📋 查询历史买点", type="primary"):
        if history_code:
            kline_data = db.get_kline_data(history_code, days=history_days)

            if kline_data.empty:
                st.error("暂无数据")
            else:
                result = analyzer.analyze(kline_data, history_code)

                if result['success']:
                    summary_df = analyzer.get_buy_signals_summary(result)

                    if not summary_df.empty:
                        st.success(f"找到 {len(summary_df)} 个买点信号")

                        def highlight_yangxian(val):
                            if isinstance(val, str) and '%' in val:
                                pct = float(val.replace('%', ''))
                                if pct > 3:
                                    return 'color: red; font-weight: bold'
                            return ''

                        styled_df = summary_df.style.map(
                            highlight_yangxian,
                            subset=['次阳涨幅%']
                        )
                        st.dataframe(styled_df, use_container_width=True)

                        csv = summary_df.to_csv(index=False)
                        st.download_button(
                            "📥 下载买点数据",
                            csv,
                            f"buy_signals_{history_code}_{datetime.now().strftime('%Y%m%d')}.csv",
                            "text/csv"
                        )
                    else:
                        st.info("在查询范围内未找到买点信号")
                else:
                    st.error(f"分析失败: {result.get('error')}")
        else:
            st.warning("请输入股票代码")

st.markdown("---")
st.markdown("""
### 📖 缠论基础概念

**分型**: K线图中，顶分型是中间K线最高、相邻K线低于中间K线；底分型是中间K线最低、相邻K线高于中间K线。

**趋势**:
- 下降趋势: 顶分型 → 底分型
- 上升趋势: 底分型 → 顶分型

**背驰**: 当前趋势段的力度比前一段减弱，表现为MACD指标的变化:
- 底背驰: 绿柱面积/高度减少，下跌力度减弱
- 顶背驰: 红柱面积/高度减少，上升力度减弱

**买卖点**:
- **1买**: 下降趋势结束时的底背驰买点
- **2买**: 1买后上升回调、不破1买的买点
""")
