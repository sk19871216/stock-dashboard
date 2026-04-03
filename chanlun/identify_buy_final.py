# 正确的identify_first_buy实现

def identify_first_buy(trends, df):
    """
    下降趋势ABCD，最低点abcd

    1. B和A比较：差距<1%（形成中枢）
    2. C和A比较：差距>1%，用C和A比较背驰
    """
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

            if low_diff_pct > 1:
                pd_t = extract_trend_data(downs[compare_idx], df)
                break

            compare_idx -= 1

        # 进行背驰检测
        div = detect_divergence(td, pd_t, 'bottom')
        # ... 处理结果
