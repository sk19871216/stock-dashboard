# 股票数据看板

基于 Streamlit 的自用股票情报追踪与缠论分析系统。

## 功能特性

### 页面导航（侧边栏顺序）
1. **数据更新** - 全市场股票数据批量更新（通达信 + akshare）
2. **市场情绪分析** - 板块资金流向、涨跌停统计、市场情绪指标
3. **热门个股** - 东财股吧热门个股排行、历史数据回溯
4. **缠论分析** - 单股缠论买卖点分析、背驰判断、信号回测
5. **情报追踪** - 自选股管理、触发指标筛选，大盘分析
6. **数据分析** - 涨跌停分析、龙虎榜数据
7. **股票预测** - 技术指标分析和明日股价预测
8. **复盘分析** - 预测与实际对比、准确率统计
9. **K线训练** - 交互式K线训练、AI辅助分析、交易复盘

### 市场情绪分析页面功能

#### 板块资金流向
- **数据来源**: 同花顺行业板块数据
- **数据获取**: 支持获取第1页和第2页全部板块数据（约90个板块）
- **日期选择**: 可选择任意日期存入/查看历史数据
- **柱状图展示**: 主力净流入TOP15横向柱状图（绿色=净流入，红色=净流出）
- **数据表格**: 展示所有板块的涨跌幅和主力净流入数据

#### 涨跌停统计
- **涨停列表**: 显示涨停股票、连板数、所属板块
- **跌停列表**: 显示跌停股票及所属板块
- **板块分布**: 饼图展示涨跌停股票的板块分布

### 热门个股页面功能

#### 数据来源
- **东财股吧**: 从东方财富股吧排行榜获取热门个股数据
- **Selenium抓取**: 使用Selenium动态抓取页面数据

#### 数据展示
- **排名**: 热门排名序号
- **代码**: 股票代码
- **名称**: 股票名称
- **涨跌幅**: 当日涨跌幅
- **排名变动**: 相比上一期的排名变化

#### 日期筛选
- 支持按日期查看历史数据
- 数据存入SQLite数据库，可追溯历史

### K线训练页面功能

#### 训练模式
- **预加载**: 获取最多300天历史数据
- **显示**: 显示200天K线给用户分析
- **训练**: 从第200天开始，训练剩余的100天（或1/3数据）

#### 交易规则
- **买入**: 用当前剩余资金全部买入（满仓）
- **卖出**: 卖出全部持仓（清仓）
- **观望**: 记录当前状态，不进行买卖

#### 图表功能
- **K线图**: 显示K线、MA5/MA10/MA20均线、成交量
- **成交量**: 阳线红色量柱，阴线绿色量柱
- **当前日期**: 虚线标记训练开始位置
- **买卖标记**: 气泡注释显示在图顶部

#### 技术指标
- **MACD**: 显示MACD线、Signal线和Histogram柱状图
- **RSI**: 显示RSI6/RSI12/RSI24三条线

#### 收益计算
- 总市值 = 剩余资金 + 持仓股数 × 当前股价
- 收益率 = (总市值 - 初始资金) / 初始资金 × 100%

## 技术栈

- **前端**: Streamlit (原生多页面架构)
- **数据获取**: mootdx (通达信, 优先), akshare (备选), Selenium (网页抓取)
- **数据存储**: SQLite (daily 表、板块资金流向表、热门个股表等)
- **技术分析**: pandas, numpy, plotly

## 数据库结构

### daily 表（K线数据）
```sql
CREATE TABLE daily (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    date TEXT NOT NULL,        -- 日期 YYYY-MM-DD
    code TEXT NOT NULL,       -- 股票代码
    open REAL,                 -- 开盘价
    close REAL,                -- 收盘价
    high REAL,                 -- 最高价
    low REAL,                  -- 最低价
    volume REAL,               -- 成交量
    amount REAL,               -- 成交额
    amplitude REAL,            -- 振幅
    pct_chg REAL,              -- 涨跌幅
    chg REAL,                  -- 涨跌额
    turnover REAL,             -- 换手率
    valid_data INTEGER DEFAULT 1,
    UNIQUE(date, code)
);
```

### sector_flow_history 表（板块资金流向）
```sql
CREATE TABLE sector_flow_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_date TEXT NOT NULL,      -- 交易日期
    sector_name TEXT NOT NULL,     -- 板块名称
    main_net_inflow REAL,          -- 主力净流入（亿元）
    change_pct REAL,               -- 涨跌幅(%)
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(trade_date, sector_name)
);
```

### hot_stocks 表（热门个股）
```sql
CREATE TABLE hot_stocks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_date TEXT NOT NULL,      -- 日期
    rank INTEGER,                  -- 排名
    code TEXT NOT NULL,            -- 股票代码
    name TEXT,                     -- 股票名称
    change_pct REAL,               -- 涨跌幅
    rank_change INTEGER,           -- 排名变动
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(trade_date, code)
);
```

