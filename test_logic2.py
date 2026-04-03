import sys
sys.path.insert(0, r'f:\trae_project\股票看板')

from utils.database import StockDatabase

db = StockDatabase()
kline_data = db.get_kline_data("000001", days=180)

print("正确的中枢跳过逻辑：")
print()
print("对于趋势6：")
print("1. 趋势6和趋势4比较：差距2.25% > 1%")
print("   但是，趋势4和趋势2差距0.09% < 1%，形成中枢")
print("   所以趋势4应该被跳过")
print()
print("2. 趋势6和趋势2比较：差距2.16% > 1%")
print("   趋势2和趋势1差距未知，但是...")
print("   如果趋势2是第一个下降趋势，就和趋势2比较")
print()

print("实现逻辑：")
print("- 从当前趋势往前找")
print("- 检查当前趋势和前一个趋势的差距")
print("- 如果差距不超过1%，认为形成中枢，跳过前一个，继续找")
print("- 如果差距超过1%，检查前一个和再前一个是否形成中枢")
print("  - 如果形成中枢，继续往前找")
print("  - 如果不形成中枢，则使用前一个趋势进行比较")

print()
print("代码实现：")
print("""
for i, t in enumerate(downs):
    curr_low = t['end_fenxing'][2]['low']
    compare_idx = i - 1

    while compare_idx >= 0:
        if downs[compare_idx]['type'] == '下降':
            prev_low = downs[compare_idx]['end_fenxing'][2]['low']
            low_diff_pct = abs(curr_low - prev_low) / prev_low * 100

            if low_diff_pct > 1:
                # 检查中间的趋势是否和当前趋势形成中枢
                is_zhongshu = False
                for mid_idx in range(compare_idx + 1, i):
                    if downs[mid_idx]['type'] == '下降':
                        mid_low = downs[mid_idx]['end_fenxing'][2]['low']
                        mid_diff = abs(curr_low - mid_low) / mid_low * 100
                        if mid_diff < 1:
                            is_zhongshu = True
                            break

                if not is_zhongshu:
                    pd_t = extract_trend_data(downs[compare_idx], df)
                    break

            compare_idx -= 1
        else:
            compare_idx -= 1
""")
