import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
import random
import uuid
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.database import StockDatabase
from utils.technical_analysis import add_technical_indicators, calculate_profit
from ai.analyzer import AIAnalyzer

st.markdown("""
<style>
/* 修改rangeslider高度为40px */
.rangeslider-slidebox {
    height: 40px !important;
}
</style>
""", unsafe_allow_html=True)

def init_session_state():
    """初始化会话状态"""
    if 'training_id' not in st.session_state:
        st.session_state.training_id = None
    if 'current_stock' not in st.session_state:
        st.session_state.current_stock = None
    if 'current_date_index' not in st.session_state:
        st.session_state.current_date_index = 0
    if 'kline_data' not in st.session_state:
        st.session_state.kline_data = None
    if 'weekly_data' not in st.session_state:
        st.session_state.weekly_data = None
    if 'show_type' not in st.session_state:
        st.session_state.show_type = '日线'
    if 'current_position' not in st.session_state:
        st.session_state.current_position = 0
    if 'total_cash' not in st.session_state:
        st.session_state.total_cash = 100000
    if 'initial_cash' not in st.session_state:
        st.session_state.initial_cash = 100000
    if 'trade_records' not in st.session_state:
        st.session_state.trade_records = []
    if 'max_position' not in st.session_state:
        st.session_state.max_position = 3
    if 'training_start_date' not in st.session_state:
        st.session_state.training_start_date = None
    if 'training_end_date' not in st.session_state:
        st.session_state.training_end_date = None

def get_random_stock(db, max_days=300):
    """随机获取一只股票，获取最多max_days天的数据"""
    all_codes = db.get_all_stock_codes()
    if not all_codes:
        return None
    
    while True:
        code = random.choice(all_codes)
        kline_data = db.get_kline_data(code, days=max_days)
        if len(kline_data) >= 100:
            return code, kline_data

def get_weekly_index(weekly_df, target_date):
    """找到周线中最后一个日期小于等于目标日期的索引"""
    target_date_str = str(target_date)[:10]
    for i in range(len(weekly_df) - 1, -1, -1):
        weekly_date_str = str(weekly_df.iloc[i]['date'])[:10]
        if weekly_date_str <= target_date_str:
            return i
    return 0

