import re
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

class GubaFileReader:
    """从文本文件读取东方财富人气榜数据"""

    def __init__(self, data_dir: str = None):
        if data_dir is None:
            self.data_dir = Path(__file__).parent.parent
        else:
            self.data_dir = Path(data_dir)

    def get_latest_file(self) -> Optional[Path]:
        """获取最新的人气榜文件"""

        txt_files = list(self.data_dir.glob("*.txt"))

        if not txt_files:
            return None

        latest_file = None
        latest_time = 0

        for file in txt_files:
            if file.stem.isdigit():
                try:
                    file_time = datetime.strptime(file.stem, "%y%m%d")
                    timestamp = file_time.timestamp()
                    if timestamp > latest_time:
                        latest_time = timestamp
                        latest_file = file
                except:
                    pass

        return latest_file

    def parse_file(self, file_path: Path) -> List[Dict]:
        """解析人气榜文件（不带日期格式）"""

        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        stocks = []
        i = 0
        rank = 1

        while i < len(lines):
            line = lines[i].strip()

            if not line or line == "排名详情 股吧":
                i += 1
                continue

            if line.isdigit() and len(line) == 6:
                code = line

                if i + 3 < len(lines):
                    name_line = lines[i + 1].strip()
                    name = name_line

                    price = 0
                    change_amt = 0
                    change_pct = 0.0
                    attention_up = 0
                    attention_down = 0

                    if i + 7 < len(lines):
                        price_line = lines[i + 4].strip()
                        change_amt_line = lines[i + 5].strip()
                        change_pct_line = lines[i + 6].strip()
                        attention_line = lines[i + 7].strip()

                        try:
                            price = float(price_line) if price_line else 0
                        except:
                            price = 0

                        try:
                            change_amt = float(change_amt_line) if change_amt_line else 0
                        except:
                            change_amt = 0

                        try:
                            change_match = re.search(r'([+-]?\d+\.?\d*)', change_pct_line)
                            if change_match:
                                change_pct = float(change_match.group(1))
                        except:
                            change_pct = 0.0

                        attention_match = re.findall(r'(\d+\.?\d*)%', attention_line)
                        if len(attention_match) >= 2:
                            attention_up = float(attention_match[0])
                            attention_down = float(attention_match[1])

                    trade_date = self._extract_date_from_filename(file_path.stem)

                    stocks.append({
                        'rank': rank,
                        'code': code,
                        'name': name,
                        'price': price,
                        'change_amt': change_amt,
                        'change_pct': change_pct,
                        'attention_up': attention_up,
                        'attention_down': attention_down,
                        'trade_date': trade_date
                    })

                    rank += 1

            i += 1

        return stocks

    def parse_file_with_date(self, file_path: Path) -> List[Dict]:
        """解析人气榜文件（带日期格式：第一行是日期）"""

        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        if not lines:
            return []

        first_line = lines[0].strip()

        if re.match(r'\d{4}-\d{2}-\d{2}', first_line):
            trade_date = first_line
        else:
            trade_date = datetime.now().strftime("%Y-%m-%d")

        stocks = []
        rank = 1

        for i in range(1, len(lines)):
            line = lines[i].strip()

            if line.isdigit() and len(line) == 6:
                code = line

                rank_change = 0
                if i > 1:
                    prev_line = lines[i - 1].strip()
                    if prev_line.isdigit():
                        rank_change = int(prev_line)
                    elif prev_line.startswith('-') and prev_line[1:].isdigit():
                        rank_change = int(prev_line)

                if i + 1 < len(lines):
                    name = lines[i + 1].strip()

                    change_pct = 0.0
                    attention_ratio = ""

                    if i + 5 < len(lines):
                        change_line = lines[i + 5].strip()
                        change_match = re.search(r'([+-]?\d+\.?\d*)', change_line)
                        if change_match:
                            change_pct = float(change_match.group(1))

                    if i + 6 < len(lines):
                        attention_ratio = lines[i + 6].strip()

                    stocks.append({
                        'rank': rank,
                        'code': code,
                        'name': name,
                        'change_pct': change_pct,
                        'rank_change': rank_change,
                        'attention_ratio': attention_ratio,
                        'trade_date': trade_date
                    })

                    rank += 1

        return stocks

    def read_latest(self) -> Optional[List[Dict]]:
        """读取最新的人气榜文件（自动识别格式）"""
        latest_file = self.get_latest_file()

        if not latest_file:
            print(f"❌ 未找到人气榜文件（格式：YYMMDD.txt）")
            return None

        print(f"📂 读取文件: {latest_file}")

        with open(latest_file, 'r', encoding='utf-8') as f:
            first_line = f.readline().strip()

        if re.match(r'\d{4}-\d{2}-\d{2}', first_line):
            stocks = self.parse_file_with_date(latest_file)
        else:
            stocks = self.parse_file(latest_file)

        if stocks:
            print(f"✅ 成功解析 {len(stocks)} 条股票数据")
        else:
            print(f"❌ 解析失败")

        return stocks

    def read_latest_with_date(self) -> Optional[List[Dict]]:
        """读取最新的人气榜文件（带日期格式）"""
        latest_file = self.get_latest_file()

        if not latest_file:
            print(f"❌ 未找到人气榜文件（格式：YYMMDD.txt）")
            return None

        print(f"📂 读取文件: {latest_file}")

        with open(latest_file, 'r', encoding='utf-8') as f:
            first_line = f.readline().strip()

        if not re.match(r'\d{4}-\d{2}-\d{2}', first_line):
            print(f"⚠️ 文件第一行不是日期格式: {first_line}")
            return None

        stocks = self.parse_file_with_date(latest_file)

        if stocks:
            print(f"✅ 成功解析 {len(stocks)} 条股票数据")
            print(f"📅 数据日期: {first_line}")
        else:
            print(f"❌ 解析失败")

        return stocks

    def _extract_date_from_filename(self, filename: str) -> str:
        """从文件名提取日期"""
        try:
            if filename.isdigit() and len(filename) == 6:
                date_obj = datetime.strptime(filename, "%y%m%d")
                return date_obj.strftime("%Y-%m-%d")
        except:
            pass
        return datetime.now().strftime("%Y-%m-%d")


if __name__ == "__main__":
    reader = GubaFileReader()

    print("=" * 80)
    print("读取东方财富人气榜文件")
    print("=" * 80)

    stocks = reader.read_latest_with_date()

    if stocks:
        print(f"\n数据预览（前10条）:\n")
        for i, stock in enumerate(stocks[:10], 1):
            print(f"{i:2d}. {stock['rank']:3d}  {stock['code']:6s}  {stock['name']:10s}  "
                  f"涨跌幅:{stock['change_pct']:+6.2f}%  日期:{stock['trade_date']}")
