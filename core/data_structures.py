"""
核心数据结构和常量定义文件
"""

from enum import Enum
from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any, Union
from datetime import datetime
import json

class StrategyState(Enum):
    """策略状态枚举"""
    WAITING = "waiting"                # 等待信号
    READY_TO_ENTER = "ready_to_enter"  # 准备进场
    OPEN = "open"                      # 已开仓
    PYRAMIDING = "pyramiding"          # 加仓中
    HOLDING = "holding"                # 持仓追踪
    PARTIAL_EXIT = "partial_exit"      # 部分平仓
    EXITED = "exited"                  # 全部平仓
    COOLDOWN = "cooldown"              # 冷却期
    FORCE_EXIT = "force_exit"          # 强制平仓
    ERROR = "error"                    # 异常状态

class MarketRegime(Enum):
    """市场阶段枚举"""
    BULL_TREND_STRONG = "bull_trend_strong"      # 强牛市
    BULL_TREND_WEAK = "bull_trend_weak"          # 弱牛市
    BEAR_TREND_STRONG = "bear_trend_strong"      # 强熊市
    BEAR_TREND_WEAK = "bear_trend_weak"          # 弱熊市
    SIDEWAYS_HIGH_VOL = "sideways_high_vol"      # 高波动震荡
    SIDEWAYS_LOW_VOL = "sideways_low_vol"        # 低波动震荡
    EVENT_DRIVEN_POLICY = "event_driven_policy"  # 政策驱动
    EVENT_DRIVEN_EARNINGS = "event_driven_earnings"  # 财报驱动

class SignalType(Enum):
    """信号类型枚举"""
    TREND = "trend"                    # 趋势信号
    MOMENTUM = "momentum"              # 动量信号
    PULLBACK = "pullback"              # 回调信号
    VALUATION = "valuation"            # 价值信号
    SENTIMENT = "sentiment"            # 情绪信号
    VOLATILITY = "volatility"          # 风险信号

class SignalStrength(Enum):
    """信号强度枚举"""
    VERY_STRONG = 5    # 非常强
    STRONG = 4         # 强
    MODERATE = 3       # 中等
    WEAK = 2          # 弱
    VERY_WEAK = 1     # 非常弱
    NEUTRAL = 0       # 中性

class TradingStrategy(Enum):
    """交易策略枚举"""
    TREND_FOLLOW_HIGH_FREQ = "trend_follow_high_freq"      # 高频趋势跟随
    TREND_FOLLOW_MID_FREQ = "trend_follow_mid_freq"        # 中频趋势跟随
    REVERSION_LOW_FREQ = "reversion_low_freq"              # 低频反转策略
    FUNDAMENTAL_DRIVEN = "fundamental_driven"              # 基本面驱动策略
    MOMENTUM_BREAKOUT = "momentum_breakout"                # 动量突破策略
    SENTIMENT_REVERSAL = "sentiment_reversal"              # 情绪拐点策略
    VOLATILITY_TRADING = "volatility_trading"              # 波动率交易策略
    EVENT_DRIVEN = "event_driven"                          # 事件驱动策略
    NEUTRAL_HOLD = "neutral_hold"                          # 中性持有

class PositionAction(Enum):
    """仓位操作类型"""
    ENTER = "enter"                    # 开仓
    ADD_POSITION = "add_position"      # 加仓
    REDUCE_POSITION = "reduce_position" # 减仓
    EXIT_POSITION = "exit_position"    # 平仓
    MAINTAIN = "maintain"              # 维持不变
    WAIT = "wait"                      # 等待

class RiskMethod(Enum):
    """风险控制方法"""
    FIXED_RISK = "fixed_risk"          # 固定风险
    ATR_BASED = "atr_based"            # ATR基础
    VOLATILITY_BASED = "volatility_based"  # 波动率基础
    KELLY_CRITERION = "kelly_criterion"  # 凯利公式

@dataclass
class TradingSignal:
    """交易信号数据结构"""
    signal_type: SignalType
    direction: str  # "long", "short", "neutral", "high_risk", "medium_risk", "low_risk"
    strength: SignalStrength
    confidence: float  # 0-1
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    time_horizon: str = "short"  # "short", "medium", "long"
    evidence: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "signal_type": self.signal_type.value,
            "direction": self.direction,
            "strength": self.strength.value,
            "confidence": self.confidence,
            "entry_price": self.entry_price,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "time_horizon": self.time_horizon,
            "evidence": self.evidence,
            "timestamp": self.timestamp.isoformat()
        }

