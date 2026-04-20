import streamlit as st
import pandas as pd
import numpy as np
from datetime import datetime, timedelta, date
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.database import StockDatabase
from utils.data_fetcher import StockDataFetcher
import plotly.graph_objects as go


def get_trading_dates(n: int) -> list:
    """获取最近n个交易日"""
    dates = []
    current = datetime.now()
    while len(dates) < n:
        if current.weekday() < 5:
            dates.append(current.strftime('%Y%m%d'))
        current -= timedelta(days=1)
    return dates


def format_date(d: str) -> str:
    """格式化日期显示"""
    if len(d) == 8:
        return f"{d[4:6]}-{d[6:8]}"
    return d


def fetch_limit_up(date_str: str):
    """获取涨停数据"""
    try:
        df = fetcher.get_limit_up_data(date=date_str)
        if df is not None and not df.empty:
            return df
    except Exception as e:
        print(f"获取涨停数据失败 {date_str}: {e}")
    return pd.DataFrame()


def fetch_limit_down(date_str: str):
    """获取跌停数据"""
    try:
        df = fetcher.get_limit_down_data(date=date_str)
        if df is not None and not df.empty:
            return df
    except Exception as e:
        print(f"获取跌停数据失败 {date_str}: {e}")
    return pd.DataFrame()


def normalize_sector_columns(df):
    """标准化板块数据列名"""
    if df.empty:
        return df
    cols = df.columns.tolist()
    if len(cols) >= 7 and all(isinstance(c, (int, float)) or (isinstance(c, str) and c.replace('.', '').replace('-', '').isdigit()) for c in cols[:3]):
        expected = ['板块', '涨跌幅', '成交额', '主力净流入', '超大单净流入', '大单净流入', '中单净流入', '小单净流入']
        df.columns = expected[:len(cols)]
    return df


def fetch_sector_flow():
    """获取板块资金流向（当日汇总）"""
    df = fetcher.get_sector_flow(indicator="今日")
    if df is not None and not df.empty:
        df = normalize_sector_columns(df)
        return df
    return pd.DataFrame()


def create_sector_flow_chart(sector_df: pd.DataFrame, top_n: int = 15):
    """创建板块资金流向柱状图"""
    if sector_df.empty:
        return None

    flow_col = None
    name_col = None

    for col in sector_df.columns:
        if '净流入' in str(col):
            flow_col = col
            break

    for col in sector_df.columns:
        if col in ['板块', '名称']:
            name_col = col
            break

    if flow_col is None:
        for col in sector_df.columns:
            if sector_df[col].dtype in ['float64', 'int64', 'float32', 'int32']:
                flow_col = col
                break

    if name_col is None:
        for col in sector_df.columns:
            if sector_df[col].dtype == 'object' and col != flow_col:
                name_col = col
                break

    if flow_col is None or name_col is None:
        st.error(f"无法识别板块数据列，列名: {sector_df.columns.tolist()}")
        return None

    df_work = sector_df[[name_col, flow_col]].copy()
    df_sorted = df_work.sort_values(flow_col, ascending=True).tail(top_n)

    colors = ['#26A69A' if x >= 0 else '#EF5350' for x in df_sorted[flow_col]]

    fig = go.Figure(data=[
        go.Bar(
            x=df_sorted[flow_col].values,
            y=df_sorted[name_col].values,
            orientation='h',
            marker_color=colors,
            text=[f"{x:.2f}亿" for x in df_sorted[flow_col].values],
            textposition='outside'
        )
    ])

    fig.update_layout(
        height=400,
        margin=dict(l=150, r=20, t=30, b=30),
        xaxis=dict(title="主力净流入（亿元）"),
        yaxis=dict(title="板块", side="left"),
        showlegend=False
    )

    return fig


