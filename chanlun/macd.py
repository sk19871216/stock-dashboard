"""
MACD指标计算模块
提供MACD、DIF、DEA的计算以及面积和量柱高度分析
"""

import pandas as pd
import numpy as np


def calculate_ema(prices, period):
    """
    计算指数移动平均线 (EMA)
    """
    return prices.ewm(span=period, adjust=False).mean()


def calculate_macd(prices, fast=12, slow=26, signal=9):
    """
    计算MACD指标
    """
    ema_fast = calculate_ema(prices, fast)
    ema_slow = calculate_ema(prices, slow)

    dif = ema_fast - ema_slow
    dea = calculate_ema(dif, signal)
    macd_hist = (dif - dea) * 2

    return dif, dea, macd_hist


def calculate_macd_area(macd_hist, volumes):
    """
    计算MACD面积（考虑成交量）
    """
    area = (macd_hist.abs() * volumes).sum()
    return area


def calculate_macd_area_simple(macd_hist):
    """
    计算MACD面积（简单求和）
    """
    return macd_hist.abs().sum()


def get_max_bar_height(macd_hist):
    """
    获取最大量柱高度
    """
    return macd_hist.abs().max()


def get_trend_macd_metrics(dif, dea, macd_hist, volumes, kline_indices):
    """
    获取趋势段的MACD指标
    """
    segment_macd = macd_hist.iloc[kline_indices]
    segment_volumes = volumes.iloc[kline_indices]

    area = calculate_macd_area(segment_macd, segment_volumes)
    max_height = get_max_bar_height(segment_macd)

    return {
        'area': area,
        'max_height': max_height,
        'avg_height': segment_macd.abs().mean(),
        'bar_count': len(segment_macd)
    }


def add_macd_to_dataframe(df):
    """
    为DataFrame添加MACD相关列
    """
    df = df.copy()
    df['dif'], df['dea'], df['macd_hist'] = calculate_macd(df['close'])
    return df


def compare_trends(trend1_metrics, trend2_metrics):
    """
    比较两个趋势段的MACD指标
    """
    result = {}

    if trend1_metrics['area'] > 0:
        result['area_change_pct'] = ((trend2_metrics['area'] - trend1_metrics['area'])
                                     / trend1_metrics['area'] * 100)
    else:
        result['area_change_pct'] = 0

    if trend1_metrics['max_height'] > 0:
        result['height_change_pct'] = ((trend2_metrics['max_height'] - trend1_metrics['max_height'])
                                       / trend1_metrics['max_height'] * 100)
    else:
        result['height_change_pct'] = 0

    return result


def detect_divergence(trend1_metrics, trend2_metrics, trend_type):
    """
    检测背离
    """
    area_change = trend2_metrics['area'] - trend1_metrics['area']
    height_change = trend2_metrics['max_height'] - trend1_metrics['max_height']

    if trend_type == '下降':
        if area_change < 0 and height_change < 0:
            return '顶背离 (动能减弱)'
        elif area_change > 0 and height_change > 0:
            return '同步下跌 (动能增强)'
        else:
            return '无明显背离'
    else:
        if area_change > 0 and height_change > 0:
            return '底背离 (动能增强)'
        elif area_change < 0 and height_change < 0:
            return '同步反弹 (动能减弱)'
        else:
            return '无明显背离'
