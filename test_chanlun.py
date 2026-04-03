import sys
sys.path.insert(0, r'f:\trae_project\股票看板')

from utils.database import StockDatabase
from chanlun.analyzer import ChanlunAnalyzer

print("正在测试缠论分析功能...")

db = StockDatabase()
analyzer = ChanlunAnalyzer()

print("\n1. 测试获取股票数据...")
kline_data = db.get_kline_data("000001", days=180)
print(f"   获取到 {len(kline_data)} 条数据")
if kline_data.empty:
    print("   ❌ 数据为空！")
    sys.exit(1)
else:
    print("   ✅ 数据获取成功")

print("\n2. 测试缠论分析...")
result = analyzer.analyze(kline_data, "000001")

if result['success']:
    print(f"   ✅ 分析成功！")
    print(f"   - 数据范围: {result['data_range']}")
    print(f"   - 识别分型: {result['fenxing_count']}")
    print(f"   - 识别趋势: {result['trend_count']}")
    print(f"   - 一买信号: {len(result['first_buys'])} 个")
    print(f"   - 二买信号: {len(result['second_buys'])} 个")

    if result['first_buys']:
        print("\n   一买信号详情:")
        for fb in result['first_buys']:
            print(f"   - 日期: {fb['date']}, 价格: {fb['price']:.2f}")
            print(f"     是否新低: {fb.get('是否新低', 'N/A')}")
            print(f"     次日阳线涨幅: {fb.get('次日阳线涨幅%', 'N/A')}")

    if result['second_buys']:
        print("\n   二买信号详情:")
        for sb in result['second_buys']:
            print(f"   - 日期: {sb['date']}, 价格: {sb['price']:.2f}")
            print(f"     对应1买: {sb.get('对应1买日期', 'N/A')}")
            print(f"     次日阳线涨幅: {sb.get('次日阳线涨幅%', 'N/A')}")
else:
    print(f"   ❌ 分析失败: {result.get('error', '未知错误')}")
    sys.exit(1)

print("\n✅ 所有测试通过！缠论分析功能正常运行。")
