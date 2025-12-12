"""
TradingAgents-CN 主程序入口
基于4智能体架构的A股交易系统
"""

import argparse
import logging
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from core.data_structures import BacktestConfig, SYSTEM_CONSTANTS
from backtest.backtest_engine import BacktestEngine
from agents.market_regime_agent import MarketRegimeAgent
from agents.signal_generator_agent import SignalGeneratorAgent
from agents.strategy_selector_agent import StrategySelectorAgent
from agents.position_manager_agent import PositionManagerAgent
from core.persistence import StrategyStateMachinePersistence
from core.state_machine import StrategyStateMachine

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('trading_agents.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger("Main")

class TradingAgentsSystem:
    """交易智能体系统主类"""

    def __init__(self, config_path: str = None):
        """初始化系统"""
        self.config = self._load_config(config_path)

        # 初始化日志
        self.logger = logging.getLogger("TradingAgentsSystem")
        self.logger.info("TradingAgents-CN 系统启动")

        # 初始化组件
        self._initialize_components()

    def _load_config(self, config_path: str) -> dict:
        """加载配置文件"""
        if config_path and os.path.exists(config_path):
            import json
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)

        # 返回默认配置
        return {
            "system": {
                "name": "TradingAgents-CN",
                "version": "2.0.0",
                "description": "基于4智能体架构的A股交易系统"
            },
            "trading": {
                "initial_capital": 1000000,  # 100万初始资金
                "max_single_position": 0.15,  # 单只股票最大15%仓位
                "risk_per_trade": 0.01,       # 单笔交易1%风险
                "commission_rate": 0.0003,     # 手续费率0.03%
                "slippage_rate": 0.001,        # 滑点率0.1%
            },
            "database": {
                "mongodb_uri": "mongodb://localhost:27017",
                "redis_uri": "redis://localhost:6379"
            },
            "data_source": {
                "type": "mock",  # 暂时使用模拟数据
                "tushare_token": "",  # TuShare token
                "cache_enabled": True
            },
            "backtest": {
                "benchmark": "000300.SH",  # 沪深300基准
                "risk_free_rate": 0.03,    # 无风险收益率3%
                "default_period_days": 252  # 默认回测周期一年
            },
            "watchlist": [
                "000001.SZ", "000002.SZ", "600000.SH", "600036.SH",
                "000858.SZ", "002415.SZ", "600519.SH", "000651.SZ"
            ]
        }

    def _initialize_components(self):
        """初始化系统组件"""
        try:
            # 初始化持久化管理器
            self.persistence = StrategyStateMachinePersistence(
                mongo_uri=self.config["database"]["mongodb_uri"],
                redis_uri=self.config["database"]["redis_uri"]
            )

            # 初始化4个智能体
            self.agents = {
                "market_regime": MarketRegimeAgent(),
                "signal_generator": SignalGeneratorAgent(),
                "strategy_selector": StrategySelectorAgent(),
                "position_manager": PositionManagerAgent(
                    initial_capital=self.config["trading"]["initial_capital"]
                )
            }

            self.logger.info("所有组件初始化完成")

        except Exception as e:
            self.logger.error(f"组件初始化失败: {e}")
            raise

    def run_backtest(self, start_date: str = None, end_date: str = None,
                    days: int = None, export: bool = False) -> dict:
        """运行回测"""
        try:
            # 确定回测日期范围
            if days:
                end_date = datetime.now()
                start_date = end_date - timedelta(days=days)
            else:
                start_date = datetime.strptime(start_date, "%Y-%m-%d") if start_date else \
                            datetime.now() - timedelta(days=self.config["backtest"]["default_period_days"])
                end_date = datetime.strptime(end_date, "%Y-%m-%d") if end_date else datetime.now()

            self.logger.info(f"开始回测: {start_date.strftime('%Y-%m-%d')} 至 {end_date.strftime('%Y-%m-%d')}")

            # 创建回测配置
            backtest_config = BacktestConfig(
                start_date=start_date,
                end_date=end_date,
                initial_capital=self.config["trading"]["initial_capital"],
                benchmark=self.config["backtest"]["benchmark"],
                commission_rate=self.config["trading"]["commission_rate"],
                slippage_rate=self.config["trading"]["slippage_rate"],
                max_position_size=self.config["trading"]["max_single_position"],
                risk_free_rate=self.config["backtest"]["risk_free_rate"]
            )

            # 创建回测引擎
            backtest_engine = BacktestEngine(backtest_config)

            # 设置监听股票
            backtest_engine.watchlist = self.config["watchlist"]

            # 运行回测
            result = backtest_engine.run_backtest()

            # 生成报告
            backtest_engine.generate_backtest_report(result)

            # 导出结果
            if export:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                export_path = f"backtest_results_{timestamp}.json"
                backtest_engine.export_results(export_path)

            return {
                "result": result,
                "config": backtest_config,
                "export_path": export_path if export else None
            }

        except Exception as e:
            self.logger.error(f"回测运行失败: {e}")
            raise

    def run_daily_analysis(self, date: str = None) -> dict:
        """运行每日分析"""
        try:
            target_date = datetime.strptime(date, "%Y-%m-%d") if date else datetime.now()
            self.logger.info(f"运行每日分析: {target_date.strftime('%Y-%m-%d')}")

            results = {
                "date": target_date,
                "market_regime": None,
                "stock_analyses": {},
                "portfolio_summary": None
            }

            # 1. 市场阶段识别
            market_data = self._get_market_data(target_date)
            regime_result = self.agents["market_regime"].identify_regime(market_data)
            results["market_regime"] = regime_result

            # 2. 股票分析
            for stock_code in self.config["watchlist"]:
                try:
                    stock_data = self._get_stock_data(stock_code, target_date)
                    if stock_data:
                        # 信号生成
                        signals = self.agents["signal_generator"].generate_signals(stock_data)

                        # 策略选择
                        strategy_rec = self.agents["strategy_selector"].select_strategy(
                            regime_result.get("regime"), signals
                        )

                        # 仓位管理
                        position_decision = self.agents["position_manager"].calculate_position(
                            strategy_rec, None, stock_data
                        )

                        results["stock_analyses"][stock_code] = {
                            "signals": {k.value: v.to_dict() for k, v in signals.items()},
                            "strategy_recommendation": strategy_rec.to_dict(),
                            "position_decision": position_decision.to_dict()
                        }

                except Exception as e:
                    self.logger.error(f"分析股票 {stock_code} 失败: {e}")

            # 3. 投资组合摘要
            results["portfolio_summary"] = self._generate_portfolio_summary(results)

            return results

        except Exception as e:
            self.logger.error(f"每日分析失败: {e}")
            raise

    def _get_market_data(self, date: datetime) -> dict:
        """获取市场数据（模拟实现）"""
        # 这里应该接入真实的市场数据源
        return {
            "current_price": 3000,
            "volume": 100000000,
            "volatility": 0.02,
            "news": [{"title": "市场分析", "sentiment": "neutral"}],
            "calendar": []
        }

    def _get_stock_data(self, stock_code: str, date: datetime) -> dict:
        """获取股票数据（模拟实现）"""
        # 这里应该接入真实的股票数据源
        return {
            "current_price": 50.0,
            "volume": 1000000,
            "volatility": 0.03,
            "technical_indicators": {"rsi": 50, "macd": 0},
            "fundamentals": {"pe_ratio": 20, "pb_ratio": 2},
            "sentiment": {"news_sentiment": 0.1}
        }

    def _generate_portfolio_summary(self, results: dict) -> dict:
        """生成投资组合摘要"""
        summary = {
            "total_stocks": len(results["stock_analyses"]),
            "signal_distribution": {},
            "strategy_distribution": {},
            "position_summary": {}
        }

        # 统计信号分布
        for stock_code, analysis in results["stock_analyses"].items():
            # 信号统计
            for signal_type, signal in analysis["signals"].items():
                if signal["direction"] != "neutral":
                    summary["signal_distribution"][signal_type] = \
                        summary["signal_distribution"].get(signal_type, 0) + 1

            # 策略统计
            strategy = analysis["strategy_recommendation"]["chosen_strategy"]
            summary["strategy_distribution"][strategy] = \
                summary["strategy_distribution"].get(strategy, 0) + 1

            # 仓位统计
            action = analysis["position_decision"]["action"]
            if action != "wait":
                summary["position_summary"][action] = \
                    summary["position_summary"].get(action, 0) + 1

        return summary

    def get_system_info(self) -> dict:
        """获取系统信息"""
        return {
            "config": self.config,
            "agents": {name: agent.get_info() for name, agent in self.agents.items()},
            "database_stats": self.persistence.get_database_stats()
        }

