"""
Agent 3: 策略选择与权重智能体 (Strategy Selector)
"""

from typing import Dict, Any, List, Tuple, Optional
from datetime import datetime
import numpy as np

from core.data_structures import (
    TradingStrategy, MarketRegime, StrategyRecommendation,
    REGIME_STRATEGY_MAPPING, STRATEGY_DEFAULTS
)
from core.base_agent import BaseAgent

class StrategySelectorAgent(BaseAgent):
    """
    策略选择与权重智能体

    职责：
    1. 根据市场阶段 + 5类信号选择最适合的策略
    2. 评估每个策略的适用性和权重
    3. 提供策略执行的具体建议
    4. 考虑现有策略状态的连续性
    """

    def __init__(self):
        super().__init__("StrategySelector")
        # 策略权重配置
        self.strategy_weights = {
            "market_regime_weight": 0.30,    # 市场阶段权重
            "signal_weight": 0.40,           # 综合信号权重
            "risk_weight": 0.20,             # 风险控制权重
            "continuity_weight": 0.10        # 策略连续性权重
        }

    def select_strategy(self,
                       regime: MarketRegime,
                       signals: Dict[str, Any],
                       current_strategy: Optional[Any] = None,
                       portfolio_state: Dict[str, Any] = None) -> StrategyRecommendation:
        """
        选择最适合的交易策略

        Args:
            regime: 市场阶段
            signals: 各类信号数据
            current_strategy: 当前策略状态（如有）
            portfolio_state: 投资组合状态

        Returns:
            StrategyRecommendation: 策略推荐结果
        """

        try:
            # 1. 评估各策略的适用性
            strategy_scores = self._evaluate_strategy_applicability(regime, signals)

            # 2. 考虑策略连续性
            if current_strategy:
                strategy_scores = self._apply_strategy_continuity(
                    strategy_scores, current_strategy, signals
                )

            # 3. 风险调整
            strategy_scores = self._adjust_for_risk(strategy_scores, signals, portfolio_state)

            # 4. 选择最优策略
            chosen_strategy, max_score = max(strategy_scores.items(), key=lambda x: x[1])

            # 5. 生成策略执行建议
            execution_params = self._generate_execution_params(
                chosen_strategy, regime, signals, current_strategy
            )

            # 6. 选择备选策略
            alternative_strategies = self._select_alternatives(
                strategy_scores, chosen_strategy, max_score
            )

            return StrategyRecommendation(
                chosen_strategy=chosen_strategy,
                strategy_weight=max_score,
                entry_timing=execution_params["entry_timing"],
                position_sizing=execution_params["position_sizing"],
                time_horizon=execution_params["time_horizon"],
                risk_level=execution_params["risk_level"],
                expected_return=execution_params["expected_return"],
                confidence_score=execution_params["confidence_score"],
                reasoning=execution_params["reasoning"],
                alternative_strategies=alternative_strategies,
                timestamp=datetime.now()
            )

        except Exception as e:
            self.logger.error(f"策略选择失败: {e}")
            # 返回默认策略
            return self._get_default_strategy()

    def _evaluate_strategy_applicability(self,
                                        regime: MarketRegime,
                                        signals: Dict[str, Any]) -> Dict[TradingStrategy, float]:
        """评估各策略的适用性评分"""

        strategy_scores = {}

        # 获取适用策略列表
        applicable_strategies = REGIME_STRATEGY_MAPPING.get(regime.value, [])

        for strategy in TradingStrategy:
            base_score = 0

            # 基础适用性评分
            if strategy in applicable_strategies:
                base_score += 0.6
            else:
                base_score += 0.2  # 不适用策略给予基础分

            # 根据信号类型调整评分
            strategy_score = self._adjust_score_by_signals(strategy, signals, base_score)

            strategy_scores[strategy] = strategy_score

        return strategy_scores

    def _adjust_score_by_signals(self,
                                strategy: TradingStrategy,
                                signals: Dict[str, Any],
                                base_score: float) -> float:
        """根据各类信号调整策略评分"""

        adjusted_score = base_score
        signal_weights = {
            "trend": 0.25,
            "momentum": 0.20,
            "pullback": 0.15,
            "valuation": 0.15,
            "sentiment": 0.15,
            "volatility": 0.10
        }

        # 趋势策略评分调整
        if strategy in [TradingStrategy.TREND_FOLLOW_HIGH_FREQ,
                       TradingStrategy.TREND_FOLLOW_MID_FREQ]:
            trend_signal = signals.get("trend")
            if trend_signal and hasattr(trend_signal, 'direction') and trend_signal.direction != "neutral":
                trend_bonus = trend_signal.strength.value / 5  # 转换为0-1
                adjusted_score += trend_bonus * signal_weights["trend"]

        # 动量策略评分调整
        if strategy in [TradingStrategy.MOMENTUM_BREAKOUT]:
            momentum_signal = signals.get("momentum")
            if momentum_signal and hasattr(momentum_signal, 'direction') and momentum_signal.direction != "neutral":
                momentum_bonus = momentum_signal.strength.value / 5
                adjusted_score += momentum_bonus * signal_weights["momentum"]

        # 反转策略评分调整
        if strategy in [TradingStrategy.REVERSION_LOW_FREQ]:
            pullback_signal = signals.get("pullback")
            if pullback_signal and hasattr(pullback_signal, 'direction') and pullback_signal.direction != "neutral":
                pullback_bonus = pullback_signal.strength.value / 5
                adjusted_score += pullback_bonus * signal_weights["pullback"]

        # 基本面策略评分调整
        if strategy in [TradingStrategy.FUNDAMENTAL_DRIVEN]:
            valuation_signal = signals.get("valuation")
            if valuation_signal and hasattr(valuation_signal, 'direction') and valuation_signal.direction != "neutral":
                valuation_bonus = valuation_signal.strength.value / 5
                adjusted_score += valuation_bonus * signal_weights["valuation"]

        # 情绪策略评分调整
        if strategy in [TradingStrategy.SENTIMENT_REVERSAL]:
            sentiment_signal = signals.get("sentiment")
            if sentiment_signal and hasattr(sentiment_signal, 'direction') and sentiment_signal.direction != "neutral":
                sentiment_bonus = sentiment_signal.strength.value / 5
                adjusted_score += sentiment_bonus * signal_weights["sentiment"]

        # 波动率策略评分调整
        if strategy in [TradingStrategy.VOLATILITY_TRADING]:
            volatility_signal = signals.get("volatility")
            if volatility_signal and hasattr(volatility_signal, 'direction') and volatility_signal.direction != "low_risk":
                volatility_bonus = volatility_signal.strength.value / 5
                adjusted_score += volatility_bonus * signal_weights["volatility"]

        return min(adjusted_score, 1.0)

    def _apply_strategy_continuity(self,
                                  strategy_scores: Dict[TradingStrategy, float],
                                  current_strategy: Any,
                                  new_signals: Dict[str, Any]) -> Dict[TradingStrategy, float]:
        """应用策略连续性调整"""

        current_strategy_name = getattr(current_strategy, 'strategy_name', '')
        strategy_state = getattr(current_strategy, 'state', None)

        # 将策略名称转换为枚举
        current_strategy_enum = None
        for strategy_enum in TradingStrategy:
            if current_strategy_name in strategy_enum.value:
                current_strategy_enum = strategy_enum
                break

        if not current_strategy_enum:
            return strategy_scores

        # 如果当前策略表现良好，给予加分
        performance_bonus = 0

        # 持仓盈利策略保持性
        if strategy_state and hasattr(strategy_state, 'value'):
            if strategy_state.value in ['OPEN', 'HOLDING']:
                overall_strength = self._calculate_overall_signal_strength(new_signals)
                if overall_strength > getattr(current_strategy, 'signal_strength', 0):
                    performance_bonus += 0.1  # 信号增强，保持策略
                else:
                    performance_bonus -= 0.1  # 信号减弱，考虑调整

            # 策略在加仓阶段
            elif strategy_state.value == 'PYRAMIDING':
                performance_bonus += 0.2  # 加仓策略保持连续性

            # 策略即将完成
            elif strategy_state.value in ['PARTIAL_EXIT', 'EXITED']:
                performance_bonus -= 0.3  # 准备切换策略

        # 应用连续性调整
        adjusted_scores = strategy_scores.copy()
        if current_strategy_enum in adjusted_scores:
            adjusted_scores[current_strategy_enum] += performance_bonus

        return adjusted_scores

    def _adjust_for_risk(self,
                        strategy_scores: Dict[TradingStrategy, float],
                        signals: Dict[str, Any],
                        portfolio_state: Dict[str, Any]) -> Dict[TradingStrategy, float]:
        """基于风险因素调整策略评分"""

        risk_signal = signals.get("volatility")
        if not risk_signal:
            return strategy_scores

        adjusted_scores = strategy_scores.copy()

        # 根据风险等级调整
        if hasattr(risk_signal, 'direction'):
            if risk_signal.direction == "high_risk":
                # 高风险环境，降低激进策略评分
                aggressive_strategies = [
                    TradingStrategy.TREND_FOLLOW_HIGH_FREQ,
                    TradingStrategy.MOMENTUM_BREAKOUT
                ]
                for strategy in aggressive_strategies:
                    adjusted_scores[strategy] *= 0.7

                # 提高保守策略评分
                conservative_strategies = [
                    TradingStrategy.REVERSION_LOW_FREQ,
                    TradingStrategy.NEUTRAL_HOLD
                ]
                for strategy in conservative_strategies:
                    adjusted_scores[strategy] *= 1.2

            elif risk_signal.direction == "low_risk":
                # 低风险环境，可以适当激进
                aggressive_strategies = [
                    TradingStrategy.TREND_FOLLOW_HIGH_FREQ,
                    TradingStrategy.MOMENTUM_BREAKOUT
                ]
                for strategy in aggressive_strategies:
                    adjusted_scores[strategy] *= 1.1

        # 投资组合风险调整
        if portfolio_state:
            portfolio_exposure = portfolio_state.get("exposure", 0.5)
            if portfolio_exposure > 0.8:  # 仓位过高，降低高风险策略
                high_risk_strategies = [
                    TradingStrategy.TREND_FOLLOW_HIGH_FREQ,
                    TradingStrategy.VOLATILITY_TRADING
                ]
                for strategy in high_risk_strategies:
                    adjusted_scores[strategy] *= 0.8

        return adjusted_scores

    def _generate_execution_params(self,
                                  strategy: TradingStrategy,
                                  regime: MarketRegime,
                                  signals: Dict[str, Any],
                                  current_strategy: Optional[Any]) -> Dict[str, Any]:
        """生成策略执行参数"""

        # 基础执行参数
        base_params = STRATEGY_DEFAULTS.get(strategy, {
            "default_time_horizon": "medium",
            "risk_level": "medium",
            "max_position": 0.08
        })

        # 根据信号强度调整
        overall_strength = self._calculate_overall_signal_strength(signals)

        # 时间框架
        time_horizon = base_params["default_time_horizon"]
        if overall_strength > 0.8:
            time_horizon = "short"  # 强信号，短期执行
        elif overall_strength < 0.4:
            time_horizon = "long"   # 弱信号，长期观察

        # 入场时机
        entry_timing = self._determine_entry_timing(strategy, signals, current_strategy)

        # 仓位大小
        position_sizing = self._determine_position_sizing(strategy, overall_strength, regime)

        # 风险等级
        risk_level = self._assess_strategy_risk(strategy, signals, regime)

        # 预期收益
        expected_return = self._estimate_expected_return(strategy, regime, overall_strength)

        # 置信度
        confidence_score = min(overall_strength + 0.2, 1.0)

        # 选择理由
        reasoning = self._generate_reasoning(strategy, regime, signals, current_strategy)

        return {
            "entry_timing": entry_timing,
            "position_sizing": position_sizing,
            "time_horizon": time_horizon,
            "risk_level": risk_level,
            "expected_return": expected_return,
            "confidence_score": confidence_score,
            "reasoning": reasoning
        }

    def _calculate_overall_signal_strength(self, signals: Dict[str, Any]) -> float:
        """计算综合信号强度"""

        signal_strengths = []
        signal_weights = {
            "trend": 0.25,
            "momentum": 0.20,
            "pullback": 0.15,
            "valuation": 0.15,
            "sentiment": 0.15,
            "volatility": 0.10
        }

        for signal_type, weight in signal_weights.items():
            signal = signals.get(signal_type)
            if signal and hasattr(signal, 'strength') and hasattr(signal.strength, 'value'):
                # 将信号强度转换为0-1，中性信号计为0
                if hasattr(signal, 'direction') and signal.direction == "neutral":
                    strength = 0
                else:
                    strength = signal.strength.value / 5  # very_strong=1, ..., weak=0.2
                signal_strengths.append(strength * weight)

        return sum(signal_strengths) if signal_strengths else 0

    def _determine_entry_timing(self,
                               strategy: TradingStrategy,
                               signals: Dict[str, Any],
                               current_strategy: Optional[Any]) -> str:
        """确定入场时机"""

        if current_strategy:
            strategy_state = getattr(current_strategy, 'state', None)
            if hasattr(strategy_state, 'value') and strategy_state.value in ['OPEN', 'HOLDING']:
                return "maintain"  # 维持现有仓位

        pullback_signal = signals.get("pullback")
        momentum_signal = signals.get("momentum")

        if strategy in [TradingStrategy.TREND_FOLLOW_HIGH_FREQ, TradingStrategy.MOMENTUM_BREAKOUT]:
            if momentum_signal and hasattr(momentum_signal, 'strength') and momentum_signal.strength.value >= 4:
                return "immediate"  # 强动量，立即入场
            elif pullback_signal and hasattr(pullback_signal, 'strength') and pullback_signal.strength.value >= 3:
                return "wait_pullback"  # 等待回调
            else:
                return "wait_breakout"  # 等待突破

        elif strategy in [TradingStrategy.REVERSION_LOW_FREQ]:
            if pullback_signal and hasattr(pullback_signal, 'strength') and pullback_signal.strength.value >= 4:
                return "immediate"  # 深度回调，立即入场
            else:
                return "wait_pullback"

        elif strategy in [TradingStrategy.FUNDAMENTAL_DRIVEN]:
            return "immediate"  # 基本面策略可以分批建仓

        else:
            return "immediate"

    def _determine_position_sizing(self,
                                  strategy: TradingStrategy,
                                  signal_strength: float,
                                  regime: MarketRegime) -> str:
        """确定仓位大小策略"""

        # 基础仓位等级
        if signal_strength > 0.8:
            base_sizing = "aggressive"
        elif signal_strength > 0.5:
            base_sizing = "moderate"
        else:
            base_sizing = "conservative"

        # 根据市场阶段调整
        if regime in [MarketRegime.BULL_TREND_STRONG]:
            if base_sizing == "conservative":
                return "moderate"
        elif regime in [MarketRegime.BEAR_TREND_STRONG]:
            if base_sizing == "aggressive":
                return "moderate"
            elif base_sizing == "moderate":
                return "conservative"

        return base_sizing

    def _assess_strategy_risk(self,
                             strategy: TradingStrategy,
                             signals: Dict[str, Any],
                             regime: MarketRegime) -> str:
        """评估策略风险等级"""

        risk_factors = []

        # 策略固有风险
        strategy_risk_map = {
            TradingStrategy.TREND_FOLLOW_HIGH_FREQ: "high",
            TradingStrategy.MOMENTUM_BREAKOUT: "high",
            TradingStrategy.TREND_FOLLOW_MID_FREQ: "medium",
            TradingStrategy.VOLATILITY_TRADING: "high",
            TradingStrategy.EVENT_DRIVEN: "medium",
            TradingStrategy.REVERSION_LOW_FREQ: "medium",
            TradingStrategy.SENTIMENT_REVERSAL: "medium",
            TradingStrategy.FUNDAMENTAL_DRIVEN: "low",
            TradingStrategy.NEUTRAL_HOLD: "low"
        }

        strategy_risk = strategy_risk_map.get(strategy, "medium")
        risk_factors.append(strategy_risk)

        # 市场阶段风险
        regime_risk_map = {
            MarketRegime.BULL_TREND_STRONG: "medium",
            MarketRegime.BEAR_TREND_STRONG: "high",
            MarketRegime.SIDEWAYS_HIGH_VOL: "medium",
            MarketRegime.SIDEWAYS_LOW_VOL: "low",
            MarketRegime.EVENT_DRIVEN_POLICY: "high",
            MarketRegime.EVENT_DRIVEN_EARNINGS: "high"
        }

        regime_risk = regime_risk_map.get(regime, "medium")
        risk_factors.append(regime_risk)

        # 风险信号影响
        volatility_signal = signals.get("volatility")
        if volatility_signal and hasattr(volatility_signal, 'direction'):
            risk_factors.append(volatility_signal.direction)

        # 综合风险评级
        high_risk_count = sum(1 for r in risk_factors if r == "high")
        medium_risk_count = sum(1 for r in risk_factors if r == "medium")

        if high_risk_count >= 2:
            return "high"
        elif high_risk_count >= 1 or medium_risk_count >= 2:
            return "medium"
        else:
            return "low"

    def _estimate_expected_return(self,
                                 strategy: TradingStrategy,
                                 regime: MarketRegime,
                                 signal_strength: float) -> float:
        """估算预期收益率"""

        # 基础收益率
        base_returns = {
            TradingStrategy.TREND_FOLLOW_HIGH_FREQ: 0.15,    # 15%
            TradingStrategy.MOMENTUM_BREAKOUT: 0.12,         # 12%
            TradingStrategy.TREND_FOLLOW_MID_FREQ: 0.10,     # 10%
            TradingStrategy.VOLATILITY_TRADING: 0.08,        # 8%
            TradingStrategy.EVENT_DRIVEN: 0.10,              # 10%
            TradingStrategy.REVERSION_LOW_FREQ: 0.06,        # 6%
            TradingStrategy.SENTIMENT_REVERSAL: 0.07,        # 7%
            TradingStrategy.FUNDAMENTAL_DRIVEN: 0.05,        # 5%
            TradingStrategy.NEUTRAL_HOLD: 0.02               # 2%
        }

        base_return = base_returns.get(strategy, 0.08)

        # 市场阶段调整
        regime_multipliers = {
            MarketRegime.BULL_TREND_STRONG: 1.5,
            MarketRegime.BULL_TREND_WEAK: 1.2,
            MarketRegime.BEAR_TREND_STRONG: 0.7,
            MarketRegime.BEAR_TREND_WEAK: 0.9,
            MarketRegime.SIDEWAYS_HIGH_VOL: 1.0,
            MarketRegime.SIDEWAYS_LOW_VOL: 0.8,
            MarketRegime.EVENT_DRIVEN_POLICY: 1.3,
            MarketRegime.EVENT_DRIVEN_EARNINGS: 1.2
        }

        regime_multiplier = regime_multipliers.get(regime, 1.0)

        # 信号强度调整
        signal_multiplier = 0.5 + signal_strength  # 0.5-1.5

        expected_return = base_return * regime_multiplier * signal_multiplier

        return min(expected_return, 0.25)  # 限制最大预期收益25%

    def _generate_reasoning(self,
                           strategy: TradingStrategy,
                           regime: MarketRegime,
                           signals: Dict[str, Any],
                           current_strategy: Optional[Any]) -> List[str]:
        """生成策略选择理由"""

        reasoning = []

        # 市场阶段匹配
        if strategy in REGIME_STRATEGY_MAPPING.get(regime.value, []):
            reasoning.append(f"策略适合当前{regime.value}市场阶段")

        # 信号支撑
        key_signals = []
        signal_map = {
            TradingStrategy.TREND_FOLLOW_HIGH_FREQ: ["trend"],
            TradingStrategy.MOMENTUM_BREAKOUT: ["momentum", "trend"],
            TradingStrategy.REVERSION_LOW_FREQ: ["pullback"],
            TradingStrategy.FUNDAMENTAL_DRIVEN: ["valuation"],
            TradingStrategy.SENTIMENT_REVERSAL: ["sentiment"],
            TradingStrategy.VOLATILITY_TRADING: ["volatility"]
        }

        relevant_signals = signal_map.get(strategy, [])
        for signal_type in relevant_signals:
            signal = signals.get(signal_type)
            if signal and hasattr(signal, 'direction') and signal.direction != "neutral" and hasattr(signal, 'strength') and signal.strength.value >= 3:
                key_signals.append(signal_type)

        if key_signals:
            reasoning.append(f"获得{', '.join(key_signals)}信号支撑")

        # 风险考虑
        volatility_signal = signals.get("volatility")
        if volatility_signal and hasattr(volatility_signal, 'direction'):
            if volatility_signal.direction == "low_risk":
                reasoning.append("当前市场风险较低，适合主动策略")
            elif volatility_signal.direction == "high_risk":
                reasoning.append("市场风险较高，采用相对保守的策略")

        # 策略连续性
        if current_strategy:
            strategy_state = getattr(current_strategy, 'state', None)
            if hasattr(strategy_state, 'value'):
                if strategy_state.value in ['OPEN', 'HOLDING']:
                    reasoning.append("考虑维持现有策略的连续性")
                elif strategy_state.value in ['EXITED', 'COOLDOWN']:
                    reasoning.append("当前策略已完成，选择新的策略机会")

        if not reasoning:
            reasoning.append("基于综合分析选择最优策略")

        return reasoning

    def _select_alternatives(self,
                           strategy_scores: Dict[TradingStrategy, float],
                           chosen_strategy: TradingStrategy,
                           chosen_score: float) -> List[Tuple[TradingStrategy, float]]:
        """选择备选策略"""

        # 过滤掉主策略，按分数排序
        alternatives = []
        for strategy, score in strategy_scores.items():
            if strategy != chosen_strategy and score > 0.5:  # 至少0.5分才考虑
                alternatives.append((strategy, score))

        # 按分数排序，取前2个
        alternatives.sort(key=lambda x: x[1], reverse=True)
        return alternatives[:2]

    def _get_default_strategy(self) -> StrategyRecommendation:
        """获取默认策略推荐"""
        return StrategyRecommendation(
            chosen_strategy=TradingStrategy.NEUTRAL_HOLD,
            strategy_weight=0.3,
            entry_timing="wait",
            position_sizing="conservative",
            time_horizon="long",
            risk_level="low",
            expected_return=0.02,
            confidence_score=0.3,
            reasoning=["系统错误，使用默认保守策略"],
            alternative_strategies=[],
            timestamp=datetime.now()
        )