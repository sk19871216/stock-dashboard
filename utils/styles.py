"""Streamlit 公共样式工具函数"""
import pandas as pd


def highlight_yangxian(val: str) -> str:
    """
    次阳涨幅高亮函数
    涨幅超过3%的单元格显示红色加粗

    Args:
        val: 单元格值，如 "3.45%"

    Returns:
        CSS样式字符串
    """
    if isinstance(val, str) and '%' in val:
        try:
            pct = float(val.replace('%', ''))
            if pct > 3:
                return 'color: red; font-weight: bold'
        except ValueError:
            pass
    return ''
