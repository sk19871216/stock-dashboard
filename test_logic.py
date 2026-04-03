import sys
sys.path.insert(0, r'f:\trae_project\股票看板')

from utils.database import StockDatabase

db = StockDatabase()
kline_data = db.get_kline_data("000001", days=180)

print("理解中枢逻辑：")
print("趋势2低点: 10.66")
print("趋势4低点: 10.67")
print("趋势6低点: 10.43")

print("\n趋势2和趋势4:")
diff_2_4 = abs(10.66 - 10.67) / 10.66 * 100
print(f"  差距: {diff_2_4:.4f}%")
print(f"  是否形成中枢: {'是' if diff_2_4 < 1 else '否'}")

print("\n趋势2和趋势6:")
diff_2_6 = abs(10.66 - 10.43) / 10.66 * 100
print(f"  差距: {diff_2_6:.4f}%")
print(f"  是否形成中枢: {'是' if diff_2_6 < 1 else '否'}")

print("\n趋势4和趋势6:")
diff_4_6 = abs(10.67 - 10.43) / 10.67 * 100
print(f"  差距: {diff_4_6:.4f}%")
print(f"  是否形成中枢: {'是' if diff_4_6 < 1 else '否'}")

print("\n正确逻辑：")
print("1. 趋势6和趋势4比较：差距2.25% > 1%，暂时认为可以比较")
print("2. 但是，趋势4和趋势2形成中枢（0.09% < 1%）")
print("3. 所以趋势4不应该被用做比较对象")
print("4. 趋势6应该跳过趋势4，和趋势2比较")
print("5. 趋势6和趋势2差距2.16% > 1%，满足条件，应该比较")

print("\n结论：应该比较趋势2和趋势6")
