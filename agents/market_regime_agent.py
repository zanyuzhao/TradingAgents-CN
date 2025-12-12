"""
Agent 1: 市场阶段识别智能体 (Market Regime Classifier)
"""

from typing import Dict, Any, Tuple, Optional
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
from scipy.signal import argrelextrema

from core.data_structures import MarketRegime
from core.base_agent import BaseAgent

class MarketRegimeAgent(BaseAgent):
    """
    市场阶段识别智能体

    职责：
    1. 识别当前市场阶段（牛/熊/震荡/事件驱动）
    2. 评估趋势强度
    3. 检测重大市场事件
    4. 输出标准化的市场阶段判断
    """

    def __init__(self, lookback_days: int = 60):
        super().__init__()
        self.lookback_days = lookback_days
        self.regime_weights = {
            'trend_weight': 0.4,      # 趋势权重
            'volatility_weight': 0.2,  # 波动率权重
            'momentum_weight': 0.2,    # 动量权重
            'volume_weight': 0.2       # 成交量权重
        }

    def identify_regime(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        识别市场阶段

        Args:
            market_data: 包含价格、成交量、技术指标等数据

        Returns:
            {
                "regime": MarketRegime,
                "strength": float,  # 0-1
                "confidence": float,  # 0-1
                "evidence": Dict,  # 支撑证据
                "timestamp": datetime
            }
        """

        try:
            # 解析市场数据
            price_data = self._extract_price_data(market_data)
            volume_data = self._extract_volume_data(market_data)
            technical_data = self._extract_technical_data(market_data)

            if len(price_data) < 20:
                return self._get_default_regime()

            # 计算各项指标
            trend_analysis = self._analyze_trend(price_data)
            volatility_analysis = self._analyze_volatility(price_data)
            momentum_analysis = self._analyze_momentum(price_data)
            volume_analysis = self._analyze_volume(volume_data)

            # 事件检测
            event_signals = self._detect_market_events(market_data)

            # 综合判断
            regime_result = self._make_regime_decision(
                trend_analysis,
                volatility_analysis,
                momentum_analysis,
                volume_analysis,
                event_signals
            )

            return regime_result

        except Exception as e:
            self.logger.error(f"市场阶段识别失败: {e}")
            return self._get_default_regime()

    def _analyze_trend(self, price_data: pd.DataFrame) -> Dict[str, Any]:
        """分析价格趋势"""

        if len(price_data) < 20:
            return {"direction": "unknown", "strength": 0.0}

        try:
            # 多时间周期趋势分析
            ma_5 = price_data['close'].rolling(5).mean()
            ma_10 = price_data['close'].rolling(10).mean()
            ma_20 = price_data['close'].rolling(20).mean()
            ma_60 = price_data['close'].rolling(60).mean() if len(price_data) >= 60 else ma_20

            current_price = price_data['close'].iloc[-1]

            # 趋势方向判断
            short_trend = 1 if current_price > ma_5.iloc[-1] else -1
            medium_trend = 1 if current_price > ma_10.iloc[-1] else -1
            long_trend = 1 if current_price > ma_20.iloc[-1] else -1

            # 趋势强度计算
            trend_alignment = (short_trend + medium_trend + long_trend) / 3

            # 价格变化率
            if len(price_data) >= 5:
                price_change_5d = (current_price / price_data['close'].iloc[-5] - 1)
            else:
                price_change_5d = 0

            if len(price_data) >= 20:
                price_change_20d = (current_price / price_data['close'].iloc[-20] - 1)
            else:
                price_change_20d = 0

            return {
                "direction": "bull" if trend_alignment > 0.3 else "bear" if trend_alignment < -0.3 else "neutral",
                "strength": abs(trend_alignment),
                "price_change_5d": price_change_5d,
                "price_change_20d": price_change_20d,
                "ma_alignment": {
                    "short_above_medium": ma_5.iloc[-1] > ma_10.iloc[-1],
                    "medium_above_long": ma_10.iloc[-1] > ma_20.iloc[-1],
                    "trend_consistency": (short_trend == medium_trend == long_trend)
                }
            }

        except Exception as e:
            self.logger.error(f"趋势分析失败: {e}")
            return {"direction": "unknown", "strength": 0.0}

    def _analyze_volatility(self, price_data: pd.DataFrame) -> Dict[str, Any]:
        """分析波动率"""

        if len(price_data) < 20:
            return {"level": "unknown", "strength": 0.0}

        try:
            returns = price_data['close'].pct_change().dropna()

            # 计算波动率指标
            volatility_10d = returns.rolling(10).std().iloc[-1] * np.sqrt(252)
            volatility_20d = returns.rolling(20).std().iloc[-1] * np.sqrt(252)

            if len(returns) >= 60:
                volatility_60d = returns.rolling(60).std().iloc[-1] * np.sqrt(252)
            else:
                volatility_60d = volatility_20d

            # 波动率相对水平
            if volatility_60d > 0:
                vol_ratio = volatility_10d / volatility_60d
            else:
                vol_ratio = 1

            # 波动率水平分类
            if vol_ratio > 1.5:
                vol_level = "high"
            elif vol_ratio > 1.2:
                vol_level = "medium"
            else:
                vol_level = "low"

            return {
                "level": vol_level,
                "current_vol": volatility_10d,
                "historical_vol": volatility_60d,
                "vol_ratio": vol_ratio,
                "strength": min(vol_ratio / 2, 1.0)  # 归一化强度
            }

        except Exception as e:
            self.logger.error(f"波动率分析失败: {e}")
            return {"level": "unknown", "strength": 0.0}

    def _analyze_momentum(self, price_data: pd.DataFrame) -> Dict[str, Any]:
        """分析动量指标"""

        if len(price_data) < 14:
            return {"direction": "neutral", "strength": 0.0}

        try:
            # RSI计算
            delta = price_data['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()

            # 避免除零错误
            loss = loss.replace(0, np.nan)
            gain = gain.replace(0, np.nan)

            rs = gain / loss
            rs = rs.fillna(0)

            rsi = 100 - (100 / (1 + rs))

            # MACD计算
            exp12 = price_data['close'].ewm(span=12).mean()
            exp26 = price_data['close'].ewm(span=26).mean()
            macd = exp12 - exp26
            signal = macd.ewm(span=9).mean()

            current_rsi = rsi.iloc[-1]
            current_macd = macd.iloc[-1]
            current_signal = signal.iloc[-1]

            # 动量方向和强度
            if 30 < current_rsi < 70:
                rsi_signal = "bull"
            elif current_rsi >= 70:
                rsi_signal = "overbought"
            else:
                rsi_signal = "oversold"

            macd_signal = "bull" if current_macd > current_signal else "bear"

            momentum_strength = 0
            if rsi_signal == "bull" and macd_signal == "bull":
                momentum_strength = 0.8
            elif rsi_signal == "bull" or macd_signal == "bull":
                momentum_strength = 0.5
            elif current_rsi >= 70 or current_rsi <= 30:
                momentum_strength = 0.3  # 极端区域可能反转

            return {
                "direction": "bull" if (rsi_signal == "bull" and macd_signal == "bull") else
                           "bear" if (rsi_signal != "bull" and macd_signal == "bear") else "neutral",
                "strength": momentum_strength,
                "rsi": current_rsi,
                "macd": current_macd,
                "signal": current_signal,
                "rsi_signal": rsi_signal,
                "macd_signal": macd_signal
            }

        except Exception as e:
            self.logger.error(f"动量分析失败: {e}")
            return {"direction": "neutral", "strength": 0.0}

    def _analyze_volume(self, volume_data: pd.DataFrame) -> Dict[str, Any]:
        """分析成交量"""

        if len(volume_data) < 20:
            return {"level": "unknown", "strength": 0.0}

        try:
            # 成交量移动平均
            vol_ma_10 = volume_data['volume'].rolling(10).mean()
            vol_ma_20 = volume_data['volume'].rolling(20).mean()

            current_volume = volume_data['volume'].iloc[-1]
            avg_volume_10 = vol_ma_10.iloc[-1]
            avg_volume_20 = vol_ma_20.iloc[-1]

            # 成交量相对水平
            if avg_volume_10 > 0:
                vol_ratio_10 = current_volume / avg_volume_10
            else:
                vol_ratio_10 = 1

            if avg_volume_20 > 0:
                vol_ratio_20 = current_volume / avg_volume_20
            else:
                vol_ratio_20 = 1

            # 成交量趋势
            if vol_ma_10.iloc[-1] > vol_ma_20.iloc[-1]:
                volume_trend = 1
            else:
                volume_trend = -1

            # 成交量水平分类
            if vol_ratio_10 > 2.0:
                vol_level = "very_high"
            elif vol_ratio_10 > 1.5:
                vol_level = "high"
            elif vol_ratio_10 > 0.8:
                vol_level = "normal"
            else:
                vol_level = "low"

            return {
                "level": vol_level,
                "current_volume": current_volume,
                "avg_volume_10": avg_volume_10,
                "avg_volume_20": avg_volume_20,
                "vol_ratio_10": vol_ratio_10,
                "vol_ratio_20": vol_ratio_20,
                "volume_trend": volume_trend,
                "strength": min(vol_ratio_10 / 3, 1.0)  # 归一化强度
            }

        except Exception as e:
            self.logger.error(f"成交量分析失败: {e}")
            return {"level": "unknown", "strength": 0.0}

    def _detect_market_events(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """检测重大市场事件"""

        events = {
            "policy_events": [],
            "earnings_events": [],
            "economic_data": [],
            "market_shocks": []
        }

        try:
            # 政策事件检测
            news_data = market_data.get('news', [])
            for news_item in news_data[:10]:  # 最近10条新闻
                if any(keyword in news_item.get('title', '').lower() for keyword in
                       ['政策', '央行', '降准', '加息', '监管', '财政', '国常会']):
                    events["policy_events"].append({
                        "title": news_item.get('title', ''),
                        "sentiment": news_item.get('sentiment', 'neutral'),
                        "impact": self._estimate_news_impact(news_item)
                    })

            # 财报事件检测
            calendar_data = market_data.get('calendar', [])
            for cal_item in calendar_data:
                if '财报' in cal_item.get('event', '') or '业绩' in cal_item.get('event', ''):
                    events["earnings_events"].append({
                        "event": cal_item.get('event', ''),
                        "date": cal_item.get('date', ''),
                        "impact_level": cal_item.get('importance', 'medium')
                    })

            # 市场冲击检测（价格异常波动）
            price_data = self._extract_price_data(market_data)
            if len(price_data) >= 5:
                daily_returns = price_data['close'].pct_change().dropna()
                if len(daily_returns) >= 5:
                    extreme_move = daily_returns.abs().iloc[-5:].max()
                    if extreme_move > 0.05:  # 单日涨跌幅超过5%
                        events["market_shocks"].append({
                            "date": daily_returns.index[-5:].max(),
                            "magnitude": extreme_move,
                            "direction": "up" if daily_returns.iloc[-1] > 0 else "down"
                        })

            return {
                "events": events,
                "has_policy_impact": len(events["policy_events"]) > 0,
                "has_earnings_impact": len(events["earnings_events"]) > 0,
                "has_market_shock": len(events["market_shocks"]) > 0,
                "overall_event_strength": min((len(events["policy_events"]) +
                                            len(events["earnings_events"]) +
                                            len(events["market_shocks"])) / 5, 1.0)
            }

        except Exception as e:
            self.logger.error(f"事件检测失败: {e}")
            return {
                "events": events,
                "has_policy_impact": False,
                "has_earnings_impact": False,
                "has_market_shock": False,
                "overall_event_strength": 0.0
            }

    def _make_regime_decision(self, trend_analysis: Dict, volatility_analysis: Dict,
                            momentum_analysis: Dict, volume_analysis: Dict,
                            event_signals: Dict) -> Dict[str, Any]:
        """综合判断市场阶段"""

        try:
            # 计算综合得分
            trend_score = trend_analysis["strength"] * (1 if trend_analysis["direction"] == "bull" else
                                                      -1 if trend_analysis["direction"] == "bear" else 0)
            momentum_score = momentum_analysis["strength"] * (1 if momentum_analysis["direction"] == "bull" else
                                                           -1 if momentum_analysis["direction"] == "bear" else 0)
            volume_score = volume_analysis["strength"] * volume_analysis["volume_trend"]

            # 事件驱动检查
            if event_signals["overall_event_strength"] > 0.3:
                if event_signals["has_policy_impact"]:
                    regime = MarketRegime.EVENT_DRIVEN_POLICY
                    strength = event_signals["overall_event_strength"]
                elif event_signals["has_earnings_impact"]:
                    regime = MarketRegime.EVENT_DRIVEN_EARNINGS
                    strength = event_signals["overall_event_strength"]
                else:
                    # 事件驱动但不明确类型，按趋势判断
                    regime, strength = self._determine_trend_regime(trend_score, momentum_analysis, volatility_analysis)
            else:
                # 无重大事件，按常规趋势判断
                regime, strength = self._determine_trend_regime(trend_score, momentum_analysis, volatility_analysis)

            # 计算置信度
            confidence_factors = [
                abs(trend_score),
                abs(momentum_score),
                volume_analysis["strength"],
                1 - event_signals["overall_event_strength"]  # 事件越少，置信度越高
            ]
            confidence = np.mean(confidence_factors)

            return {
                "regime": regime,
                "strength": min(strength, 1.0),
                "confidence": min(confidence, 1.0),
                "evidence": {
                    "trend": trend_analysis,
                    "momentum": momentum_analysis,
                    "volume": volume_analysis,
                    "volatility": volatility_analysis,
                    "events": event_signals
                },
                "timestamp": datetime.now()
            }

        except Exception as e:
            self.logger.error(f"市场阶段决策失败: {e}")
            return self._get_default_regime()

    def _determine_trend_regime(self, trend_score: float, momentum_analysis: Dict,
                               volatility_analysis: Dict) -> tuple:
        """确定趋势类型市场阶段"""

        try:
            combined_score = (trend_score + momentum_analysis["strength"]) / 2
            vol_level = volatility_analysis.get("level", "medium")

            if combined_score > 0.5:
                # 牛市
                if vol_level == "high":
                    return MarketRegime.BULL_TREND_STRONG, abs(combined_score)
                else:
                    return MarketRegime.BULL_TREND_WEAK, abs(combined_score) * 0.8
            elif combined_score < -0.5:
                # 熊市
                if vol_level == "high":
                    return MarketRegime.BEAR_TREND_STRONG, abs(combined_score)
                else:
                    return MarketRegime.BEAR_TREND_WEAK, abs(combined_score) * 0.8
            else:
                # 震荡市
                if vol_level in ["high", "medium"]:
                    return MarketRegime.SIDEWAYS_HIGH_VOL, 0.5
                else:
                    return MarketRegime.SIDEWAYS_LOW_VOL, 0.4

        except Exception as e:
            self.logger.error(f"趋势类型判断失败: {e}")
            return MarketRegime.SIDEWAYS_LOW_VOL, 0.3

    def _estimate_news_impact(self, news_item: Dict[str, Any]) -> str:
        """评估新闻影响"""
        title = news_item.get('title', '').lower()

        high_impact_keywords = ['重大', '紧急', '突发', '重要', '官方', '宣布', '国常会']
        medium_impact_keywords = ['可能', '预计', '计划', '考虑', '讨论']

        if any(keyword in title for keyword in high_impact_keywords):
            return "high"
        elif any(keyword in title for keyword in medium_impact_keywords):
            return "medium"
        else:
            return "low"

    def _get_default_regime(self) -> Dict[str, Any]:
        """获取默认市场阶段"""
        return {
            "regime": MarketRegime.SIDEWAYS_LOW_VOL,
            "strength": 0.3,
            "confidence": 0.3,
            "evidence": {"error": "insufficient_data"},
            "timestamp": datetime.now()
        }

    def _extract_price_data(self, market_data: Dict[str, Any]) -> pd.DataFrame:
        """提取价格数据"""
        try:
            price_data = market_data.get('price_data')
            if price_data is None:
                return pd.DataFrame()

            if isinstance(price_data, dict):
                price_data = pd.DataFrame(price_data)

            # 确保必要的列存在
            required_columns = ['open', 'high', 'low', 'close', 'volume']
            for col in required_columns:
                if col not in price_data.columns:
                    price_data[col] = 0

            return price_data

        except Exception as e:
            self.logger.error(f"价格数据提取失败: {e}")
            return pd.DataFrame()

    def _extract_volume_data(self, market_data: Dict[str, Any]) -> pd.DataFrame:
        """提取成交量数据"""
        try:
            volume_data = market_data.get('volume_data')
            if volume_data is None:
                # 从价格数据中提取成交量
                price_data = self._extract_price_data(market_data)
                if 'volume' in price_data.columns:
                    return price_data[['volume']]
                else:
                    return pd.DataFrame({"volume": [0]})

            if isinstance(volume_data, dict):
                volume_data = pd.DataFrame(volume_data)

            # 确保volume列存在
            if 'volume' not in volume_data.columns:
                volume_data['volume'] = 0

            return volume_data[['volume']]

        except Exception as e:
            self.logger.error(f"成交量数据提取失败: {e}")
            return pd.DataFrame({"volume": [0]})

    def _extract_technical_data(self, market_data: Dict[str, Any]) -> Dict[str, Any]:
        """提取技术指标数据"""
        return market_data.get('technical_indicators', {})