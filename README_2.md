# TradingAgents-CN 2.0 🚀

基于4智能体架构的A股交易系统

## 🎯 项目简介

TradingAgents-CN 2.0 是一个基于大语言模型和传统量化分析的智能A股交易系统。系统采用全新的4智能体协作架构，实现了从分析决策到执行交易的完整闭环。

### 核心特性

- **🤖 4智能体协作**: 市场阶段识别、信号生成、策略选择、仓位管理
- **🔄 状态化管理**: 策略状态机确保交易决策的连续性和可追溯性
- **⚡ 实时回测**: 支持历史数据验证和参数优化
- **🛡️ 风险控制**: 多层次风险管理体系保障资金安全
- **📊 监控系统**: 完整的性能监控和预警机制

## 🧩 系统架构

### 智能体架构

```
🎯 Agent 1: 市场阶段识别 (Market Regime Classifier)
├── 识别牛市/熊市/震荡/事件驱动
├── 评估趋势强度
└── 输出: {regime, strength, confidence}

🧩 Agent 2: 信号生成 (Signal Generator)
├── 趋势信号 (Trend)
├── 动量信号 (Momentum)
├── 回调信号 (Pullback)
├── 价值信号 (Valuation)
├── 情绪信号 (Sentiment)
└── 风险信号 (Volatility)

🎯 Agent 3: 策略选择 (Strategy Selector)
├── 根据市场阶段选择适配策略
├── 综合评估信号权重
├── 考虑策略连续性
└── 输出: {chosen_strategy, weight, timing}

📊 Agent 4: 仓位管理 (Position Manager)
├── 固定风险R控制
├── ATR动态止损
├── 支持加仓/减仓
└── 输出: {position_size, stop_loss, take_profit}
```

### 策略状态机

```
WAITING → READY_TO_ENTER → OPEN → HOLDING → EXITED → COOLDOWN
    ↓           ↓              ↓        ↓         ↑
    └───────── PYRAMIDING ←─────────┴─────┘
```

## 🚀 快速开始

### 环境要求

- Python 3.8+
- MongoDB (可选)
- Redis (可选)

### 安装依赖

```bash
# 克隆项目
git clone <repository-url>
cd TradingAgents-CN

# 安装依赖
pip install pandas numpy matplotlib seaborn pymongo redis langchain

# 或使用requirements.txt
pip install -r requirements.txt
```

### 基本使用

#### 1. 回测模式

```bash
# 运行默认回测 (过去一年)
python run.py --mode backtest

# 指定日期范围
python run.py --mode backtest --start 2023-01-01 --end 2023-12-31

# 运行指定天数
python run.py --mode backtest --days 252

# 导出结果
python run.py --mode backtest --export
```

#### 2. 每日分析模式

```bash
# 分析今日
python run.py --mode daily

# 分析指定日期
python run.py --mode daily --date 2024-01-15
```

#### 3. 运行测试

```bash
# 运行系统测试
python test_system.py
```

## 📊 回测报告示例

```
📊 新架构回测报告
====================================

💰 收益指标:
总收益率: 15.67%
年化收益率: 18.23%
最大回撤: -8.45%

⚠️  风险指标:
年化波动率: 12.34%
夏普比率: 1.42
索提诺比率: 1.89
Beta: 0.85
Alpha: 3.45%

📈 交易指标:
总交易次数: 48
盈利交易: 32
亏损交易: 16
胜率: 66.67%
盈亏比: 1.85
平均持仓天数: 12.5
换手率: 2.34
```

## 📁 项目结构

```
TradingAgents-CN/
├── core/                      # 核心模块
│   ├── data_structures.py     # 数据结构定义
│   ├── base_agent.py          # 智能体基类
│   ├── state_machine.py       # 状态机引擎
│   └── persistence.py         # 持久化管理
├── agents/                    # 智能体实现
│   ├── market_regime_agent.py
│   ├── signal_generator_agent.py
│   ├── strategy_selector_agent.py
│   └── position_manager_agent.py
├── backtest/                  # 回测引擎
│   └── backtest_engine.py
├── run.py                     # 主程序入口
├── test_system.py             # 测试用例
└── README.md                  # 项目文档
```

## 🧪 系统测试

运行测试验证所有功能：

```bash
python test_system.py
```

测试包括：
- ✅ 市场阶段识别智能体
- ✅ 信号生成智能体 (6类信号)
- ✅ 策略选择智能体
- ✅ 仓位管理智能体
- ✅ 状态迁移引擎
- ✅ 回测引擎
- ✅ 持久化系统
- ✅ 完整工作流程

## 📈 核心优势

### 1. 状态化决策
- 策略状态机保证决策连续性
- 历史状态可追溯和分析
- 支持策略暂停、恢复、切换

### 2. 独立信号生成
- 6类信号独立生成，避免交叉污染
- 每类信号基于独立的逻辑和指标
- 便于信号权重调整和优化

### 3. 智能策略选择
- 根据市场阶段自动选择适配策略
- 考虑策略连续性，避免频繁切换
- 支持多策略并行运行

### 4. 精确仓位控制
- 4种仓位计算方法
- 动态风险调整
- 支持加仓、减仓、部分止盈

### 5. 完整回测框架
- 状态感知的回测引擎
- 详细的性能分析
- 支持策略参数优化

## ⚠️ 风险提示

本系统仅供学习和研究使用，不构成投资建议。实际交易存在风险，请谨慎使用。

## 📄 许可证

本项目采用 MIT 许可证