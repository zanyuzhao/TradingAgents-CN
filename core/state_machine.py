"""
策略状态机和迁移引擎
"""

from typing import Dict, Any, Optional
from datetime import datetime, timedelta
import logging

from core.data_structures import StrategyState, MarketRegime, StrategyInstance

class StateTransitionEngine:
    """状态迁移引擎"""

    def __init__(self):
        self.logger = logging.getLogger("StateTransitionEngine")

    def evaluate_transition(self,
                          strategy: StrategyInstance,
                          market_data: Dict[str, Any],
                          new_signals: Dict[str, Any],
                          risk_metrics: Dict[str, Any]) -> Optional[StrategyState]:
        """
        评估是否需要进行状态迁移

        Args:
            strategy: 当前策略实例
            market_data: 市场数据
            new_signals: 新的信号数据
            risk_metrics: 风险指标

        Returns:
            新的状态，如果不需要迁移则返回None
        """

        try:
            current_state = strategy.state

            # 状态迁移规则映射
            transition_evaluators = {
                StrategyState.WAITING: self._evaluate_from_waiting,
                StrategyState.READY_TO_ENTER: self._evaluate_from_ready,
                StrategyState.OPEN: self._evaluate_from_open,
                StrategyState.PYRAMIDING: self._evaluate_from_pyramiding,
                StrategyState.HOLDING: self._evaluate_from_holding,
                StrategyState.PARTIAL_EXIT: self._evaluate_from_partial_exit,
                StrategyState.EXITED: self._evaluate_from_exited,
                StrategyState.COOLDOWN: self._evaluate_from_cooldown,
                StrategyState.FORCE_EXIT: self._evaluate_from_force_exit,
                StrategyState.ERROR: self._evaluate_from_error
            }

            evaluator = transition_evaluators.get(current_state)
            if evaluator:
                return evaluator(strategy, market_data, new_signals, risk_metrics)

            return None

        except Exception as e:
            self.logger.error(f"状态迁移评估失败: {e}")
            return None

    def _evaluate_from_waiting(self, strategy: StrategyInstance,
                              market_data: Dict, new_signals: Dict,
                              risk_metrics: Dict) -> Optional[StrategyState]:
        """从WAITING状态的迁移逻辑"""

        # 检查冷却期是否结束
        if strategy.days_in_position < strategy.cooldown_days:
            return None

        # 检查是否有强信号
        overall_strength = self._calculate_overall_signal_strength(new_signals)
        if overall_strength >= 0.7:  # 进入阈值
            # 检查市场阶段是否支持
            supported_regimes = [MarketRegime.BULL_TREND_STRONG,
                               MarketRegime.BULL_TREND_WEAK,
                               MarketRegime.SIDEWAYS_HIGH_VOL]
            if strategy.regime in supported_regimes:
                return StrategyState.READY_TO_ENTER

        return None

    def _evaluate_from_ready(self, strategy: StrategyInstance,
                            market_data: Dict, new_signals: Dict,
                            risk_metrics: Dict) -> Optional[StrategyState]:
        """从READY_TO_ENTER状态的迁移逻辑"""

        current_price = market_data.get('current_price', 0)
        entry_threshold = new_signals.get('entry_threshold', 0)

        # 价格突破确认或触发买入条件
        if current_price >= entry_threshold:
            # 检查风险敞口
            portfolio_risk = risk_metrics.get('portfolio_exposure', 0)
            if portfolio_risk < 0.8:  # 最大80%仓位
                return StrategyState.OPEN

        # 信号减弱，回到等待
        overall_strength = self._calculate_overall_signal_strength(new_signals)
        if overall_strength < 0.5:
            return StrategyState.WAITING

        return None

    def _evaluate_from_open(self, strategy: StrategyInstance,
                           market_data: Dict, new_signals: Dict,
                           risk_metrics: Dict) -> Optional[StrategyState]:
        """从OPEN状态的迁移逻辑"""

        current_price = market_data.get('current_price', 0)

        # 检查止损
        if strategy.stop_loss and current_price <= strategy.stop_loss:
            return StrategyState.FORCE_EXIT

        # 检查止盈
        if strategy.take_profit and current_price >= strategy.take_profit:
            return StrategyState.EXITED

        # 检查是否可以加仓
        if (strategy.pyramid_steps < strategy.max_pyramid_steps and
            self._calculate_overall_signal_strength(new_signals) > strategy.signal_strength):
            return StrategyState.PYRAMIDING

        # 检查是否需要部分止盈
        if strategy.entry_price and current_price > 0:
            profit_ratio = (current_price - strategy.entry_price) / strategy.entry_price
            if profit_ratio >= 0.1:  # 10%盈利时考虑部分止盈
                return StrategyState.PARTIAL_EXIT

        # 正常持仓
        strategy.days_in_position += 1
        if strategy.days_in_position > 7:  # 持仓超过7天进入稳定持有
            return StrategyState.HOLDING

        return None

    def _evaluate_from_pyramiding(self, strategy: StrategyInstance,
                                 market_data: Dict, new_signals: Dict,
                                 risk_metrics: Dict) -> Optional[StrategyState]:
        """从PYRAMIDING状态的迁移逻辑"""

        current_price = market_data.get('current_price', 0)

        # 加仓完成回到OPEN状态
        if strategy.position >= strategy.target_size:
            return StrategyState.OPEN

        # 止损检查
        if strategy.stop_loss and current_price <= strategy.stop_loss:
            return StrategyState.FORCE_EXIT

        return None

    def _evaluate_from_holding(self, strategy: StrategyInstance,
                              market_data: Dict, new_signals: Dict,
                              risk_metrics: Dict) -> Optional[StrategyState]:
        """从HOLDING状态的迁移逻辑"""

        current_price = market_data.get('current_price', 0)

        # 检查止损
        if strategy.stop_loss and current_price <= strategy.stop_loss:
            return StrategyState.FORCE_EXIT

        # 检查止盈
        if strategy.take_profit and current_price >= strategy.take_profit:
            return StrategyState.EXITED

        # 检查最大持仓时间
        if strategy.days_in_position >= strategy.max_position_days:
            return StrategyState.EXITED

        # 检查市场阶段反转
        new_regime = new_signals.get('regime')
        if new_regime and self._is_regime_reversal(strategy.regime, new_regime):
            return StrategyState.EXITED

        strategy.days_in_position += 1
        return None

    def _evaluate_from_partial_exit(self, strategy: StrategyInstance,
                                   market_data: Dict, new_signals: Dict,
                                   risk_metrics: Dict) -> Optional[StrategyState]:
        """从PARTIAL_EXIT状态的迁移逻辑"""

        # 部分止盈后回到HOLDING
        return StrategyState.HOLDING

    def _evaluate_from_exited(self, strategy: StrategyInstance,
                             market_data: Dict, new_signals: Dict,
                             risk_metrics: Dict) -> Optional[StrategyState]:
        """从EXITED状态的迁移逻辑"""

        # 完成交易周期后进入冷却
        return StrategyState.COOLDOWN

    def _evaluate_from_cooldown(self, strategy: StrategyInstance,
                               market_data: Dict, new_signals: Dict,
                               risk_metrics: Dict) -> Optional[StrategyState]:
        """从COOLDOWN状态的迁移逻辑"""

        strategy.days_in_position += 1
        if strategy.days_in_position >= strategy.cooldown_days:
            # 重置持仓天数，重新进入等待
            strategy.days_in_position = 0
            return StrategyState.WAITING

        return None

    def _evaluate_from_force_exit(self, strategy: StrategyInstance,
                                 market_data: Dict, new_signals: Dict,
                                 risk_metrics: Dict) -> Optional[StrategyState]:
        """从FORCE_EXIT状态的迁移逻辑"""

        # 强制平仓后直接进入冷却
        return StrategyState.COOLDOWN

    def _evaluate_from_error(self, strategy: StrategyInstance,
                            market_data: Dict, new_signals: Dict,
                            risk_metrics: Dict) -> Optional[StrategyState]:
        """从ERROR状态的迁移逻辑"""

        # 错误恢复逻辑，可人工干预或自动重置
        if risk_metrics.get('data_quality', 1) > 0.9:
            return StrategyState.WAITING

        return None

    def _calculate_overall_signal_strength(self, signals: Dict[str, Any]) -> float:
        """计算综合信号强度"""
        if isinstance(signals, dict):
            # 如果是信号字典，计算加权平均
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
                if signal and hasattr(signal, 'strength'):
                    if hasattr(signal.strength, 'value'):
                        strength = signal.strength.value / 5  # 转换为0-1
                    else:
                        strength = 0
                    signal_strengths.append(strength * weight)

            return sum(signal_strengths) if signal_strengths else 0

        elif isinstance(signals, (int, float)):
            return min(signals, 1.0)  # 直接返回信号强度，限制在0-1

        return 0

    def _is_regime_reversal(self, current_regime: MarketRegime,
                           new_regime: Optional[MarketRegime]) -> bool:
        """检查市场阶段是否反转"""
        if not new_regime:
            return False

        reversal_pairs = [
            (MarketRegime.BULL_TREND_STRONG, MarketRegime.BEAR_TREND_STRONG),
            (MarketRegime.BULL_TREND_WEAK, MarketRegime.BEAR_TREND_WEAK),
            (MarketRegime.BEAR_TREND_STRONG, MarketRegime.BULL_TREND_STRONG),
            (MarketRegime.BEAR_TREND_WEAK, MarketRegime.BULL_TREND_WEAK),
        ]

        return (current_regime, new_regime) in reversal_pairs

