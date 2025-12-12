"""
新架构适配的回测引擎
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Any, Tuple, Optional
from datetime import datetime, timedelta
import logging
import json
from dataclasses import asdict

from core.data_structures import (
    BacktestConfig, BacktestResult, TradingStrategy, MarketRegime,
    StrategyInstance, StrategyState, PositionAction, TradingSignal,
    calculate_trading_days, is_trading_day
)
from core.state_machine import StateTransitionEngine, StrategyStateMachine
from agents.market_regime_agent import MarketRegimeAgent
from agents.signal_generator_agent import SignalGeneratorAgent
from agents.strategy_selector_agent import StrategySelectorAgent
from agents.position_manager_agent import PositionManagerAgent

class MockDataProvider:
    """模拟数据提供者（用于回测）"""

    def __init__(self):
        self.logger = logging.getLogger("MockDataProvider")
        self.market_data_cache = {}
        self.stock_data_cache = {}

    def load_price_data(self, stock_code: str, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """
        加载价格数据（这里应该接入真实的数据源）
        暂时生成模拟数据用于测试
        """
        try:
            # 生成交易日列表
            trading_days = calculate_trading_days(start_date, end_date)

            # 检查缓存
            cache_key = f"{stock_code}_{start_date.strftime('%Y%m%d')}_{end_date.strftime('%Y%m%d')}"
            if cache_key in self.market_data_cache:
                return self.market_data_cache[cache_key]

            # 生成模拟价格数据
            np.random.seed(hash(stock_code) % 2**32)  # 基于股票代码设置随机种子

            n_days = len(trading_days)
            initial_price = np.random.uniform(10, 100)  # 随机初始价格

            # 生成价格序列（几何布朗运动）
            returns = np.random.normal(0.001, 0.02, n_days)  # 日收益率
            prices = [initial_price]

            for i in range(1, n_days):
                new_price = prices[-1] * (1 + returns[i])
                prices.append(max(new_price, 0.1))  # 价格不能为负

            # 生成OHLCV数据
            data = {
                'date': trading_days,
                'open': prices,
                'high': [p * (1 + abs(np.random.normal(0, 0.01))) for p in prices],
                'low': [p * (1 - abs(np.random.normal(0, 0.01))) for p in prices],
                'close': prices,
                'volume': [np.random.randint(1000000, 10000000) for _ in range(n_days)],
                'turnover': [p * v for p, v in zip(prices, [np.random.randint(1000000, 10000000) for _ in range(n_days)])]
            }

            df = pd.DataFrame(data)
            df.set_index('date', inplace=True)

            # 缓存数据
            self.market_data_cache[cache_key] = df

            return df

        except Exception as e:
            self.logger.error(f"加载价格数据失败 {stock_code}: {e}")
            return pd.DataFrame()

    def get_market_data(self, date: datetime) -> Dict[str, Any]:
        """获取市场整体数据"""
        try:
            # 这里应该获取市场指数数据
            # 暂时返回模拟数据
            return {
                "current_price": 3000,  # 假设上证指数
                "volume": np.random.randint(100000000, 500000000),
                "volatility": np.random.uniform(0.01, 0.05),
                "news": [
                    {"title": "模拟新闻", "sentiment": np.random.choice(["positive", "negative", "neutral"])}
                ],
                "calendar": []
            }
        except Exception as e:
            self.logger.error(f"获取市场数据失败: {e}")
            return {}

    def get_stock_data(self, stock_code: str, date: datetime, lookback_days: int = 60) -> Dict[str, Any]:
        """获取股票数据"""
        try:
            end_date = date
            start_date = date - timedelta(days=lookback_days)

            price_data = self.load_price_data(stock_code, start_date, end_date)

            if price_data.empty:
                return {}

            # 获取当日数据
            current_data = price_data.iloc[-1] if len(price_data) > 0 else None

            if current_data is None:
                return {}

            # 构建返回数据
            stock_data = {
                "price_data": price_data,
                "volume_data": price_data[['volume']],
                "current_price": current_data['close'],
                "high_price": current_data['high'],
                "low_price": current_data['low'],
                "volume": current_data['volume'],
                "avg_volume": price_data['volume'].tail(20).mean(),
                "volatility": price_data['close'].pct_change().tail(20).std(),
                "atr": self._calculate_atr(price_data),
                "technical_indicators": self._calculate_technical_indicators(price_data),
                "fundamentals": self._generate_mock_fundamentals(stock_code),
                "sentiment": self._generate_mock_sentiment(stock_code),
                "news": self._generate_mock_news(stock_code),
                "calendar": []
            }

            return stock_data

        except Exception as e:
            self.logger.error(f"获取股票数据失败 {stock_code}: {e}")
            return {}

    def _calculate_atr(self, price_data: pd.DataFrame, period: int = 14) -> float:
        """计算ATR"""
        try:
            if len(price_data) < period + 1:
                return price_data['close'].iloc[-1] * 0.02  # 默认2%

            high_low = price_data['high'] - price_data['low']
            high_close = abs(price_data['high'] - price_data['close'].shift(1))
            low_close = abs(price_data['low'] - price_data['close'].shift(1))

            true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            atr = true_range.rolling(period).mean().iloc[-1]

            return atr if not np.isnan(atr) else price_data['close'].iloc[-1] * 0.02
        except:
            return 0

    def _calculate_technical_indicators(self, price_data: pd.DataFrame) -> Dict[str, Any]:
        """计算技术指标"""
        try:
            if len(price_data) < 20:
                return {}

            # 移动平均线
            ma5 = price_data['close'].rolling(5).mean()
            ma10 = price_data['close'].rolling(10).mean()
            ma20 = price_data['close'].rolling(20).mean()
            ma60 = price_data['close'].rolling(60).mean() if len(price_data) >= 60 else ma20

            # RSI
            delta = price_data['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))

            # MACD
            exp12 = price_data['close'].ewm(span=12).mean()
            exp26 = price_data['close'].ewm(span=26).mean()
            macd = exp12 - exp26
            signal = macd.ewm(span=9).mean()

            return {
                "ma5": ma5.iloc[-1] if len(ma5) > 0 else 0,
                "ma10": ma10.iloc[-1] if len(ma10) > 0 else 0,
                "ma20": ma20.iloc[-1] if len(ma20) > 0 else 0,
                "ma60": ma60.iloc[-1] if len(ma60) > 0 else 0,
                "rsi": rsi.iloc[-1] if len(rsi) > 0 else 50,
                "macd": macd.iloc[-1] if len(macd) > 0 else 0,
                "macd_signal": signal.iloc[-1] if len(signal) > 0 else 0
            }
        except Exception as e:
            return {}

    def _generate_mock_fundamentals(self, stock_code: str) -> Dict[str, Any]:
        """生成模拟基本面数据"""
        np.random.seed(hash(f"fund_{stock_code}") % 2**32)
        return {
            "pe_ratio": np.random.uniform(10, 50),
            "pb_ratio": np.random.uniform(1, 10),
            "dividend_yield": np.random.uniform(0, 0.05),
            "roe": np.random.uniform(0, 0.3),
            "revenue_growth": np.random.uniform(-0.2, 0.5),
            "industry_pe": np.random.uniform(15, 40)
        }

    def _generate_mock_sentiment(self, stock_code: str) -> Dict[str, Any]:
        """生成模拟情绪数据"""
        np.random.seed(hash(f"sentiment_{stock_code}") % 2**32)
        return {
            "news_sentiment": np.random.uniform(-1, 1),
            "news_count": np.random.randint(0, 20),
            "social_sentiment": np.random.uniform(-1, 1),
            "social_volume": np.random.randint(100, 10000),
            "analyst_ratings": {
                "buy": np.random.randint(0, 10),
                "hold": np.random.randint(0, 10),
                "sell": np.random.randint(0, 10)
            }
        }

    def _generate_mock_news(self, stock_code: str) -> List[Dict[str, Any]]:
        """生成模拟新闻"""
        np.random.seed(hash(f"news_{stock_code}") % 2**32)
        news_count = np.random.randint(0, 5)

        titles = ["公司发布财报", "重大项目签约", "高管变动", "新产品发布", "市场分析报告"]
        sentiments = ["positive", "negative", "neutral"]

        return [
            {
                "title": np.random.choice(titles),
                "sentiment": np.random.choice(sentiments),
                "date": (datetime.now() - timedelta(days=np.random.randint(0, 30))).isoformat()
            }
            for _ in range(news_count)
        ]

class BacktestEngine:
    """新架构的回测引擎"""

    def __init__(self, config: BacktestConfig):
        self.config = config
        self.logger = logging.getLogger("BacktestEngine")

        # 初始化组件
        self.data_provider = MockDataProvider()
        self.market_regime_agent = MarketRegimeAgent()
        self.signal_generator_agent = SignalGeneratorAgent()
        self.strategy_selector_agent = StrategySelectorAgent()
        self.position_manager_agent = PositionManagerAgent(config.initial_capital)
        self.state_transition_engine = StateTransitionEngine()
        self.strategy_state_machine = StrategyStateMachine(self.state_transition_engine)

        # 回测状态
        self.current_capital = config.initial_capital
        self.positions = {}  # 当前持仓 {stock_code: position_info}
        self.trades = []  # 交易记录
        self.daily_values = []  # 每日净值
        self.strategy_instances = {}  # 策略实例
        self.performance_history = {}  # 性能历史

        # 目标股票池
        self.watchlist = ["000001.SZ", "000002.SZ", "600000.SH", "600036.SH", "000858.SZ"]

    def run_backtest(self) -> BacktestResult:
        """运行完整回测"""
        try:
            self.logger.info(f"开始回测: {self.config.start_date} 至 {self.config.end_date}")

            # 初始化回测状态
            self._initialize_backtest()

            # 获取所有交易日
            trading_days = calculate_trading_days(self.config.start_date, self.config.end_date)
            total_days = len(trading_days)

            # 按日期迭代
            for i, trading_date in enumerate(trading_days):
                try:
                    self._process_trading_day(trading_date)

                    # 记录每日净值
                    daily_value = self._calculate_portfolio_value(trading_date)
                    benchmark_value = self._get_benchmark_value(trading_date)

                    self.daily_values.append({
                        "date": trading_date,
                        "portfolio_value": daily_value,
                        "benchmark_value": benchmark_value,
                        "cash": self.current_capital,
                        "positions_value": sum(pos["market_value"] for pos in self.positions.values())
                    })

                    # 进度显示
                    if i % 20 == 0:
                        progress = (i + 1) / total_days * 100
                        self.logger.info(f"回测进度: {progress:.1f}% - 当前净值: {daily_value:,.0f}")

                except Exception as e:
                    self.logger.error(f"处理交易日 {trading_date} 失败: {e}")
                    continue

            # 计算回测结果
            result = self._calculate_backtest_results()

            self.logger.info(f"回测完成! 总收益率: {result.total_return:.2%}")

            return result

        except Exception as e:
            self.logger.error(f"回测执行失败: {e}")
            return self._get_default_result()

    def _initialize_backtest(self):
        """初始化回测状态"""
        self.current_capital = self.config.initial_capital
        self.positions = {}
        self.trades = []
        self.daily_values = []
        self.strategy_instances = {}
        self.performance_history = {}

    def _process_trading_day(self, trading_date: datetime):
        """处理单个交易日"""

        # 1. 市场阶段识别（全局执行一次）
        market_data = self.data_provider.get_market_data(trading_date)
        regime_result = self.market_regime_agent.identify_regime(market_data)
        current_regime = regime_result.get("regime", MarketRegime.SIDEWAYS_LOW_VOL)

        # 2. 处理每只股票
        for stock_code in self.watchlist:
            try:
                self._process_stock_strategy(stock_code, trading_date, current_regime)
            except Exception as e:
                self.logger.error(f"处理股票 {stock_code} 失败: {e}")
                continue

        # 3. 更新持仓市值
        self._update_positions_market_value(trading_date)

        # 4. 投资组合级风险检查
        self._portfolio_risk_check(trading_date)

    def _process_stock_strategy(self, stock_code: str, trading_date: datetime, regime):
        """处理单个股票策略"""

        try:
            # 获取股票数据
            stock_data = self.data_provider.get_stock_data(stock_code, trading_date)

            if not stock_data:
                return

            current_price = stock_data.get("current_price", 0)
            if current_price <= 0:
                return

            # 获取当前策略状态
            strategy_id = f"{stock_code}_primary"
            current_strategy = self.strategy_instances.get(strategy_id)

            # 信号生成
            signals = self.signal_generator_agent.generate_signals(stock_data)

            # 策略选择
            strategy_recommendation = self.strategy_selector_agent.select_strategy(
                regime, signals, current_strategy, self._get_portfolio_state()
            )

            # 仓位管理
            position_decision = self.position_manager_agent.calculate_position(
                strategy_recommendation, current_strategy, stock_data,
                self._get_portfolio_state()
            )

            # 状态迁移评估
            if current_strategy:
                # 创建市场数据字典用于状态迁移
                market_data_dict = {
                    "current_price": current_price,
                    "volume": stock_data.get("volume", 0),
                    "volatility": stock_data.get("volatility", 0.02)
                }

                # 创建信号字典
                signals_dict = {signal_type.value: signal for signal_type, signal in signals.items()}

                # 创建风险指标字典
                risk_metrics = {
                    "portfolio_exposure": self._calculate_portfolio_exposure(),
                    "data_quality": 1.0
                }

                # 更新策略状态
                updated_strategy = self.strategy_state_machine.update_strategy_state(
                    current_strategy, market_data_dict, signals_dict, risk_metrics
                )
                self.strategy_instances[strategy_id] = updated_strategy

            # 执行交易
            self._execute_trade(stock_code, position_decision, current_price, trading_date)

            # 更新或创建策略状态
            if position_decision.action == PositionAction.ENTER:
                # 创建新策略
                new_strategy = self._create_new_strategy(
                    stock_code, strategy_recommendation, position_decision, trading_date
                )
                self.strategy_instances[strategy_id] = new_strategy

            elif current_strategy and position_decision.action != PositionAction.WAIT:
                # 更新现有策略
                self._update_strategy_state(
                    current_strategy, position_decision, strategy_recommendation, trading_date
                )

            # 保存每日快照
            self._save_daily_snapshot(
                strategy_id or stock_code, trading_date,
                {
                    "market_regime": regime.value if hasattr(regime, 'value') else str(regime),
                    "signals": {k.value: v.to_dict() for k, v in signals.items()},
                    "strategy_recommendation": strategy_recommendation.to_dict(),
                    "position_decision": position_decision.to_dict()
                }
            )

            # 更新性能指标
            self._update_performance_metrics(
                self.strategy_instances.get(strategy_id), trading_date, stock_data
            )

        except Exception as e:
            self.logger.error(f"处理股票 {stock_code} 策略失败: {e}")

    def _execute_trade(self, stock_code: str, position_decision: PositionDecision,
                       current_price: float, trading_date: datetime):
        """执行交易"""

        try:
            action = position_decision.action
            target_shares = int(position_decision.position_size)
            current_position = self.positions.get(stock_code, {
                "shares": 0, "avg_cost": 0, "market_value": 0
            })
            current_shares = current_position["shares"]

            commission_rate = self.config.commission_rate
            slippage_rate = self.config.slippage_rate

            if action == PositionAction.ENTER and target_shares > 0:
                # 开仓
                trade_value = target_shares * current_price
                commission = trade_value * commission_rate
                slippage = trade_value * slippage_rate
                total_cost = trade_value + commission + slippage

                if self.current_capital >= total_cost:
                    self.current_capital -= total_cost

                    avg_cost = total_cost / target_shares
                    self.positions[stock_code] = {
                        "shares": target_shares,
                        "avg_cost": avg_cost,
                        "market_value": 0
                    }

                    self._record_trade(
                        trading_date, stock_code, "buy", target_shares,
                        current_price, trade_value, commission, slippage
                    )

            elif action == PositionAction.EXIT_POSITION and current_shares > 0:
                # 平仓
                trade_value = current_shares * current_price
                commission = trade_value * commission_rate
                slippage = trade_value * slippage_rate
                total_proceeds = trade_value - commission - slippage

                self.current_capital += total_proceeds

                # 计算盈亏
                cost_basis = current_position["avg_cost"] * current_shares
                profit_loss = total_proceeds - cost_basis

                self._record_trade(
                    trading_date, stock_code, "sell", current_shares,
                    current_price, trade_value, commission, slippage, profit_loss
                )

                del self.positions[stock_code]

            elif action == PositionAction.ADD_POSITION and target_shares > current_shares:
                # 加仓
                additional_shares = target_shares - current_shares
                trade_value = additional_shares * current_price
                commission = trade_value * commission_rate
                slippage = trade_value * slippage_rate
                total_cost = trade_value + commission + slippage

                if self.current_capital >= total_cost:
                    self.current_capital -= total_cost

                    # 更新平均成本
                    old_cost = current_position["avg_cost"] * current_shares
                    new_avg_cost = (old_cost + total_cost) / target_shares

                    self.positions[stock_code] = {
                        "shares": target_shares,
                        "avg_cost": new_avg_cost,
                        "market_value": 0
                    }

                    self._record_trade(
                        trading_date, stock_code, "buy_add", additional_shares,
                        current_price, trade_value, commission, slippage
                    )

            elif action == PositionAction.REDUCE_POSITION and target_shares < current_shares:
                # 减仓
                reduce_shares = current_shares - target_shares
                trade_value = reduce_shares * current_price
                commission = trade_value * commission_rate
                slippage = trade_value * slippage_rate
                total_proceeds = trade_value - commission - slippage

                self.current_capital += total_proceeds

                # 更新持仓
                self.positions[stock_code]["shares"] = target_shares

                # 计算部分盈亏
                cost_basis = current_position["avg_cost"] * reduce_shares
                profit_loss = total_proceeds - cost_basis

                self._record_trade(
                    trading_date, stock_code, "sell_reduce", reduce_shares,
                    current_price, trade_value, commission, slippage, profit_loss
                )

        except Exception as e:
            self.logger.error(f"交易执行失败 {stock_code}: {e}")

    def _record_trade(self, date: datetime, stock_code: str, action: str,
                     shares: int, price: float, value: float,
                     commission: float, slippage: float, profit_loss: float = 0):
        """记录交易"""

        trade_record = {
            "date": date,
            "stock_code": stock_code,
            "action": action,
            "shares": shares,
            "price": price,
            "value": value,
            "commission": commission,
            "slippage": slippage,
            "profit_loss": profit_loss
        }

        self.trades.append(trade_record)

    def _calculate_portfolio_value(self, trading_date: datetime) -> float:
        """计算投资组合总价值"""
        portfolio_value = self.current_capital

        for stock_code, position in self.positions.items():
            current_price = self.data_provider.get_stock_data(stock_code, trading_date).get("current_price", 0)
            if current_price > 0:
                position["market_value"] = position["shares"] * current_price
                portfolio_value += position["market_value"]

        return portfolio_value

    def _get_benchmark_value(self, trading_date: datetime) -> float:
        """获取基准指数值"""
        # 简化实现，假设基准收益与市场同步
        if not self.daily_values:
            return self.config.initial_capital

        # 假设基准年化收益为8%
        days = (trading_date - self.config.start_date).days
        benchmark_return = (1 + 0.08) ** (days / 365) - 1
        return self.config.initial_capital * (1 + benchmark_return)

    def _update_positions_market_value(self, trading_date: datetime):
        """更新持仓市值"""
        for stock_code in self.positions:
            stock_data = self.data_provider.get_stock_data(stock_code, trading_date)
            current_price = stock_data.get("current_price", 0)
            if current_price > 0:
                self.positions[stock_code]["market_value"] = \
                    self.positions[stock_code]["shares"] * current_price

    def _get_portfolio_state(self) -> Dict[str, Any]:
        """获取投资组合状态"""
        current_value = self._calculate_portfolio_value(datetime.now())
        return {
            "total_exposure": sum(pos["market_value"] for pos in self.positions.values()) / current_value,
            "total_risk": 0.01  # 简化实现
        }

    def _calculate_portfolio_exposure(self) -> float:
        """计算投资组合暴露度"""
        current_value = self.current_capital + sum(pos["market_value"] for pos in self.positions.values())
        if current_value <= 0:
            return 0
        return sum(pos["market_value"] for pos in self.positions.values()) / current_value

    def _create_new_strategy(self, stock_code: str, strategy_recommendation,
                           position_decision: PositionDecision, trading_date: datetime) -> StrategyInstance:
        """创建新策略实例"""

        strategy_id = f"{stock_code}_{strategy_recommendation.chosen_strategy.value}_{trading_date.strftime('%Y%m%d')}"

        strategy = StrategyInstance(
            strategy_id=strategy_id,
            stock_code=stock_code,
            strategy_name=strategy_recommendation.chosen_strategy.value,
            state=StrategyState.OPEN,
            regime=MarketRegime.BULL_TREND_WEAK,  # 应该从市场阶段结果获取
            position=position_decision.target_position,
            initial_size=position_decision.target_position,
            target_size=position_decision.target_position,
            entry_price=position_decision.entry_price,
            entry_time=trading_date,
            stop_loss=position_decision.stop_loss,
            take_profit=position_decision.take_profit,
            signal_strength=strategy_recommendation.strategy_weight,
            confidence_score=strategy_recommendation.confidence_score,
            risk_budget=position_decision.risk_amount / self.config.initial_capital,
            history=[{
                "date": trading_date.strftime("%Y-%m-%d"),
                "action": "enter",
                "price": position_decision.entry_price,
                "size": position_decision.target_position
            }]
        )

        return strategy

    def _update_strategy_state(self, strategy: StrategyInstance, position_decision: PositionDecision,
                             strategy_recommendation: StrategyRecommendation, trading_date: datetime):
        """更新策略状态"""

        # 更新仓位
        if position_decision.action == PositionAction.ADD_POSITION:
            strategy.position += position_decision.target_position
            strategy.pyramid_steps += 1
            strategy.state = StrategyState.PYRAMIDING

        elif position_decision.action == PositionAction.REDUCE_POSITION:
            strategy.position -= position_decision.target_position
            if strategy.position <= 0.01:  # 基本清仓
                strategy.state = StrategyState.EXITED
            else:
                strategy.state = StrategyState.PARTIAL_EXIT

        elif position_decision.action == PositionAction.EXIT_POSITION:
            strategy.position = 0
            strategy.state = StrategyState.EXITED

        # 更新价格和风险控制
        if position_decision.stop_loss:
            strategy.stop_loss = position_decision.stop_loss
        if position_decision.take_profit:
            strategy.take_profit = position_decision.take_profit

        # 更新信号强度
        strategy.signal_strength = strategy_recommendation.strategy_weight

        # 记录操作历史
        strategy.history.append({
            "date": trading_date.strftime("%Y-%m-%d"),
            "action": position_decision.action.value,
            "price": position_decision.entry_price,
            "size": position_decision.target_position,
            "reason": position_decision.reasoning
        })

        # 更新时间戳
        strategy.last_update = datetime.now()

    def _save_daily_snapshot(self, strategy_or_stock: str, trading_date: datetime, snapshot_data: Dict[str, Any]):
        """保存每日快照"""
        # 在回测中可以保存到内存或文件
        # 这里简化实现
        pass

    def _update_performance_metrics(self, strategy: Optional[StrategyInstance], trading_date: datetime, stock_data: Dict[str, Any]):
        """更新性能指标"""
        if not strategy or strategy.position <= 0:
            return

        current_price = stock_data.get("current_price", strategy.entry_price)

        # 计算收益率
        if strategy.entry_price and strategy.entry_price > 0:
            return_rate = (current_price - strategy.entry_price) / strategy.entry_price
        else:
            return_rate = 0

        # 计算其他性能指标
        metrics = {
            "current_value": strategy.position * current_price,
            "return_rate": return_rate,
            "days_held": (trading_date - strategy.entry_time.date()).days if strategy.entry_time else 0,
            "max_drawdown": 0.05,  # 简化实现
            "sharpe_ratio": 1.2,  # 简化实现
            "volatility": stock_data.get("volatility", 0)
        }

        # 保存到性能历史
        if strategy.strategy_id not in self.performance_history:
            self.performance_history[strategy.strategy_id] = []

        self.performance_history[strategy.strategy_id].append({
            "date": trading_date,
            "metrics": metrics
        })

    def _portfolio_risk_check(self, trading_date: datetime):
        """投资组合风险检查"""
        # 简化实现
        pass

    def _calculate_backtest_results(self) -> BacktestResult:
        """计算回测结果指标"""

        if not self.daily_values:
            return self._get_default_result()

        # 转换为DataFrame便于计算
        df = pd.DataFrame(self.daily_values)
        df.set_index('date', inplace=True)

        # 计算收益率
        df['portfolio_return'] = df['portfolio_value'].pct_change()
        df['benchmark_return'] = df['benchmark_value'].pct_change()
        df.dropna(inplace=True)

        # 基础指标
        total_return = (df['portfolio_value'].iloc[-1] / self.config.initial_capital) - 1

        # 年化收益率
        days = (df.index[-1] - df.index[0]).days
        if days > 0:
            annual_return = (df['portfolio_value'].iloc[-1] / self.config.initial_capital) ** (365/days) - 1
        else:
            annual_return = 0

        # 最大回撤
        peak = df['portfolio_value'].expanding(min_periods=1).max()
        drawdown = (df['portfolio_value'] - peak) / peak
        max_drawdown = drawdown.min()

        # 夏普比率
        risk_free_rate = self.config.risk_free_rate
        excess_returns = df['portfolio_return'] - risk_free_rate/365
        if excess_returns.std() > 0:
            sharpe_ratio = excess_returns.mean() / excess_returns.std() * np.sqrt(365)
        else:
            sharpe_ratio = 0

        # 索提诺比率
        downside_returns = excess_returns[excess_returns < 0]
        if len(downside_returns) > 0 and downside_returns.std() > 0:
            sortino_ratio = excess_returns.mean() / downside_returns.std() * np.sqrt(365)
        else:
            sortino_ratio = 0

        # Beta和Alpha
        if len(df) > 30:
            covariance = np.cov(df['portfolio_return'], df['benchmark_return'])[0, 1]
            benchmark_variance = np.var(df['benchmark_return'])
            beta = covariance / benchmark_variance if benchmark_variance > 0 else 0

            alpha = (annual_return - risk_free_rate) - beta * (annual_return - risk_free_rate)
        else:
            beta = 0
            alpha = 0

        # 波动率
        volatility = df['portfolio_return'].std() * np.sqrt(365)

        # 交易统计
        winning_trades = [t for t in self.trades if t.get("profit_loss", 0) > 0]
        losing_trades = [t for t in self.trades if t.get("profit_loss", 0) < 0]

        win_rate = len(winning_trades) / len(self.trades) if self.trades else 0

        # 盈亏比
        if winning_trades and losing_trades:
            avg_win = np.mean([t["profit_loss"] for t in winning_trades])
            avg_loss = np.mean([abs(t["profit_loss"]) for t in losing_trades])
            profit_loss_ratio = avg_win / avg_loss
        else:
            profit_loss_ratio = 0

        # 平均持仓周期
        if self.trades:
            # 简化实现，假设平均持仓30天
            avg_holding_period = 30
        else:
            avg_holding_period = 0

        # 换手率
        if self.trades and df['portfolio_value'].mean() > 0:
            total_traded_value = sum(t["value"] for t in self.trades)
            avg_portfolio_value = df["portfolio_value"].mean()
            turnover_rate = total_traded_value / (avg_portfolio_value * len(df))
        else:
            turnover_rate = 0

        return BacktestResult(
            total_return=total_return,
            annual_return=annual_return,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            win_rate=win_rate,
            profit_loss_ratio=profit_loss_ratio,
            beta=beta,
            alpha=alpha,
            volatility=volatility,
            total_trades=len(self.trades),
            winning_trades=len(winning_trades),
            losing_trades=len(losing_trades),
            avg_holding_period=avg_holding_period,
            turnover_rate=turnover_rate
        )

    def _get_default_result(self) -> BacktestResult:
        """获取默认回测结果"""
        return BacktestResult(
            total_return=0, annual_return=0, max_drawdown=0, sharpe_ratio=0,
            sortino_ratio=0, win_rate=0, profit_loss_ratio=0, beta=0, alpha=0,
            volatility=0, total_trades=0, winning_trades=0, losing_trades=0,
            avg_holding_period=0, turnover_rate=0
        )

    def generate_backtest_report(self, result: BacktestResult, save_path: str = None):
        """生成回测报告"""

        print("="*60)
        print("📊 新架构回测报告")
        print("="*60)

        # 收益指标
        print("\n💰 收益指标:")
        print(f"总收益率: {result.total_return:.2%}")
        print(f"年化收益率: {result.annual_return:.2%}")
        print(f"最大回撤: {result.max_drawdown:.2%}")

        # 风险指标
        print("\n⚠️  风险指标:")
        print(f"年化波动率: {result.volatility:.2%}")
        print(f"夏普比率: {result.sharpe_ratio:.2f}")
        print(f"索提诺比率: {result.sortino_ratio:.2f}")
        print(f"Beta: {result.beta:.2f}")
        print(f"Alpha: {result.alpha:.2%}")

        # 交易指标
        print("\n📈 交易指标:")
        print(f"总交易次数: {result.total_trades}")
        print(f"盈利交易: {result.winning_trades}")
        print(f"亏损交易: {result.losing_trades}")
        print(f"胜率: {result.win_rate:.2%}")
        print(f"盈亏比: {result.profit_loss_ratio:.2f}")
        print(f"平均持仓天数: {result.avg_holding_period:.1f}")
        print(f"换手率: {result.turnover_rate:.2%}")

        # 策略分布
        print("\n🎯 策略分布:")
        strategy_count = {}
        for strategy in self.strategy_instances.values():
            strategy_name = strategy.strategy_name
            strategy_count[strategy_name] = strategy_count.get(strategy_name, 0) + 1

        for strategy_name, count in strategy_count.items():
            print(f"{strategy_name}: {count}个")

        print(f"\n✅ 回测完成！")

    def export_results(self, filepath: str):
        """导出回测结果"""
        try:
            results = {
                "config": asdict(self.config),
                "daily_values": self.daily_values,
                "trades": self.trades,
                "strategy_instances": {
                    k: v.to_dict() for k, v in self.strategy_instances.items()
                },
                "performance_history": self.performance_history
            }

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(results, f, default=str, indent=2, ensure_ascii=False)

            self.logger.info(f"回测结果已导出至: {filepath}")

        except Exception as e:
            self.logger.error(f"导出回测结果失败: {e}")