def create_kline_chart(df, current_index=None, trade_points=None, training_start_index=None):
    """创建K线图 - 使用subplot实现3行布局（价格、成交量、量能）"""
    # 确保日期列是datetime格式（解决日期间隔问题）
    df_plot = df.copy()
    df_plot['date'] = pd.to_datetime(df_plot['date'])
    
    # 创建subplot结构：3行，价格400份，成交量225份，量能40份
    # 总共665份
    fig = make_subplots(
        rows=3,
        cols=1,
        row_heights=[400, 225, 40],  # 价格400份，成交量225份，量能40份
        shared_xaxes=True,
        vertical_spacing=0.02,  # 上下间距
        subplot_titles=('', ''),  # 不显示子标题
        x_title='日期'
    )
    
    # 添加K线到第1行
    fig.add_trace(go.Candlestick(
        x=df_plot['date'],
        open=df_plot['open'],
        high=df_plot['high'],
        low=df_plot['low'],
        close=df_plot['close'],
        name='K线',
        increasing_line_color='red',
        decreasing_line_color='green',
        legendgroup='kline'  # 分组
    ), row=1, col=1)
    
    # 添加均线到第1行
    for ma in ['MA5', 'MA10', 'MA20']:
        if ma in df_plot.columns:
            fig.add_trace(go.Scatter(
                x=df_plot['date'],
                y=df_plot[ma],
                mode='lines',
                name=ma,
                line=dict(width=1)
            ), row=1, col=1)
    
    # 添加买卖气泡注释（在图顶部显示，不遮挡K线）
    if trade_points:
        # 计算K线最高价位置，用于确定注释Y坐标
        max_price = df_plot['high'].max()
        
        for i, point in enumerate(trade_points):
            point_date = pd.to_datetime(point['date'])
            # 注释位置在K线图顶部，y=1.15（在图之外）
            offset_y = 0.05 * i  # 错开不同注释的Y坐标
            
            # 颜色：买入蓝色，卖出橙色
            color = 'blue' if point['type'] == '买入' else 'orange'
            
            # 添加气泡注释
            fig.add_annotation(
                x=point_date,
                y=1.12 + offset_y,  # 在图顶部上方
                yref='paper',
                text=f"📌 {point['type']}: {point['price']:.2f}",
                showarrow=False,
                font=dict(size=10, color=color),
                bgcolor='white',
                bordercolor=color,
                borderwidth=1,
                borderpad=3,
                align='left'
            )
    
    # 计算阳线和阴线
    is_bullish = df_plot['close'] >= df_plot['open']
    
    # 设置颜色：阳线红色，阴线绿色
    colors = ['red' if bullish else 'green' for bullish in is_bullish]
    
    # 添加量柱到第2行 - 单个Bar trace，颜色根据阳阴线变化
    fig.add_trace(go.Bar(
        x=df_plot['date'],
        y=df_plot['volume'],
        marker_color=colors,
        width=0.8  # 设置柱子宽度
    ), row=2, col=1)
    
    # 添加量柱到第3行 - 显示量柱变化（与第2行类似但更小）
    fig.add_trace(go.Bar(
        x=df_plot['date'],
        y=df_plot['volume'],
        marker_color=colors,
        width=0.8,  # 设置柱子宽度
        name='量柱'
    ), row=3, col=1)
    
    # 计算量柱y轴范围
    max_volume = df_plot['volume'].max()
    volume_y_max = max_volume * 1.2  # 留出20%的顶部空间
    
    # 配置y轴标题和域（分离K线、成交量和量柱）
    fig.update_yaxes(title_text='价格', title_font=dict(size=12), row=1, col=1)
    fig.update_yaxes(title_text='成交量', title_font=dict(size=12), row=2, col=1)
    fig.update_yaxes(title_text='量柱', title_font=dict(size=10), row=3, col=1)
    
    # 设置Y轴域，分离K线、成交量和量柱区域
    fig.update_yaxes(domain=[0.35, 1], row=1, col=1)  # K线占上方65%
    fig.update_yaxes(domain=[0.15, 0.32], row=2, col=1)  # 成交量占15%-32%
    fig.update_yaxes(domain=[0, 0.12], row=3, col=1)  # 量柱占下方12%
    
    # 虚线固定在训练开始位置，不随交易移动
    if training_start_index is not None and training_start_index < len(df_plot):
        start_date = df_plot.iloc[training_start_index]['date']
        fig.add_shape(
            type='line',
            x0=start_date,
            x1=start_date,
            y0=0,
            y1=1,
            yref='y domain',
            line=dict(color='gray', width=2, dash='dash'),
            row=1, col=1
        )
        # 添加训练开始标记
        fig.add_annotation(
            x=start_date,
            y=1.05,
            yref='paper',
            text='训练开始',
            showarrow=False,
            font=dict(color='gray', size=10)
        )
    
    # 设置整体布局
    fig.update_layout(
        title=dict(
            text='K线图',
            font=dict(size=16)
        ),
        showlegend=True,
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1.02,
            xanchor='right',
            x=1
        ),
        hovermode='closest',  # 只显示最近的数据点，移除成交量区域的K线hover信息
        height=665,  # 固定高度（价格400 + 成交量225 + 量能40 + 间距等）
        width=2200,  # 增加宽度到2200
        hoverlabel=dict(
            namelength=-1,  # 显示完整信息
            bgcolor='white',  # 白色背景
            font_size=12
        ),
        margin=dict(
            t=80,  # 顶部边距，为标题留空间
            b=50,  # 底部边距
            l=60,  # 左边距
            r=60   # 右边距
        )
    )
    
    # 配置量柱y轴范围
    fig.update_yaxes(range=[0, volume_y_max], row=2, col=1)
    
    # 配置x轴，设置type为date以正确显示日期间隔，禁用rangeslider
    fig.update_xaxes(
        type='date',
        showticklabels=True,
        showgrid=True,
        gridcolor='lightgray',
        rangeslider=dict(visible=False),  # 禁用rangeslider
        row=1, col=1
    )
    fig.update_xaxes(
        type='date',
        showticklabels=True,
        showgrid=True,
        gridcolor='lightgray',
        rangeslider=dict(visible=False),  # 禁用rangeslider
        row=2, col=1
    )
    fig.update_xaxes(
        type='date',
        showticklabels=True,
        showgrid=True,
        gridcolor='lightgray',
        rangeslider=dict(visible=False),  # 禁用rangeslider
        row=3, col=1
    )
    
    return fig

def create_macd_chart(df):
    """创建MACD图表"""
    fig = go.Figure()
    
    if 'MACD' in df.columns and 'Signal' in df.columns and 'Histogram' in df.columns:
        fig.add_trace(go.Scatter(
            x=df['date'],
            y=df['MACD'],
            mode='lines',
            name='MACD',
            line=dict(color='blue')
        ))
        
        fig.add_trace(go.Scatter(
            x=df['date'],
            y=df['Signal'],
            mode='lines',
            name='Signal',
            line=dict(color='red')
        ))
        
        fig.add_trace(go.Bar(
            x=df['date'],
            y=df['Histogram'],
            name='Histogram',
            marker_color=['red' if val > 0 else 'green' for val in df['Histogram']]
        ))
        
        fig.update_layout(
            title='MACD指标',
            xaxis_title='日期',
            yaxis_title='值',
            legend=dict(orientation='h'),
            height=300
        )
    
    return fig

