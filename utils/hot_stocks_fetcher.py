import time
import random
from typing import List, Dict, Optional
from datetime import date
import pandas as pd

try:
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from selenium.webdriver.chrome.options import Options
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.common.exceptions import TimeoutException, NoSuchElementException
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

try:
    from webdriver_manager.chrome import ChromeDriverManager
    WEBDRIVER_MANAGER_AVAILABLE = True
except ImportError:
    WEBDRIVER_MANAGER_AVAILABLE = False


class HotStocksFetcher:
    def __init__(self):
        self.url = "https://guba.eastmoney.com/rank/"
        self.driver = None

    def _init_driver(self) -> bool:
        if not SELENIUM_AVAILABLE:
            print("Selenium 未安装，请运行: pip install selenium")
            return False

        try:
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
            chrome_options.add_experimental_option('useAutomationExtension', False)

            user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            chrome_options.add_argument(f'user-agent={user_agent}')

            if WEBDRIVER_MANAGER_AVAILABLE:
                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
            else:
                self.driver = webdriver.Chrome(options=chrome_options)

            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

            return True
        except Exception as e:
            print(f"初始化 WebDriver 失败: {e}")
            return False

    def fetch_hot_stocks(self, max_items: int = 100) -> Optional[List[Dict]]:
        if not self._init_driver():
            return None

        try:
            print(f"正在访问 {self.url}...")
            self.driver.get(self.url)

            time.sleep(random.uniform(10, 15))

            try:
                WebDriverWait(self.driver, 40).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, ".ranklist .ranklist-item, #ranklist .ranklist-item, .article-list .list-item, table"))
                )
            except:
                print("主选择器未找到，继续尝试...")

            time.sleep(random.uniform(8, 10))

            stocks_data = self._parse_page_data(max_items)

            return stocks_data

        except TimeoutException:
            print("页面加载超时")
            return None
        except Exception as e:
            print(f"获取数据失败: {e}")
            return None
        finally:
            if self.driver:
                self.driver.quit()
                self.driver = None

    def _parse_page_data(self, max_items: int) -> List[Dict]:
        stocks_data = []

        selectors = [
            ".ranklist .ranklist-item",
            "#ranklist .ranklist-item",
            ".article-list .list-item",
            ".ranklist-item",
            "[class*='ranklist'] [class*='item']",
            ".bankuai .list",
            ".hotstock-list .item"
        ]

        items = []
        for selector in selectors:
            try:
                items = self.driver.find_elements(By.CSS_SELECTOR, selector)
                if items:
                    print(f"使用 CSS 选择器 '{selector}' 找到 {len(items)} 个元素")
                    break
            except:
                continue

        if not items:
            print("CSS 选择器未找到元素，尝试 XPath 表格选择器...")
            items = self._parse_table_by_xpath()

        if not items:
            print("无法找到排名列表元素，尝试备选方法...")
            return self._parse_alternative()

        for idx, item in enumerate(items[:max_items]):
            try:
                stock_info = self._extract_stock_info(item, idx + 1)
                if stock_info:
                    stocks_data.append(stock_info)
            except Exception as e:
                print(f"解析第 {idx + 1} 个元素失败: {e}")
                continue

        return stocks_data

    def _parse_table_by_xpath(self) -> List:
        """使用 XPath 解析表格数据"""
        try:
            table_xpaths = [
                "/html/body/div[2]/div[3]/div[1]/div[2]/table/tbody/tr",
                "//table[@class='ranktable']//tbody//tr",
                "//table//tbody//tr",
                "//div[@class='ranklist']//table//tr",
                "//div[contains(@class,'rank')]//tr"
            ]

            for xpath in table_xpaths:
                try:
                    rows = self.driver.find_elements(By.XPATH, xpath)
                    if rows and len(rows) > 0:
                        print(f"使用 XPath '{xpath}' 找到 {len(rows)} 行")
                        return rows
                except:
                    continue

            print("XPath 选择器也未找到表格行")
            return []

        except Exception as e:
            print(f"XPath 解析失败: {e}")
            return []

    def _extract_stock_info(self, item, rank: int) -> Optional[Dict]:
        try:
            import re

            code = ""
            name = ""
            change_pct = 0.0

            td_elements = item.find_elements(By.TAG_NAME, "td")

            if len(td_elements) >= 10:
                cell_0_html = td_elements[0].get_attribute('innerHTML')
                rank_match = re.search(r'icon_rank(\d+)', cell_0_html)
                if rank_match:
                    rank = int(rank_match.group(1))

                cell_3_html = td_elements[3].get_attribute('innerHTML')
                code_match = re.search(r'quote_(\d{6})', cell_3_html)
                if code_match:
                    code = code_match.group(1)

                try:
                    name_elem = td_elements[4].find_element(By.XPATH, ".//a")
                    name = name_elem.text.strip()
                except:
                    name = ""

                try:
                    change_elem = td_elements[8].find_element(By.XPATH, ".//div")
                    change_text = change_elem.text.strip()
                    if change_text and change_text != '--':
                        change_match = re.search(r'([+-]?\d+\.?\d*)', change_text)
                        if change_match:
                            change_pct = float(change_match.group(1))
                except:
                    pass

            if not code:
                return None

            return {
                'rank': rank,
                'code': code,
                'name': name if name else code,
                'change_pct': change_pct
            }

        except Exception as e:
            print(f"提取股票信息失败: {e}")
            return None

    def _parse_alternative(self) -> List[Dict]:
        import re
        stocks_data = []

        try:
            page_source = self.driver.page_source

            title_pattern = r'<a[^>]*href=["\']https?://guba\.eastmoney\.com/notice/\d+["\'][^>]*>([^<]+)</a>'
            titles = re.findall(title_pattern, page_source)

            code_pattern = r'https?://guba\.eastmoney\.com/notice/(\d{6})'
            codes = re.findall(code_pattern, page_source)

            for i, (code, title) in enumerate(zip(codes, titles)):
                if i >= 100:
                    break

                name = title.strip() if title else ""

                stocks_data.append({
                    'rank': i + 1,
                    'code': code,
                    'name': name,
                    'popularity_index': 0,
                    'attention_change': 0,
                    'change_pct': 0,
                    'attention_ratio_up': 0,
                    'attention_ratio_down': 0,
                    'comment': '',
                    'url': f'https://guba.eastmoney.com/notice/{code}'
                })

        except Exception as e:
            print(f"备选解析方法失败: {e}")

        return stocks_data


def fetch_hot_stocks_data(max_items: int = 100) -> Optional[List[Dict]]:
    fetcher = HotStocksFetcher()
    return fetcher.fetch_hot_stocks(max_items)


if __name__ == "__main__":
    print("测试热门个股爬虫...")
    data = fetch_hot_stocks_data(20)
    if data:
        print(f"成功获取 {len(data)} 条数据")
        for item in data[:5]:
            print(item)
    else:
        print("获取数据失败")
