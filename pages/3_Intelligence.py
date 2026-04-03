import streamlit as st
import pandas as pd
from datetime import datetime, date
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.database import StockDatabase
from utils.data_fetcher import StockDataFetcher, TechnicalIndicators


st.header("🔍 情报追踪")

db = StockDatabase()
fetcher = StockDataFetcher()

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "⭐ 自选股",
    "📈 触发指标",
    "📉 大盘分析",
    "💹 涨跌停",
    "📰 舆情"
])

with tab1:
    st.subheader("自选股管理")

    col1, col2 = st.columns([1, 1])
    with col1:
        new_code = st.text_input("股票代码", placeholder="例如: 600000")
        new_name = st.text_input("股票名称（可选）", placeholder="例如: 浦发银行")
        market = st.selectbox("市场", ["A股", "港股", "美股"])

    if st.button("➕ 添加自选股", type="primary"):
        if new_code:
            if db.add_to_watchlist(new_code, new_name, market):
                st.success(f"✅ {new_code} 已添加到自选股")
                st.rerun()
            else:
                st.error("添加失败，可能已存在")
        else:
            st.warning("请输入股票代码")

    st.markdown("---")

    watchlist = db.get_watchlist()

    if watchlist.empty:
        st.info("自选股列表为空，请添加股票")
    else:
        st.markdown(f"### 自选股列表 (共 {len(watchlist)} 只)")

        for idx, row in watchlist.iterrows():
            col1, col2, col3 = st.columns([2, 2, 1])
            with col1:
                code = row['code']
                name = row['name'] if row['name'] else code
                st.markdown(f"**{name}** ({code})")

            with col2:
                kline_data = db.get_kline_data(code, days=5)
                if not kline_data.empty:
                    latest = kline_data.iloc[-1]
                    change = latest['close'] - kline_data.iloc[-2]['close'] if len(kline_data) > 1 else 0
                    change_pct = (change / kline_data.iloc[-2]['close'] * 100) if len(kline_data) > 1 and kline_data.iloc[-2]['close'] != 0 else 0

                    color = "🔴" if change > 0 else "🟢" if change < 0 else "⚪"
                    st.markdown(f"{color} 现价: {latest['close']:.2f}  涨跌: {change:+.2f} ({change_pct:+.2f}%)")
                else:
                    st.markdown("暂无数据")

            with col3:
                if st.button("🗑️ 删除", key=f"del_{code}"):
                    db.remove_from_watchlist(code)
                    st.rerun()

        st.markdown("---")

        if st.button("📊 查看所有自选股K线"):
            st.markdown("### 📈 自选股K线图")
            selected_codes = st.multiselect(
                "选择股票查看K线",
                options=watchlist['code'].tolist(),
                default=watchlist['code'].tolist()[:3] if len(watchlist) > 3 else watchlist['code'].tolist()
            )

            for code in selected_codes:
                kline_data = db.get_kline_data(code, days=120)
                if not kline_data.empty:
                    st.markdown(f"#### {code}")
                    chart_data = kline_data.tail(60)
                    st.line_chart(chart_data.set_index('date')['close'])

    with tab2:
        st.subheader("触发指标股（从缠论选股导入）")

        if 'triggered_stocks' not in st.session_state:
            st.session_state['triggered_stocks'] = []

        triggered_stocks = st.session_state['triggered_stocks']

        if st.button("🗑️ 清空列表"):
            st.session_state['triggered_stocks'] = []
            st.rerun()

        if not triggered_stocks:
            st.info("暂无触发指标股，请从「缠论选股」页面导入")
            st.markdown("""
            ### 导入方法
            1. 进入「🎯 缠论选股」页面
            2. 进行全市场扫描
            3. 在「扫描结果」中点击「📥 导入到触发指标」
            """)
        else:
            st.markdown(f"### 触发指标股列表 (共 {len(triggered_stocks)} 只)")

            triggered_df = pd.DataFrame(triggered_stocks)

            st.dataframe(triggered_df, use_container_width=True)

            st.markdown("---")
            st.markdown("### 操作")

            col1, col2 = st.columns([1, 1])

            codes_to_remove = st.multiselect(
                "选择要删除的股票",
                options=[s['股票代码'] for s in triggered_stocks],
                default=[]
            )

            if st.button("🗑️ 删除选中", type="primary") and codes_to_remove:
                st.session_state['triggered_stocks'] = [
                    s for s in triggered_stocks if s['股票代码'] not in codes_to_remove
                ]
                st.success(f"已删除 {len(codes_to_remove)} 只股票")
                st.rerun()

            if st.button("➕ 添加到自选股", type="secondary"):
                added_count = 0
                for stock in triggered_stocks:
                    if db.add_to_watchlist(stock['股票代码'], stock.get('名称', ''), 'A股'):
                        added_count += 1
                st.success(f"已将 {added_count} 只股票添加到自选股")

    with tab3:
        st.subheader("大盘分析")

        index_codes = {
            "上证指数": "000001",
            "深证成指": "399001",
            "创业板指": "399006",
            "沪深300": "000300"
        }

        selected_index = st.selectbox("选择指数", list(index_codes.keys()))
        index_code = index_codes[selected_index]

        with st.spinner("正在获取数据..."):
            kline_data = db.get_kline_data(index_code, days=60)

            if not kline_data.empty:
                df = TechnicalIndicators.get_all_indicators(kline_data)
                latest = df.iloc[-1]
                prev = df.iloc[-2]

                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    change = latest['close'] - prev['close']
                    change_pct = (change / prev['close'] * 100) if prev['close'] != 0 else 0
                    st.metric("收盘价", f"{latest['close']:.2f}", f"{change:+.2f} ({change_pct:+.2f}%)")

                with col2:
                    st.metric("成交量", f"{latest['volume']/10000:.2f}万")

                with col3:
                    st.metric("MACD", f"{latest['macd']:.2f}", f"DIF: {latest['macd']-latest['macd_signal']:.2f}")

                with col4:
                    st.metric("KDJ", f"K:{latest['kdj_k']:.1f} D:{latest['kdj_d']:.1f} J:{latest['kdj_j']:.1f}")

                st.markdown("### 近期走势")
                chart_data = df.tail(30)
                if 'ma5' in chart_data.columns:
                    st.line_chart(chart_data.set_index('date')[['close', 'ma5', 'ma10', 'ma20']].rename(
                        columns={'ma5': 'MA5', 'ma10': 'MA10', 'ma20': 'MA20'}
                    ))
                else:
                    st.line_chart(chart_data.set_index('date')[['close']])

                trend = "震荡" if abs(change_pct) < 0.5 else ("上涨" if change_pct > 0 else "下跌")
                st.info(f"当前趋势: **{trend}**，{'建议关注' if trend == '上涨' else '谨慎操作'}")
            else:
                st.warning("暂无数据，请先更新数据")

    with tab4:
        st.subheader("涨跌停分析")

        limit_df = fetcher.get_limit_up_data(date.today().strftime('%Y%m%d'))

        if limit_df is not None and not limit_df.empty:
            st.markdown(f"### 📈 涨停股票 ({len(limit_df)} 只)")

            display_cols = [col for col in limit_df.columns if col in
                          ['代码', '名称', '涨停统计', '流通市值', '连板数', '涨停原因', '板块']]
            if display_cols:
                st.dataframe(limit_df[display_cols], use_container_width=True)

            if '涨停原因' in limit_df.columns:
                st.markdown("### 涨停原因分析")
                reason_counts = limit_df['涨停原因'].value_counts().head(10)
                st.bar_chart(reason_counts)
        else:
            st.info("今日暂无涨停数据")

    with tab5:
        st.subheader("舆情监控")

        st.markdown("""
        ### 📰 新闻舆情

        > ⚠️ 注意: 舆情数据依赖外部API，可能不稳定。

        建议关注的信息源：
        - 东方财富财经新闻
        - 新浪财经
        - 证券时报
        - 第一财经

        ---
        """)

        news_sources = {
            "东方财富": "https://finance.eastmoney.com",
            "新浪财经": "https://finance.sina.com.cn",
            "证券时报": "https://www.stcn.com",
            "第一财经": "https://www.yicai.com"
        }

        st.markdown("### 常用财经网站")
        for name, url in news_sources.items():
            st.markdown(f"- [{name}]({url})")

        st.markdown("---")
        st.markdown("### 重大事件记录")

        event_log = st.text_area(
            "记录重大事件",
            placeholder="例如: 特朗普讲话、央行降准等重大事件...",
            height=100
        )

        if st.button("💾 保存事件"):
            if event_log:
                st.success("事件已记录")
                st.session_state['last_event'] = event_log
            else:
                st.warning("请输入事件内容")

        if 'last_event' in st.session_state:
            st.info(f"上次记录: {st.session_state['last_event']}")
