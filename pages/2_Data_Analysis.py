import streamlit as st
import pandas as pd
import sys
from pathlib import Path
from datetime import datetime, date, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.database import StockDatabase
from utils.data_fetcher import StockDataFetcher, TechnicalIndicators


DEFAULT_INDICES = {
    "上证指数": "000001",
    "深证成指": "399001",
    "创业板指": "399006",
    "沪深300": "000300",
    "中证500": "000905",
    "中证1000": "000852",
    "上证50": "000016",
    "科创50": "000688",
}


st.header("📊 数据分析")

st.info("💡 分析前一日的市场数据，帮助判断市场整体趋势和状态")

db = StockDatabase()
fetcher = StockDataFetcher()

tab1, tab2, tab3 = st.tabs(["📈 重点指标分析", "⚙️ 指标管理", "📋 历史记录"])

    with tab1:
        st.subheader("重点指标分析")

        if 'custom_indices' not in st.session_state:
            st.session_state['custom_indices'] = {}

        custom_indices = st.session_state['custom_indices']

        all_indices = {**DEFAULT_INDICES, **custom_indices}

        if not all_indices:
            st.warning("暂无监控指标，请在「指标管理」中添加")
        else:
            col1, col2 = st.columns([1, 1])
            with col1:
                selected_index = st.selectbox(
                    "选择要分析的指标",
                    list(all_indices.keys())
                )

            with col2:
                analysis_date = st.date_input(
                    "分析日期（默认昨日）",
                    value=date.today() - timedelta(days=1)
                )

            if st.button("🔍 开始分析", type="primary"):
                index_code = all_indices[selected_index]

                with st.spinner("正在获取数据..."):
                    kline_data = fetcher.get_daily_kline(index_code, days=60)

                    if kline_data is None or kline_data.empty:
                        st.error("获取数据失败，请检查指标代码是否正确")
                    else:
                        kline_data['date'] = pd.to_datetime(kline_data['date'])
                        target_date = pd.to_datetime(analysis_date)
                        kline_data = kline_data[kline_data['date'] <= target_date]

                        if kline_data.empty:
                            st.error("该日期暂无数据，请选择更早的日期")
                        else:
                            df = TechnicalIndicators.get_all_indicators(kline_data)

                            latest = df.iloc[-1]
                            prev = df.iloc[-2]

                            st.markdown("---")
                            st.markdown(f"### {selected_index} ({index_code}) 分析报告")
                            st.markdown(f"**分析日期**: {latest['date']}")

                            col1, col2, col3, col4 = st.columns(4)

                            change = latest['close'] - prev['close']
                            change_pct = (change / prev['close'] * 100) if prev['close'] != 0 else 0

                            with col1:
                                st.metric(
                                    "收盘价",
                                    f"{latest['close']:.2f}",
                                    f"{change:+.2f} ({change_pct:+.2f}%)"
                                )

                            with col2:
                                volume_str = f"{latest['volume']/10000:.0f}万" if latest['volume'] > 10000 else f"{latest['volume']:.0f}"
                                st.metric("成交量", volume_str)

                            with col3:
                                high_low = f"H:{latest['high']:.2f} L:{latest['low']:.2f}"
                                st.metric("日内波动", high_low)

                            with col4:
                                amplitude = ((latest['high'] - latest['low']) / prev['close'] * 100) if prev['close'] != 0 else 0
                                st.metric("振幅", f"{amplitude:.2f}%")

                            st.markdown("---")
                            st.markdown("### 技术指标")

                            col1, col2, col3 = st.columns(3)

                            with col1:
                                st.markdown("**均线系统**")
                                st.write(f"- MA5: {latest['ma5']:.2f}")
                                st.write(f"- MA10: {latest['ma10']:.2f}")
                                st.write(f"- MA20: {latest['ma20']:.2f}")
                                st.write(f"- MA60: {latest['ma60']:.2f}")

                                ma_status = []
                                if latest['close'] > latest['ma5']:
                                    ma_status.append("✅ 价格 > MA5")
                                else:
                                    ma_status.append("❌ 价格 < MA5")
                                if latest['ma5'] > latest['ma10']:
                                    ma_status.append("✅ MA5 > MA10")
                                else:
                                    ma_status.append("❌ MA5 < MA10")
                                if latest['ma10'] > latest['ma20']:
                                    ma_status.append("✅ MA10 > MA20")
                                else:
                                    ma_status.append("❌ MA10 < MA20")

                                for status in ma_status:
                                    st.markdown(status)

                            with col2:
                                st.markdown("**MACD指标**")
                                st.write(f"- DIF: {latest['macd']:.3f}")
                                st.write(f"- DEA: {latest['macd_signal']:.3f}")
                                st.write(f"- MACD柱: {latest['macd_hist']:.3f}")

                                if latest['macd'] > latest['macd_signal']:
                                    st.markdown("✅ DIF > DEA (金叉)")
                                else:
                                    st.markdown("❌ DIF < DEA (死叉)")

                                if latest['macd_hist'] > 0:
                                    st.markdown("🔴 MACD红柱")
                                else:
                                    st.markdown("🟢 MACD绿柱")

                            with col3:
                                st.markdown("**KDJ指标**")
                                st.write(f"- K: {latest['kdj_k']:.2f}")
                                st.write(f"- D: {latest['kdj_d']:.2f}")
                                st.write(f"- J: {latest['kdj_j']:.2f}")

                                if latest['kdj_k'] > latest['kdj_d']:
                                    st.markdown("✅ K > D (金叉)")
                                else:
                                    st.markdown("❌ K < D (死叉)")

                                if latest['kdj_j'] > 80:
                                    st.markdown("⚠️ J值超买")
                                elif latest['kdj_j'] < 20:
                                    st.markdown("⚠️ J值超卖")

                            st.markdown("---")
                            st.markdown("### 趋势判断")

                            trend_signals = []

                            if change_pct > 0:
                                trend_signals.append(("📈 今日上涨", "positive"))
                            else:
                                trend_signals.append(("📉 今日下跌", "negative"))

                            if latest['close'] > latest['ma20']:
                                trend_signals.append(("✅ 价格站上20日均线", "positive"))
                            else:
                                trend_signals.append(("❌ 价格跌破20日均线", "negative"))

                            if latest['macd_hist'] > 0:
                                trend_signals.append(("🔴 MACD多头", "positive"))
                            else:
                                trend_signals.append(("🟢 MACD空头", "negative"))

                            if latest['kdj_k'] > latest['kdj_d']:
                                trend_signals.append(("✅ KDJ多头信号", "positive"))
                            else:
                                trend_signals.append(("❌ KDJ空头信号", "negative"))

                            if latest['ma5'] > latest['ma20']:
                                trend_signals.append(("✅ 短期均线多头排列", "positive"))
                            else:
                                trend_signals.append(("❌ 短期均线空头排列", "negative"))

                            col1, col2 = st.columns(2)
                            positive_count = sum(1 for _, t in trend_signals if t == "positive")
                            total_count = len(trend_signals)

                            with col1:
                                st.markdown("**趋势信号汇总**")
                                for signal, signal_type in trend_signals:
                                    color = "green" if signal_type == "positive" else "red"
                                    st.markdown(f"<span style='color:{'green' if signal_type == 'positive' else 'red'}'>{signal}</span>", unsafe_allow_html=True)

                            with col2:
                                st.markdown("**综合判断**")

                                positive_ratio = positive_count / total_count if total_count > 0 else 0

                                if positive_ratio >= 0.7:
                                    st.success(f"🟢 强势 ({positive_count}/{total_count})")
                                    st.markdown("整体趋势向好，可适当乐观")
                                elif positive_ratio >= 0.5:
                                    st.info(f"🟡 中性 ({positive_count}/{total_count})")
                                    st.markdown("多空平衡，保持观望")
                                elif positive_ratio >= 0.3:
                                    st.warning(f"🟠 偏弱 ({positive_count}/{total_count})")
                                    st.markdown("整体趋势偏弱，注意风险")
                                else:
                                    st.error(f"🔴 弱势 ({positive_count}/{total_count})")
                                    st.markdown("趋势较弱，谨慎操作")

                            st.markdown("---")

                            st.markdown("### 近期走势图表")

                            chart_data = df.tail(30)[['date', 'close', 'ma5', 'ma10', 'ma20']].copy()
                            chart_data = chart_data.set_index('date')
                            st.line_chart(chart_data)

                            with st.expander("📊 查看更多历史数据"):
                                st.dataframe(df.tail(10)[['date', 'open', 'high', 'low', 'close', 'volume', 'ma5', 'ma10', 'ma20', 'macd', 'macd_signal', 'macd_hist']])

    with tab2:
        st.subheader("指标管理")

        st.markdown("### 添加自定义指标")

        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            new_index_name = st.text_input("指标名称", placeholder="例如: 银行指数")
        with col2:
            new_index_code = st.text_input("指标代码", placeholder="例如: 399940")
        with col3:
            st.markdown("")  # 占位

        if st.button("➕ 添加指标", type="primary"):
            if new_index_name and new_index_code:
                st.session_state['custom_indices'][new_index_name] = new_index_code
                st.success(f"✅ 已添加 {new_index_name} ({new_index_code})")
                st.rerun()
            else:
                st.warning("请输入指标名称和代码")

        st.markdown("---")
        st.markdown("### 当前监控指标")

        st.markdown("#### 默认指标")
        for name, code in DEFAULT_INDICES.items():
            st.markdown(f"- {name} ({code})")

        if custom_indices:
            st.markdown("#### 自定义指标")

            for name in list(custom_indices.keys()):
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(f"- {name} ({custom_indices[name]})")
                with col2:
                    if st.button(f"🗑️ 删除", key=f"del_{name}"):
                        del st.session_state['custom_indices'][name]
                        st.rerun()

        st.markdown("---")
        st.markdown("### 常用指标代码参考")

        common_indices = {
            "大盘指数": {
                "上证指数": "000001",
                "深证成指": "399001",
                "创业板指": "399006",
                "沪深300": "000300",
            },
            "规模指数": {
                "上证50": "000016",
                "中证100": "000903",
                "中证500": "000905",
                "中证1000": "000852",
            },
            "行业指数": {
                "银行指数": "399940",
                "证券指数": "399975",
                "房地产指数": "000005",
                "医药指数": "399933",
            },
            "风格指数": {
                "沪深300价值": "000914",
                "沪深300成长": "000918",
                "中证500价值": "000905",
                "中证500成长": "000905",
            }
        }

        for category, indices in common_indices.items():
            with st.expander(f"{category}"):
                for name, code in indices.items():
                    if name not in DEFAULT_INDICES:
                        st.markdown(f"- {name}: `{code}`")

    with tab3:
        st.subheader("历史分析记录")

        st.info("💡 记录最近的分析结果，方便回顾")

        if 'analysis_history' not in st.session_state:
            st.session_state['analysis_history'] = []

        history = st.session_state['analysis_history']

        if not history:
            st.info("暂无历史记录")
        else:
            st.markdown(f"### 历史记录 (共 {len(history)} 条)")

            for i, record in enumerate(reversed(history[-20:])):
                with st.container():
                    col1, col2 = st.columns([1, 3])
                    with col1:
                        st.markdown(f"**{record['name']}**")
                        st.caption(record['date'])

                    with col2:
                        positive_count = record['positive_count']
                        total_count = record['total_count']
                        ratio = positive_count / total_count if total_count > 0 else 0

                        if ratio >= 0.7:
                            st.markdown(f"🟢 强势 ({positive_count}/{total_count})")
                        elif ratio >= 0.5:
                            st.markdown(f"🟡 中性 ({positive_count}/{total_count})")
                        elif ratio >= 0.3:
                            st.markdown(f"🟠 偏弱 ({positive_count}/{total_count})")
                        else:
                            st.markdown(f"🔴 弱势 ({positive_count}/{total_count})")

                        st.markdown(f"收盘价: {record['close']:.2f} | 涨跌: {record['change_pct']:+.2f}%")

                    st.markdown("---")

            if st.button("🗑️ 清空历史"):
                st.session_state['analysis_history'] = []
                st.success("历史记录已清空")
                st.rerun()

    st.markdown("---")
    st.markdown("""
    ### 📖 分析说明

    **重点指标分析** 旨在帮助您快速了解特定市场指数的状态，辅助投资决策。

    **分析内容包括**:
    - 基础行情数据（收盘价、成交量、振幅等）
    - 均线系统状态（MA5/10/20/60）
    - MACD指标（DIF/DEA/MACD柱）
    - KDJ指标（K/D/J值）
    - 综合趋势判断

    **使用建议**:
    1. 建议每天盘后分析前一交易日的数据
    2. 关注趋势信号的积累变化
    3. 结合作者标的技术分析和基本面综合判断

    ### ⚠️ 免责声明

    所有分析仅供参考，不构成投资建议。股市有风险，投资需谨慎！
    """)