def create_sector_change_chart(sector_df: pd.DataFrame, top_n: int = 15):
    """创建板块涨跌幅柱状图"""
    if sector_df.empty:
        return None

    change_col = None
    name_col = None

    for col in sector_df.columns:
        if '涨跌幅' in str(col):
            change_col = col
            break

    for col in sector_df.columns:
        if col in ['板块', '名称']:
            name_col = col
            break

    if change_col is None:
        for col in sector_df.columns:
            if sector_df[col].dtype in ['float64', 'int64', 'float32', 'int32'] and col != name_col:
                change_col = col
                break

    if change_col is None or name_col is None:
        st.error(f"无法识别板块涨跌列，列名: {sector_df.columns.tolist()}")
        return None

    df_work = sector_df[[name_col, change_col]].copy()
    df_sorted = df_work.sort_values(change_col, ascending=True)

    top_rise = df_sorted.tail(top_n)
    top_fall = df_sorted.head(top_n)

    fig = go.Figure()

    fig.add_trace(go.Bar(
        x=top_fall[change_col].values,
        y=top_fall[name_col].values,
        orientation='h',
        marker_color='#4ECDC4',
        name='下跌'
    ))

    fig.add_trace(go.Bar(
        x=top_rise[change_col].values,
        y=top_rise[name_col].values,
        orientation='h',
        marker_color='#FF6B6B',
        name='上涨'
    ))

    fig.update_layout(
        height=400,
        margin=dict(l=150, r=80, t=30, b=30),
        xaxis=dict(title="涨跌幅（%）"),
        yaxis=dict(title="板块", side="left"),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=1.02)
    )

    return fig


def create_pie_chart(data: pd.Series, title: str):
    """创建饼图"""
    if data.empty:
        return None

    colors = [
        '#2E86AB', '#A23B72', '#F18F01', '#C73E1D', '#3B1F2B',
        '#6B4226', '#4A7C59', '#87CEEB', '#FF6B6B', '#4ECDC4'
    ]

    fig = go.Figure(data=[go.Pie(
        labels=data.index.tolist()[:10],
        values=data.values[:10],
        marker=dict(colors=colors[:len(data)]),
        textinfo='label+percent',
        textposition='outside',
        hole=0.4
    )])

    fig.update_layout(
        title=dict(text=title, x=0.5, font=dict(size=14)),
        height=350,
        margin=dict(l=20, r=20, t=50, b=20),
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.2)
    )

    return fig


st.set_page_config(page_title="市场情绪分析", page_icon="📊", layout="wide")

st.header("📊 市场情绪分析")
st.warning("⚠️ **免责声明**: 数据仅供参考，不构成投资建议。股市有风险，投资需谨慎！")

db = StockDatabase()
fetcher = StockDataFetcher()

col1, col2, col3 = st.columns([1, 2, 2])
with col1:
    selected_date = st.date_input("选择日期", value=date.today())
    selected_date_str = selected_date.strftime('%Y%m%d')

with col2:
    st.info(f"📅 当前查看: {selected_date_str}")

with col3:
    col_refresh_up, col_refresh_sector = st.columns([1, 1])
    with col_refresh_up:
        refresh_limit = st.button("📈 获取涨跌停数据", type="primary")
    with col_refresh_sector:
        refresh_sector = st.button("💰 获取板块数据", type="primary")

if refresh_limit:
    with st.spinner("正在获取涨跌停数据..."):
        progress_bar = st.progress(0)
        progress_text = st.empty()

        saved_up = 0
        saved_down = 0
        actual_date = None

        progress_text.text("正在获取涨停数据...")
        progress_bar.progress(0.3)

        up_df = fetch_limit_up(selected_date_str)
        if not up_df.empty:
            records = up_df.to_dict('records')
            if 'trade_date' in up_df.columns and up_df['trade_date'].iloc[0]:
                actual_date = up_df['trade_date'].iloc[0]
            count = db.save_limit_up_history(records, actual_date or selected_date_str)
            saved_up += count

        progress_text.text("正在获取跌停数据...")
        progress_bar.progress(0.7)

        down_df = fetch_limit_down(selected_date_str)
        if not down_df.empty:
            records = down_df.to_dict('records')
            if not actual_date and 'trade_date' in down_df.columns and down_df['trade_date'].iloc[0]:
                actual_date = down_df['trade_date'].iloc[0]
            count = db.save_limit_down_history(records, actual_date or selected_date_str)
            saved_down += count

        progress_bar.progress(1.0)
        progress_text.text("涨跌停数据获取完成！")

        st.success(f"✅ 成功保存 {saved_up} 条涨停、{saved_down} 条跌停数据")
        st.rerun()