@dataclass
class StrategyRecommendation:
    """策略推荐结果"""
    chosen_strategy: TradingStrategy
    strategy_weight: float  # 0-1，策略权重/信心度
    entry_timing: str       # "immediate", "wait_pullback", "wait_breakout", "maintain"
    position_sizing: str    # "conservative", "moderate", "aggressive"
    time_horizon: str       # "short", "medium", "long"
    risk_level: str         # "low", "medium", "high"
    expected_return: float  # 预期收益率
    confidence_score: float # 0-1，综合置信度
    reasoning: List[str] = field(default_factory=list)    # 选择理由
    alternative_strategies: List[tuple] = field(default_factory=list)  # 备选策略
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "chosen_strategy": self.chosen_strategy.value,
            "strategy_weight": self.strategy_weight,
            "entry_timing": self.entry_timing,
            "position_sizing": self.position_sizing,
            "time_horizon": self.time_horizon,
            "risk_level": self.risk_level,
            "expected_return": self.expected_return,
            "confidence_score": self.confidence_score,
            "reasoning": self.reasoning,
            "alternative_strategies": [(s.value, w) for s, w in self.alternative_strategies],
            "timestamp": self.timestamp.isoformat()
        }

@dataclass
class PositionDecision:
    """仓位决策结果"""
    action: PositionAction
    target_position: float              # 目标仓位比例 (0-1)
    position_size: float                # 本次交易数量
    entry_price: Optional[float]        # 入场价格
    stop_loss: Optional[float]          # 止损价格
    take_profit: Optional[float]        # 止盈价格
    risk_amount: float                  # 风险金额
    expected_return: float              # 预期收益
    risk_reward_ratio: float            # 风险收益比
    position_method: RiskMethod         # 仓位计算方法
    execution_type: str                 # "immediate", "limit", "market"
    reasoning: List[str] = field(default_factory=list)    # 决策理由
    warnings: List[str] = field(default_factory=list)     # 风险提示
    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "action": self.action.value,
            "target_position": self.target_position,
            "position_size": self.position_size,
            "entry_price": self.entry_price,
            "stop_loss": self.stop_loss,
            "take_profit": self.take_profit,
            "risk_amount": self.risk_amount,
            "expected_return": self.expected_return,
            "risk_reward_ratio": self.risk_reward_ratio,
            "position_method": self.position_method.value,
            "execution_type": self.execution_type,
            "reasoning": self.reasoning,
            "warnings": self.warnings,
            "timestamp": self.timestamp.isoformat()
        }

@dataclass
class StrategyInstance:
    """策略实例数据模型"""
    # 基础信息
    strategy_id: str                    # 策略唯一标识
    stock_code: str                     # 股票代码
    strategy_name: str                  # 策略名称
    state: StrategyState                # 当前状态
    regime: MarketRegime                # 市场阶段

    # 仓位信息
    position: float = 0.0              # 当前仓位比例 (0-1)
    initial_size: float = 0.0          # 初始开仓比例
    target_size: float = 0.0           # 目标仓位比例

    # 价格和风险控制
    entry_price: Optional[float] = None     # 开仓价格
    entry_time: Optional[datetime] = None   # 开仓时间
    stop_loss: Optional[float] = None       # 止损价格
    trailing_stop: Optional[float] = None   # 追踪止损
    take_profit: Optional[float] = None     # 止盈价格

    # 策略参数
    signal_strength: float = 0.0            # 信号强度
    confidence_score: float = 0.0           # 置信度
    risk_budget: float = 0.01              # 风险预算 (例: 1%本金)

    # 时间和状态管理
    days_in_position: int = 0              # 持仓天数
    cooldown_days: int = 5                 # 冷却天数
    max_position_days: int = 30            # 最大持仓天数
    pyramid_steps: int = 0                 # 已加仓次数
    max_pyramid_steps: int = 3             # 最大加仓次数

    # 元数据和追踪
    last_update: datetime = field(default_factory=datetime.now)
    create_time: datetime = field(default_factory=datetime.now)
    history: List[Dict[str, Any]] = field(default_factory=list)  # 操作历史

    # 快照数据（用于回测分析）
    technical_snapshot: Optional[Dict[str, Any]] = None
    sentiment_snapshot: Optional[Dict[str, Any]] = None
    fundamentals_snapshot: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "strategy_id": self.strategy_id,
            "stock_code": self.stock_code,
            "strategy_name": self.strategy_name,
            "state": self.state.value,
            "regime": self.regime.value,
            "position": self.position,
            "initial_size": self.initial_size,
            "target_size": self.target_size,
            "entry_price": self.entry_price,
            "entry_time": self.entry_time.isoformat() if self.entry_time else None,
            "stop_loss": self.stop_loss,
            "trailing_stop": self.trailing_stop,
            "take_profit": self.take_profit,
            "signal_strength": self.signal_strength,
            "confidence_score": self.confidence_score,
            "risk_budget": self.risk_budget,
            "days_in_position": self.days_in_position,
            "cooldown_days": self.cooldown_days,
            "max_position_days": self.max_position_days,
            "pyramid_steps": self.pyramid_steps,
            "max_pyramid_steps": self.max_pyramid_steps,
            "last_update": self.last_update.isoformat(),
            "create_time": self.create_time.isoformat(),
            "history": self.history,
            "technical_snapshot": self.technical_snapshot,
            "sentiment_snapshot": self.sentiment_snapshot,
            "fundamentals_snapshot": self.fundamentals_snapshot
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'StrategyInstance':
        """从字典创建实例"""
        # 处理枚举类型
        if isinstance(data.get('state'), str):
            data['state'] = StrategyState(data['state'])
        if isinstance(data.get('regime'), str):
            data['regime'] = MarketRegime(data['regime'])

        # 处理时间类型
        if data.get('entry_time'):
            data['entry_time'] = datetime.fromisoformat(data['entry_time'])
        if data.get('last_update'):
            data['last_update'] = datetime.fromisoformat(data['last_update'])
        if data.get('create_time'):
            data['create_time'] = datetime.fromisoformat(data['create_time'])

        return cls(**data)

