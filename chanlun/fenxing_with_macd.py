"""
缠论分型分析 + MACD指标比较
基于分型识别趋势段，并比较相邻相同趋势的MACD面积和量柱高度
"""

import sys
sys.stdout.reconfigure(encoding='utf-8')


def find_fenxing(klines):
    """
    找分型

    Args:
        klines: K线列表

    Returns:
        processed: 处理后的K线
        fenxing_list: 分型列表 [(idx, type, kline), ...]
    """
    def process_contains(klines):
        if len(klines) < 3:
            return klines
        result = [klines[0].copy()]
        result[0]['pos'] = 0
        for i in range(1, len(klines)):
            cur = klines[i]
            cur_pos = i
            last = result[-1]
            last_pos = last['pos']
            if cur['high'] <= last['high'] and cur['low'] >= last['low']:
                continue
            elif last['high'] <= cur['high'] and last['low'] >= cur['low']:
                if len(result) >= 2:
                    prev = result[-2]
                    if prev['high'] < cur['high']:
                        merged_h = max(last['high'], cur['high'])
                        merged_l = max(last['low'], cur['low'])
                        fx_pos = last_pos if last['high'] >= cur['high'] else cur_pos
                    else:
                        merged_h = min(last['high'], cur['high'])
                        merged_l = min(last['low'], cur['low'])
                        fx_pos = last_pos if last['low'] <= cur['low'] else cur_pos
                    result[-1] = {'high': merged_h, 'low': merged_l, 'date': klines[fx_pos]['date'], 'pos': fx_pos}
                else:
                    result[-1] = {'high': cur['high'], 'low': cur['low'], 'date': cur['date'], 'pos': cur_pos}
            else:
                result.append({'high': cur['high'], 'low': cur['low'], 'date': cur['date'], 'pos': cur_pos})
        return result

    def find_candidates(klines):
        results = []
        for i in range(1, len(klines) - 1):
            prev, curr, next_k = klines[i-1], klines[i], klines[i+1]
            if curr['high'] > prev['high'] and curr['high'] > next_k['high'] and \
               curr['low'] > prev['low'] and curr['low'] > next_k['low']:
                results.append((i, curr['pos'], '顶'))
            if curr['low'] < prev['low'] and curr['low'] < next_k['low'] and \
               curr['high'] < prev['high'] and curr['high'] < next_k['high']:
                results.append((i, curr['pos'], '底'))
        return results

    def filter_shared_boundary(all_fx_sorted, processed):
        filtered = []
        last_end = -999
        last_type = None
        for i, pos, ftype in all_fx_sorted:
            left_boundary = pos - 1
            if ftype != last_type and left_boundary <= last_end:
                pass
            else:
                kline = processed[i]
                filtered.append((pos, ftype, kline))
                last_end = pos + 1
                last_type = ftype
        return filtered

    processed = process_contains(klines)
    all_fx = find_candidates(processed)
    all_fx.sort(key=lambda x: x[1])
    filtered = filter_shared_boundary(all_fx, processed)

    return processed, filtered


def merge_same_type(filtered):
    """
    合并相邻同类型分型
    """
    def merge_once(items):
        if len(items) <= 1:
            return items, False
        result = [items[0]]
        changed = False
        for i in range(1, len(items)):
            idx, ftype, kline = items[i]
            li, lf, lk = result[-1]
            if ftype == lf:
                if ftype == '顶' and kline['high'] > lk['high']:
                    result[-1] = [idx, ftype, kline]
                    changed = True
                elif ftype == '底' and kline['low'] < lk['low']:
                    result[-1] = [idx, ftype, kline]
                    changed = True
            else:
                result.append([idx, ftype, kline])
        return result, changed

    items = [[idx, ftype, kline] for idx, ftype, kline in filtered]
    while True:
        merged, changed = merge_once(items)
        items = merged
        if not changed:
            break

    return items


def pad_fenxing(fenxing_list, klines):
    """
    在分型列表的开头补充相反的分型（不补充结尾）

    Args:
        fenxing_list: 分型列表
        klines: 原始K线数据（用于获取开头的K线信息）

    Returns:
        补全后的分型列表
    """
    if len(fenxing_list) < 1:
        return fenxing_list

    padded = fenxing_list.copy()
    first_fenxing = fenxing_list[0]
    first_kline = klines[0]

    if first_fenxing[1] == '顶':
        padded.insert(0, (0, '底', {
            'date': first_kline['date'],
            'high': first_kline['high'],
            'low': first_kline['low'],
            'pos': 0
        }))
    elif first_fenxing[1] == '底':
        padded.insert(0, (0, '顶', {
            'date': first_kline['date'],
            'high': first_kline['high'],
            'low': first_kline['low'],
            'pos': 0
        }))

    return padded


def extract_trends(fenxing_list):
    """
    从分型列表提取趋势段

    Args:
        fenxing_list: 分型列表

    Returns:
        趋势段列表 [(趋势类型, 起始分型, 结束分型), ...]
    """
    trends = []
    for i in range(len(fenxing_list) - 1):
        curr_type = fenxing_list[i][1]
        next_type = fenxing_list[i + 1][1]

        if curr_type == '顶' and next_type == '底':
            trends.append(('下降', fenxing_list[i], fenxing_list[i + 1]))
        elif curr_type == '底' and next_type == '顶':
            trends.append(('上升', fenxing_list[i], fenxing_list[i + 1]))

    return trends