def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='TradingAgents-CN 4智能体交易系统')
    parser.add_argument('--mode', choices=['backtest', 'daily', 'info'],
                       required=True, help='运行模式')
    parser.add_argument('--start', type=str, help='开始日期 (YYYY-MM-DD)')
    parser.add_argument('--end', type=str, help='结束日期 (YYYY-MM-DD)')
    parser.add_argument('--days', type=int, help='回测天数')
    parser.add_argument('--date', type=str, help='分析日期 (YYYY-MM-DD)')
    parser.add_argument('--export', action='store_true', help='导出结果')
    parser.add_argument('--config', type=str, help='配置文件路径')

    args = parser.parse_args()

    try:
        # 初始化系统
        system = TradingAgentsSystem(args.config)

        if args.mode == 'backtest':
            # 回测模式
            result = system.run_backtest(
                start_date=args.start,
                end_date=args.end,
                days=args.days,
                export=args.export
            )

            print(f"\n🎯 回测完成!")
            print(f"总收益率: {result['result'].total_return:.2%}")
            print(f"夏普比率: {result['result'].sharpe_ratio:.2f}")
            if result.get('export_path'):
                print(f"结果已导出至: {result['export_path']}")

        elif args.mode == 'daily':
            # 每日分析模式
            result = system.run_daily_analysis(args.date)

            print(f"\n📊 每日分析完成!")
            print(f"分析股票数: {result['portfolio_summary']['total_stocks']}")
            print(f"市场阶段: {result['market_regime']['regime'].value}")
            print(f"策略分布: {result['portfolio_summary']['strategy_distribution']}")

        elif args.mode == 'info':
            # 系统信息模式
            info = system.get_system_info()

            print("\n🔧 系统信息:")
            print(f"系统名称: {info['config']['system']['name']}")
            print(f"版本: {info['config']['system']['version']}")
            print(f"描述: {info['config']['system']['description']}")
            print(f"监听股票: {len(info['config']['watchlist'])} 只")

    except KeyboardInterrupt:
        print("\n⚠️  用户中断程序")
        sys.exit(0)
    except Exception as e:
        logger.error(f"程序执行失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()