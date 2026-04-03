import streamlit as st
from datetime import datetime

st.set_page_config(
    page_title="股票数据看板",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1E88E5;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #1E88E5;
    }
    .stActionButton > button {
        background-color: #1E88E5;
        color: white;
    }
</style>
""", unsafe_allow_html=True)


st.markdown('<h1 class="main-header">📈 股票数据看板</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">自用股票情报追踪与预测系统</p>', unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)

with col1:
    st.metric(label="系统状态", value="运行中", delta="正常")

with col2:
    st.metric(label="数据源", value="已连接", delta="mootdx")

with col3:
    st.metric(label="更新时间", value=datetime.now().strftime('%H:%M'), delta="实时")

st.markdown("---")
st.markdown("""
## 欢迎使用股票数据看板

这是一套自用的股票情报追踪与预测系统，主要功能包括：

### 📊 数据更新
- 自动更新自选股日K数据（历史 + 当日）
- 全市场涨跌停数据监控
- 板块资金流向追踪
- 龙虎榜数据

### 🔍 情报追踪
- 自选股管理（添加/删除）
- 触发指标股筛选
- 大盘分析
- 涨跌停分析
- 舆情监控

### 📈 缠论分析
- 缠论分型识别
- MACD背驰检测
- 缠论买卖点识别（一买、二买）
- 缠论选股功能

### 🤖 股票预测
- 技术指标计算（MA、MACD、KDJ等）
- 明日股价预测
- 走势预测

### 📝 复盘分析
- 预测与实际对比
- 准确率统计
- 原因分析

---

⚠️ **免责声明**：本系统所有数据和预测仅供参考，不构成投资建议。股市有风险，投资需谨慎！
""")
