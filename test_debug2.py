import sys
sys.path.insert(0, r'f:\trae_project\股票看板')

from utils.database import StockDatabase
from chanlun.analyzer import ChanlunAnalyzer
from chanlun.macd import add_macd_to_dataframe
from chanlun.fenxing_with_macd import find_fenxing, merge_same_type, extract_trends, pad_fenxing
from chanlun.chanlun_signals import extract_trend_data, detect_divergence

print("=" * 60)
print("详细调试identify_first_buy函数")
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
for i, t in enumerate(downs):
    print(f"  [{i}] 趋势{t['index']}: {t['end_fenxing'][2]['date']} @ {t['end_fenxing'][2]['low']:.2f}")

print("\n" + "=" * 60)
print("逐个检查每个下降趋势")
print("=" * 60)

results = []

for i, t in enumerate(downs):
    td = extract_trend_data(t, df_with_macd)
    ef = t['end_fenxing']

    print(f"\n--- 检查趋势{t['index']} (索引{i}) ---")
    print(f"结束分型类型: {ef[1]}")
    print(f"结束分型日期: {ef[2]['date']}")
    print(f"结束分型低价: {ef[2]['low']:.2f}")

    if ef[1] != '底':
        print("  ❌ 不是底分型，跳过")
        continue

    curr_low = ef[2]['low']

    pd_t = None
    compare_idx = i - 1

    print(f"  curr_low = {curr_low:.2f}")
    print(f"  compare_idx = {compare_idx}")

    while compare_idx >= 0:
        if downs[compare_idx]['type'] == '下降':
            prev_low = downs[compare_idx]['end_fenxing'][2]['low']
            low_diff_pct = abs(curr_low - prev_low) / prev_low * 100

            print(f"    比较趋势{downs[compare_idx]['index']}: 低点={prev_low:.2f}, 差距={low_diff_pct:.4f}%")

            if low_diff_pct > 1:
                pd_t = extract_trend_data(downs[compare_idx], df_with_macd)
                print(f"    ✅ 差距超过1%，使用趋势{downs[compare_idx]['index']}进行比较")
                break
            else:
                print(f"    ❌ 差距不超过1%，继续向前找")
                compare_idx -= 1
        else:
            print(f"    ⚠️ 不是下降趋势，继续向前找")
            compare_idx -= 1

    if compare_idx < 0:
        print(f"  ⚠️ 没有找到可比较的趋势，pd_t = None")
    elif pd_t is None:
        print(f"  ⚠️ pd_t仍然为None")

    print(f"\n  调用detect_divergence...")
    div = detect_divergence(td, pd_t, 'bottom')

    if div is None:
        print(f"  ❌ detect_divergence返回None")
        continue

    print(f"  div['has_divergence'] = {div['has_divergence']}")

    if div and div['has_divergence']:
        print(f"  ✅ 识别为1买!")
        print(f"     背驰条件: A={div['cond_a']}, B={div['cond_b']}, C={div['cond_c']}")
        results.append({
            'date': str(ef[2]['date'])[:10],
            'price': ef[2]['low'],
            'trend_index': t['index']
        })
    else:
        print(f"  ❌ 没有背驰")

print("\n" + "=" * 60)
print(f"最终结果: {len(results)} 个1买")
print("=" * 60)

for r in results:
    print(f"  - {r['date']} @ {r['price']:.2f} (趋势{r['trend_index']})")
