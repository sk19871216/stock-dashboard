"""缠论分析器主模块"""
import pandas as pd
from typing import Dict, List, Optional

from .macd import add_macd_to_dataframe
from .fenxing_with_macd import find_fenxing, merge_same_type, extract_trends, pad_fenxing
from .chanlun_signals import identify_first_buy, identify_second_buy


class ChanlunAnalyzer:
    """缠论分析器"""

    def __init__(self):
        pass

    def analyze(self, kline_data: pd.DataFrame, code: str = '') -> Dict:
        """
        分析股票K线数据

        Args:
            kline_data: K线数据DataFrame
            code: 股票代码

        Returns:
            分析结果字典
        """
        try:
            if kline_data.empty or len(kline_data) < 30:
                return {
                    'success': False,
                    'error': '数据不足，无法进行缠论分析（至少需要30条数据）',
                    'data_count': len(kline_data) if not kline_data.empty else 0,
                    'fenxing_count': 0,
                    'trend_count': 0,
                    'first_buys': [],
                    'second_buys': [],
                    'fenxing_list': []
                }

            df = kline_data.copy()
            df = add_macd_to_dataframe(df)
            df = df.reset_index(drop=True)

            klines = []
            for idx, row in df.iterrows():
                klines.append({
                    'date': row['date'],
                    'open': float(row['open']),
                    'high': float(row['high']),
                    'low': float(row['low']),
                    'close': float(row['close']),
                    'volume': float(row['volume']) if pd.notna(row.get('volume', None)) else 0,
                    'pos': idx
                })

            processed, fenxing_list = find_fenxing(klines)
            merged = merge_same_type(fenxing_list)

            if len(merged) < 2:
                return {
                    'success': True,
                    'data_count': len(df),
                    'fenxing_count': len(merged),
                    'trend_count': 0,
                    'first_buys': [],
                    'second_buys': [],
                    'fenxing_list': merged,
                    'error': None
                }

            padded = pad_fenxing(merged, klines)

            trends_data = []
            trends_raw = extract_trends(padded)
            for i, (trend_type, start_fx, end_fx) in enumerate(trends_raw):
                start_idx = start_fx[2]['pos'] if isinstance(start_fx[2], dict) and 'pos' in start_fx[2] else start_fx[0]
                end_idx = end_fx[2]['pos'] if isinstance(end_fx[2], dict) and 'pos' in end_fx[2] else end_fx[0]
                trends_data.append({
                    'index': i,
                    'type': trend_type,
                    'start_fenxing': start_fx,
                    'end_fenxing': end_fx,
                    'start_kline_idx': start_idx,
                    'end_kline_idx': end_idx
                })

            first_buys_raw = identify_first_buy(trends_data, df, klines)
            second_buys_raw = identify_second_buy(trends_data, df, first_buys_raw)

            first_buys = []
            for fb in first_buys_raw:
                first_buys.append(fb.to_dict())

            second_buys = []
            for sb in second_buys_raw:
                second_buys.append(sb.to_dict())

            fenxing_output = []
            for idx, (pos, ftype, kline) in enumerate(merged):
                fenxing_output.append((idx, ftype, kline))

            return {
                'success': True,
                'data_count': len(df),
                'fenxing_count': len(merged),
                'trend_count': len(trends_data),
                'first_buys': first_buys,
                'second_buys': second_buys,
                'fenxing_list': fenxing_output,
                'error': None
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'data_count': 0,
                'fenxing_count': 0,
                'trend_count': 0,
                'first_buys': [],
                'second_buys': [],
                'fenxing_list': []
            }

    @staticmethod
    def get_buy_signals_summary(result: Dict) -> pd.DataFrame:
        """
        从分析结果生成买点信号汇总表格

        Args:
            result: analyze() 返回的分析结果

        Returns:
            买点信号汇总DataFrame
        """
        all_signals = []

        for fb in result.get('first_buys', []):
            all_signals.append({
                '序号': len(all_signals) + 1,
                '买点类型': '一买',
                '日期': fb.get('date', ''),
                '价格': fb.get('price', 0),
                '是否新低': fb.get('是否新低', '否'),
                '次日阳线涨幅%': fb.get('次日阳线涨幅%', '0%'),
                '是否背驰': fb.get('是否背驰', '未知')
            })

        for sb in result.get('second_buys', []):
            all_signals.append({
                '序号': len(all_signals) + 1,
                '买点类型': '二买',
                '日期': sb.get('date', ''),
                '价格': sb.get('price', 0),
                '是否新低': '否',
                '次日阳线涨幅%': sb.get('次日阳线涨幅%', '0%'),
                '是否背驰': 'N/A'
            })

        if not all_signals:
            return pd.DataFrame()

        return pd.DataFrame(all_signals)
