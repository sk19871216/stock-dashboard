import streamlit as st
import pandas as pd
from datetime import datetime, date
import sys
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.database import StockDatabase
from utils.data_fetcher import StockDataFetcher


st.header("📊 数据更新")

db = StockDatabase()
fetcher = StockDataFetcher()

tab1 = st.tabs(["📊 全市场批量更新"])[0]

with tab1:
    st.subheader("全市场股票批量更新")

    if 'retry_result' in st.session_state:
        result = st.session_state.pop('retry_result')
        if result['success'] > 0 or result['fail'] > 0:
            st.success(f"✅ 重试完成！成功: {result['success']}, 失败: {result['fail']}")
        if result.get('remaining', 0) > 0:
            st.warning(f"⚠️ 还有 {result['remaining']} 只股票更新失败，可以再次点击「重试失败股票」继续处理")
        elif result['fail'] == 0:
            st.success("🎉 所有失败股票已处理完成！")

    col1, col2 = st.columns([1, 1])
    with col1:
        full_start_date = st.date_input("开始日期", value=date(2026, 1, 1), key="full_start")
    with col2:
        full_end_date = st.date_input("结束日期", value=date.today(), key="full_end")

    st.info(f"日期范围: {full_start_date} 至 {full_end_date}")

    stock_list_count = db.get_stock_list_count()
    failed_count = db.get_failed_stocks_count()

    if stock_list_count == 0:
        if st.button("📥 获取全市场股票列表", type="primary"):
            with st.spinner("正在获取全市场股票列表..."):
                all_stocks = fetcher.get_all_a_stocks()
                if not all_stocks.empty:
                    count = db.save_stock_list(all_stocks)
                    st.success(f"成功获取并保存 {count} 只股票！")
                    st.rerun()
                else:
                    st.error("获取股票列表失败")
    else:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("股票数量", stock_list_count)
        with col2:
            max_workers = st.selectbox("并发线程数", [1, 3, 5, 10], index=1)
        with col3:
            batch_size = st.selectbox("批次大小", [50, 100, 200], index=1)

        st.markdown("---")

        if failed_count > 0:
            st.warning(f"⚠️ 有 {failed_count} 只股票更新失败")

            failed_df = db.get_failed_stocks()
            with st.expander("📋 查看失败股票列表"):
                st.dataframe(failed_df[['code', 'name', 'error_msg', 'retry_count']], use_container_width=True)

            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                if st.button("🔄 重试失败股票", type="primary"):
                    retry_codes = failed_df['code'].tolist()
                    total_stocks = len(retry_codes)

                    st.info(f"开始重试 {total_stocks} 只失败股票...")

                    progress_bar = st.progress(0)
                    stats_col1, stats_col2 = st.columns(2)
                    success_cnt = 0
                    fail_cnt = 0
                    skip_cnt = 0

                    for idx, row in failed_df.iterrows():
                        code = row['code']
                        try:
                            df = fetcher.get_recent_kline(code, days=10)
                            if df is not None and not df.empty:
                                db.save_kline_data(code, df)
                                db.remove_failed_stock(code)
                                success_cnt += 1
                            else:
                                db.save_failed_stock(code, row.get('name'), "无数据")
                                fail_cnt += 1
                        except Exception as e:
                            db.save_failed_stock(code, row.get('name'), str(e)[:100])
                            fail_cnt += 1

                        time.sleep(0.05)

                        progress = (idx + 1) / total_stocks
                        progress_bar.progress(progress)

                    remaining_failed = db.get_failed_stocks_count()
                    st.session_state['retry_result'] = {
                        'success': success_cnt,
                        'fail': fail_cnt,
                        'remaining': remaining_failed
                    }
                    st.rerun()

            with col_btn2:
                if st.button("🗑️ 清空失败记录"):
                    db.clear_failed_stocks()
                    st.success("已清空失败记录")
                    st.rerun()

        st.markdown("---")
        st.markdown("### 🔄 批量更新选项")

        update_mode = st.radio(
            "选择更新模式",
            ["📅 快速更新（最近几天）", "📅 区间更新（指定日期范围）", "📜 全部更新（所有历史数据）"],
            horizontal=True
        )

        if update_mode == "📅 快速更新（最近几天）":
            recent_days = st.selectbox("获取最近天数", [3, 5, 10, 20], index=1)

            if st.button(f"🚀 快速更新（最近{recent_days}天）", type="primary"):
                db.clear_failed_stocks()
                stock_list = db.get_stock_list()
                total_stocks = len(stock_list)

                st.info(f"开始快速更新 {total_stocks} 只股票（每只获取最近{recent_days}天）...")

                progress_bar = st.progress(0)
                stats_col1, stats_col2 = st.columns(2)

                success_cnt = 0
                fail_cnt = 0
                start_time = time.time()

                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = {}
                    for _, row in stock_list.iterrows():
                        code = row['code']
                        future = executor.submit(fetcher.get_recent_kline, code, recent_days)
                        futures[future] = (code, row.get('name', ''))

                    completed = 0
                    for future in as_completed(futures):
                        code, name = futures[future]
                        try:
                            df = future.result()
                            if df is not None and not df.empty:
                                db.save_kline_data(code, df)
                                db.remove_failed_stock(code)
                                success_cnt += 1
                            else:
                                db.save_failed_stock(code, name, "无数据")
                                fail_cnt += 1
                        except Exception as e:
                            db.save_failed_stock(code, name, str(e)[:100])
                            fail_cnt += 1

                        time.sleep(0.05)

                        completed += 1
                        progress = completed / total_stocks
                        progress_bar.progress(progress)

                        with stats_col1:
                            st.metric("成功", success_cnt)
                        with stats_col2:
                            st.metric("失败", fail_cnt)

                elapsed = time.time() - start_time
                st.success(f"✅ 快速更新完成！成功: {success_cnt}, 失败: {fail_cnt}，耗时: {elapsed:.1f}秒")

                remaining_failed = db.get_failed_stocks_count()
                if remaining_failed > 0:
                    st.warning(f"⚠️ 还有 {remaining_failed} 只股票更新失败，可以再次点击重试")
                else:
                    st.success("🎉 所有股票更新成功！")

                st.rerun()
        elif update_mode == "📅 区间更新（指定日期范围）":
            if st.button("🚀 区间更新（指定日期范围）", type="primary"):
                db.clear_failed_stocks()
                stock_list = db.get_stock_list()
                total_stocks = len(stock_list)

                st.info(f"开始区间更新 {total_stocks} 只股票（日期范围: {full_start_date} 至 {full_end_date}），请耐心等待...")

                progress_bar = st.progress(0)
                stats_col1, stats_col2 = st.columns(2)

                success_cnt = 0
                fail_cnt = 0
                start_time = time.time()

                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = {}
                    for _, row in stock_list.iterrows():
                        code = row['code']
                        future = executor.submit(fetcher.get_daily_kline_by_date, code, full_start_date, full_end_date)
                        futures[future] = (code, row.get('name', ''))

                    completed = 0
                    for future in as_completed(futures):
                        code, name = futures[future]
                        try:
                            df = future.result()
                            if df is not None and not df.empty:
                                db.save_kline_data(code, df)
                                db.remove_failed_stock(code)
                                success_cnt += 1
                            else:
                                db.save_failed_stock(code, name, "无数据")
                                fail_cnt += 1
                        except Exception as e:
                            db.save_failed_stock(code, name, str(e)[:100])
                            fail_cnt += 1

                        time.sleep(0.05)

                        completed += 1
                        progress = completed / total_stocks
                        progress_bar.progress(progress)

                        with stats_col1:
                            st.metric("成功", success_cnt)
                        with stats_col2:
                            st.metric("失败", fail_cnt)

                elapsed = time.time() - start_time
                st.success(f"✅ 区间更新完成！成功: {success_cnt}, 失败: {fail_cnt}，耗时: {elapsed:.1f}秒")

                remaining_failed = db.get_failed_stocks_count()
                if remaining_failed > 0:
                    st.warning(f"⚠️ 还有 {remaining_failed} 只股票更新失败，可以再次点击重试")
                else:
                    st.success("🎉 所有股票更新成功！")

                st.rerun()
        else:
            if st.button("🚀 全部更新（所有历史数据）", type="primary"):
                db.clear_failed_stocks()
                stock_list = db.get_stock_list()
                total_stocks = len(stock_list)

                st.info(f"开始全部更新 {total_stocks} 只股票（获取所有历史数据），请耐心等待...")

                progress_bar = st.progress(0)
                stats_col1, stats_col2 = st.columns(2)

                success_cnt = 0
                fail_cnt = 0
                start_time = time.time()

                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = {}
                    for _, row in stock_list.iterrows():
                        code = row['code']
                        future = executor.submit(fetcher.get_daily_kline, code)
                        futures[future] = (code, row.get('name', ''))

                    completed = 0
                    for future in as_completed(futures):
                        code, name = futures[future]
                        try:
                            df = future.result()
                            if df is not None and not df.empty:
                                db.save_kline_data(code, df)
                                db.remove_failed_stock(code)
                                success_cnt += 1
                            else:
                                db.save_failed_stock(code, name, "无数据")
                                fail_cnt += 1
                        except Exception as e:
                            db.save_failed_stock(code, name, str(e)[:100])
                            fail_cnt += 1

                        time.sleep(0.05)

                        completed += 1
                        progress = completed / total_stocks
                        progress_bar.progress(progress)

                        with stats_col1:
                            st.metric("成功", success_cnt)
                        with stats_col2:
                            st.metric("失败", fail_cnt)

                elapsed = time.time() - start_time
                st.success(f"✅ 全部更新完成！成功: {success_cnt}, 失败: {fail_cnt}，耗时: {elapsed:.1f}秒")

                remaining_failed = db.get_failed_stocks_count()
                if remaining_failed > 0:
                    st.warning(f"⚠️ 还有 {remaining_failed} 只股票更新失败，可以再次点击重试")
                else:
                    st.success("🎉 所有股票更新成功！")

                st.rerun()

    st.markdown("---")
    st.markdown("### 📋 数据库状态")
    daily_count = len(db.get_all_stock_codes())
    st.info(f"已下载K线数据的股票: {daily_count} 只")

st.markdown("---")
st.markdown("### 📋 数据更新日志")
st.info("最近更新时间: " + datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