if refresh_sector:
    with st.spinner("正在从同花顺获取板块资金流向..."):
        try:
            import requests
            from bs4 import BeautifulSoup

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Referer': 'https://www.10jqka.com.cn/',
            }

            all_data_list = []

            # 获取第1页和第2页数据
            for page_num in range(1, 3):
                if page_num == 1:
                    url = "https://q.10jqka.com.cn/thshy/"
                else:
                    url = f"https://q.10jqka.com.cn/thshy/index/field/199112/order/desc/page/{page_num}/ajax/1/"

                response = requests.get(url, headers=headers, timeout=30)
                response.encoding = 'gbk'
                soup = BeautifulSoup(response.text, 'html.parser')

                table = soup.find('table')
                if table:
                    rows = table.find_all('tr')[1:]

                    for row in rows:
                        cols = row.find_all(['td', 'th'])
                        if len(cols) >= 11:
                            try:
                                seq = cols[0].text.strip()
                                board_name = cols[1].text.strip()
                                change_pct_str = cols[2].text.strip().replace('%', '')
                                net_flow_str = cols[5].text.strip()

                                try:
                                    change_pct = float(change_pct_str)
                                except:
                                    change_pct = 0.0

                                all_data_list.append({
                                    '序号': seq,
                                    '板块': board_name,
                                    '涨跌幅': change_pct,
                                    '主力净流入': net_flow_str
                                })
                            except Exception as e:
                                continue

            if all_data_list:
                sector_df = pd.DataFrame(all_data_list)
                # 使用用户选择的日期
                trade_date = selected_date.strftime('%Y-%m-%d')

                conn = db._get_connection()
                cursor = conn.cursor()

                cursor.execute("DELETE FROM sector_flow_history WHERE trade_date = ?", (trade_date,))
                cursor.execute("DELETE FROM industry_data WHERE trade_date = ?", (trade_date,))

                saved_count = 0
                for seq, (_, row) in enumerate(sector_df.iterrows(), 1):
                    try:
                        net_flow = float(row['主力净流入']) if row['主力净流入'] and row['主力净流入'] != '-' else 0
                    except:
                        net_flow = 0

                    cursor.execute("""
                        INSERT OR REPLACE INTO sector_flow_history
                        (trade_date, sector_name, main_net_inflow, change_pct)
                        VALUES (?, ?, ?, ?)
                    """, (
                        trade_date,
                        row['板块'],
                        net_flow,
                        row['涨跌幅']
                    ))

                    cursor.execute("""
                        INSERT OR REPLACE INTO industry_data
                        (trade_date, seq, board_name, change_pct)
                        VALUES (?, ?, ?, ?)
                    """, (
                        trade_date,
                        seq,
                        row['板块'],
                        row['涨跌幅']
                    ))

                    saved_count += 1

                conn.commit()
                conn.close()

                st.success(f"✅ 成功从同花顺获取并保存 {saved_count} 个板块数据 (数据日期: {trade_date})")
            else:
                st.warning("未能获取板块数据")
        except Exception as e:
            st.error(f"获取失败: {e}")

        st.rerun()

st.markdown("---")

# 获取选定日期的数据
limit_up_df = db.get_limit_up_history_by_date(selected_date_str)
limit_down_df = db.get_limit_down_history_by_date(selected_date_str)
sector_df = db.get_sector_flow_history_by_date(selected_date_str)

# 检查是否有数据
has_data = not limit_up_df.empty or not limit_down_df.empty or not sector_df.empty

if not has_data:
    st.warning(f"📭 {selected_date_str} ({format_date(selected_date_str)}) 暂无数据，请点击「获取板块数据」按钮获取最新数据")

if not limit_up_df.empty:
    limit_up_df['trade_date_fmt'] = limit_up_df['trade_date'].apply(format_date)
if not limit_down_df.empty:
    limit_down_df['trade_date_fmt'] = limit_down_df['trade_date'].apply(format_date)

st.subheader("📈 板块资金流向（TOP15柱状图）")

