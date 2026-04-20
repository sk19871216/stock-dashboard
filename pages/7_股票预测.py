import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.database import StockDatabase
from utils.data_fetcher import StockDataFetcher, TechnicalIndicators


def safe_val(val, default=None, decimals=2):
    """安全获取值，处理NaN"""
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return default if default is not None else 0
    if decimals is not None:
        return round(val, decimals)
    return val


def predict_next_price(df):
    """简单预测明日价格"""
    latest = df.iloc[-1]
    ma5 = latest.get('ma5', latest['close'])
    ma20 = latest.get('ma20', latest['close'])
    macd = latest.get('macd', 0)
    macd_signal = latest.get('macd_signal', 0)

    if np.isnan(ma5):
        ma5 = latest['close']
    if np.isnan(ma20):
        ma20 = latest['close']

    if latest['close'] > ma5 and ma5 > ma20 and macd > macd_signal:
        return latest['close'] * 1.02
    elif latest['close'] < ma5 and ma5 < ma20 and macd < macd_signal:
        return latest['close'] * 0.98
    else:
        return latest['close']


def calculate_confidence(df):
    """计算预测置信度"""
    if len(df) < 20:
        return 50

    latest = df.iloc[-1]
    score = 50

    ma5 = latest.get('ma5', latest['close'])
    ma20 = latest.get('ma20', latest['close'])
    if np.isnan(ma5):
        ma5 = latest['close']
    if np.isnan(ma20):
        ma20 = latest['close']

    if latest['close'] > ma5:
        score += 10
    if ma5 > ma20:
        score += 10
    if latest.get('macd', 0) > latest.get('macd_signal', 0):
        score += 10
    if latest.get('macd_hist', 0) > 0:
        score += 10
    kdj_j = latest.get('kdj_j', 50)
    if 20 < kdj_j < 80:
        score += 10

    return min(score, 95)


def generate_prediction_reasons(df, latest):
    """生成预测理由"""
    reasons = []

    ma5 = latest.get('ma5', latest['close'])
    if np.isnan(ma5):
        ma5 = latest['close']

    if latest['close'] > ma5:
        reasons.append("价格站上5日均线，短期趋势向好")
    else:
        reasons.append("价格跌破5日均线，短期趋势偏弱")

    macd = latest.get('macd', 0)
    macd_signal = latest.get('macd_signal', 0)
    if macd > macd_signal:
        reasons.append("MACD形成金叉，看多信号")
    else:
        reasons.append("MACD形成死叉，看空信号")

    macd_hist = latest.get('macd_hist', 0)
    if macd_hist > 0:
        reasons.append("MACD柱为红柱，多头力量占优")
    else:
        reasons.append("MACD柱为绿柱，空头力量占优")

    kdj_j = latest.get('kdj_j', 50)
    if kdj_j > 80:
        reasons.append("KDJ J值超买，可能面临回调")
    elif kdj_j < 20:
        reasons.append("KDJ J值超卖，可能存在反弹机会")

    return reasons


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
            kline_data = db.get_kline_data(predict_code, days=365)

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
                    st.metric("当前价格", f"{safe_val(latest['close']):.2f}",
                            f"{((latest['close']-prev['close'])/prev['close']*100):+.2f}%" if prev['close'] != 0 else "")

                with col2:
                    st.metric("MA5", f"{safe_val(latest.get('ma5'), '-')}")
                with col3:
                    st.metric("MA20", f"{safe_val(latest.get('ma20'), '-')}")
                with col4:
                    st.metric("MA60", f"{safe_val(latest.get('ma60'), '-')}")

                st.markdown("#### MACD指标")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("DIF", f"{safe_val(latest.get('macd'), 0, 3)}")
                with col2:
                    st.metric("DEA", f"{safe_val(latest.get('macd_signal'), 0, 3)}")
                with col3:
                    macd_hist = safe_val(latest.get('macd_hist'), 0)
                    macd_color = "🔴" if macd_hist > 0 else "🟢"
                    st.metric("MACD柱", f"{safe_val(macd_hist, 0, 3)}", macd_color)

                st.markdown("#### KDJ指标")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("K值", f"{safe_val(latest.get('kdj_k'), '-')}")
                with col2:
                    st.metric("D值", f"{safe_val(latest.get('kdj_d'), '-')}")
                with col3:
                    st.metric("J值", f"{safe_val(latest.get('kdj_j'), '-')}")

                st.markdown("#### RSI指标")
                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("RSI6", f"{safe_val(latest.get('rsi6'), '-')}")
                with col2:
                    st.metric("RSI12", f"{safe_val(latest.get('rsi12'), '-')}")
                with col3:
                    st.metric("RSI24", f"{safe_val(latest.get('rsi24'), '-')}")

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
                    kline_data = db.get_kline_data(code, days=365)
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
