import streamlit as st
import pandas as pd
from datetime import datetime, date
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.database import StockDatabase
from utils.guba_file_reader import GubaFileReader


st.header("🔥 热门个股")

db = StockDatabase()

st.markdown("""
### 功能说明
- 从人气榜文件导入股票数据
- 支持按日期查看历史数据
- 数据来源：东方财富人气榜
""")

tab1, tab2 = st.tabs(["📥 数据导入", "📊 数据查看"])

with tab1:
    st.subheader("📥 从文件导入数据")

    reader = GubaFileReader()
    latest_file = reader.get_latest_file()

    if latest_file:
        with open(latest_file, 'r', encoding='utf-8') as f:
            first_line = f.readline().strip()

        if first_line and len(first_line) == 10 and first_line[:4].isdigit():
            st.info(f"📅 发现文件: **{latest_file.name}**  (日期: **{first_line}**)")

            if st.button("📥 导入数据到数据库", type="primary"):
                stocks = reader.read_latest_with_date()

                if stocks and len(stocks) > 0:
                    trade_date = first_line

                    db.clear_hot_stocks(trade_date)

                    saved_count = db.save_hot_stocks(stocks, trade_date)

                    if saved_count > 0:
                        st.success(f"✅ 成功保存 {saved_count} 条数据到数据库！")
                        st.info(f"📅 数据日期: {trade_date}")
                        st.rerun()
                    else:
                        st.error("❌ 保存数据失败")
                else:
                    st.error("❌ 读取文件失败")
        else:
            st.warning(f"⚠️ 文件格式不正确，第一行应为日期（如 2026-04-19）")
            st.code(f"第一行内容: {first_line}")
    else:
        st.warning("⚠️ 未找到人气榜文件")
        st.markdown("""
        **请确保人气榜文件位于项目根目录，文件名格式为：**
        - `240101.txt`
        - `240102.txt`
        
        **文件格式要求：**
        - 第一行：日期（如 `2026-04-19`）
        - 第二行起：按规则排列的股票数据
        """)

with tab2:
    st.subheader("📊 查看热门个股")

    available_dates = db.get_hot_stocks_dates()

    if not available_dates:
        st.info("📭 暂无数据，请先从文件导入")
    else:
        selected_date = st.selectbox(
            "选择日期",
            options=available_dates,
            index=0
        )

        if st.button("🔍 查询", type="secondary"):
            hot_data = db.get_hot_stocks_by_date(selected_date)

            if not hot_data.empty:
                st.success(f"✅ 找到 {len(hot_data)} 条热门个股数据")

                col1, col2, col3 = st.columns(3)

                with col1:
                    st.metric("股票总数", len(hot_data))

                with col2:
                    avg_change = hot_data['change_pct'].mean()
                    st.metric("平均涨跌幅", f"{avg_change:+.2f}%")

                with col3:
                    up_count = len(hot_data[hot_data['change_pct'] > 0])
                    st.metric("上涨数量", up_count)

                st.markdown("### 详细数据")

                display_df = hot_data[['rank', 'rank_change', 'code', 'name', 'change_pct', 'attention_ratio']].copy()
                display_df.columns = ['排名', '排名变动', '代码', '名称', '涨跌幅(%)', '上榜原因']

                display_df['涨跌幅(%)'] = display_df['涨跌幅(%)'].apply(
                    lambda x: f"{x:+.2f}%" if pd.notna(x) else "N/A"
                )

                display_df['排名变动'] = display_df['排名变动'].apply(
                    lambda x: f"{x:+d}" if pd.notna(x) else "0"
                )

                st.dataframe(
                    display_df,
                    use_container_width=True,
                    height=600
                )

                csv_data = hot_data[['rank', 'rank_change', 'code', 'name', 'change_pct', 'attention_ratio']].copy()
                csv_data.columns = ['排名', '排名变动', '代码', '名称', '涨跌幅(%)', '上榜原因']

                csv = csv_data.to_csv(index=False, encoding='utf-8-sig')

                st.download_button(
                    label="📥 导出为CSV",
                    data=csv,
                    file_name=f"hot_stocks_{selected_date}.csv",
                    mime="text/csv"
                )

            else:
                st.warning(f"⚠️ {selected_date} 没有数据")

st.markdown("---")

st.markdown("""
### 💡 使用提示

1. **文件命名**: `YYMMDD.txt` 格式（如 `240101.txt`）
2. **文件格式**: 第一行必须是日期（YYYY-MM-DD格式）
3. **数据导入**: 导入时会自动清空该日期的旧数据
4. **历史查询**: 可以查看不同日期的人气榜数据

**文件格式示例：**
```
2026-04-19
600703
三安光电
排名详情 股吧
13.34
1.21
9.98%
41.28%58.72%
...
```

---
*数据来源：东方财富人气榜*
""")