class StrategyStateMachine:
    """策略状态机管理器"""

    def __init__(self, transition_engine: StateTransitionEngine = None):
        self.transition_engine = transition_engine or StateTransitionEngine()
        self.logger = logging.getLogger("StrategyStateMachine")

    def update_strategy_state(self,
                             strategy: StrategyInstance,
                             market_data: Dict[str, Any],
                             signals: Dict[str, Any],
                             risk_metrics: Dict[str, Any]) -> StrategyInstance:
        """
        更新策略状态

        Args:
            strategy: 当前策略实例
            market_data: 市场数据
            signals: 信号数据
            risk_metrics: 风险指标

        Returns:
            更新后的策略实例
        """

        try:
            # 评估状态迁移
            new_state = self.transition_engine.evaluate_transition(
                strategy, market_data, signals, risk_metrics
            )

            if new_state and new_state != strategy.state:
                # 执行状态迁移
                old_state = strategy.state
                strategy.state = new_state
                strategy.last_update = datetime.now()

                # 记录迁移历史
                self._record_state_transition(strategy, old_state, new_state, market_data, signals)

                self.logger.info(f"策略 {strategy.strategy_id} 状态迁移: {old_state.value} -> {new_state.value}")

            # 更新策略元数据
            self._update_strategy_metadata(strategy, signals, market_data)

            return strategy

        except Exception as e:
            self.logger.error(f"策略状态更新失败: {e}")
            # 发生错误时迁移到ERROR状态
            strategy.state = StrategyState.ERROR
            strategy.last_update = datetime.now()
            return strategy

    def _record_state_transition(self,
                                strategy: StrategyInstance,
                                old_state: StrategyState,
                                new_state: StrategyState,
                                market_data: Dict[str, Any],
                                signals: Dict[str, Any]) -> None:
        """记录状态迁移历史"""

        transition_record = {
            "timestamp": datetime.now().isoformat(),
            "from_state": old_state.value,
            "to_state": new_state.value,
            "trigger": self._identify_transition_trigger(old_state, new_state, signals, market_data),
            "market_snapshot": {
                "price": market_data.get('current_price'),
                "regime": strategy.regime.value
            }
        }

        strategy.history.append(transition_record)

    def _identify_transition_trigger(self,
                                    old_state: StrategyState,
                                    new_state: StrategyState,
                                    signals: Dict[str, Any],
                                    market_data: Dict[str, Any]) -> str:
        """识别状态迁移触发原因"""

        if new_state == StrategyState.OPEN:
            return "signal_strength_threshold_met"
        elif new_state == StrategyState.FORCE_EXIT:
            return "stop_loss_triggered"
        elif new_state == StrategyState.EXITED:
            return "take_profit_triggered"
        elif new_state == StrategyState.PYRAMIDING:
            return "signal_enhancement"
        elif new_state == StrategyState.PARTIAL_EXIT:
            return "partial_profit_taking"
        elif new_state == StrategyState.COOLDOWN:
            return "trade_cycle_complete"
        elif new_state == StrategyState.WAITING:
            return "cooldown_complete"
        else:
            return "automatic_transition"

    def _update_strategy_metadata(self,
                                 strategy: StrategyInstance,
                                 signals: Dict[str, Any],
                                 market_data: Dict[str, Any]) -> None:
        """更新策略元数据"""

        # 更新信号强度快照
        if isinstance(signals, dict):
            signal_strengths = {}
            for signal_type, signal in signals.items():
                if hasattr(signal, 'strength') and hasattr(signal.strength, 'value'):
                    signal_strengths[signal_type] = {
                        "direction": signal.direction if hasattr(signal, 'direction') else "unknown",
                        "strength": signal.strength.value,
                        "confidence": signal.confidence if hasattr(signal, 'confidence') else 0
                    }

            strategy.technical_snapshot = signal_strengths

        # 更新市场数据快照
        if market_data:
            strategy.sentiment_snapshot = {
                "current_price": market_data.get('current_price'),
                "volume": market_data.get('volume'),
                "volatility": market_data.get('volatility')
            }

    def get_strategy_summary(self, strategy: StrategyInstance) -> Dict[str, Any]:
        """获取策略摘要信息"""

        return {
            "strategy_id": strategy.strategy_id,
            "stock_code": strategy.stock_code,
            "strategy_name": strategy.strategy_name,
            "current_state": strategy.state.value,
            "regime": strategy.regime.value,
            "position": strategy.position,
            "signal_strength": strategy.signal_strength,
            "confidence_score": strategy.confidence_score,
            "days_in_position": strategy.days_in_position,
            "entry_price": strategy.entry_price,
            "current_pnl": self._calculate_current_pnl(strategy),
            "last_update": strategy.last_update.isoformat(),
            "history_count": len(strategy.history),
            "next_actions": self._get_next_state_actions(strategy.state)
        }

    def _calculate_current_pnl(self, strategy: StrategyInstance) -> float:
        """计算当前盈亏（简化实现）"""
        # 这里应该根据当前价格计算实际盈亏
        # 简化实现，返回0
        return 0.0

    def _get_next_state_actions(self, state: StrategyState) -> List[str]:
        """获取下一个状态的可能操作"""

        action_map = {
            StrategyState.WAITING: ["等待信号", "监控市场"],
            StrategyState.READY_TO_ENTER: ["准备入场", "设置买入条件"],
            StrategyState.OPEN: ["监控止损止盈", "考虑加仓"],
            StrategyState.PYRAMIDING: ["执行加仓", "风险控制"],
            StrategyState.HOLDING: ["长期持有", "定期检查"],
            StrategyState.PARTIAL_EXIT: ["部分止盈", "调整仓位"],
            StrategyState.EXITED: ["完成交易", "记录收益"],
            StrategyState.COOLDOWN: ["冷却期", "准备下一轮"],
            StrategyState.FORCE_EXIT: ["强制平仓", "风险控制"],
            StrategyState.ERROR: ["错误恢复", "重新评估"]
        }

        return action_map.get(state, ["等待处理"])

