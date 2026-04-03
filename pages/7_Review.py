import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.database import StockDatabase
from utils.data_fetcher import StockDataFetcher


st.header("📝 复盘分析")

st.info("📖 复盘可以帮助您分析预测与实际的差距，总结经验教训，提高预测准确率")

db = StockDatabase()
fetcher = StockDataFetcher()

tab1, tab2, tab3, tab4 = st.tabs([
    "📊 预测对比",
    "📈 准确率统计",
    "📝 记录复盘",
    "📋 历史复盘"
])

with tab1:
    st.subheader("预测与实际对比")

    predictions = db.get_predictions(days=30)

    if predictions.empty:
        st.info("暂无预测记录，请先进行股票预测")
    else:
        watchlist = db.get_watchlist()

        st.markdown("### 待验证预测")
        st.markdown("以下预测需要更新实际结果来验证准确性")

        need_verification = []

        for idx, pred in predictions.iterrows():
            if pred['actual_price'] is None:
                code = pred['code']
                kline_data = db.get_kline_data(code, days=10)

                if not kline_data.empty:
                    latest = kline_data.iloc[-1]
                    actual_date = latest['date']

                    if actual_date > pred['predict_date']:
                        need_verification.append({
                            '代码': code,
                            '预测日期': pred['predict_date'],
                            '预测价格': pred['predicted_price'],
                            '预测方向': pred['predicted_direction'],
                            '实际价格': latest['close'],
                            '实际日期': actual_date
                        })

            if need_verification:
                ver_df = pd.DataFrame(need_verification)
                st.dataframe(ver_df, use_container_width=True)

                col1, col2 = st.columns([1, 1])
                with col1:
                    update_code = st.selectbox("选择要更新的股票", [v['代码'] for v in need_verification])

                with col2:
                    if st.button("🔄 更新实际结果", type="primary"):
                        pred_row = [v for v in need_verification if v['代码'] == update_code][0]
                        db.update_prediction_result(update_code, pred_row['预测日期'], pred_row['实际价格'])
                        st.success(f"✅ {update_code} 实际结果已更新")
                        st.rerun()
            else:
                st.success("所有预测都已验证完成！")

            st.markdown("---")
            st.markdown("### 历史预测记录")
            st.dataframe(predictions, use_container_width=True)

    with tab2:
        st.subheader("准确率统计")

        predictions = db.get_predictions(days=30)
        verified_predictions = predictions[predictions['actual_price'].notna()]

        if verified_predictions.empty:
            st.info("暂无已验证的预测数据")
        else:
            total = len(verified_predictions)

            verified_predictions['direction_correct'] = verified_predictions.apply(
                lambda x: 1 if (x['predicted_direction'] == '上涨' and x['actual_price'] > x['predicted_price']) or
                              (x['predicted_direction'] == '下跌' and x['actual_price'] < x['predicted_price']) or
                              (x['predicted_direction'] == '持平' and x['actual_price'] == x['predicted_price'])
                        else 0, axis=1
            )

            direction_accuracy = verified_predictions['direction_correct'].sum() / total * 100

            avg_accuracy = verified_predictions['accuracy'].mean() * 100 if 'accuracy' in verified_predictions.columns else 0

            correct_count = verified_predictions['direction_correct'].sum()
            wrong_count = total - correct_count

            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("总预测数", total)
            with col2:
                st.metric("方向准确率", f"{direction_accuracy:.1f}%")
            with col3:
                st.metric("价格偏离度", f"{100-avg_accuracy:.1f}%" if avg_accuracy > 0 else "N/A")
            with col4:
                st.metric("正确/错误", f"{correct_count}/{wrong_count}")

            st.markdown("### 准确率趋势")
            if len(verified_predictions) > 5:
                recent_predictions = verified_predictions.tail(20)
                chart_data = pd.DataFrame({
                    '日期': recent_predictions['predict_date'],
                    '准确率': recent_predictions['accuracy'] * 100
                })
                st.line_chart(chart_data.set_index('日期'))

            st.markdown("### 按股票统计")
            stock_stats = verified_predictions.groupby('代码').agg({
                'accuracy': ['count', 'mean'],
                'direction_correct': 'sum'
            }).round(2)
            stock_stats.columns = ['预测次数', '平均偏离度%', '方向正确']
            stock_stats['准确率%'] = 100 - stock_stats['平均偏离度%']
            stock_stats = stock_stats.sort_values('预测次数', ascending=False)
            st.dataframe(stock_stats)

    with tab3:
        st.subheader("记录复盘")

        col1, col2 = st.columns([1, 1])
        with col1:
            review_code = st.text_input("股票代码", placeholder="例如: 600000")

        watchlist = db.get_watchlist()
        if not watchlist.empty:
            watchlist_codes = watchlist['code'].tolist()
            selected = st.selectbox("或从自选股选择", [""] + watchlist_codes, key="review_select")
            if selected:
                review_code = selected

        predictions = db.get_predictions(review_code if review_code else None, days=30)
        recent_predictions = predictions[predictions['actual_price'].notna()]

        if review_code and not recent_predictions.empty:
            st.markdown(f"### {review_code} 近期预测")
            st.dataframe(recent_predictions.head(5))

            st.markdown("---")
            st.markdown("### 添加复盘记录")

            review_date = st.date_input("复盘日期", value=datetime.now().date())

            selected_pred_idx = st.selectbox(
                "选择预测记录",
                range(len(recent_predictions)),
                format_func=lambda x: f"{recent_predictions.iloc[x]['predict_date']} - 预测:{recent_predictions.iloc[x]['predicted_price']} - 实际:{recent_predictions.iloc[x]['actual_price']}"
            ) if not recent_predictions.empty else None

            if selected_pred_idx is not None:
                selected_pred = recent_predictions.iloc[selected_pred_idx]

                st.markdown(f"""
                **预测日期**: {selected_pred['predict_date']}
                **预测价格**: {selected_pred['predicted_price']}
                **实际价格**: {selected_pred['actual_price']}
                **预测方向**: {selected_pred['predicted_direction']}
                """)

            analysis_type = st.selectbox(
                "分析类型",
                ["符合预期", "超出预期-好", "超出预期-差", "不符合预期"]
            )

            analysis_content = st.text_area(
                "复盘分析内容",
                placeholder="分析为什么预测准确/不准确...",
                height=150
            )

            if st.button("💾 保存复盘", type="primary"):
                if analysis_content:
                    prediction_str = f"预测:{selected_pred['predicted_price']} 方向:{selected_pred['predicted_direction']}"
                    actual_str = f"实际:{selected_pred['actual_price']}"

                    db.save_review(
                        review_code,
                        review_date.strftime('%Y-%m-%d'),
                        prediction_str,
                        actual_str,
                        f"[{analysis_type}] {analysis_content}"
                    )
                    st.success("✅ 复盘记录已保存")
                    st.rerun()
                else:
                    st.warning("请输入分析内容")

    with tab4:
        st.subheader("历史复盘记录")

        reviews = db.get_reviews(days=30)

        if reviews.empty:
            st.info("暂无复盘记录")
        else:
            st.markdown(f"### 复盘记录 (共 {len(reviews)} 条)")

            for idx, review in reviews.iterrows():
                with st.container():
                    col1, col2 = st.columns([1, 4])
                    with col1:
                        st.markdown(f"**{review['code']}**")
                        st.caption(review['review_date'])

                    with col2:
                        st.markdown(f"📌 {review['prediction']} vs {review['actual_result']}")
                        st.markdown(f"📝 {review['analysis']}")

                    st.markdown("---")

            if st.button("📥 导出复盘记录"):
                csv = reviews.to_csv(index=False)
                st.download_button(
                    "下载CSV",
                    csv,
                    f"reviews_{datetime.now().strftime('%Y%m%d')}.csv",
                    "text/csv"
                )

    st.markdown("---")
    st.markdown("""
    ### 📖 复盘指南

    1. **每日复盘**: 每天收盘后，回顾当天的预测是否准确
    2. **分析原因**: 思考预测正确/错误的原因
    3. **总结经验**: 从错误中学习，改进预测方法
    4. **持续优化**: 根据复盘结果调整指标权重

    ### 💡 常见问题分析

    - **预测过于乐观**: 可能是对利好消息反应过度
    - **预测过于悲观**: 可能是忽略了市场整体趋势
    - **技术指标失效**: 可能遇到了特殊市场环境
    - **数据延迟**: 及时更新数据，提高预测准确性
    """)
