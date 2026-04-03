"""缠论买卖点识别模块 - 基于背驰逻辑"""
import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Optional


ZHONGSHU_THRESHOLD = 1.0
PRICE_DIFF_THRESHOLD = 2.0


@dataclass
class SignalPoint:
    date: str
    price: float
    signal_type: str
    level: int
    fenxing_index: int
    trend_index: int
    kline_index: int
    macd_info: Dict
    is_new_low: bool = True
    yangxian_pct: float = 0.0

    def to_dict(self) -> Dict:
        t = f"{self.level}"
        t = t.replace('1', '一').replace('2', '二').replace('3', '三')
        t = t + ('买' if self.signal_type == 'buy' else '卖')
        return {
            'date': self.date, 'price': self.price, 'type': t,
            '是否新低': '是' if self.is_new_low else '否',
            '次日阳线涨幅%': f"{self.yangxian_pct:.2f}%",
            **self.macd_info
        }


def extract_trend_data(trend: Dict, df) -> Dict:
    """提取趋势段的数据"""
    s, e = trend['start_kline_idx'], trend['end_kline_idx']
    seg = df.iloc[s:e+1]
    m = seg['macd_hist']

    greens = m[m < 0]
    reds = m[m > 0]

    g_area = greens.sum() if len(greens) > 0 else 0
    r_area = reds.sum() if len(reds) > 0 else 0
    g_h = greens.min() if len(greens) > 0 else 0
    r_h = reds.max() if len(reds) > 0 else 0

    sd = pd.to_datetime(trend['start_fenxing'][2]['date'])
    ed = pd.to_datetime(trend['end_fenxing'][2]['date'])
    days = max((ed - sd).days, 1)

    sp = trend['start_fenxing'][2]['high']
    ep = trend['end_fenxing'][2]['low']

    if trend['type'] == '下降':
        force = (sp - ep) / days
    else:
        force = (trend['end_fenxing'][2]['high'] - sp) / days

    return {
        'prices': seg['close'],
        'highs': seg['high'],
        'lows': seg['low'],
        'volume': seg['volume'],
        'dif': seg['dif'],
        'dea': seg['dea'],
        'macd_hist': m,
        'dates': seg['date'],
        'start_idx': s,
        'end_idx': e,
        'price_high': seg['high'].max(),
        'price_low': seg['low'].min(),
        'macd_high': m.max(),
        'macd_low': m.min(),
        'green_area': g_area,
        'red_area': r_area,
        'green_bar_height': g_h,
        'red_bar_height': r_h,
        'force': force,
        'days': days
    }


def detect_divergence(curr: Dict, prev: Optional[Dict], direction: str = 'bottom') -> Optional[Dict]:
    """检测背驰"""
    if prev is None:
        return None

    if direction == 'bottom':
        pl = abs(curr['price_low'] - prev['price_low']) / prev['price_low'] * 100
        in_z = pl < ZHONGSHU_THRESHOLD

        cg = curr['green_area'] < 0
        pg = prev['green_area'] < 0

        if not cg and not pg:
            return None

        cond_a = cond_b = cond_c = False

        if cg and pg:
            cond_a = abs(curr['green_area']) < abs(prev['green_area'])
            cond_b = abs(curr['green_bar_height']) < abs(prev['green_bar_height'])

        if prev['force'] > 0 and curr['force'] < 0:
            cond_c = abs(curr['force']) < abs(prev['force'])

        if not (cond_a or cond_b or cond_c):
            return None

        return {
            'has_divergence': True,
            'in_zhongshu': in_z,
            'price_diff_pct': pl,
            'cond_a': cond_a,
            'cond_b': cond_b,
            'cond_c': cond_c,
            'current_green': curr['green_area'],
            'prev_green': prev['green_area'],
            'current_green_h': curr['green_bar_height'],
            'prev_green_h': prev['green_bar_height'],
            'current_force': curr['force'],
            'prev_force': prev['force'],
            'days': curr['days'],
            'price_new_low': curr['price_low'] < prev['price_low']
        }
    else:
        ph = abs(curr['price_high'] - prev['price_high']) / prev['price_high'] * 100
        in_z = ph < PRICE_DIFF_THRESHOLD
        cr = curr['red_area'] > 0
        pr = prev['red_area'] > 0

        if not cr and not pr:
            return None

        cond_a = cond_b = cond_c = False

        if cr and pr:
            cond_a = curr['red_area'] < prev['red_area']
            cond_b = curr['red_bar_height'] < prev['red_bar_height']

        if prev['force'] > 0 and curr['force'] > 0:
            cond_c = abs(curr['force']) < abs(prev['force'])

        if not (cond_a or cond_b or cond_c):
            return None

        return {
            'has_divergence': True,
            'in_zhongshu': in_z,
            'price_diff_pct': ph,
            'cond_a': cond_a,
            'cond_b': cond_b,
            'cond_c': cond_c,
            'current_red': curr['red_area'],
            'prev_red': prev['red_area'],
            'current_red_h': curr['red_bar_height'],
            'prev_red_h': prev['red_bar_height'],
            'current_force': curr['force'],
            'prev_force': prev['force'],
            'days': curr['days'],
            'price_new_high': curr['price_high'] > prev['price_high']
        }


