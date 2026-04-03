import sys
sys.path.insert(0, r'f:\trae_project\股票看板')

from utils.database import StockDatabase
from chanlun.macd import add_macd_to_dataframe
from chanlun.fenxing_with_macd import find_fenxing, merge_same_type, extract_trends, pad_fenxing
from chanlun.chanlun_signals import extract_trend_data, detect_divergence

print("=" * 60)
print("最终调试：检查趋势2和趋势6的背驰检测")
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
print("手动模拟identify_first_buy逻辑")
print("=" * 60)

print("\n检查趋势6(索引2):")
i = 2
t = downs[2]
td = extract_trend_data(t, df_with_macd)
ef = t['end_fenxing']

print(f"  结束分型日期: {ef[2]['date']}")
print(f"  结束分型低价: {ef[2]['low']:.2f}")

curr_low = ef[2]['low']
compare_idx = i - 1  # = 1

print(f"  curr_low = {curr_low}")
print(f"  compare_idx = {compare_idx}")

while compare_idx >= 0:
    prev_low = downs[compare_idx]['end_fenxing'][2]['low']
    low_diff_pct = abs(curr_low - prev_low) / prev_low * 100

    print(f"\n  比较curr_low({curr_low}) 和 prev_low({prev_low}):")
    print(f"    差距 = {low_diff_pct:.4f}%")

    if low_diff_pct > 1:
        print(f"    差距 > 1%，使用这个趋势进行比较")
        pd_t = extract_trend_data(downs[compare_idx], df_with_macd)
        print(f"    prev趋势数据:")
        print(f"      绿柱面积 = {pd_t['green_area']:.6f}")
        print(f"      绿柱高度 = {pd_t['green_bar_height']:.6f}")
        print(f"      力度 = {pd_t['force']:.6f}")

        print(f"\n    curr趋势数据:")
        print(f"      绿柱面积 = {td['green_area']:.6f}")
        print(f"      绿柱高度 = {td['green_bar_height']:.6f}")
        print(f"      力度 = {td['force']:.6f}")

        print(f"\n    调用detect_divergence...")
        div = detect_divergence(td, pd_t, 'bottom')

        if div is None:
            print(f"    ❌ detect_divergence返回None")

            print(f"\n    检查为什么返回None:")
            print(f"      检查1: prev是否为None? {pd_t is None}")

            cg = td['green_area'] < 0
            pg = pd_t['green_area'] < 0
            print(f"      检查2: cg={cg} (curr绿柱<0), pg={pg} (prev绿柱<0)")
            print(f"      检查3: not cg and not pg? {not cg and not pg}")

            if not cg and not pg:
                print(f"      原因: curr和prev都不是绿柱，返回None")
            else:
                cond_a = cond_b = cond_c = False
                if cg and pg:
                    cond_a = abs(td['green_area']) < abs(pd_t['green_area'])
                    cond_b = abs(td['green_bar_height']) < abs(pd_t['green_bar_height'])
                    print(f"      条件A: abs({td['green_area']:.6f}) < abs({pd_t['green_area']:.6f})? {cond_a}")
                    print(f"      条件B: abs({td['green_bar_height']:.6f}) < abs({pd_t['green_bar_height']:.6f})? {cond_b}")

                if pd_t['force'] > 0:
                    cond_c = td['force'] < pd_t['force']
                    print(f"      条件C: {td['force']:.6f} < {pd_t['force']:.6f}? {cond_c}")
                else:
                    print(f"      条件C: prev_force({pd_t['force']:.6f}) <= 0，跳过")

                print(f"      条件A or B or C? {cond_a or cond_b or cond_c}")
                if not (cond_a or cond_b or cond_c):
                    print(f"      原因: 没有满足任何背驰条件，返回None")
        else:
            print(f"    ✅ detect_divergence返回结果:")
            print(f"      has_divergence: {div['has_divergence']}")
            print(f"      cond_a: {div['cond_a']}, cond_b: {div['cond_b']}, cond_c: {div['cond_c']}")
        break
    else:
        print(f"    差距 < 1%，形成中枢，继续往前找")
        compare_idx -= 1

print("\n" + "=" * 60)