@dataclass
class BacktestConfig:
    """回测配置"""
    start_date: datetime
    end_date: datetime
    initial_capital: float
    benchmark: str = "000300.SH"  # 沪深300作为基准
    commission_rate: float = 0.0003  # 手续费率
    slippage_rate: float = 0.001     # 滑点率
    max_position_size: float = 0.15  # 单只股票最大仓位
    rebalance_frequency: str = "daily"  # "daily", "weekly", "monthly"
    risk_free_rate: float = 0.03      # 无风险收益率

@dataclass
class BacktestResult:
    """回测结果"""
    total_return: float
    annual_return: float
    max_drawdown: float
    sharpe_ratio: float
    sortino_ratio: float
    win_rate: float
    profit_loss_ratio: float
    beta: float
    alpha: float
    volatility: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    avg_holding_period: float
    turnover_rate: float

# 系统常量
SYSTEM_CONSTANTS = {
    "DEFAULT_RISK_PER_TRADE": 0.01,      # 默认单笔风险1%
    "DEFAULT_MAX_POSITION": 0.15,        # 默认单股最大仓位15%
    "DEFAULT_PORTFOLIO_RISK": 0.02,      # 默认投资组合风险2%
    "DEFAULT_MIN_RISK_REWARD": 2.0,      # 默认最小风险收益比
    "MAX_PYRAMID_STEPS": 3,              # 最大加仓次数
    "PYRAMID_STEP_SIZE": 0.3,            # 加仓步长30%
    "COOLDOWN_DAYS": 5,                  # 默认冷却天数
    "MAX_POSITION_DAYS": 30,             # 最大持仓天数
    "CACHE_TTL": 3600,                   # 缓存TTL（秒）
    "MAX_CONCURRENT_STRATEGIES": 20,     # 最大并发策略数
    "MARKET_OPEN_TIME": "09:30",         # 市场开盘时间
    "MARKET_CLOSE_TIME": "15:00",        # 市场收盘时间
}

# 市场阶段策略映射
REGIME_STRATEGY_MAPPING = {
    "bull_trend_strong": [
        TradingStrategy.TREND_FOLLOW_HIGH_FREQ,
        TradingStrategy.MOMENTUM_BREAKOUT,
        TradingStrategy.FUNDAMENTAL_DRIVEN
    ],
    "bull_trend_weak": [
        TradingStrategy.TREND_FOLLOW_MID_FREQ,
        TradingStrategy.MOMENTUM_BREAKOUT,
        TradingStrategy.REVERSION_LOW_FREQ
    ],
    "bear_trend_strong": [
        TradingStrategy.REVERSION_LOW_FREQ,
        TradingStrategy.VOLATILITY_TRADING,
        TradingStrategy.SENTIMENT_REVERSAL
    ],
    "bear_trend_weak": [
        TradingStrategy.REVERSION_LOW_FREQ,
        TradingStrategy.TREND_FOLLOW_MID_FREQ,
        TradingStrategy.NEUTRAL_HOLD
    ],
    "sideways_high_vol": [
        TradingStrategy.VOLATILITY_TRADING,
        TradingStrategy.REVERSION_LOW_FREQ,
        TradingStrategy.MOMENTUM_BREAKOUT
    ],
    "sideways_low_vol": [
        TradingStrategy.NEUTRAL_HOLD,
        TradingStrategy.FUNDAMENTAL_DRIVEN,
        TradingStrategy.REVERSION_LOW_FREQ
    ],
    "event_driven_policy": [
        TradingStrategy.EVENT_DRIVEN,
        TradingStrategy.MOMENTUM_BREAKOUT,
        TradingStrategy.SENTIMENT_REVERSAL
    ],
    "event_driven_earnings": [
        TradingStrategy.EVENT_DRIVEN,
        TradingStrategy.FUNDAMENTAL_DRIVEN,
        TradingStrategy.VOLATILITY_TRADING
    ]
}

