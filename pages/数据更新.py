import streamlit as st
import pandas as pd
from datetime import datetime, date
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.database import StockDatabase
from utils.data_fetcher import StockDataFetcher


st.header("📊 数据更新")

db = StockDatabase()
fetcher = StockDataFetcher()

tab1, tab2, tab3, tab4 = st.tabs([
    "📈 日K数据",
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
                success_count = 0
                fail_count = 0

                for idx, row in watchlist.iterrows():
                    code = row['code']
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
            all_limit_data = []

            current_date = limit_start_date
            while current_date <= limit_end_date:
                try:
                    limit_df = fetcher.get_limit_up_data(current_date.strftime('%Y%m%d'))
                    if limit_df is not None and not limit_df.empty:
                        limit_df['查询日期'] = current_date.strftime('%Y-%m-%d')
                        all_limit_data.append(limit_df)
                except:
                    pass

                current_date = date.fromordinal(current_date.toordinal() + 1)

            if all_limit_data:
                combined_df = pd.concat(all_limit_data, ignore_index=True)
                st.success(f"找到 {len(combined_df)} 条涨停记录")

                st.markdown("### 📈 涨停股票")
                display_cols = [col for col in combined_df.columns if col in
                              ['代码', '名称', '涨停统计', '流通市值', '连板数', '涨停原因', '查询日期']]
                if display_cols:
                    st.dataframe(combined_df[display_cols], use_container_width=True)

                csv = combined_df.to_csv(index=False)
                st.download_button(
                    "📥 下载涨停数据",
                    csv,
                    f"limit_up_{limit_start_date.strftime('%Y%m%d')}_{limit_end_date.strftime('%Y%m%d')}.csv",
                    "text/csv"
                )
            else:
                st.warning("未获取到涨停数据，可能是非交易日或日期范围选择有误")

with tab3:
    st.subheader("板块资金流向")

    if st.button("🔄 刷新板块数据", type="primary"):
        with st.spinner("正在获取板块数据..."):
            sector_df = fetcher.get_sector_flow()
            if sector_df is not None and not sector_df.empty:
                st.success(f"获取到 {len(sector_df)} 个板块数据")

                if '名称' in sector_df.columns and '涨跌幅' in sector_df.columns:
                    sector_df_sorted = sector_df.sort_values('涨跌幅', ascending=False)

                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown("### 涨幅板块")
                        top_sectors = sector_df_sorted.head(10)
                        st.dataframe(top_sectors)
                    with col2:
                        st.markdown("### 跌幅板块")
                        bottom_sectors = sector_df_sorted.tail(10)
                        st.dataframe(bottom_sectors)
            else:
                st.error("获取板块数据失败")

with tab4:
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
