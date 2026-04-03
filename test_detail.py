import sys
sys.path.insert(0, r'f:\trae_project\股票看板')

from utils.database import StockDatabase
from chanlun.analyzer import ChanlunAnalyzer
from chanlun.macd import add_macd_to_dataframe
from chanlun.fenxing_with_macd import find_fenxing, merge_same_type, extract_trends, pad_fenxing

print("=" * 60)
print("详细分析 000001 的分型和买点识别")
print("=" * 60)

db = StockDatabase()
kline_data = db.get_kline_data("000001", days=180)
df = kline_data.sort_values('date').reset_index(drop=True)
df_with_macd = add_macd_to_dataframe(df)

print(f"\n数据范围: {df['date'].iloc[0]} ~ {df['date'].iloc[-1]}")
print(f"数据条数: {len(df)}")

klines = df[['date', 'open', 'close', 'high', 'low', 'volume']].to_dict('records')

print("\n" + "=" * 60)
print("1. 分型识别")
print("=" * 60)
processed, filtered = find_fenxing(klines)
merged = merge_same_type(filtered)

print(f"\n识别出 {len(merged)} 个分型:")
for idx, ftype, kline in merged:
    fx_type = "顶" if ftype == '顶' else "底"
    print(f"  [{idx}] {fx_type} - 日期:{kline['date']}, 高:{kline['high']:.2f}, 低:{kline['low']:.2f}")

print("\n" + "=" * 60)
print("2. 分型补全")
print("=" * 60)
padded_merged = pad_fenxing(merged, klines)
print(f"\n补全后 {len(padded_merged)} 个分型:")
for idx, ftype, kline in padded_merged:
    fx_type = "顶" if ftype == '顶' else "底"
    print(f"  [{idx}] {fx_type} - 日期:{kline['date']}, 高:{kline['high']:.2f}, 低:{kline['low']:.2f}")

print("\n" + "=" * 60)
print("3. 趋势识别")
print("=" * 60)
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

print(f"\n识别出 {len(trends)} 个趋势段:")
for t in trends:
    start_date = t['start_fenxing'][2]['date']
    end_date = t['end_fenxing'][2]['date']
    start_price = t['start_fenxing'][2]['high'] if t['type'] == '上升' else t['start_fenxing'][2]['low']
    end_price = t['end_fenxing'][2]['high'] if t['type'] == '上升' else t['end_fenxing'][2]['low']
    print(f"  [{t['index']}] {t['type']} - {start_date} ~ {end_date}")
    print(f"       起始:{start_price:.2f} → 结束:{end_price:.2f}")

print("\n" + "=" * 60)
print("4. 背驰检测")
print("=" * 60)
downs = [t for t in trends if t['type'] == '下降']
print(f"\n下降趋势段: {len(downs)} 个")

for i, t in enumerate(downs):
    from chanlun.chanlun_signals import extract_trend_data, detect_divergence

    td = extract_trend_data(t, df_with_macd)

    pd_t = None
    for j in range(i-1, -1, -1):
        if downs[j]['type'] == '下降':
            pd_t = extract_trend_data(downs[j], df_with_macd)
            break

    div = detect_divergence(td, pd_t, 'bottom')

    end_date = t['end_fenxing'][2]['date']
    end_price = t['end_fenxing'][2]['low']

    print(f"\n趋势段 {t['index']}:")
    print(f"  结束分型: {end_date} @ {end_price:.2f}")
    print(f"  绿柱面积: {td['green_area']:.4f}")
    print(f"  绿柱高度: {td['green_bar_height']:.4f}")
    print(f"  力度: {td['force']:.4f}")

    if div:
        print(f"  ✅ 背驰检测: 是")
        print(f"     条件A(面积减少): {'满足' if div['cond_a'] else '不满足'}")
        print(f"     条件B(高度降低): {'满足' if div['cond_b'] else '不满足'}")
        print(f"     条件C(力度减弱): {'满足' if div['cond_c'] else '不满足'}")
        print(f"     创新低: {'是' if div['price_new_low'] else '否'}")
    else:
        print(f"  ❌ 背驰检测: 否")
        if pd_t:
            print(f"     (没有满足背驰条件A/B/C中的任一条件)")
        else:
            print(f"     (没有前一个下降趋势用于比较)")

print("\n" + "=" * 60)
print("5. 买点识别结果")
print("=" * 60)
analyzer = ChanlunAnalyzer()
result = analyzer.analyze(kline_data, "000001")

print(f"\n一买: {len(result['first_buys'])} 个")
for fb in result['first_buys']:
    print(f"  - {fb['date']} @ {fb['price']:.2f}")
    print(f"    是否新低: {fb.get('是否新低')}")
    print(f"    是否背驰: {fb.get('是否背驰')}")
    print(f"    背驰详情: {fb.get('背驰详情')}")

print(f"\n二买: {len(result['second_buys'])} 个")
for sb in result['second_buys']:
    print(f"  - {sb['date']} @ {sb['price']:.2f}")

print("\n" + "=" * 60)