def create_rsi_chart(df):
    """创建RSI图表"""
    fig = go.Figure()
    
    if 'RSI' in df.columns:
        fig.add_trace(go.Scatter(
            x=df['date'],
            y=df['RSI'],
            mode='lines',
            name='RSI',
            line=dict(color='purple')
        ))
        
        # 添加超买超卖线
        fig.add_hline(y=70, line_dash='dash', line_color='red', annotation_text='超买')
        fig.add_hline(y=30, line_dash='dash', line_color='green', annotation_text='超卖')
        
        fig.update_layout(
            title='RSI指标',
            xaxis_title='日期',
            yaxis_title='RSI (0-100)',
            legend=dict(orientation='h'),
            height=300
        )
    
    return fig

def start_new_training(db):
    """开始新的训练"""
    code, kline_data = get_random_stock(db, max_days=300)
    if not code:
        st.error("无法获取股票数据，请确保数据已更新")
        return False
    
    # 添加技术指标
    df, weekly_df = add_technical_indicators(kline_data, include_weekly=True)
    
    total_days = len(df)
    
    # 实现300/200/100规则（或2/3和1/3规则）
    if total_days >= 300:
        display_days = 200  # 显示200天
        remaining_days = total_days - 200  # 剩余用于训练
    else:
        display_days = int(total_days * 2 / 3)  # 显示2/3
        remaining_days = total_days - display_days  # 剩余1/3用于训练
    
    # 训练从第display_days根K线开始
    training_start_index = display_days
    
    # 检查数据是否足够
    if total_days < 100:
        st.error("数据不足，无法开始训练")
        return False
    
    # 初始化训练状态
    st.session_state.training_id = str(uuid.uuid4())
    st.session_state.current_stock = code
    st.session_state.kline_data = df
    st.session_state.weekly_data = weekly_df
    st.session_state.current_date_index = training_start_index
    st.session_state.training_start_index = training_start_index  # 保存训练开始索引
    st.session_state.display_days = display_days
    st.session_state.remaining_days = remaining_days
    st.session_state.current_position = 0
    st.session_state.trade_records = []
    st.session_state.total_cash = st.session_state.initial_cash
    st.session_state.training_start_date = df.iloc[training_start_index]['date']
    
    return True

def execute_trade(trade_type, reason):
    """执行交易"""
    if not st.session_state.training_id or st.session_state.kline_data is None or len(st.session_state.kline_data) == 0:
        return False, "请先开始训练"
    
    # 交易理由必填验证
    if trade_type in ['买入', '卖出']:
        if not reason or not reason.strip():
            return False, "请填写交易理由"
    
    current_data = st.session_state.kline_data.iloc[st.session_state.current_date_index]
    current_price = current_data['close']
    
    if trade_type == '买入':
        # 用当前剩余资金全部买入（满仓）
        need_cash = st.session_state.total_cash
        
        if need_cash <= 0:
            return False, "资金不足"
        
        quantity = int(need_cash / current_price)
        
        if quantity <= 0:
            return False, "资金不足"
        
        # 执行买入
        cost = quantity * current_price
        st.session_state.total_cash -= cost
        st.session_state.current_position += quantity
        
        # 记录交易
        trade_record = {
            'date': current_data['date'],
            'type': '买入',
            'price': current_price,
            'quantity': quantity,
            'reason': reason,
            'cash': st.session_state.total_cash,
            'total_position': st.session_state.current_position
        }
        
    elif trade_type == '卖出':
        # 卖出全部持仓（清仓）
        if st.session_state.current_position <= 0:
            return False, "无持仓"
        
        sell_quantity = st.session_state.current_position
        
        # 执行卖出
        proceeds = sell_quantity * current_price
        st.session_state.total_cash += proceeds
        st.session_state.current_position = 0
        
        # 记录交易
        trade_record = {
            'date': current_data['date'],
            'type': '卖出',
            'price': current_price,
            'quantity': sell_quantity,
            'reason': reason,
            'cash': st.session_state.total_cash,
            'total_position': 0
        }
        
    elif trade_type == '观望':
        # 记录观望
        trade_record = {
            'date': current_data['date'],
            'type': '观望',
            'price': current_price,
            'quantity': 0,
            'reason': reason,
            'cash': st.session_state.total_cash,
            'total_position': st.session_state.current_position
        }
    
    st.session_state.trade_records.append(trade_record)
    
    # AI分析
    analyzer = AIAnalyzer()
    df_slice = st.session_state.kline_data.iloc[:st.session_state.current_date_index + 1]
    ai_comment = analyzer.analyze_trade_signal(df_slice, trade_type, reason)
    trade_record['ai_comment'] = ai_comment
    
    return True, f"{trade_type}成功"

