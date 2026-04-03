import sys
sys.path.insert(0, r'f:\trae_project\股票看板')

from utils.database import StockDatabase
from chanlun.macd import add_macd_to_dataframe
from chanlun.fenxing_with_macd import find_fenxing, merge_same_type, extract_trends, pad_fenxing
from chanlun.chanlun_signals import extract_trend_data, detect_divergence

print("=" * 60)
print("调试背驰检测 - 趋势2 vs 趋势6")
print("=" * 60)

db = StockDatabase()
kline_data = db.get_kline_data("000001", days=180)
df = kline_data.sort_values('date').reset_index(drop=True)
df_with_macd = add_macd_to_dataframe(df)

klines = df[['date', 'open', 'close', 'high', 'low', 'volume']].to_dict('records')
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

downs = [t for t in trends if t['type'] == '下降']
print(f"\n下降趋势: {len(downs)} 个")
for t in downs:
    print(f"  趋势{t['index']}: {t['end_fenxing'][2]['date']} @ {t['end_fenxing'][2]['low']:.2f}")

print("\n" + "=" * 60)
print("手动比较趋势2和趋势6")
print("=" * 60)

trend2 = downs[0]  # 趋势2
trend6 = downs[2]  # 趋势6

print(f"\n趋势2结束分型: {trend2['end_fenxing'][2]['date']} @ {trend2['end_fenxing'][2]['low']:.2f}")
print(f"趋势6结束分型: {trend6['end_fenxing'][2]['date']} @ {trend6['end_fenxing'][2]['low']:.2f}")

curr_low = trend6['end_fenxing'][2]['low']
prev_low = trend2['end_fenxing'][2]['low']
low_diff_pct = abs(curr_low - prev_low) / prev_low * 100

print(f"\n低点差距: {low_diff_pct:.4f}%")
print(f"是否超过1%: {low_diff_pct > 1}")

trend2_data = extract_trend_data(trend2, df_with_macd)
trend6_data = extract_trend_data(trend6, df_with_macd)

print(f"\n趋势2数据:")
print(f"  绿柱面积: {trend2_data['green_area']:.6f}")
print(f"  绿柱高度: {trend2_data['green_bar_height']:.6f}")
print(f"  力度: {trend2_data['force']:.6f}")

print(f"\n趋势6数据:")
print(f"  绿柱面积: {trend6_data['green_area']:.6f}")
print(f"  绿柱高度: {trend6_data['green_bar_height']:.6f}")
print(f"  力度: {trend6_data['force']:.6f}")

print("\n" + "=" * 60)
print("调用detect_divergence函数")
print("=" * 60)

div = detect_divergence(trend6_data, trend2_data, 'bottom')

if div:
    print(f"\n背驰检测结果:")
    print(f"  has_divergence: {div['has_divergence']}")
    print(f"  price_diff_pct: {div['price_diff_pct']:.4f}%")
    print(f"  in_zhongshu: {div['in_zhongshu']}")
    print(f"  cond_a: {div['cond_a']}")
    print(f"  cond_b: {div['cond_b']}")
    print(f"  cond_c: {div['cond_c']}")
    print(f"  price_new_low: {div['price_new_low']}")

    print(f"\n背驰条件判断:")
    print(f"  条件A(面积减少): {'满足' if div['cond_a'] else '不满足'}")
    print(f"    abs(curr)={abs(div['current_green']):.6f} < abs(prev)={abs(div['prev_green']):.6f}? {abs(div['current_green']) < abs(div['prev_green'])}")

    print(f"  条件B(高度降低): {'满足' if div['cond_b'] else '不满足'}")
    print(f"    abs(curr)={abs(div['current_green_h']):.6f} < abs(prev)={abs(div['prev_green_h']):.6f}? {abs(div['current_green_h']) < abs(div['prev_green_h'])}")

    print(f"  条件C(力度减弱): {'满足' if div['cond_c'] else '不满足'}")
    print(f"    curr_force={div['current_force']:.6f} < prev_force={div['prev_force']:.6f}? {div['current_force'] < div['prev_force']}")
    print(f"    prev_force > 0? {div['prev_force'] > 0}")
else:
    print("\n背驰检测返回None")

print("\n" + "=" * 60)
