"""
Agent 2: 信号生成智能体 (Signal Generator)
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import pandas as pd
import numpy as np
from scipy.signal import argrelextrema

from core.data_structures import TradingSignal, SignalType, SignalStrength
from core.base_agent import BaseAgent

class SignalGeneratorAgent(BaseAgent):
    """
    信号生成智能体

    职责：
    1. 独立生成6类信号（不交叉、不融合）
    2. 每类信号基于独立的逻辑和指标
    3. 提供详细的信号强度和置信度评估
    4. 支持多时间框架分析
    """

    def __init__(self):
        super().__init__("SignalGenerator")
        self.signal_configs = {
            SignalType.TREND: {
                "lookback_periods": [5, 10, 20, 60],
                "thresholds": {"strong": 0.8, "moderate": 0.5, "weak": 0.3}
            },
            SignalType.MOMENTUM: {
                "rsi_period": 14,
                "macd_params": (12, 26, 9),
                "stoch_params": (14, 3, 3)
            },
            SignalType.PULLBACK: {
                "ma_periods": [10, 20, 50],
                "pullback_threshold": 0.05,
                "volume_threshold": 1.5
            },
            SignalType.VALUATION: {
                "pe_ranges": {"cheap": 10, "fair": 20, "expensive": 30},
                "pb_ranges": {"cheap": 1.5, "fair": 3, "expensive": 5},
                "dividend_threshold": 0.03
            },
            SignalType.SENTIMENT: {
                "news_weight": 0.4,
                "social_weight": 0.3,
                "analyst_weight": 0.3
            },
            SignalType.VOLATILITY: {
                "atr_period": 14,
                "vol_window": 20,
                "vol_threshold": 2.0
            }
        }

    def generate_signals(self, stock_data: Dict[str, Any]) -> Dict[str, TradingSignal]:
        """
        为单只股票生成所有类型的信号

        Args:
            stock_data: 包含价格、基本面、新闻等数据的字典

        Returns:
            Dict[SignalType, TradingSignal]: 6类信号的集合
        """

        try:
            signals = {}

            # 生成各类信号
            signals[SignalType.TREND] = self._generate_trend_signal(stock_data)
            signals[SignalType.MOMENTUM] = self._generate_momentum_signal(stock_data)
            signals[SignalType.PULLBACK] = self._generate_pullback_signal(stock_data)
            signals[SignalType.VALUATION] = self._generate_valuation_signal(stock_data)
            signals[SignalType.SENTIMENT] = self._generate_sentiment_signal(stock_data)
            signals[SignalType.VOLATILITY] = self._generate_volatility_signal(stock_data)

            return signals

        except Exception as e:
            self.logger.error(f"信号生成失败: {e}")
            # 返回中性信号
            return {signal_type: self._get_neutral_signal(signal_type) for signal_type in SignalType}

    def _generate_trend_signal(self, stock_data: Dict[str, Any]) -> TradingSignal:
        """生成趋势信号"""

        try:
            price_data = stock_data.get('price_data', pd.DataFrame())

            if len(price_data) < 20:
                return self._get_neutral_signal(SignalType.TREND)

            current_price = price_data['close'].iloc[-1]

            # 多周期移动平均线分析
            ma_analysis = {}
            for period in [5, 10, 20, 60]:
                if len(price_data) >= period:
                    ma = price_data['close'].rolling(period).mean().iloc[-1]
                    ma_analysis[f'ma_{period}'] = {
                        'value': ma,
                        'above': current_price > ma,
                        'distance': (current_price - ma) / ma if ma > 0 else 0
                    }

            # 均线排列分析
            ma_5 = ma_analysis.get('ma_5', {}).get('value', 0)
            ma_10 = ma_analysis.get('ma_10', {}).get('value', 0)
            ma_20 = ma_analysis.get('ma_20', {}).get('value', 0)
            ma_60 = ma_analysis.get('ma_60', {}).get('value', 0)

            # 趋势强度评分
            trend_score = 0

            # 均线多头排列 (+2分)
            if ma_5 > ma_10 > ma_20 > ma_60:
                trend_score += 2
            # 均线空头排列 (-2分)
            elif ma_5 < ma_10 < ma_20 < ma_60:
                trend_score -= 2

            # 价格相对于均线位置
            if ma_analysis.get('ma_5', {}).get('above', False):
                trend_score += 1
            else:
                trend_score -= 1

            # 趋势持续性（近期波动）
            if len(price_data) >= 10:
                recent_volatility = price_data['close'].pct_change().tail(10).std()
                if recent_volatility < 0.03:  # 低波动，趋势稳定
                    trend_score += 0.5
                elif recent_volatility > 0.08:  # 高波动，趋势不稳定
                    trend_score -= 0.5

            # 成交量确认
            volume_data = stock_data.get('volume_data', pd.DataFrame())
            if len(volume_data) > 0:
                recent_volume = volume_data['volume'].tail(10).mean()
                avg_volume = volume_data['volume'].mean()
                if avg_volume > 0:
                    volume_ratio = recent_volume / avg_volume

                    if trend_score > 0 and volume_ratio > 1.2:  # 上涨放量
                        trend_score += 0.5
                    elif trend_score > 0 and volume_ratio < 0.8:  # 上涨缩量
                        trend_score -= 0.5

            # 确定信号方向和强度
            if trend_score >= 2.5:
                direction = "long"
                strength = SignalStrength.VERY_STRONG
            elif trend_score >= 1.5:
                direction = "long"
                strength = SignalStrength.STRONG
            elif trend_score >= 0.5:
                direction = "long"
                strength = SignalStrength.MODERATE
            elif trend_score <= -2.5:
                direction = "short"
                strength = SignalStrength.VERY_STRONG
            elif trend_score <= -1.5:
                direction = "short"
                strength = SignalStrength.STRONG
            elif trend_score <= -0.5:
                direction = "short"
                strength = SignalStrength.MODERATE
            else:
                direction = "neutral"
                strength = SignalStrength.NEUTRAL

            confidence = min(abs(trend_score) / 3, 1.0)

            # 设置关键价位
            stop_loss = None
            take_profit = None

            if direction == "long":
                atr = self._calculate_atr(price_data, 14)
                if atr > 0:
                    stop_loss = current_price - 2 * atr
                    take_profit = current_price + 3 * atr
            elif direction == "short":
                atr = self._calculate_atr(price_data, 14)
                if atr > 0:
                    stop_loss = current_price + 2 * atr
                    take_profit = current_price - 3 * atr

            return TradingSignal(
                signal_type=SignalType.TREND,
                direction=direction,
                strength=strength,
                confidence=confidence,
                entry_price=current_price,
                stop_loss=stop_loss,
                take_profit=take_profit,
                time_horizon="medium",
                evidence={
                    "trend_score": trend_score,
                    "ma_analysis": ma_analysis,
                    "volume_confirmation": volume_ratio if 'volume_ratio' in locals() else 1.0,
                    "volatility": recent_volatility if 'recent_volatility' in locals() else 0.02
                },
                timestamp=datetime.now()
            )

        except Exception as e:
            self.logger.error(f"趋势信号生成失败: {e}")
            return self._get_neutral_signal(SignalType.TREND)

    def _generate_momentum_signal(self, stock_data: Dict[str, Any]) -> TradingSignal:
        """生成动量信号"""

        try:
            price_data = stock_data.get('price_data', pd.DataFrame())

            if len(price_data) < 26:
                return self._get_neutral_signal(SignalType.MOMENTUM)

            current_price = price_data['close'].iloc[-1]

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
            signal_line = macd.ewm(span=9).mean()
            histogram = macd - signal_line

            current_rsi = rsi.iloc[-1]
            current_macd = macd.iloc[-1]
            current_signal = signal_line.iloc[-1]
            current_histogram = histogram.iloc[-1]

            # 随机指标分析
            low_14 = price_data['low'].rolling(14).min()
            high_14 = price_data['high'].rolling(14).max()
            k_percent = 100 * ((price_data['close'] - low_14) / (high_14 - low_14))
            d_percent = k_percent.rolling(3).mean()

            current_k = k_percent.iloc[-1]
            current_d = d_percent.iloc[-1]

            # 动量评分
            momentum_score = 0

            # RSI贡献
            if 30 < current_rsi < 70:
                if current_rsi > 50:
                    momentum_score += 1
                else:
                    momentum_score -= 1
            elif current_rsi <= 30:  # 超卖，可能反弹
                momentum_score += 1.5
            elif current_rsi >= 70:  # 超买，可能回调
                momentum_score -= 1.5

            # MACD贡献
            if current_macd > current_signal:
                if current_histogram > 0:  # MACD金叉且柱状图为正
                    momentum_score += 1.5
                else:  # MACD在信号线上方但柱状图转负
                    momentum_score += 0.5
            else:
                if current_histogram < 0:  # MACD死叉且柱状图为负
                    momentum_score -= 1.5
                else:  # MACD在信号线下方但柱状图转正
                    momentum_score -= 0.5

            # 随机指标贡献
            if current_k > current_d:
                if current_k < 80:  # K>D且未超买
                    momentum_score += 1
                else:  # K>D但超买
                    momentum_score += 0.3
            else:
                if current_k > 20:  # K<D且未超卖
                    momentum_score -= 1
                else:  # K<D但超卖
                    momentum_score -= 0.3

            # 动量趋势变化
            if len(rsi) >= 5:
                rsi_trend = rsi.tail(5).diff().mean()
                if rsi_trend > 0:
                    momentum_score += 0.5
                elif rsi_trend < 0:
                    momentum_score -= 0.5

            # 确定信号方向和强度
            if momentum_score >= 3:
                direction = "long"
                strength = SignalStrength.VERY_STRONG
            elif momentum_score >= 2:
                direction = "long"
                strength = SignalStrength.STRONG
            elif momentum_score >= 1:
                direction = "long"
                strength = SignalStrength.MODERATE
            elif momentum_score <= -3:
                direction = "short"
                strength = SignalStrength.VERY_STRONG
            elif momentum_score <= -2:
                direction = "short"
                strength = SignalStrength.STRONG
            elif momentum_score <= -1:
                direction = "short"
                strength = SignalStrength.MODERATE
            else:
                direction = "neutral"
                strength = SignalStrength.NEUTRAL

            confidence = min(abs(momentum_score) / 4, 1.0)

            return TradingSignal(
                signal_type=SignalType.MOMENTUM,
                direction=direction,
                strength=strength,
                confidence=confidence,
                entry_price=current_price,
                time_horizon="short",
                evidence={
                    "momentum_score": momentum_score,
                    "rsi": current_rsi,
                    "macd": current_macd,
                    "macd_signal": current_signal,
                    "histogram": current_histogram,
                    "stoch_k": current_k,
                    "stoch_d": current_d
                },
                timestamp=datetime.now()
            )

        except Exception as e:
            self.logger.error(f"动量信号生成失败: {e}")
            return self._get_neutral_signal(SignalType.MOMENTUM)

    def _generate_pullback_signal(self, stock_data: Dict[str, Any]) -> TradingSignal:
        """生成回调信号"""

        try:
            price_data = stock_data.get('price_data', pd.DataFrame())

            if len(price_data) < 50:
                return self._get_neutral_signal(SignalType.PULLBACK)

            current_price = price_data['close'].iloc[-1]

            # 多周期均线分析
            ma_10 = price_data['close'].rolling(10).mean().iloc[-1] if len(price_data) >= 10 else current_price
            ma_20 = price_data['close'].rolling(20).mean().iloc[-1] if len(price_data) >= 20 else current_price
            ma_50 = price_data['close'].rolling(50).mean().iloc[-1] if len(price_data) >= 50 else current_price

            # 判断整体趋势
            overall_trend = "up" if ma_10 > ma_20 > ma_50 else "down" if ma_10 < ma_20 < ma_50 else "sideways"

            # 回调分析
            pullback_score = 0

            if overall_trend == "up":
                # 上升趋势中的回调买入机会
                if ma_20 > 0:
                    pullback_depth = (ma_20 - current_price) / ma_20
                else:
                    pullback_depth = 0

                if pullback_depth > 0.08:  # 回调超过8%
                    pullback_score += 2
                elif pullback_depth > 0.05:  # 回调5-8%
                    pullback_score += 1.5
                elif pullback_depth > 0.03:  # 回调3-5%
                    pullback_score += 1

                # 价格接近关键均线
                if abs(current_price - ma_20) / ma_20 < 0.02:  # 接近20日线
                    pullback_score += 1
                if abs(current_price - ma_50) / ma_50 < 0.05:  # 接近50日线
                    pullback_score += 0.5

                direction = "long"

            elif overall_trend == "down":
                # 下降趋势中的反弹卖出机会
                if ma_20 > 0:
                    pullback_depth = (current_price - ma_20) / ma_20
                else:
                    pullback_depth = 0

                if pullback_depth > 0.08:  # 反弹超过8%
                    pullback_score += 2
                elif pullback_depth > 0.05:  # 反弹5-8%
                    pullback_score += 1.5
                elif pullback_depth > 0.03:  # 反弹3-5%
                    pullback_score += 1

                direction = "short"
            else:
                # 震荡市，回调信号较弱
                direction = "neutral"

            # 成交量确认
            volume_data = stock_data.get('volume_data', pd.DataFrame())
            if len(volume_data) > 0:
                recent_volume = volume_data['volume'].tail(5).mean()
                avg_volume = volume_data['volume'].tail(20).mean()
                if avg_volume > 0:
                    volume_ratio = recent_volume / avg_volume

                    # 回调时成交量萎缩是好信号
                    if direction == "long" and volume_ratio < 0.7:
                        pullback_score += 0.5
                    # 反弹时成交量放大是确认信号
                    elif direction == "short" and volume_ratio > 1.3:
                        pullback_score += 0.5

            # 支撑阻力位分析
            support_resistance = self._find_support_resistance(price_data)
            if support_resistance:
                nearest_support = support_resistance.get('nearest_support')
                nearest_resistance = support_resistance.get('nearest_resistance')

                if direction == "long" and nearest_support:
                    support_distance = (current_price - nearest_support) / current_price
                    if support_distance < 0.05:  # 接近支撑位
                        pullback_score += 1

                if direction == "short" and nearest_resistance:
                    resistance_distance = (nearest_resistance - current_price) / current_price
                    if resistance_distance < 0.05:  # 接近阻力位
                        pullback_score += 1

            # 确定信号强度
            if pullback_score >= 3:
                strength = SignalStrength.STRONG
            elif pullback_score >= 2:
                strength = SignalStrength.MODERATE
            elif pullback_score >= 1:
                strength = SignalStrength.WEAK
            elif direction == "neutral":
                strength = SignalStrength.NEUTRAL
            else:
                strength = SignalStrength.VERY_WEAK

            confidence = min(abs(pullback_score) / 3.5, 1.0)

            return TradingSignal(
                signal_type=SignalType.PULLBACK,
                direction=direction,
                strength=strength,
                confidence=confidence,
                entry_price=current_price,
                time_horizon="short",
                evidence={
                    "pullback_score": pullback_score,
                    "overall_trend": overall_trend,
                    "pullback_depth": (ma_20 - current_price) / ma_20 if overall_trend == "up" and ma_20 > 0 else
                                     (current_price - ma_20) / ma_20 if overall_trend == "down" and ma_20 > 0 else 0,
                    "ma_levels": {"ma_10": ma_10, "ma_20": ma_20, "ma_50": ma_50},
                    "support_resistance": support_resistance
                },
                timestamp=datetime.now()
            )

        except Exception as e:
            self.logger.error(f"回调信号生成失败: {e}")
            return self._get_neutral_signal(SignalType.PULLBACK)

    def _generate_valuation_signal(self, stock_data: Dict[str, Any]) -> TradingSignal:
        """生成价值信号"""

        try:
            fundamentals = stock_data.get('fundamentals', {})

            if not fundamentals:
                return self._get_neutral_signal(SignalType.VALUATION)

            valuation_score = 0
            evidence = {}

            # PE估值分析
            pe_ratio = fundamentals.get('pe_ratio')
            if pe_ratio and pe_ratio > 0:
                evidence['pe_ratio'] = pe_ratio
                if pe_ratio < 10:
                    valuation_score += 2
                elif pe_ratio < 15:
                    valuation_score += 1
                elif pe_ratio > 50:
                    valuation_score -= 2
                elif pe_ratio > 30:
                    valuation_score -= 1

            # PB估值分析
            pb_ratio = fundamentals.get('pb_ratio')
            if pb_ratio and pb_ratio > 0:
                evidence['pb_ratio'] = pb_ratio
                if pb_ratio < 1.5:
                    valuation_score += 2
                elif pb_ratio < 3:
                    valuation_score += 1
                elif pb_ratio > 8:
                    valuation_score -= 2
                elif pb_ratio > 5:
                    valuation_score -= 1

            # 股息率分析
            dividend_yield = fundamentals.get('dividend_yield', 0)
            if dividend_yield > 0:
                evidence['dividend_yield'] = dividend_yield
                if dividend_yield > 0.05:  # 5%以上高股息
                    valuation_score += 1.5
                elif dividend_yield > 0.03:  # 3%以上合理股息
                    valuation_score += 1
                elif dividend_yield < 0.01:  # 1%以下低股息
                    valuation_score -= 0.5

            # ROE分析
            roe = fundamentals.get('roe')
            if roe and roe > 0:
                evidence['roe'] = roe
                if roe > 0.20:  # ROE超过20%
                    valuation_score += 1.5
                elif roe > 0.15:  # ROE超过15%
                    valuation_score += 1
                elif roe < 0.05:  # ROE低于5%
                    valuation_score -= 1

            # 营收增长分析
            revenue_growth = fundamentals.get('revenue_growth')
            if revenue_growth:
                evidence['revenue_growth'] = revenue_growth
                if revenue_growth > 0.30:  # 30%以上高增长
                    valuation_score += 1
                elif revenue_growth > 0.15:  # 15%以上稳健增长
                    valuation_score += 0.5
                elif revenue_growth < -0.10:  # 负增长
                    valuation_score -= 1

            # 行业比较估值
            industry_pe = fundamentals.get('industry_pe')
            if industry_pe and industry_pe > 0 and pe_ratio and pe_ratio > 0:
                pe_comparison = (industry_pe - pe_ratio) / industry_pe
                evidence['pe_vs_industry'] = pe_comparison
                if pe_comparison > 0.2:  # 比行业平均便宜20%以上
                    valuation_score += 1
                elif pe_comparison < -0.2:  # 比行业平均贵20%以上
                    valuation_score -= 1

            # 确定信号方向和强度
            if valuation_score >= 4:
                direction = "long"
                strength = SignalStrength.STRONG
            elif valuation_score >= 2:
                direction = "long"
                strength = SignalStrength.MODERATE
            elif valuation_score >= 1:
                direction = "long"
                strength = SignalStrength.WEAK
            elif valuation_score <= -3:
                direction = "short"
                strength = SignalStrength.STRONG
            elif valuation_score <= -2:
                direction = "short"
                strength = SignalStrength.MODERATE
            elif valuation_score <= -1:
                direction = "short"
                strength = SignalStrength.WEAK
            else:
                direction = "neutral"
                strength = SignalStrength.NEUTRAL

            confidence = min(abs(valuation_score) / 5, 1.0)

            return TradingSignal(
                signal_type=SignalType.VALUATION,
                direction=direction,
                strength=strength,
                confidence=confidence,
                time_horizon="long",
                evidence=evidence,
                timestamp=datetime.now()
            )

        except Exception as e:
            self.logger.error(f"价值信号生成失败: {e}")
            return self._get_neutral_signal(SignalType.VALUATION)

    def _generate_sentiment_signal(self, stock_data: Dict[str, Any]) -> TradingSignal:
        """生成情绪信号"""

        try:
            sentiment_data = stock_data.get('sentiment', {})

            if not sentiment_data:
                return self._get_neutral_signal(SignalType.SENTIMENT)

            sentiment_score = 0
            evidence = {}

            # 新闻情绪分析
            news_sentiment = sentiment_data.get('news_sentiment', 0)
            news_count = sentiment_data.get('news_count', 0)

            if news_count > 0:
                evidence['news_sentiment'] = news_sentiment
                evidence['news_count'] = news_count

                # 新闻情绪权重根据新闻数量调整
                news_weight = min(news_count / 10, 1.0) * 0.4
                sentiment_score += news_sentiment * news_weight

            # 社交媒体情绪
            social_sentiment = sentiment_data.get('social_sentiment', 0)
            social_volume = sentiment_data.get('social_volume', 0)

            if social_volume > 100:  # 最低讨论量门槛
                evidence['social_sentiment'] = social_sentiment
                evidence['social_volume'] = social_volume

                # 社交媒体情绪权重
                social_weight = min(social_volume / 1000, 1.0) * 0.3
                sentiment_score += social_sentiment * social_weight

            # 分析师评级
            analyst_ratings = sentiment_data.get('analyst_ratings', {})
            if analyst_ratings:
                buy_count = analyst_ratings.get('buy', 0)
                hold_count = analyst_ratings.get('hold', 0)
                sell_count = analyst_ratings.get('sell', 0)
                total_ratings = buy_count + hold_count + sell_count

                if total_ratings > 0:
                    analyst_score = (buy_count - sell_count) / total_ratings
                    evidence['analyst_score'] = analyst_score
                    evidence['total_ratings'] = total_ratings

                    # 分析师评级权重
                    analyst_weight = min(total_ratings / 20, 1.0) * 0.3
                    sentiment_score += analyst_score * analyst_weight

            # 机构持仓变化
            institution_change = sentiment_data.get('institution_change', 0)
            if institution_change:
                evidence['institution_change'] = institution_change
                if institution_change > 0.05:  # 机构增持超过5%
                    sentiment_score += 0.5
                elif institution_change < -0.05:  # 机构减持超过5%
                    sentiment_score -= 0.5

            # 情绪极值检测
            if abs(sentiment_score) > 1.5:
                sentiment_score = np.sign(sentiment_score) * 1.5  # 限制极值

            # 确定信号方向和强度
            if sentiment_score >= 1.0:
                direction = "long"
                strength = SignalStrength.STRONG
            elif sentiment_score >= 0.5:
                direction = "long"
                strength = SignalStrength.MODERATE
            elif sentiment_score >= 0.2:
                direction = "long"
                strength = SignalStrength.WEAK
            elif sentiment_score <= -1.0:
                direction = "short"
                strength = SignalStrength.STRONG
            elif sentiment_score <= -0.5:
                direction = "short"
                strength = SignalStrength.MODERATE
            elif sentiment_score <= -0.2:
                direction = "short"
                strength = SignalStrength.WEAK
            else:
                direction = "neutral"
                strength = SignalStrength.NEUTRAL

            # 计算置信度
            confidence_factors = []
            if news_count > 0:
                confidence_factors.append(min(news_count / 5, 1.0))
            if social_volume > 100:
                confidence_factors.append(min(social_volume / 500, 1.0))
            if analyst_ratings and sum(analyst_ratings.values()) > 0:
                confidence_factors.append(min(sum(analyst_ratings.values()) / 10, 1.0))

            confidence = np.mean(confidence_factors) if confidence_factors else 0.0

            return TradingSignal(
                signal_type=SignalType.SENTIMENT,
                direction=direction,
                strength=strength,
                confidence=confidence,
                time_horizon="medium",
                evidence=evidence,
                timestamp=datetime.now()
            )

        except Exception as e:
            self.logger.error(f"情绪信号生成失败: {e}")
            return self._get_neutral_signal(SignalType.SENTIMENT)

    def _generate_volatility_signal(self, stock_data: Dict[str, Any]) -> TradingSignal:
        """生成风险信号"""

        try:
            price_data = stock_data.get('price_data', pd.DataFrame())

            if len(price_data) < 30:
                return self._get_neutral_signal(SignalType.VOLATILITY)

            current_price = price_data['close'].iloc[-1]

            # ATR计算
            atr = self._calculate_atr(price_data, 14)

            # 历史波动率
            returns = price_data['close'].pct_change().dropna()
            if len(returns) >= 20:
                historical_vol = returns.rolling(20).std().iloc[-1] * np.sqrt(252)
            else:
                historical_vol = returns.std() * np.sqrt(252) if len(returns) > 0 else 0.02

            # 近期波动率
            if len(returns) >= 10:
                recent_vol = returns.tail(10).std() * np.sqrt(252)
            else:
                recent_vol = returns.std() * np.sqrt(252) if len(returns) > 0 else 0.02

            # 波动率比率
            if historical_vol > 0:
                vol_ratio = recent_vol / historical_vol
            else:
                vol_ratio = 1

            # 价格区间分析
            if len(price_data) >= 20:
                high_20 = price_data['high'].rolling(20).max().iloc[-1]
                low_20 = price_data['low'].rolling(20).min().iloc[-1]
                if low_20 > 0:
                    price_range = (high_20 - low_20) / low_20
                else:
                    price_range = 0.1
            else:
                price_range = 0.1

            # 风险评分
            risk_score = 0

            # 波动率异常
            if vol_ratio > 2.0:  # 波动率是历史2倍以上
                risk_score += 2
            elif vol_ratio > 1.5:
                risk_score += 1
            elif vol_ratio < 0.5:  # 波动率极低也可能风险
                risk_score += 0.5

            # ATR异常
            if atr and atr > 0:
                atr_ratio = atr / current_price
                if atr_ratio > 0.05:  # 日波动超过5%
                    risk_score += 1.5
                elif atr_ratio > 0.03:  # 日波动超过3%
                    risk_score += 0.5

            # 价格位置风险
            if len(price_data) >= 20:
                price_position = (current_price - low_20) / (high_20 - low_20) if high_20 != low_20 else 0.5
                if price_position > 0.9 or price_position < 0.1:  # 价格在区间极端
                    risk_score += 1

            # 连续涨跌风险
            consecutive_moves = self._count_consecutive_moves(price_data)
            if abs(consecutive_moves) > 5:  # 连续5天以上同方向
                risk_score += 1

            # 确定信号强度（注意：这是风险信号，方向表示风险等级）
            if risk_score >= 3:
                strength = SignalStrength.VERY_STRONG
            elif risk_score >= 2:
                strength = SignalStrength.STRONG
            elif risk_score >= 1:
                strength = SignalStrength.MODERATE
            else:
                strength = SignalStrength.WEAK

            # 风险信号的方向表示风险等级
            if risk_score >= 2:
                direction = "high_risk"
            elif risk_score >= 1:
                direction = "medium_risk"
            else:
                direction = "low_risk"

            confidence = min(risk_score / 4, 1.0)

            return TradingSignal(
                signal_type=SignalType.VOLATILITY,
                direction=direction,
                strength=strength,
                confidence=confidence,
                entry_price=current_price,
                stop_loss=current_price - 2 * atr if atr and atr > 0 else None,
                time_horizon="short",
                evidence={
                    "risk_score": risk_score,
                    "vol_ratio": vol_ratio,
                    "historical_vol": historical_vol,
                    "recent_vol": recent_vol,
                    "atr": atr,
                    "atr_ratio": atr_ratio if atr and atr > 0 else 0,
                    "price_range": price_range,
                    "price_position": price_position if 'price_position' in locals() else 0.5,
                    "consecutive_moves": consecutive_moves
                },
                timestamp=datetime.now()
            )

        except Exception as e:
            self.logger.error(f"风险信号生成失败: {e}")
            return self._get_neutral_signal(SignalType.VOLATILITY)

    def _calculate_atr(self, price_data: pd.DataFrame, period: int = 14) -> float:
        """计算ATR"""
        try:
            if len(price_data) < period + 1:
                return 0

            high_low = price_data['high'] - price_data['low']
            high_close = abs(price_data['high'] - price_data['close'].shift(1))
            low_close = abs(price_data['low'] - price_data['close'].shift(1))

            true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            atr = true_range.rolling(period).mean().iloc[-1]

            return atr if not np.isnan(atr) else 0

        except Exception as e:
            self.logger.error(f"ATR计算失败: {e}")
            return 0

    def _find_support_resistance(self, price_data: pd.DataFrame, lookback: int = 100) -> Optional[Dict]:
        """寻找支撑阻力位"""
        try:
            if len(price_data) < lookback:
                return None

            recent_data = price_data.tail(lookback)
            highs = recent_data['high']
            lows = recent_data['low']
            current_price = price_data['close'].iloc[-1]

            # 寻找局部高点和低点
            try:
                high_indices = argrelextrema(highs.values, np.greater, order=5)[0]
                low_indices = argrelextrema(lows.values, np.less, order=5)[0]
            except:
                return None

            if len(high_indices) == 0 or len(low_indices) == 0:
                return None

            # 找到最近的支撑阻力位
            recent_highs = highs.iloc[high_indices]
            recent_lows = lows.iloc[low_indices]

            # 当前价格上方的最小阻力位
            resistance_levels = recent_highs[recent_highs > current_price]
            nearest_resistance = resistance_levels.min() if len(resistance_levels) > 0 else None

            # 当前价格下方的最大支撑位
            support_levels = recent_lows[recent_lows < current_price]
            nearest_support = support_levels.max() if len(support_levels) > 0 else None

            return {
                "nearest_support": nearest_support,
                "nearest_resistance": nearest_resistance,
                "all_supports": recent_lows.tolist(),
                "all_resistances": recent_highs.tolist()
            }

        except Exception as e:
            self.logger.error(f"支撑阻力位识别失败: {e}")
            return None

    def _count_consecutive_moves(self, price_data: pd.DataFrame) -> int:
        """计算连续涨跌天数"""
        try:
            if len(price_data) < 2:
                return 0

            daily_changes = price_data['close'].diff().dropna()
            consecutive_count = 0
            current_direction = np.sign(daily_changes.iloc[-1])

            if current_direction == 0:
                return 0

            # 从最新日期向前计算
            for i in range(len(daily_changes) - 1, -1, -1):
                if np.sign(daily_changes.iloc[i]) == current_direction:
                    consecutive_count += 1
                else:
                    break

            return consecutive_count * current_direction

        except Exception as e:
            self.logger.error(f"连续涨跌计算失败: {e}")
            return 0

    def _get_neutral_signal(self, signal_type: SignalType) -> TradingSignal:
        """获取中性信号"""
        return TradingSignal(
            signal_type=signal_type,
            direction="neutral" if signal_type != SignalType.VOLATILITY else "medium_risk",
            strength=SignalStrength.NEUTRAL,
            confidence=0.0,
            timestamp=datetime.now()
        )