class StrategyStateMonitor:
    """策略状态监控器"""

    def __init__(self, state_machine: StrategyStateMachine):
        self.state_machine = state_machine
        self.logger = logging.getLogger("StrategyStateMonitor")

    def monitor_strategies(self, strategies: list) -> Dict[str, Any]:
        """监控多个策略的状态"""

        monitor_report = {
            "timestamp": datetime.now().isoformat(),
            "total_strategies": len(strategies),
            "state_distribution": {},
            "alert_strategies": [],
            "performance_summary": {}
        }

        for strategy in strategies:
            # 统计状态分布
            state_name = strategy.state.value
            monitor_report["state_distribution"][state_name] = \
                monitor_report["state_distribution"].get(state_name, 0) + 1

            # 检查需要关注的策略
            alert_conditions = self._check_alert_conditions(strategy)
            if alert_conditions:
                monitor_report["alert_strategies"].append({
                    "strategy_id": strategy.strategy_id,
                    "stock_code": strategy.stock_code,
                    "state": strategy.state.value,
                    "alerts": alert_conditions
                })

        return monitor_report

    def _check_alert_conditions(self, strategy: StrategyInstance) -> List[str]:
        """检查策略预警条件"""

        alerts = []

        # 长时间持仓预警
        if strategy.days_in_position > 20:
            alerts.append("持仓时间过长")

        # 信号强度下降预警
        if strategy.signal_strength < 0.3 and strategy.state in [StrategyState.OPEN, StrategyState.HOLDING]:
            alerts.append("信号强度过低")

        # 错误状态预警
        if strategy.state == StrategyState.ERROR:
            alerts.append("策略处于错误状态")

        # 风险状态预警
        if strategy.state == StrategyState.FORCE_EXIT:
            alerts.append("触发强制平仓")

        return alerts