# 只使用数据库中选定日期的历史数据，不获取当日数据
if not sector_df.empty:
    sector_df_fresh = sector_df.copy()
    # 数据库历史数据的列名映射
    column_mapping = {
        'sector_name': '板块',
        'main_net_inflow': '主力净流入',
        'change_pct': '涨跌幅'
    }
    sector_df_fresh = sector_df_fresh.rename(columns=column_mapping)
else:
    sector_df_fresh = pd.DataFrame()

if not sector_df_fresh.empty:
    st.markdown("##### 主力净流入TOP15")
    flow_chart = create_sector_flow_chart(sector_df_fresh, top_n=15)
    if flow_chart:
        st.plotly_chart(flow_chart, use_container_width=True)
else:
    st.info("暂无板块资金流向数据")

st.markdown("---")

st.subheader("📊 板块数据表格（全部数据）")

if not sector_df.empty:
    display_df = sector_df[['sector_name', 'change_pct', 'main_net_inflow']].copy()
    display_df.columns = ['板块名称', '涨跌幅(%)', '主力净流入(亿元)']

    display_df['涨跌幅(%)'] = display_df['涨跌幅(%)'].apply(
        lambda x: f"{x:+.2f}%" if pd.notna(x) else "N/A"
    )
    display_df['主力净流入(亿元)'] = display_df['主力净流入(亿元)'].apply(
        lambda x: f"{x:.2f}" if pd.notna(x) else "N/A"
    )

    st.dataframe(display_df, use_container_width=True, height=500)
    st.caption(f"共 {len(display_df)} 个板块")
else:
    st.info("暂无板块数据")

st.markdown("---")

col1, col2 = st.columns(2)

with col1:
    st.subheader("📈 涨停板块分布")
    if not limit_up_df.empty:
        reason_counts = limit_up_df['reason'].value_counts()
        pie_fig_up = create_pie_chart(reason_counts, "涨停股票板块分布")
        if pie_fig_up:
            st.plotly_chart(pie_fig_up, use_container_width=True)
    else:
        st.info("暂无涨停数据")

with col2:
    st.subheader("📉 跌停板块分布")
    if not limit_down_df.empty:
        reason_counts_down = limit_down_df['reason'].value_counts()
        pie_fig_down = create_pie_chart(reason_counts_down, "跌停股票板块分布")
        if pie_fig_down:
            st.plotly_chart(pie_fig_down, use_container_width=True)
    else:
        st.info("暂无跌停数据")

st.markdown("---")

st.subheader("📋 详细数据")

col_up, col_down = st.columns(2)

with col_up:
    st.markdown("#### 涨停列表")
    if not limit_up_df.empty:
        display_cols = ['trade_date_fmt', 'code', 'name', 'reason', 'limit_count']
        display_df = limit_up_df[[c for c in display_cols if c in limit_up_df.columns]]
        display_df.columns = ['日期', '代码', '名称', '所属板块', '连板数']
        st.dataframe(display_df, use_container_width=True, height=400, hide_index=True)
        st.caption(f"共 {len(limit_up_df)} 条记录")
    else:
        st.info("暂无涨停数据")

with col_down:
    st.markdown("#### 跌停列表")
    if not limit_down_df.empty:
        display_cols_down = ['trade_date_fmt', 'code', 'name', 'reason', 'limit_count']
        display_df_down = limit_down_df[[c for c in display_cols_down if c in limit_down_df.columns]]
        display_df_down.columns = ['日期', '代码', '名称', '所属板块', '连板数']
        st.dataframe(display_df_down, use_container_width=True, height=400, hide_index=True)
        st.caption(f"共 {len(limit_down_df)} 条记录")
    else:
        st.info("暂无跌停数据")

st.markdown("---")
st.markdown(f"""
### 📖 说明

**数据来源**: 同花顺行业板块

**数据日期**: {format_date(selected_date_str)}

**图表说明**:
- **主力净流入TOP15**: 横向柱状图展示主力净流入排名前15的板块（绿色=净流入，红色=净流出）
- **板块数据表格**: 展示所有板块完整数据（涨跌幅、主力净流入）

**更新说明**: 点击「获取板块数据」按钮从同花顺获取最新数据
""")
