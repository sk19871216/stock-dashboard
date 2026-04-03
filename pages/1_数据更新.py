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

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "📈 日K数据（自选股）",
    "📊 全市场批量更新",
    "💹 涨跌停",
    "📊 板块资金",
    "🐉 龙虎榜"
])

with tab1:
    st.subheader("更新自选股日K数据")

    col1, col2 = st.columns([1, 1])
    with col1:
        start_date = st.date_input("开始日期", value=date.today())
    with col2:
        end_date = st.date_input("结束日期", value=date.today())

    watchlist = db.get_watchlist()

    if watchlist.empty:
        st.warning("自选股列表为空，请先在情报追踪页面添加自选股")
    else:
        st.info(f"自选股数量: {len(watchlist)}")

        date_range_info = f"日期范围: {start_date} 至 {end_date}"
        st.info(date_range_info)

        if st.button("🔄 更新所有自选股数据", type="primary"):
            with st.spinner("正在更新数据..."):
                progress_bar = st.progress(0)
                status_text = st.empty()
                success_count = 0
                fail_count = 0

                for idx, row in watchlist.iterrows():
                    code = row['code']
                    status_text.text(f"正在更新 {code}...")
                    try:
                        df = fetcher.get_daily_kline_by_date(code, start_date, end_date)
                        if df is not None and not df.empty:
                            db.save_kline_data(code, df)
                            success_count += 1
                        else:
                            fail_count += 1
                    except Exception as e:
                        fail_count += 1
                        st.error(f"更新 {code} 失败: {str(e)}")

                    progress = (idx + 1) / len(watchlist)
                    progress_bar.progress(progress)

                status_text.text("更新完成！")
                st.success(f"更新完成！成功: {success_count}, 失败: {fail_count}")

        st.markdown("---")
        st.markdown("### 单只股票查询")

        col1, col2 = st.columns([1, 1])
        with col1:
            code_input = st.text_input("股票代码", placeholder="例如: 600000")
        with col2:
            if st.button("查询单只股票"):
                if code_input:
                    with st.spinner("正在获取数据..."):
                        df = fetcher.get_daily_kline_by_date(code_input, start_date, end_date)
                        if df is not None and not df.empty:
                            db.save_kline_data(code_input, df)
                            st.success(f"✅ {code_input} 数据更新成功！")
                            st.dataframe(df.tail(10))
                        else:
                            st.error("❌ 获取数据失败，请检查股票代码是否正确")
                else:
                    st.warning("请输入股票代码")

with tab2:
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
            ["📅 快速更新（最近几天）", "📜 全量更新（全部历史数据）"],
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
        else:
            if st.button("🚀 全量更新（全部历史数据）", type="primary"):
                db.clear_failed_stocks()
                stock_list = db.get_stock_list()
                total_stocks = len(stock_list)

                st.info(f"开始全量更新 {total_stocks} 只股票（获取全部历史数据），请耐心等待...")

                progress_bar = st.progress(0)
                stats_col1, stats_col2, stats_col3 = st.columns(3)

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

                elapsed = time.time() - start_time
                st.success(f"✅ 全量更新完成！成功: {success_cnt}, 失败: {fail_cnt}，耗时: {elapsed:.1f}秒")

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

