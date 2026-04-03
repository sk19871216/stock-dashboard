# 股票数据看板

基于 Streamlit 的自用股票情报追踪与缠论分析系统。

## 功能特性

### 页面导航（侧边栏顺序）
1. **数据更新** - 全市场股票数据批量更新（通达信 + akshare）
2. **情报追踪** - 自选股管理、触发指标筛选、大盘分析、涨跌停统计
3. **数据分析** - 涨跌停分析、板块资金流向、龙虎榜数据
4. **缠论分析** - 单股缠论买卖点分析、背驰判断、信号回测
5. **缠论选股** - 全市场缠论买点扫描
6. **股票预测** - 技术指标分析和明日股价预测
7. **复盘分析** - 预测与实际对比、准确率统计

## 技术栈

- **前端**: Streamlit (原生多页面架构)
- **数据获取**: mootdx (通达信, 优先), akshare (备选)
- **数据存储**: SQLite (daily 表)
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

### 其他表
- `stock_list` - 全市场股票列表
- `watchlist` - 自选股
- `triggered_stocks` - 触发指标股票
- `update_failed_stocks` - 更新失败的股票（用于重试）
- `predictions` - 预测记录
- `review_log` - 复盘记录

## 安装

```bash
pip install -r requirements.txt
```

主要依赖:
- streamlit >= 1.28.0
- mootdx >= 0.8.0 (通达信数据源)
- akshare >= 1.12.0 (备用数据源)
- pandas >= 2.0.0
- plotly >= 5.18.0

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

### 停牌股票处理
- 通达信会返回停牌假数据（成交量=0）
- `save_kline_data` 方法会自动过滤 `volume < 1` 的记录
- 数据库中只保留有真实交易的日期数据

### 批量更新
- 支持快速更新（最近N天）和全量更新
- 使用 ThreadPoolExecutor 并发处理
- 失败记录自动保存，可重试
- 每次更新前清空失败列表

## 项目结构

```
股票看板/
├── app.py                    # 主应用入口
├── config.py                 # 配置文件
├── requirements.txt           # 依赖清单
├── README.md                 # 本文档
├── pages/                    # Streamlit 多页面
│   ├── 1_数据更新.py        # 数据更新
│   ├── 2_情报追踪.py        # 情报追踪
│   ├── 3_数据分析.py        # 数据分析
│   ├── 4_缠论分析.py        # 缠论分析
│   ├── 5_缠论选股.py        # 缠论选股
│   ├── 6_股票预测.py         # 股票预测
│   └── 7_复盘分析.py         # 复盘分析
├── utils/                    # 工具模块
│   ├── database.py           # 数据库管理
│   ├── data_fetcher.py      # 数据获取
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

## 注意事项

⚠️ **免责声明**: 本系统所有数据和预测仅供参考，不构成投资建议。股市有风险，投资需谨慎！

- 数据依赖第三方接口，可能不稳定
- 预测基于历史数据，不能保证准确性
- 建议结合其他信息源综合判断

## GitHub

项目地址: https://github.com/sk19871216/stock-dashboard

## License

仅供个人学习使用，禁止商业用途。