### 其他表
- `stock_list` - 全市场股票列表
- `watchlist` - 自选股
- `triggered_stocks` - 触发指标股票
- `update_failed_stocks` - 更新失败的股票（用于重试）
- `predictions` - 预测记录
- `review_log` - 复盘记录
- `limit_up_history` - 涨停历史
- `limit_down_history` - 跌停历史
- `industry_data` - 行业板块数据

## 安装

```bash
pip install -r requirements.txt
```

主要依赖:
- streamlit >= 1.28.0
- mootdx >= 0.8.0 (通达信数据源)
- akshare >= 1.12.0 (备用数据源)
- selenium >= 4.0.0 (网页抓取)
- pandas >= 2.0.0
- plotly >= 5.18.0
- beautifulsoup4 >= 4.12.0

## 运行

```bash
cd f:\trae_project\股票看板
streamlit run app.py
```

访问 http://localhost:8501

## 数据更新说明

### 通达信 (mootdx)
- 优先级高，速度快
- 需连接通达信服务器
- 支持实时数据获取

### akshare
- 备选数据源
- 速度较慢
- 用于通达信失败时的补充

### 同花顺板块数据
- 从 https://q.10jqka.com.cn/thshy/ 抓取
- 支持分页获取全部板块数据
- 数据包括：板块名称、涨跌幅、主力净流入等

### 东财热门个股
- 从 https://guba.eastmoney.com/rank/ 抓取
- 使用Selenium动态加载页面
- 支持排名变动分析

### 停牌股票处理
- 通达信会返回停牌假数据（成交量=0）
- `save_kline_data` 方法会自动过滤 `volume < 1` 的记录
- 数据库中只保留有真实交易的日期数据

### 批量更新
- 支持三种更新模式：
  - **快速更新** - 更新最近N天的数据
  - **区间更新** - 更新指定日期范围内的数据
  - **全部更新** - 更新股票的所有历史数据
- 使用 ThreadPoolExecutor 并发处理，提高更新速度
- 失败记录自动保存，支持重试（区分不同更新模式）
- 每次更新前清空失败列表

## 项目结构

```
股票看板/
├── app.py                    # 主应用入口
├── config.py                 # 配置文件
├── requirements.txt           # 依赖清单
├── README.md                 # 本文档
├── .streamlit/              # Streamlit 配置
│   └── config.toml          # Streamlit 设置
├── pages/                    # Streamlit 多页面
│   ├── 1_数据更新.py        # 数据更新
│   ├── 2_市场情绪分析.py    # 市场情绪分析（板块资金、涨跌停）
│   ├── 3_热门个股.py        # 热门个股排行
│   ├── 4_缠论分析.py        # 缠论分析
│   ├── 5_情报追踪.py        # 情报追踪
│   ├── 6_数据分析.py        # 数据分析
│   ├── 7_股票预测.py         # 股票预测
│   ├── 8_复盘分析.py         # 复盘分析
│   └── 9_K线训练.py         # K线训练
├── utils/                    # 工具模块
│   ├── database.py           # 数据库管理
│   ├── data_fetcher.py      # 数据获取
│   ├── hot_stocks_fetcher.py # 热门个股抓取
│   ├── technical_analysis.py # 技术指标计算
│   └── styles.py             # 样式工具
├── chanlun/                  # 缠论模块
│   ├── fenxing_with_macd.py # 分型识别
│   ├── trend_analysis.py     # 趋势分析
│   └── chanlun_signals.py   # 买卖点信号
└── data/                    # 数据存储
    └── stock_data.db         # SQLite 数据库
```

## 常见问题

### Q: 数据更新失败率高
A: 检查网络连接和通达信服务器状态。可使用 akshare 作为备选。

### Q: 如何处理停牌股票
A: 系统自动过滤成交量<1的记录，不写入数据库。

### Q: 如何重试失败的更新
A: 在"数据更新"页面，失败区域会显示"重试失败股票"按钮。

### Q: mootdx 连接失败
A: 检查通达信服务器是否运行，IP和端口是否正确。代码会自动切换到 akshare 备选。

### Q: 缠论分型判断逻辑
A: 分型需要前后都有独立K线才会确认，不在头尾补充分型。

### Q: 板块数据获取不完整
A: 系统会自动获取第1页和第2页数据，确保获取全部约90个板块。

## 注意事项

⚠️ **免责声明**: 本系统所有数据和预测仅供参考，不构成投资建议。股市有风险，投资需谨慎！

- 数据依赖第三方接口，可能不稳定
- 预测基于历史数据，不能保证准确性
- 建议结合其他信息源综合判断

## GitHub

项目地址: https://github.com/sk19871216/stock-dashboard

## License

仅供个人学习使用，禁止商业用途。