with tab3:
    st.subheader("涨跌停数据")

    col1, col2, col3 = st.columns([1, 1, 1])
    with col1:
        limit_start_date = st.date_input("开始日期", value=date.today(), key="limit_start")
    with col2:
        limit_end_date = st.date_input("结束日期", value=date.today(), key="limit_end")
    with col3:
        st.markdown("")

    st.info(f"查询日期范围: {limit_start_date} 至 {limit_end_date}")

    if st.button("🔍 查询涨跌停", type="primary"):
        with st.spinner("正在获取数据..."):
            limit_up_list = []
            limit_down_list = []

            current_date = limit_start_date
            while current_date <= limit_end_date:
                date_str = current_date.strftime('%Y%m%d')

                try:
                    up_df = fetcher.get_limit_up_data(date_str)
                    if up_df is not None and not up_df.empty:
                        up_df['查询日期'] = current_date.strftime('%Y-%m-%d')
                        limit_up_list.append(up_df)
                except:
                    pass

                try:
                    down_df = fetcher.get_limit_down_data(date_str)
                    if down_df is not None and not down_df.empty:
                        down_df['查询日期'] = current_date.strftime('%Y-%m-%d')
                        limit_down_list.append(down_df)
                except:
                    pass

                current_date = date.fromordinal(current_date.toordinal() + 1)

            def format_amount(df, cols=['成交额', '流通市值', '总市值']):
                for col in cols:
                    if col in df.columns:
                        df[col] = df[col].apply(
                            lambda x: f"{x/100000000:.2f}亿" if pd.notna(x) and x >= 100000000
                            else (f"{x/10000:.2f}万" if pd.notna(x) and x >= 10000 else f"{x:.2f}")
                        )
                return df

            if limit_up_list:
                limit_up_df = pd.concat(limit_up_list, ignore_index=True)
                limit_up_df = format_amount(limit_up_df)
                st.success(f"📈 找到 {len(limit_up_df)} 条涨停记录")

                st.markdown("### 涨停股票（按涨停板数降序）")

                up_display_cols = ['代码', '名称', '涨跌幅', '最新价', '成交额', '流通市值',
                                   '换手率', '炸板次数', '涨停统计', '连板数', '首次封板时间', '所属行业']
                up_display_cols = [c for c in up_display_cols if c in limit_up_df.columns]

                limit_up_df = limit_up_df[up_display_cols]
                limit_up_df = limit_up_df.sort_values('涨停统计', ascending=False)
                st.dataframe(limit_up_df, use_container_width=True)

                csv_up = limit_up_df.to_csv(index=False)
                st.download_button(
                    "📥 下载涨停数据",
                    csv_up,
                    f"limit_up_{limit_start_date.strftime('%Y%m%d')}_{limit_end_date.strftime('%Y%m%d')}.csv",
                    "text/csv"
                )
            else:
                st.warning("未获取到涨停数据，可能是非交易日")

            st.markdown("---")

            if limit_down_list:
                limit_down_df = pd.concat(limit_down_list, ignore_index=True)
                limit_down_df = format_amount(limit_down_df)
                st.success(f"📉 找到 {len(limit_down_df)} 条跌停记录")

                st.markdown("### 跌停股票（按涨停板数降序）")

                down_display_cols = ['代码', '名称', '涨跌幅', '最新价', '成交额', '流通市值',
                                     '换手率', '涨停统计', '振幅', '首次封板时间', '炸板次数', '所属行业']
                down_display_cols = [c for c in down_display_cols if c in limit_down_df.columns]

                limit_down_df = limit_down_df[down_display_cols]
                limit_down_df = limit_down_df.sort_values('涨停统计', ascending=False)
                st.dataframe(limit_down_df, use_container_width=True)

                csv_down = limit_down_df.to_csv(index=False)
                st.download_button(
                    "📥 下载跌停数据",
                    csv_down,
                    f"limit_down_{limit_start_date.strftime('%Y%m%d')}_{limit_end_date.strftime('%Y%m%d')}.csv",
                    "text/csv"
                )
            else:
                st.info("未获取到跌停数据")

