import pandas as pd
import numpy as np

def calculate_ma(df, periods=[5, 10, 20]):
    """计算均线"""
    df = df.copy()
    for period in periods:
        df[f'MA{period}'] = df['close'].rolling(window=period).mean()
    return df

def calculate_macd(df, fast_period=12, slow_period=26, signal_period=9):
    """计算MACD指标"""
    df = df.copy()
    
    exp1 = df['close'].ewm(span=fast_period, adjust=False).mean()
    exp2 = df['close'].ewm(span=slow_period, adjust=False).mean()
    
    df['MACD'] = exp1 - exp2
    df['Signal'] = df['MACD'].ewm(span=signal_period, adjust=False).mean()
    df['Histogram'] = df['MACD'] - df['Signal']
    
    return df

def calculate_rsi(df, period=14):
    """计算RSI指标"""
    df = df.copy()
    
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    return df

def calculate_volatility(df, period=20):
    """计算波动率"""
    df = df.copy()
    df['volatility'] = df['close'].rolling(window=period).std() / df['close'].rolling(window=period).mean() * 100
    return df

def calculate_bollinger_bands(df, period=20, std_dev=2):
    """计算布林带"""
    df = df.copy()
    
    df['MA20'] = df['close'].rolling(window=period).mean()
    df['Upper'] = df['MA20'] + (df['close'].rolling(window=period).std() * std_dev)
    df['Lower'] = df['MA20'] - (df['close'].rolling(window=period).std() * std_dev)
    
    return df

def resample_to_weekly(df):
    """将日线数据转换为周线数据"""
    df = df.copy()
    df['date'] = pd.to_datetime(df['date'])
    
    weekly_df = df.set_index('date').resample('W').agg({
        'open': 'first',
        'close': 'last',
        'high': 'max',
        'low': 'min',
        'volume': 'sum',
        'amount': 'sum'
    }).reset_index()
    
    weekly_df['date'] = weekly_df['date'].dt.strftime('%Y-%m-%d')
    
    return weekly_df

def add_technical_indicators(df, include_weekly=False):
    """添加所有技术指标"""
    df = df.copy()
    
    # 计算基本指标
    df = calculate_ma(df)
    df = calculate_macd(df)
    df = calculate_rsi(df)
    df = calculate_volatility(df)
    df = calculate_bollinger_bands(df)
    
    # 计算涨跌幅
    df['pct_change'] = df['close'].pct_change() * 100
    
    if include_weekly:
        weekly_df = resample_to_weekly(df)
        weekly_df = calculate_ma(weekly_df)
        weekly_df = calculate_macd(weekly_df)
        weekly_df = calculate_rsi(weekly_df)
        return df, weekly_df
    
    return df

def calculate_position_size(cash, price, risk_percent=0.01, stop_loss_pct=0.02):
    """计算仓位大小"""
    risk_amount = cash * risk_percent
    position_size = risk_amount / (price * stop_loss_pct)
    return int(position_size)

def calculate_profit(current_price, entry_price, quantity):
    """计算盈亏"""
    return (current_price - entry_price) * quantity

def calculate_max_drawdown(equity_curve):
    """计算最大回撤"""
    running_max = equity_curve.cummax()
    drawdown = (equity_curve - running_max) / running_max * 100
    return drawdown.min()

def calculate_win_rate(trades):
    """计算胜率"""
    if len(trades) == 0:
        return 0
    winning_trades = sum(1 for trade in trades if trade['profit'] > 0)
    return winning_trades / len(trades) * 100