# 策略默认配置
STRATEGY_DEFAULTS = {
    TradingStrategy.TREND_FOLLOW_HIGH_FREQ: {
        "default_time_horizon": "short",
        "risk_level": "high",
        "max_position": 0.12
    },
    TradingStrategy.TREND_FOLLOW_MID_FREQ: {
        "default_time_horizon": "medium",
        "risk_level": "medium",
        "max_position": 0.10
    },
    TradingStrategy.MOMENTUM_BREAKOUT: {
        "default_time_horizon": "short",
        "risk_level": "high",
        "max_position": 0.08
    },
    TradingStrategy.REVERSION_LOW_FREQ: {
        "default_time_horizon": "long",
        "risk_level": "medium",
        "max_position": 0.10
    },
    TradingStrategy.FUNDAMENTAL_DRIVEN: {
        "default_time_horizon": "long",
        "risk_level": "low",
        "max_position": 0.15
    },
    TradingStrategy.SENTIMENT_REVERSAL: {
        "default_time_horizon": "medium",
        "risk_level": "medium",
        "max_position": 0.08
    },
    TradingStrategy.VOLATILITY_TRADING: {
        "default_time_horizon": "short",
        "risk_level": "high",
        "max_position": 0.06
    },
    TradingStrategy.EVENT_DRIVEN: {
        "default_time_horizon": "short",
        "risk_level": "medium",
        "max_position": 0.10
    },
    TradingStrategy.NEUTRAL_HOLD: {
        "default_time_horizon": "long",
        "risk_level": "low",
        "max_position": 0.05
    }
}

# 状态迁移规则
STATE_TRANSITION_RULES = {
    StrategyState.WAITING: {
        "to": [StrategyState.READY_TO_ENTER],
        "conditions": ["signal_strength >= 0.7", "regime_support", "cooldown_ended"]
    },
    StrategyState.READY_TO_ENTER: {
        "to": [StrategyState.OPEN, StrategyState.WAITING],
        "conditions": ["price_breakout", "risk_budget_ok"]
    },
    StrategyState.OPEN: {
        "to": [StrategyState.PYRAMIDING, StrategyState.PARTIAL_EXIT, StrategyState.HOLDING,
               StrategyState.FORCE_EXIT, StrategyState.EXITED],
        "conditions": ["signal_enhanced", "profit_target", "stop_loss", "max_days_reached"]
    },
    StrategyState.PYRAMIDING: {
        "to": [StrategyState.OPEN, StrategyState.FORCE_EXIT],
        "conditions": ["pyramid_complete", "stop_loss"]
    },
    StrategyState.HOLDING: {
        "to": [StrategyState.EXITED, StrategyState.FORCE_EXIT],
        "conditions": ["regime_reversal", "profit_target", "stop_loss", "max_days"]
    },
    StrategyState.PARTIAL_EXIT: {
        "to": [StrategyState.HOLDING],
        "conditions": ["partial_exit_complete"]
    },
    StrategyState.EXITED: {
        "to": [StrategyState.COOLDOWN],
        "conditions": ["trade_complete"]
    },
    StrategyState.COOLDOWN: {
        "to": [StrategyState.WAITING],
        "conditions": ["cooldown_complete"]
    },
    StrategyState.FORCE_EXIT: {
        "to": [StrategyState.COOLDOWN],
        "conditions": ["force_exit_complete"]
    }
}

def is_trading_day(date: datetime) -> bool:
    """判断是否为交易日"""
    # 排除周末
    if date.weekday() >= 5:
        return False

    # 这里可以添加节假日排除逻辑
    # 例如：使用节假日数据源排除非交易日

    return True

def get_next_trading_day(date: datetime) -> datetime:
    """获取下一个交易日"""
    next_day = date + timedelta(days=1)
    while not is_trading_day(next_day):
        next_day += timedelta(days=1)
    return next_day

def calculate_trading_days(start_date: datetime, end_date: datetime) -> List[datetime]:
    """计算两个日期之间的所有交易日"""
    trading_days = []
    current_date = start_date

    while current_date <= end_date:
        if is_trading_day(current_date):
            trading_days.append(current_date)
        current_date += timedelta(days=1)

    return trading_days