with tab4:
    st.subheader("板块资金流向")

    sector_col1, sector_col2 = st.columns([1, 1])
    with sector_col1:
        sector_indicator = st.selectbox(
            "选择时间范围",
            ["今日", "3日排行", "5日排行", "10日排行", "20日排行"],
            index=0
        )
    with sector_col2:
        st.markdown("")
        st.info(f"当前选择: {sector_indicator}")

    if st.button("🔄 刷新板块数据", type="primary"):
        with st.spinner("正在获取板块数据..."):
            sector_df = fetcher.get_sector_flow(indicator=sector_indicator)

            if sector_df is not None and not sector_df.empty:
                st.success(f"获取到 {len(sector_df)} 个板块数据")

                def format_amount(df, cols=['成交额', '总成交额', '主力净流入', '超大单净流入', '大单净流入', '中单净流入', '小单净流入']):
                    for col in cols:
                        if col in df.columns:
                            df[col] = df[col].apply(
                                lambda x: f"{x/100000000:.2f}亿" if pd.notna(x) and abs(x) >= 100000000
                                else (f"{x/10000:.2f}万" if pd.notna(x) and abs(x) >= 10000 else f"{x:.2f}")
                            )
                    return df

                sector_df = format_amount(sector_df)

                display_cols = [c for c in sector_df.columns if c in
                              ['板块', '涨跌幅', '成交额', '总成交额', '主力净流入', '超大单净流入',
                               '大单净流入', '中单净流入', '小单净流入', '公司家数']]
                display_cols = [c for c in display_cols if c in sector_df.columns]

                sector_df = sector_df[display_cols]

                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("### 📈 涨幅板块")
                    top_sectors = sector_df[sector_df['涨跌幅'].apply(
                        lambda x: float(str(x).replace('%', '')) > 0 if str(x).replace('%', '').replace('-', '').replace('.', '').isdigit() else False
                    )].head(15)
                    if not top_sectors.empty:
                        st.dataframe(top_sectors, use_container_width=True)
                    else:
                        try:
                            sector_df['涨跌幅_num'] = sector_df['涨跌幅'].apply(
                                lambda x: float(str(x).replace('%', '')) if isinstance(x, str) else x
                            )
                            top_sectors = sector_df[sector_df['涨跌幅_num'] > 0].head(15)
                            st.dataframe(top_sectors.drop(columns=['涨跌幅_num']), use_container_width=True)
                        except:
                            st.dataframe(sector_df.head(15), use_container_width=True)

                with col2:
                    st.markdown("### 📉 跌幅板块")
                    bottom_sectors = sector_df[sector_df['涨跌幅'].apply(
                        lambda x: float(str(x).replace('%', '').replace('-', '')) if str(x).replace('%', '').replace('-', '').replace('.', '').isdigit() else False
                    )]
                    try:
                        sector_df['涨跌幅_num'] = sector_df['涨跌幅'].apply(
                            lambda x: float(str(x).replace('%', '')) if isinstance(x, str) else x
                        )
                        bottom_sectors = sector_df[sector_df['涨跌幅_num'] < 0].tail(15)
                        st.dataframe(bottom_sectors.drop(columns=['涨跌幅_num']), use_container_width=True)
                    except:
                        st.dataframe(sector_df.tail(15), use_container_width=True)

                st.markdown("### 📋 全部板块")
                st.dataframe(sector_df, use_container_width=True)

                csv = sector_df.to_csv(index=False)
                st.download_button(
                    "📥 下载板块资金流向",
                    csv,
                    f"sector_flow_{sector_indicator}_{date.today()}.csv",
                    "text/csv"
                )
            else:
                st.error("获取板块数据失败，可能是网络问题或非交易日")

with tab5:
    st.subheader("龙虎榜数据")

    col1, col2 = st.columns([1, 1])
    with col1:
        lhb_date = st.date_input("选择日期", value=date.today(), key="lhb_date")

    if st.button("🔍 查询龙虎榜", type="primary"):
        with st.spinner("正在获取龙虎榜数据..."):
            dragon_tiger_df = fetcher.get_dragon_tiger_data(lhb_date.strftime('%Y%m%d'))
            if dragon_tiger_df is not None and not dragon_tiger_df.empty:
                st.success(f"获取到 {len(dragon_tiger_df)} 条龙虎榜数据")
                st.dataframe(dragon_tiger_df, use_container_width=True)

                csv = dragon_tiger_df.to_csv(index=False)
                st.download_button(
                    "📥 下载龙虎榜数据",
                    csv,
                    f"dragon_tiger_{lhb_date.strftime('%Y%m%d')}.csv",
                    "text/csv"
                )
            else:
                st.info("未获取到龙虎榜数据，可能是非交易日或数据源问题")

st.markdown("---")
st.markdown("### 📋 数据更新日志")
st.info("最近更新时间: " + datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
