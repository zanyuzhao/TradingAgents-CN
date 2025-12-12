"""
Agent 4: 仓位管理智能体 (Position Sizer)
"""

from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
import numpy as np

from core.data_structures import (
    PositionAction, PositionDecision, RiskMethod, TradingStrategy,
    StrategyInstance, StrategyRecommendation, SYSTEM_CONSTANTS
)
from core.base_agent import BaseAgent

class PositionManagerAgent(BaseAgent):
    """
    仓位管理智能体

    职责：
    1. 基于策略+风险预算计算精确仓位
    2. 实现固定风险R、ATR控制、趋势强度控制
    3. 支持仓位递增(pyramiding)和递减(partial exit)
    4. 提供详细的风险控制参数
    """

    def __init__(self, initial_capital: float = 1000000):
        super().__init__("PositionManager")
        self.initial_capital = initial_capital
        self.current_capital = initial_capital

        # 风险控制参数
        self.risk_params = {
            "max_single_position": SYSTEM_CONSTANTS["DEFAULT_MAX_POSITION"],
            "max_portfolio_risk": SYSTEM_CONSTANTS["DEFAULT_PORTFOLIO_RISK"],
            "risk_per_trade": SYSTEM_CONSTANTS["DEFAULT_RISK_PER_TRADE"],
            "min_risk_reward": SYSTEM_CONSTANTS["DEFAULT_MIN_RISK_REWARD"],
            "max_pyramid_steps": SYSTEM_CONSTANTS["MAX_PYRAMID_STEPS"],
            "pyramid_step_size": SYSTEM_CONSTANTS["PYRAMID_STEP_SIZE"],
            "partial_exit_levels": [0.1, 0.2, 0.3],  # 10%, 20%, 30%盈利时部分止盈
            "partial_exit_ratios": [0.3, 0.3, 0.4]   # 对应止盈比例
        }

        # 当前持仓状态
        self.current_positions = {}
        self.portfolio_risk = 0

    def calculate_position(self,
                          strategy_recommendation: StrategyRecommendation,
                          current_strategy: Optional[StrategyInstance] = None,
                          market_data: Dict[str, Any] = None,
                          portfolio_state: Dict[str, Any] = None) -> PositionDecision:
        """
        计算目标仓位和交易参数

        Args:
            strategy_recommendation: 策略推荐结果
            current_strategy: 当前策略状态
            market_data: 市场数据
            portfolio_state: 投资组合状态

        Returns:
            PositionDecision: 详细的仓位决策
        """

        try:
            # 1. 确定基本操作类型
            base_action = self._determine_base_action(strategy_recommendation, current_strategy)

            # 2. 选择仓位计算方法
            position_method = self._select_position_method(
                strategy_recommendation, market_data, current_strategy
            )

            # 3. 计算基础仓位
            base_position = self._calculate_base_position(
                strategy_recommendation, position_method, market_data
            )

            # 4. 应用仓位调整
            adjusted_position = self._apply_position_adjustments(
                base_position, strategy_recommendation, current_strategy, portfolio_state
            )

            # 5. 计算交易参数
            trade_params = self._calculate_trade_parameters(
                adjusted_position, market_data, position_method, current_strategy
            )

            # 6. 风险控制检查
            risk_check = self._risk_control_check(
                adjusted_position, trade_params, portfolio_state
            )

            # 7. 生成最终决策
            final_decision = self._generate_position_decision(
                base_action, adjusted_position, trade_params,
                risk_check, strategy_recommendation, current_strategy
            )

            return final_decision

        except Exception as e:
            self.logger.error(f"仓位计算失败: {e}")
            return self._get_neutral_decision()

    def _determine_base_action(self,
                               strategy_rec: StrategyRecommendation,
                               current_strategy: Optional[StrategyInstance]) -> PositionAction:
        """确定基本操作类型"""

        if not current_strategy:
            # 无当前策略，判断是否开仓
            if strategy_rec.confidence_score > 0.6:
                return PositionAction.ENTER
            else:
                return PositionAction.WAIT

        # 有当前策略，根据状态决定操作
        state = current_strategy.state

        if state.value == "WAITING":
            if strategy_rec.confidence_score > 0.7:
                return PositionAction.ENTER
            else:
                return PositionAction.WAIT

        elif state.value in ["READY_TO_ENTER", "OPEN"]:
            if strategy_rec.strategy_weight > current_strategy.signal_strength:
                return PositionAction.ADD_POSITION
            elif strategy_rec.strategy_weight < current_strategy.signal_strength * 0.7:
                return PositionAction.REDUCE_POSITION
            else:
                return PositionAction.MAINTAIN

        elif state.value == "PYRAMIDING":
            if strategy_rec.strategy_weight > 0.8:
                return PositionAction.ADD_POSITION
            else:
                return PositionAction.MAINTAIN

        elif state.value == "HOLDING":
            if strategy_rec.strategy_weight < 0.3:
                return PositionAction.EXIT_POSITION
            else:
                return PositionAction.MAINTAIN

        elif state.value == "PARTIAL_EXIT":
            return PositionAction.REDUCE_POSITION

        elif state.value in ["EXITED", "COOLDOWN"]:
            return PositionAction.WAIT

        elif state.value == "FORCE_EXIT":
            return PositionAction.EXIT_POSITION

        else:
            return PositionAction.MAINTAIN

    def _select_position_method(self,
                               strategy_rec: StrategyRecommendation,
                               market_data: Dict[str, Any],
                               current_strategy: Optional[StrategyInstance]) -> RiskMethod:
        """选择仓位计算方法"""

        # 根据策略类型和市场条件选择计算方法
        if strategy_rec.chosen_strategy in [TradingStrategy.TREND_FOLLOW_HIGH_FREQ,
                                           TradingStrategy.MOMENTUM_BREAKOUT]:
            # 趋势和动量策略使用ATR方法
            return RiskMethod.ATR_BASED

        elif strategy_rec.chosen_strategy in [TradingStrategy.VOLATILITY_TRADING]:
            # 波动率交易使用波动率基础方法
            return RiskMethod.VOLATILITY_BASED

        elif strategy_rec.chosen_strategy in [TradingStrategy.FUNDAMENTAL_DRIVEN]:
            # 基本面策略使用凯利公式
            return RiskMethod.KELLY_CRITERION

        else:
            # 默认使用固定风险方法
            return RiskMethod.FIXED_RISK

    def _calculate_base_position(self,
                                strategy_rec: StrategyRecommendation,
                                method: RiskMethod,
                                market_data: Dict[str, Any]) -> float:
        """计算基础仓位比例"""

        if not market_data:
            return 0

        current_price = market_data.get('current_price', 0)
        if current_price <= 0:
            return 0

        if method == RiskMethod.FIXED_RISK:
            return self._calculate_fixed_risk_position(strategy_rec, market_data)

        elif method == RiskMethod.ATR_BASED:
            return self._calculate_atr_position(strategy_rec, market_data)

        elif method == RiskMethod.VOLATILITY_BASED:
            return self._calculate_volatility_position(strategy_rec, market_data)

        elif method == RiskMethod.KELLY_CRITERION:
            return self._calculate_kelly_position(strategy_rec, market_data)

        else:
            return 0

    def _calculate_fixed_risk_position(self,
                                      strategy_rec: StrategyRecommendation,
                                      market_data: Dict[str, Any]) -> float:
        """固定风险方法计算仓位"""

        current_price = market_data.get('current_price', 0)
        stop_loss_price = market_data.get('stop_loss_price', current_price * 0.95)

        # 计算每股风险
        risk_per_share = abs(current_price - stop_loss_price)
        if risk_per_share <= 0:
            return 0

        # 计算最大允许仓位
        max_risk_amount = self.current_capital * self.risk_params["risk_per_trade"]
        max_shares = max_risk_amount / risk_per_share
        max_position_value = max_shares * current_price

        # 转换为仓位比例
        base_position = min(
            max_position_value / self.current_capital,
            self.risk_params["max_single_position"]
        )

        # 根据策略信心度调整
        confidence_adjusted = base_position * strategy_rec.confidence_score

        # 根据仓位大小策略调整
        sizing_multiplier = {
            "conservative": 0.6,
            "moderate": 0.8,
            "aggressive": 1.0
        }

        multiplier = sizing_multiplier.get(strategy_rec.position_sizing, 0.8)

        return confidence_adjusted * multiplier

    def _calculate_atr_position(self,
                               strategy_rec: StrategyRecommendation,
                               market_data: Dict[str, Any]) -> float:
        """ATR方法计算仓位"""

        current_price = market_data.get('current_price', 0)
        atr = market_data.get('atr', current_price * 0.02)

        # 使用2倍ATR作为止损距离
        stop_distance = 2 * atr
        if stop_distance <= 0:
            return 0

        # 计算风险金额
        risk_per_share = stop_distance
        max_risk_amount = self.current_capital * self.risk_params["risk_per_trade"]
        max_shares = max_risk_amount / risk_per_share
        max_position_value = max_shares * current_price

        # 转换为仓位比例
        base_position = min(
            max_position_value / self.current_capital,
            self.risk_params["max_single_position"]
        )

        # 根据趋势强度调整
        trend_multiplier = min(strategy_rec.strategy_weight * 1.2, 1.0)

        return base_position * trend_multiplier

    def _calculate_volatility_position(self,
                                      strategy_rec: StrategyRecommendation,
                                      market_data: Dict[str, Any]) -> float:
        """波动率方法计算仓位"""

        current_price = market_data.get('current_price', 0)
        volatility = market_data.get('volatility', 0.2)

        # 根据波动率调整仓位：高波动率降低仓位
        volatility_adjustment = min(1.0 / (1 + volatility * 5), 1.0)

        # 基础仓位
        base_position = self.risk_params["max_single_position"] * 0.5

        # 应用波动率调整
        volatility_adjusted = base_position * volatility_adjustment

        # 根据策略信心度调整
        return volatility_adjusted * strategy_rec.confidence_score

    def _calculate_kelly_position(self,
                                 strategy_rec: StrategyRecommendation,
                                 market_data: Dict[str, Any]) -> float:
        """凯利公式计算仓位"""

        win_rate = strategy_rec.confidence_score  # 假设置信度近似胜率
        avg_win = strategy_rec.expected_return
        avg_loss = self.risk_params["risk_per_trade"]

        # 凯利公式: f* = (bp - q) / b
        # b = 平均盈利/平均亏损, p = 胜率, q = 败率
        if avg_loss <= 0:
            return 0

        b = avg_win / avg_loss
        p = win_rate
        q = 1 - win_rate

        kelly_fraction = (b * p - q) / b

        # 限制凯利比例，避免过度集中
        limited_kelly = max(0, min(kelly_fraction, 0.25))  # 限制在25%以内

        # 应用安全系数（通常使用凯利公式的一半）
        safe_kelly = limited_kelly * 0.5

        return min(safe_kelly, self.risk_params["max_single_position"])

    def _apply_position_adjustments(self,
                                   base_position: float,
                                   strategy_rec: StrategyRecommendation,
                                   current_strategy: Optional[StrategyInstance],
                                   portfolio_state: Dict[str, Any]) -> float:
        """应用仓位调整"""

        adjusted_position = base_position

        # 1. 投资组合暴露度调整
        if portfolio_state:
            current_exposure = portfolio_state.get("total_exposure", 0)
            max_exposure = 0.8  # 最大80%仓位

            if current_exposure + adjusted_position > max_exposure:
                adjusted_position = max_exposure - current_exposure

            # 集中度调整（同一行业/板块限制）
            industry_exposure = self._calculate_industry_exposure(
                strategy_rec, portfolio_state
            )
            max_industry_exposure = 0.3  # 单一行业最大30%

            if industry_exposure + adjusted_position > max_industry_exposure:
                adjusted_position = max_industry_exposure - industry_exposure

        # 2. 流动性调整
        liquidity_score = self._assess_liquidity(strategy_rec, portfolio_state)
        if liquidity_score < 0.5:  # 低流动性降低仓位
            adjusted_position *= liquidity_score

        # 3. 策略连续性调整
        if current_strategy:
            if current_strategy.state.value == "PYRAMIDING":
                # 加仓步骤，限制加仓幅度
                step_size = self.risk_params["pyramid_step_size"]
                max_add_position = current_strategy.initial_size * step_size
                adjusted_position = min(adjusted_position, max_add_position)

            elif current_strategy.state.value == "PARTIAL_EXIT":
                # 部分止盈，只减仓
                adjusted_position = min(adjusted_position, current_strategy.position * 0.5)

        # 4. 市场条件调整
        if portfolio_state:
            market_condition = portfolio_state.get("market_condition", "normal")
            if market_condition == "crisis":
                adjusted_position *= 0.3  # 危机时期大幅减仓
            elif market_condition == "correction":
                adjusted_position *= 0.6  # 调整时期适度减仓

        return max(0, adjusted_position)

    def _calculate_trade_parameters(self,
                                   target_position: float,
                                   market_data: Dict[str, Any],
                                   method: RiskMethod,
                                   current_strategy: Optional[StrategyInstance]) -> Dict[str, Any]:
        """计算交易参数"""

        if not market_data:
            return self._get_default_trade_params()

        current_price = market_data.get('current_price', 0)
        high_price = market_data.get('high_price', current_price)
        low_price = market_data.get('low_price', current_price)

        # 计算仓位大小
        position_value = target_position * self.current_capital
        position_size = position_value / current_price if current_price > 0 else 0

        # 计算止损价格
        stop_loss = self._calculate_stop_loss(
            method, current_price, market_data, current_strategy
        )

        # 计算止盈价格
        take_profit = self._calculate_take_profit(
            method, current_price, market_data, current_strategy
        )

        # 计算风险金额
        if stop_loss and stop_loss > 0:
            risk_amount = position_size * abs(current_price - stop_loss)
        else:
            risk_amount = position_value * 0.02  # 默认2%风险

        # 计算预期收益
        if take_profit and take_profit > 0:
            expected_return = position_size * (take_profit - current_price)
        else:
            expected_return = position_value * 0.06  # 默认6%预期收益

        # 风险收益比
        risk_reward_ratio = expected_return / risk_amount if risk_amount > 0 else 0

        # 执行类型
        execution_type = self._determine_execution_type(method, market_data)

        return {
            "position_size": position_size,
            "position_value": position_value,
            "stop_loss": stop_loss,
            "take_profit": take_profit,
            "risk_amount": risk_amount,
            "expected_return": expected_return,
            "risk_reward_ratio": risk_reward_ratio,
            "execution_type": execution_type
        }

    def _calculate_stop_loss(self,
                            method: RiskMethod,
                            current_price: float,
                            market_data: Dict[str, Any],
                            current_strategy: Optional[StrategyInstance]) -> Optional[float]:
        """计算止损价格"""

        if method == RiskMethod.ATR_BASED:
            atr = market_data.get('atr', current_price * 0.02)
            return current_price - 2 * atr

        elif method == RiskMethod.VOLATILITY_BASED:
            volatility = market_data.get('volatility', 0.2)
            return current_price * (1 - 2 * volatility)

        elif method == RiskMethod.FIXED_RISK:
            # 固定5%止损
            return current_price * 0.95

        elif current_strategy and current_strategy.stop_loss:
            # 继承现有止损
            return current_strategy.stop_loss

        else:
            return current_price * 0.95  # 默认5%止损

    def _calculate_take_profit(self,
                              method: RiskMethod,
                              current_price: float,
                              market_data: Dict[str, Any],
                              current_strategy: Optional[StrategyInstance]) -> Optional[float]:
        """计算止盈价格"""

        if method == RiskMethod.ATR_BASED:
            atr = market_data.get('atr', current_price * 0.02)
            return current_price + 3 * atr  # 3倍ATR

        elif method == RiskMethod.VOLATILITY_BASED:
            volatility = market_data.get('volatility', 0.2)
            return current_price * (1 + 4 * volatility)  # 4倍波动率

        elif current_strategy and current_strategy.take_profit:
            # 继承现有止盈
            return current_strategy.take_profit

        else:
            return current_price * 1.10  # 默认10%止盈

    def _determine_execution_type(self,
                                 method: RiskMethod,
                                 market_data: Dict[str, Any]) -> str:
        """确定执行类型"""

        volume = market_data.get('volume', 0)
        avg_volume = market_data.get('avg_volume', volume)

        # 根据流动性决定执行类型
        if volume > avg_volume * 0.5:  # 成交量充足，可以使用市价单
            return "immediate"
        else:  # 成交量不足，使用限价单
            return "limit"

    def _risk_control_check(self,
                           target_position: float,
                           trade_params: Dict[str, Any],
                           portfolio_state: Dict[str, Any]) -> Dict[str, Any]:
        """风险控制检查"""

        warnings = []
        is_approved = True

        # 1. 检查风险收益比
        risk_reward_ratio = trade_params["risk_reward_ratio"]
        if risk_reward_ratio < self.risk_params["min_risk_reward"]:
            warnings.append(f"风险收益比过低: {risk_reward_ratio:.2f} < {self.risk_params['min_risk_reward']}")
            is_approved = False

        # 2. 检查单笔仓位限制
        if target_position > self.risk_params["max_single_position"]:
            warnings.append(f"单笔仓位过大: {target_position:.2%} > {self.risk_params['max_single_position']:.2%}")

        # 3. 检查投资组合总风险
        if portfolio_state:
            total_portfolio_risk = portfolio_state.get("total_risk", 0) + \
                                  (trade_params["risk_amount"] / self.current_capital)

            if total_portfolio_risk > self.risk_params["max_portfolio_risk"]:
                warnings.append(f"投资组合风险过高: {total_portfolio_risk:.2%} > {self.risk_params['max_portfolio_risk']:.2%}")
                is_approved = False

        # 4. 检查集中度
        if portfolio_state:
            industry_concentration = self._check_industry_concentration(portfolio_state)
            if industry_concentration > 0.4:  # 40%集中度警告
                warnings.append(f"行业集中度过高: {industry_concentration:.2%}")

        # 5. 检查流动性
        liquidity_score = trade_params.get("liquidity_score", 1.0)
        if liquidity_score < 0.3:
            warnings.append("流动性严重不足")
            is_approved = False
        elif liquidity_score < 0.5:
            warnings.append("流动性偏低")

        return {
            "is_approved": is_approved,
            "warnings": warnings,
            "total_portfolio_risk": total_portfolio_risk if 'total_portfolio_risk' in locals() else 0,
            "industry_concentration": industry_concentration if 'industry_concentration' in locals() else 0,
            "liquidity_score": liquidity_score
        }

    def _generate_position_decision(self,
                                   base_action: PositionAction,
                                   target_position: float,
                                   trade_params: Dict[str, Any],
                                   risk_check: Dict[str, Any],
                                   strategy_rec: StrategyRecommendation,
                                   current_strategy: Optional[StrategyInstance]) -> PositionDecision:
        """生成最终仓位决策"""

        # 根据风险检查结果调整决策
        if not risk_check["is_approved"]:
            if risk_check["warnings"]:
                # 如果有风险警告，降低仓位或取消交易
                target_position *= 0.5
                if target_position < 0.01:  # 如果仓位过小，则取消交易
                    base_action = PositionAction.WAIT

        # 生成决策理由
        reasoning = self._generate_decision_reasoning(
            base_action, target_position, strategy_rec, current_strategy, risk_check
        )

        # 添加风险提示
        warnings = risk_check["warnings"]

        # 确定最终仓位大小
        if base_action in [PositionAction.ENTER, PositionAction.ADD_POSITION]:
            final_position_size = trade_params["position_size"]
        elif base_action == PositionAction.REDUCE_POSITION:
            if current_strategy:
                final_position_size = current_strategy.position - target_position
            else:
                final_position_size = 0
        else:
            final_position_size = 0

        return PositionDecision(
            action=base_action,
            target_position=target_position,
            position_size=final_position_size,
            entry_price=trade_params.get("current_price"),
            stop_loss=trade_params["stop_loss"],
            take_profit=trade_params["take_profit"],
            risk_amount=trade_params["risk_amount"],
            expected_return=trade_params["expected_return"],
            risk_reward_ratio=trade_params["risk_reward_ratio"],
            position_method=RiskMethod.FIXED_RISK,  # 可以根据实际情况调整
            execution_type=trade_params["execution_type"],
            reasoning=reasoning,
            warnings=warnings,
            timestamp=datetime.now()
        )

    def _generate_decision_reasoning(self,
                                    base_action: PositionAction,
                                    target_position: float,
                                    strategy_rec: StrategyRecommendation,
                                    current_strategy: Optional[StrategyInstance],
                                    risk_check: Dict[str, Any]) -> List[str]:
        """生成决策理由"""

        reasoning = []

        # 基本操作理由
        if base_action == PositionAction.ENTER:
            reasoning.append(f"根据{strategy_rec.chosen_strategy.value}策略开仓")
            reasoning.append(f"策略权重{strategy_rec.strategy_weight:.2f}，置信度{strategy_rec.confidence_score:.2f}")
        elif base_action == PositionAction.ADD_POSITION:
            reasoning.append("当前策略表现良好，执行加仓")
        elif base_action == PositionAction.REDUCE_POSITION:
            reasoning.append("信号减弱，降低仓位控制风险")
        elif base_action == PositionAction.EXIT_POSITION:
            reasoning.append("风险过高或信号反转，及时平仓")
        elif base_action == PositionAction.WAIT:
            reasoning.append("信号强度不足，等待更好机会")

        # 仓位大小理由
        if target_position > 0:
            reasoning.append(f"目标仓位{target_position:.2%}")
            if target_position >= 0.1:
                reasoning.append("高信心度，采用较大仓位")
            elif target_position >= 0.05:
                reasoning.append("中等信心度，采用适中仓位")
            else:
                reasoning.append("低仓位试水，控制风险")

        # 风险控制理由
        if risk_check["warnings"]:
            reasoning.append("已识别相关风险，已采取相应控制措施")

        if not reasoning:
            reasoning.append("基于综合分析做出最优决策")

        return reasoning

    def _calculate_industry_exposure(self,
                                   strategy_rec: StrategyRecommendation,
                                   portfolio_state: Dict[str, Any]) -> float:
        """计算行业暴露度"""
        # 这里应该根据实际股票的行业信息计算
        # 简化实现，返回0
        return 0

    def _assess_liquidity(self,
                         strategy_rec: StrategyRecommendation,
                         portfolio_state: Dict[str, Any]) -> float:
        """评估流动性"""
        # 这里应该根据实际股票的流动性指标计算
        # 简化实现，返回1.0
        return 1.0

    def _check_industry_concentration(self, portfolio_state: Dict[str, Any]) -> float:
        """检查行业集中度"""
        # 这里应该根据投资组合的行业分布计算
        # 简化实现，返回0
        return 0

    def _get_neutral_decision(self) -> PositionDecision:
        """获取中性决策"""
        return PositionDecision(
            action=PositionAction.WAIT,
            target_position=0.0,
            position_size=0.0,
            entry_price=None,
            stop_loss=None,
            take_profit=None,
            risk_amount=0.0,
            expected_return=0.0,
            risk_reward_ratio=0.0,
            position_method=RiskMethod.FIXED_RISK,
            execution_type="immediate",
            reasoning=["系统错误，保持等待状态"],
            warnings=["系统错误"],
            timestamp=datetime.now()
        )

    def _get_default_trade_params(self) -> Dict[str, Any]:
        """获取默认交易参数"""
        return {
            "position_size": 0,
            "position_value": 0,
            "stop_loss": None,
            "take_profit": None,
            "risk_amount": 0,
            "expected_return": 0,
            "risk_reward_ratio": 0,
            "execution_type": "limit"
        }