def calculate_yangxian_pct(df: pd.DataFrame, end_idx: int, price: float) -> float:
    """计算次日涨幅（用收盘价计算）"""
    next_idx = end_idx + 1
    if next_idx >= len(df):
        return 0.0

    next_day = df.iloc[next_idx]
    next_close = next_day['close']
    next_open = next_day['open']

    if next_close > next_open:
        yangxian_pct = (next_close - price) / price * 100
        return yangxian_pct
    return 0.0


def identify_first_buy(trends: List[Dict], df, klines) -> List[SignalPoint]:
    """识别一买

    逻辑：下降趋势ABCD，最低点abcd

    比较步骤：
    1. 从第二个下降趋势开始
    2. 当前趋势(curr)和前一个趋势(prev)比较
    3. 如果curr和prev差距<1%（形成中枢），继续往前找
    4. 如果curr和prev差距>1%，检查prev和再前一个是否形成中枢
       - 如果形成中枢，继续往前找
       - 如果不形成中枢，使用prev进行比较
    5. 背驰的底分型创新低 = 真1买
    6. 背驰的底分型不创新低 = 伪1买
    """
    results = []
    downs = [t for t in trends if t['type'] == '下降']

    for i, t in enumerate(downs):
        if i == 0:
            continue

        td = extract_trend_data(t, df)
        ef = t['end_fenxing']

        if ef[1] != '底':
            continue

        curr_low = ef[2]['low']

        pd_t = None
        compare_idx = i - 1

        while compare_idx >= 0:
            prev_low = downs[compare_idx]['end_fenxing'][2]['low']
            low_diff_pct = abs(curr_low - prev_low) / prev_low * 100

            if low_diff_pct > ZHONGSHU_THRESHOLD:
                check_idx = compare_idx - 1
                while check_idx >= 0:
                    check_low = downs[check_idx]['end_fenxing'][2]['low']
                    check_diff = abs(prev_low - check_low) / check_low * 100
                    if check_diff < ZHONGSHU_THRESHOLD:
                        compare_idx = check_idx
                        prev_low = check_low
                        check_idx -= 1
                    else:
                        break
                pd_t = extract_trend_data(downs[compare_idx], df)
                break

            compare_idx -= 1

        div = detect_divergence(td, pd_t, 'bottom')

        if div and div['has_divergence']:
            is_new_low = div['price_new_low']
            close_price = df.iloc[td['end_idx']]['close']
            yangxian_pct = calculate_yangxian_pct(df, td['end_idx'], close_price)

            cond_desc = []
            if div['cond_a']:
                cond_desc.append("绿柱面积减少")
            if div['cond_b']:
                cond_desc.append("绿柱高度降低")
            if div['cond_c']:
                cond_desc.append("下跌力度减弱")

            results.append(SignalPoint(
                date=str(ef[2]['date'])[:10],
                price=close_price,
                signal_type='buy',
                level=1,
                fenxing_index=ef[0],
                trend_index=t['index'],
                kline_index=td['end_idx'],
                macd_info={
                    '是否背驰': '是' if cond_desc else '否',
                    '背驰详情': '，'.join(cond_desc) if cond_desc else '无',
                    '在中枢内': '是' if div['in_zhongshu'] else '否',
                    '价格差%': f"{div['price_diff_pct']:.2f}%",
                    '绿柱面积': f"{td['green_area']:.4f}",
                    '绿柱高度': f"{td['green_bar_height']:.4f}",
                    '力度': f"{td['force']:.4f}",
                    '面积A': '是' if div['cond_a'] else '否',
                    '面积B': '是' if div['cond_b'] else '否',
                    '面积C': '是' if div['cond_c'] else '否',
                },
                is_new_low=is_new_low,
                yangxian_pct=yangxian_pct
            ))

    return results


def identify_second_buy(trends: List[Dict], df, first_buys: List[SignalPoint]) -> List[SignalPoint]:
    """识别二买"""
    results = []

    for fb in first_buys:
        fb_date = fb.date
        fb_price = fb.price
        fb_idx = fb.trend_index

        for i, t in enumerate(trends):
            if t['index'] <= fb_idx:
                continue

            if t['type'] == '上升':
                continue

            if t['type'] == '下降':
                td = extract_trend_data(t, df)
                cl = t['end_fenxing'][2]['low']
                cl_date = str(t['end_fenxing'][2]['date'])[:10]

                if cl >= fb_price and cl_date != fb_date:
                    close_price = df.iloc[td['end_idx']]['close']
                    yangxian_pct = calculate_yangxian_pct(df, td['end_idx'], close_price)

                    results.append(SignalPoint(
                        date=cl_date,
                        price=close_price,
                        signal_type='buy',
                        level=2,
                        fenxing_index=t['end_fenxing'][0],
                        trend_index=t['index'],
                        kline_index=td['end_idx'],
                        macd_info={
                            '对应1买日期': fb_date,
                            '对应1买价格': f"{fb_price:.2f}",
                            '回调幅度%': f"{(cl - fb_price) / fb_price * 100:.2f}%",
                            '绿柱面积': f"{td['green_area']:.4f}",
                            '力度': f"{td['force']:.4f}",
                        },
                        is_new_low=False,
                        yangxian_pct=yangxian_pct
                    ))
                break

    return results
