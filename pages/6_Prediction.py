import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.database import StockDatabase
from utils.data_fetcher import StockDataFetcher, TechnicalIndicators


st.header("🤖 股票预测")

st.warning("⚠️ **免责声明**: 预测结果仅供参考，不构成投资建议。股市有风险，投资需谨慎！")

db = StockDatabase()
fetcher = StockDataFetcher()

tab1, tab2 = st.tabs(["📊 单股预测", "📋 批量预测"])

    with tab1:
        st.subheader("单只股票预测")

        col1, col2 = st.columns([1, 1])
        with col1:
            predict_code = st.text_input("股票代码", placeholder="例如: 600000", key="predict_code")

        watchlist = db.get_watchlist()
        if not watchlist.empty:
            watchlist_codes = watchlist['code'].tolist()
            selected = st.selectbox("或从自选股选择", [""] + watchlist_codes, key="predict_select")
            if selected:
                predict_code = selected

        if st.button("🔮 开始预测", type="primary"):
            if predict_code:
                kline_data = db.get_kline_data(predict_code, days=120)

                if kline_data.empty:
                    st.error("暂无数据，请先更新数据")
                else:
                    df = TechnicalIndicators.get_all_indicators(kline_data)
                    latest = df.iloc[-1]
                    prev = df.iloc[-2]

                    st.markdown("---")
                    st.markdown(f"### {predict_code} 技术分析")

                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("当前价格", f"{latest['close']:.2f}",
                                f"{((latest['close']-prev['close'])/prev['close']*100):+.2f}%" if prev['close'] != 0 else "")

                    with col2:
                        st.metric("MA5", f"{latest['ma5']:.2f}")
                    with col3:
                        st.metric("MA20", f"{latest['ma20']:.2f}")
                    with col4:
                        st.metric("MA60", f"{latest['ma60']:.2f}")

                    st.markdown("#### MACD指标")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("DIF", f"{latest['macd']:.3f}")
                    with col2:
                        st.metric("DEA", f"{latest['macd_signal']:.3f}")
                    with col3:
                        macd_color = "🔴" if latest['macd_hist'] > 0 else "🟢"
                        st.metric("MACD柱", f"{latest['macd_hist']:.3f}", macd_color)

                    st.markdown("#### KDJ指标")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("K值", f"{latest['kdj_k']:.2f}")
                    with col2:
                        st.metric("D值", f"{latest['kdj_d']:.2f}")
                    with col3:
                        st.metric("J值", f"{latest['kdj_j']:.2f}")

                    st.markdown("#### RSI指标")
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("RSI6", f"{latest['rsi6']:.2f}")
                    with col2:
                        st.metric("RSI12", f"{latest['rsi12']:.2f}")
                    with col3:
                        st.metric("RSI24", f"{latest['rsi24']:.2f}")

                    st.markdown("---")
                    st.markdown("### 📈 明日预测")

                    predicted_price = predict_next_price(df)
                    predicted_direction = "上涨" if predicted_price > latest['close'] else ("下跌" if predicted_price < latest['close'] else "持平")

                    change = predicted_price - latest['close']
                    change_pct = (change / latest['close'] * 100) if latest['close'] != 0 else 0

                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("预测价格", f"{predicted_price:.2f}", f"{change:+.2f} ({change_pct:+.2f}%)")
                    with col2:
                        st.metric("预测方向", predicted_direction)
                    with col3:
                        confidence = calculate_confidence(df)
                        st.metric("置信度", f"{confidence}%")

                    st.markdown("#### 预测理由")
                    reasons = generate_prediction_reasons(df, latest)
                    for reason in reasons:
                        st.markdown(f"- {reason}")

                    st.markdown("---")

                    col1, col2 = st.columns([1, 1])
                    with col1:
                        if st.button("💾 保存预测"):
                            db.save_prediction(
                                predict_code,
                                datetime.now().strftime('%Y-%m-%d'),
                                predicted_price,
                                predicted_direction,
                                "; ".join(reasons)
                            )
                            st.success("预测已保存")

                    with col2:
                        if st.button("📊 查看历史预测"):
                            predictions = db.get_predictions(predict_code, days=30)
                            if not predictions.empty:
                                st.dataframe(predictions)
                            else:
                                st.info("暂无历史预测")

            else:
                st.warning("请输入股票代码或选择自选股")

    with tab2:
        st.subheader("批量预测")

        watchlist = db.get_watchlist()

        if watchlist.empty:
            st.warning("自选股列表为空，请先添加股票")
        else:
            st.info(f"将对以下 {len(watchlist)} 只股票进行预测")

            selected_codes = st.multiselect(
                "选择股票",
                options=watchlist['code'].tolist(),
                default=watchlist['code'].tolist()[:10] if len(watchlist) > 10 else watchlist['code'].tolist()
            )

            if st.button("🔮 批量预测", type="primary"):
                with st.spinner("正在预测..."):
                    results = []

                    for code in selected_codes:
                        kline_data = db.get_kline_data(code, days=120)
                        if kline_data.empty:
                            continue

                        df = TechnicalIndicators.get_all_indicators(kline_data)
                        latest = df.iloc[-1]
                        predicted_price = predict_next_price(df)
                        predicted_direction = "上涨" if predicted_price > latest['close'] else ("下跌" if predicted_price < latest['close'] else "持平")
                        confidence = calculate_confidence(df)

                        results.append({
                            '代码': code,
                            '名称': watchlist[watchlist['code']==code]['name'].values[0] if 'name' in watchlist.columns else code,
                            '当前价格': f"{latest['close']:.2f}",
                            '预测价格': f"{predicted_price:.2f}",
                            '预测方向': predicted_direction,
                            '置信度': f"{confidence}%"
                        })

                    if results:
                        result_df = pd.DataFrame(results)
                        st.success(f"完成 {len(results)} 只股票的预测")
                        st.dataframe(result_df, use_container_width=True)

                        csv = result_df.to_csv(index=False)
                        st.download_button(
                            "📥 下载预测结果",
                            csv,
                            f"predictions_{datetime.now().strftime('%Y%m%d')}.csv",
                            "text/csv"
                        )
                    else:
                        st.warning("没有可预测的股票数据")

    st.markdown("---")
    st.markdown("""
    ### 📖 预测方法说明

    本系统使用以下技术指标进行预测：

    1. **移动平均线 (MA)**: 5日、20日、60日均线
    2. **MACD**: 指数平滑异同移动平均线
    3. **KDJ**: 随机指标
    4. **布林带 (BOLL)**: 通道指标
    5. **RSI**: 相对强弱指标

    预测逻辑基于：
    - 当前价格与均线的位置关系
    - MACD的金叉/死叉信号
    - KDJ的超买/超卖区域
    - 近期趋势的延续性
    """)