def calculate_performance():
    """计算交易表现"""
    if not st.session_state.trade_records:
        return {}
    
    trades = []
    for i, record in enumerate(st.session_state.trade_records):
        if record['type'] == '买入':
            # 寻找对应的卖出
            for j in range(i + 1, len(st.session_state.trade_records)):
                if st.session_state.trade_records[j]['type'] == '卖出':
                    profit = calculate_profit(
                        st.session_state.trade_records[j]['price'],
                        record['price'],
                        record['quantity']
                    )
                    trades.append({
                        'buy_date': record['date'],
                        'sell_date': st.session_state.trade_records[j]['date'],
                        'buy_price': record['price'],
                        'sell_price': st.session_state.trade_records[j]['price'],
                        'quantity': record['quantity'],
                        'profit': profit
                    })
                    break
    
    analyzer = AIAnalyzer()
    return analyzer.analyze_trading_performance(trades)

def save_training_results(db):
    """保存训练结果"""
    if not st.session_state.training_id:
        return False
    
    performance = calculate_performance()
    
    # 保存训练记录
    success = db.save_training_record(
        training_id=st.session_state.training_id,
        code=st.session_state.current_stock,
        start_date=st.session_state.training_start_date,
        end_date=st.session_state.kline_data.iloc[st.session_state.current_date_index]['date'],
        total_profit=performance.get('total_profit', 0),
        total_trades=performance.get('total_trades', 0),
        win_rate=performance.get('win_rate', 0),
        max_drawdown=performance.get('max_drawdown', 0)
    )
    
    # 保存交易记录
    for record in st.session_state.trade_records:
        db.save_trade_record(
            training_id=st.session_state.training_id,
            trade_date=record['date'],
            code=st.session_state.current_stock,
            trade_type=record['type'],
            price=record['price'],
            quantity=record['quantity'],
            position=record['position'],
            reason=record.get('reason', ''),
            ai_comment=record.get('ai_comment', '')
        )
    
    return success

