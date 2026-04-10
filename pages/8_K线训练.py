import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import random
import uuid
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from utils.database import StockDatabase
from utils.technical_analysis import add_technical_indicators, calculate_profit
from ai.analyzer import AIAnalyzer

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

def get_random_stock(db):
    """随机获取一只股票"""
    all_codes = db.get_all_stock_codes()
    if not all_codes:
        return None
    
    while True:
        code = random.choice(all_codes)
        kline_data = db.get_kline_data(code, days=200)
        if len(kline_data) >= 100:
            return code, kline_data

def calculate_position_size(cash, price, position_ratio):
    """计算仓位大小"""
    max_position_value = cash * position_ratio
    quantity = max_position_value / price
    return int(quantity)

def create_kline_chart(df, current_index=None, trade_points=None):
    """创建K线图"""
    fig = go.Figure()
    
    # 添加K线
    fig.add_trace(go.Candlestick(
        x=df['date'],
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close'],
        name='K线',
        increasing_line_color='red',
        decreasing_line_color='green'
    ))
    
    # 添加均线
    for ma in ['MA5', 'MA10', 'MA20']:
        if ma in df.columns:
            fig.add_trace(go.Scatter(
                x=df['date'],
                y=df[ma],
                mode='lines',
                name=ma,
                line=dict(width=1)
            ))
    
    # 添加成交量
    fig.add_trace(go.Bar(
        x=df['date'],
        y=df['volume'],
        name='成交量',
        yaxis='y2',
        opacity=0.3,
        marker_color='blue'
    ))
    
    # 添加买卖点标记
    if trade_points:
        buy_dates = [point['date'] for point in trade_points if point['type'] == '买入']
        buy_prices = [point['price'] for point in trade_points if point['type'] == '买入']
        
        sell_dates = [point['date'] for point in trade_points if point['type'] == '卖出']
        sell_prices = [point['price'] for point in trade_points if point['type'] == '卖出']
        
        fig.add_trace(go.Scatter(
            x=buy_dates,
            y=buy_prices,
            mode='markers',
            name='买入',
            marker=dict(color='red', size=8, symbol='triangle-up')
        ))
        
        fig.add_trace(go.Scatter(
            x=sell_dates,
            y=sell_prices,
            mode='markers',
            name='卖出',
            marker=dict(color='green', size=8, symbol='triangle-down')
        ))
    
    # 设置布局
    fig.update_layout(
        title='K线图',
        xaxis_title='日期',
        yaxis_title='价格',
        yaxis2=dict(
            title='成交量',
            overlaying='y',
            side='right',
            showgrid=False
        ),
        legend=dict(
            orientation='h',
            yanchor='bottom',
            y=1.02,
            xanchor='right',
            x=1
        ),
        hovermode='x unified',
        height=600
    )
    
    # 如果指定了当前日期，添加一条竖线
    if current_index is not None and current_index < len(df):
        current_date = df.iloc[current_index]['date']
        fig.add_vline(
            x=current_date,
            line_dash='dash',
            line_color='gray',
            annotation_text='当前日期',
            annotation_position='top'
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
    code, kline_data = get_random_stock(db)
    if not code:
        st.error("无法获取股票数据，请确保数据已更新")
        return False
    
    # 添加技术指标
    df, weekly_df = add_technical_indicators(kline_data, include_weekly=True)
    
    # 随机选择训练起始点（至少保留60天数据用于分析）
    min_start_index = 60
    max_start_index = len(df) - 60
    if max_start_index <= min_start_index:
        st.error("数据不足，无法开始训练")
        return False
    
    start_index = random.randint(min_start_index, max_start_index)
    
    # 初始化训练状态
    st.session_state.training_id = str(uuid.uuid4())
    st.session_state.current_stock = code
    st.session_state.kline_data = df
    st.session_state.weekly_data = weekly_df
    st.session_state.current_date_index = start_index
    st.session_state.current_position = 0
    st.session_state.trade_records = []
    st.session_state.total_cash = st.session_state.initial_cash
    st.session_state.training_start_date = df.iloc[start_index]['date']
    
    return True

def execute_trade(trade_type, position_ratio, reason):
    """执行交易"""
    if not st.session_state.training_id or not st.session_state.kline_data:
        return False, "请先开始训练"
    
    current_data = st.session_state.kline_data.iloc[st.session_state.current_date_index]
    current_price = current_data['close']
    
    if trade_type == '买入':
        # 计算可买数量
        position_value = st.session_state.total_cash * position_ratio
        quantity = calculate_position_size(st.session_state.total_cash, current_price, position_ratio)
        
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
            'position': position_ratio,
            'reason': reason,
            'cash': st.session_state.total_cash,
            'total_position': st.session_state.current_position
        }
        
    elif trade_type == '卖出':
        # 计算可卖数量
        sell_quantity = int(st.session_state.current_position * position_ratio)
        
        if sell_quantity <= 0:
            return False, "没有持仓"
        
        # 执行卖出
        proceeds = sell_quantity * current_price
        st.session_state.total_cash += proceeds
        st.session_state.current_position -= sell_quantity
        
        # 记录交易
        trade_record = {
            'date': current_data['date'],
            'type': '卖出',
            'price': current_price,
            'quantity': sell_quantity,
            'position': position_ratio,
            'reason': reason,
            'cash': st.session_state.total_cash,
            'total_position': st.session_state.current_position
        }
        
    elif trade_type == '观望':
        # 记录观望
        trade_record = {
            'date': current_data['date'],
            'type': '观望',
            'price': current_price,
            'quantity': 0,
            'position': 0,
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
    
    db = StockDatabase()
    init_session_state()
    
    # 训练设置
    col1, col2 = st.columns(2)
    with col1:
        st.session_state.max_position = st.number_input("最大仓位（层）", min_value=1, max_value=10, value=3)
    with col2:
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
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("剩余资金", f"{st.session_state.total_cash:.2f}")
        with col2:
            total_value = st.session_state.total_cash + st.session_state.current_position * st.session_state.kline_data.iloc[st.session_state.current_date_index]['close']
            st.metric("总市值", f"{total_value:.2f}")
        
        # K线图类型切换
        st.session_state.show_type = st.radio("图表类型", ['日线', '周线'], horizontal=True)
        
        # 显示K线图
        display_data = st.session_state.kline_data if st.session_state.show_type == '日线' else st.session_state.weekly_data
        
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
            display_data.iloc[:st.session_state.current_date_index + 1],
            current_index=st.session_state.current_date_index,
            trade_points=trade_points
        )
        st.plotly_chart(fig_kline, use_container_width=True)
        
        # 技术指标图表
        col1, col2 = st.columns(2)
        with col1:
            fig_macd = create_macd_chart(display_data.iloc[:st.session_state.current_date_index + 1])
            st.plotly_chart(fig_macd, use_container_width=True)
        
        with col2:
            fig_rsi = create_rsi_chart(display_data.iloc[:st.session_state.current_date_index + 1])
            st.plotly_chart(fig_rsi, use_container_width=True)
        
        # 交易操作
        st.subheader("交易操作")
        
        trade_type = st.selectbox("操作类型", ['买入', '卖出', '观望'])
        
        if trade_type in ['买入', '卖出']:
            position_options = {
                1: 1/st.session_state.max_position,
                2: 2/st.session_state.max_position,
                3: 1.0
            }
            
            position_label = st.radio("仓位", ['1/3', '2/3', '全仓'], horizontal=True)
            position_ratio = position_options[int(position_label.split('/')[0])]
        else:
            position_ratio = 0
        
        reason = st.text_area("交易理由", height=100)
        
        if st.button("💡 提交操作"):
            success, message = execute_trade(trade_type, position_ratio, reason)
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
        
        # 复盘功能
        if st.button("🔍 查看完整K线（复盘）"):
            st.markdown("### 复盘模式 - 完整K线图")
            
            # 创建完整的K线图
            fig_full = create_kline_chart(st.session_state.kline_data, trade_points=trade_points)
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