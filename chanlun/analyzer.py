"""
缠论分析包装器
提供简化的分析接口，方便在 Streamlit 中使用
"""

import pandas as pd
import sys
from pathlib import Path

from .macd import add_macd_to_dataframe
from .fenxing_with_macd import find_fenxing, merge_same_type, extract_trends, pad_fenxing
from .chanlun_signals import identify_first_buy, identify_second_buy


class ChanlunAnalyzer:
    """缠论分析器"""

    def __init__(self):
        pass

    def analyze(self, df: pd.DataFrame, stock_code: str = None) -> dict:
        """
        分析单只股票的缠论信号

        Args:
            df: 包含 K线数据的 DataFrame
                必须包含列: date, open, close, high, low, volume
            stock_code: 股票代码（可选）

        Returns:
            dict: 包含分析结果的字典
        """
        if df is None or df.empty:
            return {
                'success': False,
                'error': '数据为空'
            }

        if len(df) < 30:
            return {
                'success': False,
                'error': f'数据不足，需要至少30条数据，当前只有{len(df)}条'
            }

        try:
            df_sorted = df.sort_values('date').reset_index(drop=True)

            df_with_macd = add_macd_to_dataframe(df_sorted)

            klines = df_sorted[['date', 'open', 'close', 'high', 'low', 'volume']].to_dict('records')

            processed, filtered = find_fenxing(klines)

            merged = merge_same_type(filtered)

            padded_merged = pad_fenxing(merged, klines)

            trends_raw = extract_trends(padded_merged)

            trends = []
            for i, t in enumerate(trends_raw):
                start_idx = t[1][0]
                end_idx = t[2][0]
                trends.append({
                    'index': i + 1,
                    'type': t[0],
                    'start_fenxing': t[1],
                    'end_fenxing': t[2],
                    'start_kline_idx': start_idx,
                    'end_kline_idx': end_idx
                })

            first_buys = identify_first_buy(trends, df_with_macd, klines)
            second_buys = identify_second_buy(trends, df_with_macd, first_buys)

            return {
                'success': True,
                'stock_code': stock_code,
                'data_range': f"{df_sorted['date'].iloc[0]} ~ {df_sorted['date'].iloc[-1]}",
                'data_count': len(df_sorted),
                'fenxing_count': len(merged),
                'trend_count': len(trends),
                'first_buys': [sp.to_dict() for sp in first_buys],
                'second_buys': [sp.to_dict() for sp in second_buys],
                'fenxing_list': [(idx, ftype, {'date': kline['date'], 'high': kline['high'], 'low': kline['low']})
                                for idx, ftype, kline in merged],
                'trends': trends,
                'df_with_macd': df_with_macd
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def get_buy_signals_summary(self, analysis_result: dict) -> pd.DataFrame:
        """
        获取买点信号汇总

        Args:
            analysis_result: analyze() 返回的结果

        Returns:
            pd.DataFrame: 买点信号汇总表
        """
        if not analysis_result['success']:
            return pd.DataFrame()

        signals = []

        for fb in analysis_result['first_buys']:
            signals.append({
                '日期': fb['date'],
                '价格': f"{fb['price']:.2f}",
                '买点类型': '一买',
                '是否新低': fb.get('是否新低', '未知'),
                '次阳涨幅%': fb.get('次日阳线涨幅%', '0%'),
                '是否背驰': fb.get('是否背驰', '未知'),
                '条件A(面积减少)': fb.get('面积A', '否'),
                '条件B(高度降低)': fb.get('面积B', '否'),
                '条件C(力度减弱)': fb.get('面积C', '否'),
                '在中枢内': fb.get('在中枢内', '未知'),
            })

        for sb in analysis_result['second_buys']:
            signals.append({
                '日期': sb['date'],
                '价格': f"{sb['price']:.2f}",
                '买点类型': '二买',
                '对应1买日期': sb.get('对应1买日期', 'N/A'),
                '对应1买价格': sb.get('对应1买价格', 'N/A'),
                '次阳涨幅%': sb.get('次日阳线涨幅%', '0%'),
            })

        return pd.DataFrame(signals)

    def format_analysis_report(self, analysis_result: dict) -> str:
        """
        格式化分析报告

        Args:
            analysis_result: analyze() 返回的结果

        Returns:
            str: 格式化的分析报告
        """
        if not analysis_result['success']:
            return f"分析失败: {analysis_result.get('error', '未知错误')}"

        lines = []
        lines.append("=" * 60)
        lines.append(f"股票代码: {analysis_result['stock_code']}")
        lines.append("=" * 60)
        lines.append(f"数据范围: {analysis_result['data_range']}")
        lines.append(f"数据条数: {analysis_result['data_count']}")
        lines.append(f"识别分型: {analysis_result['fenxing_count']}")
        lines.append(f"识别趋势: {analysis_result['trend_count']}")
        lines.append("")

        lines.append(f"一买信号: {len(analysis_result['first_buys'])} 个")
        for fb in analysis_result['first_buys']:
            lines.append(f"  {fb['date']} @ {fb['price']:.2f}")
            if fb.get('in_zhongshu'):
                lines.append(f"    (在中枢内，背驰验证)")
        lines.append("")

        lines.append(f"二买信号: {len(analysis_result['second_buys'])} 个")
        for sb in analysis_result['second_buys']:
            lines.append(f"  {sb['date']} @ {sb['price']:.2f}")
        lines.append("")

        return "\n".join(lines)