def main():
    """主函数"""
    st.header("🎯 K线训练")
    
    # 添加CSS注入，移除容器宽度限制，最大化K线图宽度
    st.markdown("""
    <style>
    .main .block-container {
        max-width: 100% !important;
        padding-top: 1rem;
        padding-right: 1rem;
        padding-left: 1rem;
        padding-bottom: 1rem;
    }
    </style>
    """, unsafe_allow_html=True)
    
    db = StockDatabase()
    init_session_state()
    
    # 训练设置
    st.session_state.initial_cash = st.number_input("初始资金", min_value=10000, max_value=1000000, value=100000)
    
    if st.button("🚀 开始新训练", type="primary"):
        with st.spinner("正在准备训练数据..."):
            if start_new_training(db):
                st.success(f"开始训练！股票代码：{st.session_state.current_stock}")
    
    if st.session_state.training_id:
        # 显示当前状态
        st.subheader(f"训练进度")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("当前日期", st.session_state.kline_data.iloc[st.session_state.current_date_index]['date'])
        with col2:
            st.metric("当前价格", f"{st.session_state.kline_data.iloc[st.session_state.current_date_index]['close']:.2f}")
        with col3:
            st.metric("当前仓位", f"{st.session_state.current_position}股")
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("预加载K线", len(st.session_state.kline_data))
        with col2:
            st.metric("显示K线", st.session_state.display_days)
        with col3:
            st.metric("训练K线", st.session_state.remaining_days)
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("剩余资金", f"{st.session_state.total_cash:.2f}")
        with col2:
            total_value = st.session_state.total_cash + st.session_state.current_position * st.session_state.kline_data.iloc[st.session_state.current_date_index]['close']
            st.metric("总市值", f"{total_value:.2f}")
        with col3:
            # 计算收益率
            profit = total_value - st.session_state.initial_cash
            profit_rate = (profit / st.session_state.initial_cash) * 100
            if profit >= 0:
                st.metric("收益率", f"+{profit_rate:.2f}%", f"+{profit:.2f}")
            else:
                st.metric("收益率", f"{profit_rate:.2f}%", f"{profit:.2f}")
        
        # K线图类型切换
        show_type = st.radio("图表类型", ['日线', '周线'], horizontal=True, key="show_type_radio")
        
        # 根据图表类型设置显示数据和索引
        if show_type == '日线':
            display_data = st.session_state.kline_data
            current_index = st.session_state.current_date_index
        else:
            # 周线模式：根据当前日线日期找到对应的周线索引
            display_data = st.session_state.weekly_data
            current_date = st.session_state.kline_data.iloc[st.session_state.current_date_index]['date']
            current_index = get_weekly_index(display_data, current_date)
        
        # 创建交易点标记
        trade_points = []
        for record in st.session_state.trade_records:
            if record['type'] in ['买入', '卖出']:
                trade_points.append({
                    'date': record['date'],
                    'price': record['price'],
                    'type': record['type']
                })
        
        fig_kline = create_kline_chart(
            display_data.iloc[:current_index + 1],
            current_index=current_index,
            trade_points=trade_points,
            training_start_index=st.session_state.training_start_index
        )
        st.plotly_chart(fig_kline, use_container_width=True)
        
        # 技术指标图表
        col1, col2 = st.columns(2)
        with col1:
            fig_macd = create_macd_chart(display_data.iloc[:current_index + 1])
            st.plotly_chart(fig_macd, use_container_width=True)
        
        with col2:
            fig_rsi = create_rsi_chart(display_data.iloc[:current_index + 1])
            st.plotly_chart(fig_rsi, use_container_width=True)
        
        # 交易操作
        st.subheader("交易操作")
        
        trade_type = st.selectbox("操作类型", ['买入', '卖出', '观望'])
        
        reason = st.text_area("交易理由（必填）", height=100, placeholder="请输入您的交易理由...")
        
        if st.button("💡 提交操作"):
            success, message = execute_trade(trade_type, reason)
            if success:
                st.success(message)
                
                # 显示AI分析
                if 'ai_comment' in st.session_state.trade_records[-1]:
                    st.markdown("### 🤖 AI分析")
                    st.info(st.session_state.trade_records[-1]['ai_comment'])
                
                # 移动到下一天
                if st.session_state.current_date_index < len(st.session_state.kline_data) - 1:
                    st.session_state.current_date_index += 1
                    st.rerun()
                else:
                    st.success("训练完成！")
                    save_training_results(db)
                    
                    # 显示交易表现
                    performance = calculate_performance()
                    analyzer = AIAnalyzer()
                    st.markdown("### 📊 训练总结")
                    st.info(analyzer.generate_summary(performance))
                    
                    # 显示交易记录
                    st.markdown("### 📝 交易记录")
                    if st.session_state.trade_records:
                        trade_df = pd.DataFrame(st.session_state.trade_records)
                        st.dataframe(trade_df, use_container_width=True)
            else:
                st.error(message)
        
        # 复盘功能
        if st.button("🔍 查看完整K线（复盘）"):
            st.markdown("### 复盘模式 - 完整K线图")
            
            # 创建完整的K线图
            fig_full = create_kline_chart(
                st.session_state.kline_data, 
                trade_points=trade_points,
                training_start_index=st.session_state.training_start_index
            )
            st.plotly_chart(fig_full, use_container_width=True)
            
            # 显示交易记录详情
            st.markdown("### 交易详情")
            if st.session_state.trade_records:
                for i, record in enumerate(st.session_state.trade_records):
                    st.markdown(f"#### 交易 {i + 1}: {record['type']}")
                    st.write(f"- 日期: {record['date']}")
                    st.write(f"- 价格: {record['price']:.2f}")
                    st.write(f"- 数量: {record['quantity']}")
                    st.write(f"- 仓位: {record['position']:.2f}")
                    st.write(f"- 理由: {record.get('reason', '无')}")
                    if 'ai_comment' in record:
                        st.write(f"- AI点评: {record['ai_comment']}")
                    st.markdown("---")
    
    # 训练历史
    st.markdown("---")
    st.subheader("📋 训练历史")
    
    training_history = db.get_training_records(limit=50)
    if not training_history.empty:
        st.dataframe(training_history[['training_id', 'code', 'start_date', 'end_date', 'total_profit', 'win_rate']], use_container_width=True)
        
        # 查看历史训练详情
        selected_training = st.selectbox("选择训练记录查看详情", training_history['training_id'].tolist())
        if selected_training:
            trade_records = db.get_trade_records(selected_training)
            if not trade_records.empty:
                st.markdown("### 历史交易记录")
                st.dataframe(trade_records, use_container_width=True)

if __name__ == "__main__":
    main()