import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, List, Dict
import warnings

warnings.filterwarnings('ignore')


class StockDataFetcher:
    def __init__(self):
        self.data_source = "mootdx"
        self._has_mootdx = False
        self.client = None
        self._init_data_source()

    def _init_data_source(self):
        try:
            from mootdx.quotes import Quotes
            self.client = Quotes.factory(market='std', server=('120.76.1.198', 7709))
            self._has_mootdx = True
            print("mootdx 通达信连接成功")
        except Exception as e:
            self._has_mootdx = False
            print(f"mootdx 连接失败: {e}，将使用 akshare 作为备选")

    def _reconnect(self, max_retries=3):
        """重新连接通达信"""
        import time
        for i in range(max_retries):
            try:
                from mootdx.quotes import Quotes
                self.client = Quotes.factory(market='std', server=('120.76.1.198', 7709))
                self._has_mootdx = True
                return True
            except Exception as e:
                time.sleep(0.5)
                continue
        self._has_mootdx = False
        return False

    def get_daily_kline(self, code: str, days: int = 365) -> Optional[pd.DataFrame]:
        try:
            if self._has_mootdx:
                df = self.client.bars(symbol=code)
                if df is not None and not df.empty:
                    df = df[['open', 'close', 'high', 'low', 'vol', 'amount']].copy()
                    df.columns = ['open', 'close', 'high', 'low', 'volume', 'amount']
                    df = df.reset_index()
                    df['date'] = pd.to_datetime(df['datetime']).dt.strftime('%Y-%m-%d')
                    df = df[['date', 'open', 'high', 'low', 'close', 'volume', 'amount']]
                    return df.tail(days)
        except Exception as e:
            print(f"获取K线数据失败 (mootdx): {e}")

        return self._get_daily_kline_akshare(code)

    def get_daily_kline_by_date(self, code: str, start_date, end_date) -> Optional[pd.DataFrame]:
        """根据日期范围获取K线数据"""
        try:
            if self._has_mootdx:
                start_str = start_date.strftime('%Y%m%d')
                end_str = end_date.strftime('%Y%m%d')

                df = self.client.bars(symbol=code)
                if df is not None and not df.empty:
                    df = df[['open', 'close', 'high', 'low', 'vol', 'amount']].copy()
                    df.columns = ['open', 'close', 'high', 'low', 'volume', 'amount']
                    df = df.reset_index()
                    df['date'] = pd.to_datetime(df['datetime']).dt.strftime('%Y-%m-%d')
                    df = df[['date', 'open', 'high', 'low', 'close', 'volume', 'amount']]
                    start_fmt = start_date.strftime('%Y-%m-%d')
                    end_fmt = end_date.strftime('%Y-%m-%d')
                    df = df[(df['date'] >= start_fmt) & (df['date'] <= end_fmt)]
                    return df
        except Exception as e:
            print(f"获取K线数据失败 (mootdx): {e}")

        return self._get_daily_kline_akshare_by_date(code, start_date, end_date)

    def get_realtime_daily(self, code: str) -> Optional[pd.DataFrame]:
        """只获取最新一天的日K数据（用于批量更新）"""
        try:
            if self._has_mootdx:
                df = self.client.bars(symbol=code, offset=1)
                if df is not None and not df.empty:
                    df = df[['open', 'close', 'high', 'low', 'vol', 'amount']].copy()
                    df.columns = ['open', 'close', 'high', 'low', 'volume', 'amount']
                    df = df.reset_index()
                    df['date'] = pd.to_datetime(df['datetime']).dt.strftime('%Y-%m-%d')
                    df = df[['date', 'open', 'high', 'low', 'close', 'volume', 'amount']]
                    return df
        except Exception as e:
            print(f"获取实时数据失败 (mootdx): {e}")
        return None

    def get_recent_kline(self, code: str, days: int = 5) -> Optional[pd.DataFrame]:
        """获取最近N天的K线数据（用于日常更新）"""
        import time
        try:
            if self._has_mootdx:
                df = self.client.bars(symbol=code, offset=days)
                if df is not None and not df.empty:
                    df = df[['open', 'close', 'high', 'low', 'vol', 'amount']].copy()
                    df.columns = ['open', 'close', 'high', 'low', 'volume', 'amount']
                    df = df.reset_index()
                    df['date'] = pd.to_datetime(df['datetime']).dt.strftime('%Y-%m-%d')
                    df = df[['date', 'open', 'high', 'low', 'close', 'volume', 'amount']]
                    return df
        except Exception as e:
            pass

        if not self._has_mootdx:
            self._reconnect()

        try:
            if self._has_mootdx:
                time.sleep(0.1)
                df = self.client.bars(symbol=code, offset=days)
                if df is not None and not df.empty:
                    df = df[['open', 'close', 'high', 'low', 'vol', 'amount']].copy()
                    df.columns = ['open', 'close', 'high', 'low', 'volume', 'amount']
                    df = df.reset_index()
                    df['date'] = pd.to_datetime(df['datetime']).dt.strftime('%Y-%m-%d')
                    df = df[['date', 'open', 'high', 'low', 'close', 'volume', 'amount']]
                    return df
        except Exception as e:
            pass

        return None

    def _get_daily_kline_akshare_by_date(self, code: str, start_date, end_date) -> Optional[pd.DataFrame]:
        """根据日期范围使用akshare获取K线数据"""
        try:
            import akshare as ak
            if code.startswith('6'):
                symbol = f"sh{code}"
            else:
                symbol = f"sz{code}"

            df = ak.stock_zh_a_hist(
                symbol=code,
                period="daily",
                start_date=start_date.strftime('%Y%m%d'),
                end_date=end_date.strftime('%Y%m%d'),
                adjust=""
            )
            if df is not None and not df.empty:
                df = df.rename(columns={
                    '日期': 'date',
                    '开盘': 'open',
                    '最高': 'high',
                    '最低': 'low',
                    '收盘': 'close',
                    '成交量': 'volume',
                    '成交额': 'amount'
                })
                df = df[['date', 'open', 'high', 'low', 'close', 'volume', 'amount']]
                return df
        except Exception as e:
            print(f"获取K线数据失败 (akshare): {e}")
        return None

    def _get_daily_kline_akshare(self, code: str) -> Optional[pd.DataFrame]:
        try:
            import akshare as ak
            if code.startswith('6'):
                symbol = f"sh{code}"
            else:
                symbol = f"sz{code}"

            df = ak.stock_zh_a_hist(
                symbol=code,
                period="daily",
                start_date=(datetime.now() - timedelta(days=400)).strftime('%Y%m%d'),
                end_date=datetime.now().strftime('%Y%m%d'),
                adjust=""
            )
            if df is not None and not df.empty:
                df = df.rename(columns={
                    '日期': 'date',
                    '开盘': 'open',
                    '最高': 'high',
                    '最低': 'low',
                    '收盘': 'close',
                    '成交量': 'volume',
                    '成交额': 'amount'
                })
                df = df[['date', 'open', 'high', 'low', 'close', 'volume', 'amount']]
                return df
        except Exception as e:
            print(f"获取K线数据失败 (akshare): {e}")
        return None

    def _get_market(self, code: str) -> int:
        if code.startswith('6'):
            return 1
        elif code.startswith('0') or code.startswith('3'):
            return 0
        return 0

    def get_realtime_quote(self, codes: List[str]) -> Optional[pd.DataFrame]:
        try:
            if self._has_mootdx:
                quotes = []
                for code in codes:
                    market = self._get_market(code)
                    try:
                        df = self.daily.daily(
                            code=code,
                            market=market,
                            start_date=datetime.now().strftime('%Y%m%d'),
                            end_date=datetime.now().strftime('%Y%m%d')
                        )
                        if df is not None and not df.empty:
                            df['code'] = code
                            quotes.append(df)
                    except:
                        continue

                if quotes:
                    result = pd.concat(quotes, ignore_index=True)
                    return result
        except Exception as e:
            print(f"获取实时行情失败: {e}")

        return self._get_realtime_quote_akshare(codes)

    def _get_realtime_quote_akshare(self, codes: List[str]) -> Optional[pd.DataFrame]:
        try:
            import akshare as ak
            df = ak.stock_zh_a_spot_em()
            if df is not None and not df.empty:
                symbols = [f"{'sh' if c.startswith('6') else 'sz'}{c}" for c in codes]
                df = df[df['代码'].isin(codes)]
                return df
        except Exception as e:
            print(f"获取实时行情失败 (akshare): {e}")
        return None

    def get_limit_up_data(self, date: str = None) -> Optional[pd.DataFrame]:
        if date is None:
            date = datetime.now().strftime('%Y%m%d')

        try:
            import akshare as ak
            df = ak.stock_zt_pool_em(date=date)
            if df is not None and not df.empty:
                return df
        except Exception as e:
            print(f"获取涨停数据失败: {e}")

        try:
            df = ak.stock_zt_pool_strong_em(date=date)
            if df is not None and not df.empty:
                return df
        except Exception as e:
            print(f"获取涨停数据失败 (备选): {e}")

        return None

    def get_limit_down_data(self, date: str = None) -> Optional[pd.DataFrame]:
        if date is None:
            date = datetime.now().strftime('%Y%m%d')

        try:
            import akshare as ak
            df = ak.stock_zt_pool_zbgc_em(date=date)
            if df is not None and not df.empty:
                return df
        except Exception as e:
            print(f"获取跌停数据失败: {e}")

        return None

    def get_sector_flow(self, indicator: str = "今日") -> Optional[pd.DataFrame]:
        try:
            import akshare as ak
            df = ak.stock_sector_fund_flow_rank(indicator=indicator, sector_type='行业资金流')
            if df is not None and not df.empty:
                return df
        except Exception as e:
            print(f"获取行业资金流向失败: {e}")

        try:
            import akshare as ak
            df = ak.stock_sector_spot()
            if df is not None and not df.empty:
                return df
        except Exception as e:
            print(f"获取板块资金流向失败 (备选): {e}")

        return None

    def get_sector_flow_hist(self, symbol: str) -> Optional[pd.DataFrame]:
        try:
            import akshare as ak
            df = ak.stock_sector_fund_flow_hist(symbol=symbol)
            if df is not None and not df.empty:
                return df
        except Exception as e:
            print(f"获取板块历史资金流向失败: {e}")
        return None

    def get_dragon_tiger_data(self, date: str = None) -> Optional[pd.DataFrame]:
        if date is None:
            date = datetime.now().strftime('%Y%m%d')

        try:
            import akshare as ak
            df = ak.stock_lhb_detail_em(start_date=date, end_date=date)
            if df is not None and not df.empty:
                return df
        except Exception as e:
            print(f"获取龙虎榜数据失败: {e}")

        return None

    def get_stock_info(self, code: str) -> Optional[Dict]:
        try:
            import akshare as ak
            df = ak.stock_individual_info_em(symbol=code)
            if df is not None and not df.empty:
                info_dict = dict(zip(df['item'], df['value']))
                return info_dict
        except Exception as e:
            print(f"获取股票信息失败: {e}")

        return None

    def get_all_a_stocks(self) -> pd.DataFrame:
        """获取所有A股股票列表"""
        try:
            import akshare as ak
            df = ak.stock_info_a_code_name()
            if df is not None and not df.empty:
                df = df.rename(columns={
                    '证券代码': 'code',
                    '证券名称': 'name'
                })
                return df
        except Exception as e:
            print(f"获取全市场股票列表失败: {e}")
        return pd.DataFrame()

    def get_all_stock_codes_full(self) -> List[str]:
        """获取全市场股票代码列表"""
        try:
            import akshare as ak
            df = ak.stock_info_a_code_name()
            if df is not None and not df.empty:
                return df['证券代码'].tolist()
        except Exception as e:
            print(f"获取全市场股票代码失败: {e}")
        return []


class TechnicalIndicators:
    @staticmethod
    def calculate_ma(data: pd.DataFrame, periods: List[int] = [5, 10, 20, 60]) -> pd.DataFrame:
        df = data.copy()
        for period in periods:
            df[f'ma{period}'] = df['close'].rolling(window=period).mean()
        return df

    @staticmethod
    def calculate_ema(data: pd.DataFrame, periods: List[int] = [12, 26]) -> pd.DataFrame:
        df = data.copy()
        for period in periods:
            df[f'ema{period}'] = df['close'].ewm(span=period, adjust=False).mean()
        return df

    @staticmethod
    def calculate_macd(data: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> pd.DataFrame:
        df = data.copy()
        df['ema_fast'] = df['close'].ewm(span=fast, adjust=False).mean()
        df['ema_slow'] = df['close'].ewm(span=slow, adjust=False).mean()
        df['macd'] = df['ema_fast'] - df['ema_slow']
        df['macd_signal'] = df['macd'].ewm(span=signal, adjust=False).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']
        return df

    @staticmethod
    def calculate_kdj(data: pd.DataFrame, n: int = 9, m1: int = 3, m2: int = 3) -> pd.DataFrame:
        df = data.copy()
        low_list = df['low'].rolling(window=n, min_periods=1).min()
        high_list = df['high'].rolling(window=n, min_periods=1).max()

        rsv = (df['close'] - low_list) / (high_list - low_list) * 100
        rsv = rsv.fillna(50)

        df['kdj_k'] = rsv.ewm(com=m1 - 1, adjust=False).mean()
        df['kdj_d'] = df['kdj_k'].ewm(com=m2 - 1, adjust=False).mean()
        df['kdj_j'] = 3 * df['kdj_k'] - 2 * df['kdj_d']

        return df

    @staticmethod
    def calculate_boll(data: pd.DataFrame, period: int = 20, std_dev: int = 2) -> pd.DataFrame:
        df = data.copy()
        df['boll_mid'] = df['close'].rolling(window=period).mean()
        df['boll_std'] = df['close'].rolling(window=period).std()
        df['boll_upper'] = df['boll_mid'] + std_dev * df['boll_std']
        df['boll_lower'] = df['boll_mid'] - std_dev * df['boll_std']
        return df

    @staticmethod
    def calculate_rsi(data: pd.DataFrame, periods: List[int] = [6, 12, 24]) -> pd.DataFrame:
        df = data.copy()
        for period in periods:
            delta = df['close'].diff()
            gain = delta.where(delta > 0, 0)
            loss = -delta.where(delta < 0, 0)
            avg_gain = gain.rolling(window=period).mean()
            avg_loss = loss.rolling(window=period).mean()
            rs = avg_gain / avg_loss
            df[f'rsi{period}'] = 100 - (100 / (1 + rs))
        return df

    @staticmethod
    def get_all_indicators(data: pd.DataFrame) -> pd.DataFrame:
        df = TechnicalIndicators.calculate_ma(data)
        df = TechnicalIndicators.calculate_macd(df)
        df = TechnicalIndicators.calculate_kdj(df)
        df = TechnicalIndicators.calculate_boll(df)
        df = TechnicalIndicators.calculate_rsi(df)
        return df


def predict_next_price(df: pd.DataFrame) -> float:
    latest = df.iloc[-1]
    prev = df.iloc[-2]

    weights = {
        'trend': 0.3,
        'macd': 0.25,
        'kdj': 0.2,
        'boll': 0.15,
        'ma': 0.1
    }

    predictions = []

    trend_weight = 0.5
    if latest['close'] > latest['ma5'] > latest['ma20'] > latest['ma60']:
        trend_weight = 0.8
    elif latest['close'] < latest['ma5'] < latest['ma20'] < latest['ma60']:
        trend_weight = 0.2

    price_change = (latest['close'] - prev['close']) / prev['close'] if prev['close'] != 0 else 0
    trend_pred = latest['close'] * (1 + price_change * trend_weight)
    predictions.append(trend_pred * weights['trend'])

    if latest['macd'] > latest['macd_signal']:
        macd_weight = 0.6
    else:
        macd_weight = 0.4
    macd_pred = latest['close'] * (1 + (latest['macd_hist'] / latest['close']) * macd_weight)
    predictions.append(macd_pred * weights['macd'])

    if latest['kdj_k'] > latest['kdj_d']:
        kdj_weight = 0.6
    else:
        kdj_weight = 0.4
    kdj_pred = latest['close'] * (1 + (latest['kdj_j'] - 50) / 500 * kdj_weight)
    predictions.append(kdj_pred * weights['kdj'])

    if latest['close'] > latest['boll_mid']:
        boll_weight = 0.6
    else:
        boll_weight = 0.4
    boll_pred = latest['close'] * (1 + (latest['close'] - latest['boll_mid']) / latest['boll_mid'] * boll_weight)
    predictions.append(boll_pred * weights['boll'])

    ma_pred = latest['close'] * (1 + (latest['ma5'] - latest['ma20']) / latest['ma20'] * 0.5)
    predictions.append(ma_pred * weights['ma'])

    predicted_price = sum(predictions)

    max_change = latest['close'] * 0.1
    predicted_price = max(latest['close'] - max_change, min(latest['close'] + max_change, predicted_price))

    return round(predicted_price, 2)


def calculate_confidence(df: pd.DataFrame) -> int:
    latest = df.iloc[-1]
    prev = df.iloc[-2]

    confidence = 50

    if latest['macd'] > latest['macd_signal'] and prev['macd'] <= prev['macd_signal']:
        confidence += 10

    if latest['kdj_k'] > latest['kdj_d'] and prev['kdj_k'] <= prev['kdj_d']:
        confidence += 10

    if latest['volume'] > latest['volume'] * 1.5:
        confidence += 10

    if abs(latest['rsi12'] - 50) > 20:
        confidence -= 5

    if latest['close'] > latest['ma20'] and latest['ma20'] > latest['ma60']:
        confidence += 5

    return max(30, min(95, confidence))


def generate_prediction_reasons(df: pd.DataFrame, latest) -> list:
    reasons = []

    if latest['macd'] > latest['macd_signal']:
        reasons.append("MACD处于金叉区域，红柱显示多头力量")
    else:
        reasons.append("MACD处于死叉区域，绿柱显示空头力量")

    if latest['kdj_k'] > latest['kdj_d']:
        reasons.append("KDJ形成金叉，短期看涨")
    else:
        reasons.append("KDJ形成死叉，短期看跌")

    if latest['kdj_j'] > 80:
        reasons.append("KDJ的J值超过80，处于超买区域，注意回调风险")
    elif latest['kdj_j'] < 20:
        reasons.append("KDJ的J值低于20，处于超卖区域，可能反弹")

    if latest['close'] > latest['boll_upper']:
        reasons.append("价格突破布林带上轨，可能有回调风险")
    elif latest['close'] < latest['boll_lower']:
        reasons.append("价格跌破布林带下轨，可能有反弹机会")

    if latest['rsi12'] > 70:
        reasons.append("RSI超过70，市场过热，注意风险")
    elif latest['rsi12'] < 30:
        reasons.append("RSI低于30，市场超卖，可能反弹")

    if latest['close'] > latest['ma20']:
        reasons.append("价格站稳20日均线，趋势向好")
    else:
        reasons.append("价格跌破20日均线，趋势偏弱")

    return reasons
