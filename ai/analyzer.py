import pandas as pd
import numpy as np
from typing import Dict, List, Optional

class AIAnalyzer:
    """AI交易分析器"""
    
    def __init__(self):
        pass
    
    def analyze_trade_signal(self, df: pd.DataFrame, trade_type: str, reason: str = None) -> str:
        """分析交易信号并给出建议"""
        if df.empty or len(df) < 20:
            return "数据不足，无法进行分析"
        
        latest = df.iloc[-1]
        previous = df.iloc[-2] if len(df) > 1 else None
        
        analysis = []
        
        # 基本趋势分析
        trend_analysis = self._analyze_trend(df)
        if trend_analysis:
            analysis.append(trend_analysis)
        
        # 技术指标分析
        indicator_analysis = self._analyze_indicators(latest, previous)
        if indicator_analysis:
            analysis.append(indicator_analysis)
        
        # K线形态分析
        pattern_analysis = self._analyze_candlestick_pattern(latest, previous)
        if pattern_analysis:
            analysis.append(pattern_analysis)
        
        # 交易量分析
        volume_analysis = self._analyze_volume(df)
        if volume_analysis:
            analysis.append(volume_analysis)
        
        # 根据交易类型给出具体建议
        trade_suggestion = self._get_trade_suggestion(trade_type, df, latest)
        if trade_suggestion:
            analysis.append(trade_suggestion)
        
        # 用户理由分析
        if reason:
            reason_analysis = self._analyze_user_reason(reason, df)
            if reason_analysis:
                analysis.append(reason_analysis)
        
        return "\n".join(analysis)
    
    def _analyze_trend(self, df: pd.DataFrame) -> str:
        """分析趋势"""
        if len(df) < 10:
            return ""
        
        # 均线分析
        if 'MA5' in df.columns and 'MA10' in df.columns and 'MA20' in df.columns:
            latest = df.iloc[-1]
            ma5 = latest['MA5']
            ma10 = latest['MA10']
            ma20 = latest['MA20']
            
            if ma5 > ma10 > ma20 and latest['close'] > ma5:
                return "✅ 多头排列：短期均线位于均线上方，处于强势上升趋势"
            elif ma5 < ma10 < ma20 and latest['close'] < ma5:
                return "❌ 空头排列：短期均线位于均线下方，处于弱势下跌趋势"
            else:
                return "⚠️ 震荡趋势：均线交织，方向不明"
        return ""
    
    def _analyze_indicators(self, latest: pd.Series, previous: Optional[pd.Series]) -> str:
        """分析技术指标"""
        indicators = []
        
        # RSI分析
        if 'RSI' in latest:
            rsi = latest['RSI']
            if rsi > 70:
                indicators.append(f"⚠️ RSI({rsi:.1f})处于超买区域，可能面临回调")
            elif rsi < 30:
                indicators.append(f"✅ RSI({rsi:.1f})处于超卖区域，可能反弹")
        
        # MACD分析
        if 'MACD' in latest and 'Signal' in latest:
            macd = latest['MACD']
            signal = latest['Signal']
            
            if previous is not None:
                prev_macd = previous['MACD']
                prev_signal = previous['Signal']
                
                if macd > signal and prev_macd <= prev_signal:
                    indicators.append("✅ MACD金叉：可能是买入信号")
                elif macd < signal and prev_macd >= prev_signal:
                    indicators.append("❌ MACD死叉：可能是卖出信号")
        
        # 布林带分析
        if 'Upper' in latest and 'Lower' in latest and 'MA20' in latest:
            if latest['close'] > latest['Upper']:
                indicators.append("⚠️ 价格突破布林带上轨，可能超买")
            elif latest['close'] < latest['Lower']:
                indicators.append("✅ 价格突破布林带下轨，可能超卖")
        
        return " ".join(indicators)
    
    def _analyze_candlestick_pattern(self, latest: pd.Series, previous: Optional[pd.Series]) -> str:
        """分析K线形态"""
        patterns = []
        
        if previous is None:
            return ""
        
        # 阳线/阴线判断
        latest_change = latest['close'] - latest['open']
        prev_change = previous['close'] - previous['open']
        
        if latest_change > 0:
            latest_type = "阳线"
        elif latest_change < 0:
            latest_type = "阴线"
        else:
            latest_type = "十字星"
        
        # 连续阳线/阴线
        if latest_change > 0 and prev_change > 0:
            patterns.append("连续阳线，多头强势")
        elif latest_change < 0 and prev_change < 0:
            patterns.append("连续阴线，空头强势")
        
        # 实体大小分析
        latest_body = abs(latest_change)
        prev_body = abs(prev_change)
        latest_range = latest['high'] - latest['low']
        
        if latest_body / latest_range > 0.7:
            patterns.append(f"大{latest_type}，趋势明确")
        elif latest_body / latest_range < 0.3:
            patterns.append("小实体，市场犹豫")
        
        return " ".join(patterns)
    
    def _analyze_volume(self, df: pd.DataFrame) -> str:
        """分析交易量"""
        if len(df) < 5:
            return ""
        
        latest_volume = df.iloc[-1]['volume']
        avg_volume = df['volume'].rolling(window=5).mean().iloc[-1]
        
        if latest_volume > avg_volume * 2:
            return "📈 成交量显著放大，市场关注度提高"
        elif latest_volume < avg_volume * 0.5:
            return "📉 成交量萎缩，市场参与度低"
        return ""
    
    def _get_trade_suggestion(self, trade_type: str, df: pd.DataFrame, latest: pd.Series) -> str:
        """根据交易类型给出建议"""
        suggestions = []
        
        if trade_type == '买入':
            # 买入建议
            if 'RSI' in latest and latest['RSI'] > 70:
                suggestions.append("⚠️ 当前RSI处于超买区域，建议谨慎买入")
            if 'MACD' in latest and 'Signal' in latest and latest['MACD'] < latest['Signal']:
                suggestions.append("⚠️ MACD处于死叉状态，建议等待更好买点")
            if 'MA5' in latest and 'MA20' in latest and latest['close'] < latest['MA20']:
                suggestions.append("⚠️ 价格位于20日均线下方，处于弱势")
            
            if not suggestions:
                suggestions.append("✅ 当前技术面支持买入操作")
                
        elif trade_type == '卖出':
            # 卖出建议
            if 'RSI' in latest and latest['RSI'] < 30:
                suggestions.append("⚠️ 当前RSI处于超卖区域，可能反弹")
            if 'MACD' in latest and 'Signal' in latest and latest['MACD'] > latest['Signal']:
                suggestions.append("⚠️ MACD处于金叉状态，可能继续上涨")
            if 'MA5' in latest and 'MA20' in latest and latest['close'] > latest['MA20']:
                suggestions.append("⚠️ 价格位于20日均线上方，处于强势")
            
            if not suggestions:
                suggestions.append("✅ 当前技术面支持卖出操作")
                
        elif trade_type == '观望':
            # 观望建议
            suggestions.append("⏳ 当前市场方向不明，观望是合理选择")
            
            if 'RSI' in latest and 40 <= latest['RSI'] <= 60:
                suggestions.append("RSI处于中性区域，等待明确信号")
        
        return " ".join(suggestions)
    
    def _analyze_user_reason(self, reason: str, df: pd.DataFrame) -> str:
        """分析用户交易理由"""
        analysis = []
        
        # 关键词分析
        bullish_keywords = ['突破', '金叉', '支撑', '放量', '上涨', '买入', '做多']
        bearish_keywords = ['破位', '死叉', '压力', '缩量', '下跌', '卖出', '做空']
        
        reason_lower = reason.lower()
        
        bullish_count = sum(1 for keyword in bullish_keywords if keyword in reason_lower)
        bearish_count = sum(1 for keyword in bearish_keywords if keyword in reason_lower)
        
        if bullish_count > bearish_count:
            analysis.append("用户理由偏向看多")
        elif bearish_count > bullish_count:
            analysis.append("用户理由偏向看空")
        else:
            analysis.append("用户理由较为中性")
        
        # 验证理由与技术面是否一致
        latest = df.iloc[-1]
        
        if '突破' in reason and 'MA20' in latest and latest['close'] > latest['MA20']:
            analysis.append("突破理由与技术面一致")
        elif '支撑' in reason and 'Lower' in latest and latest['close'] > latest['Lower']:
            analysis.append("支撑理由与技术面一致")
        elif '压力' in reason and 'Upper' in latest and latest['close'] < latest['Upper']:
            analysis.append("压力理由与技术面一致")
        
        return " ".join(analysis)
    
    def analyze_trading_performance(self, trades: List[Dict]) -> Dict:
        """分析交易表现"""
        if not trades:
            return {}
        
        total_trades = len(trades)
        winning_trades = sum(1 for trade in trades if trade.get('profit', 0) > 0)
        losing_trades = total_trades - winning_trades
        
        win_rate = winning_trades / total_trades * 100 if total_trades > 0 else 0
        
        profits = [trade.get('profit', 0) for trade in trades]
        total_profit = sum(profits)
        avg_profit = total_profit / total_trades if total_trades > 0 else 0
        
        max_profit = max(profits) if profits else 0
        max_loss = min(profits) if profits else 0
        
        # 计算最大回撤（简化版）
        equity_curve = []
        current_equity = 0
        max_equity = 0
        max_drawdown = 0
        
        for trade in trades:
            current_equity += trade.get('profit', 0)
            max_equity = max(max_equity, current_equity)
            if max_equity > 0:
                drawdown = (max_equity - current_equity) / max_equity * 100
                max_drawdown = max(max_drawdown, drawdown)
        
        return {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': win_rate,
            'total_profit': total_profit,
            'avg_profit': avg_profit,
            'max_profit': max_profit,
            'max_loss': max_loss,
            'max_drawdown': max_drawdown
        }
    
    def generate_summary(self, performance: Dict) -> str:
        """生成交易总结"""
        if not performance:
            return "暂无交易记录"
        
        summary = []
        summary.append(f"📊 交易总结：")
        summary.append(f"- 总交易次数：{performance['total_trades']}次")
        summary.append(f"- 盈利次数：{performance['winning_trades']}次")
        summary.append(f"- 亏损次数：{performance['losing_trades']}次")
        summary.append(f"- 胜率：{performance['win_rate']:.1f}%")
        summary.append(f"- 总盈亏：{performance['total_profit']:.2f}")
        summary.append(f"- 平均盈亏：{performance['avg_profit']:.2f}")
        summary.append(f"- 最大盈利：{performance['max_profit']:.2f}")
        summary.append(f"- 最大亏损：{performance['max_loss']:.2f}")
        summary.append(f"- 最大回撤：{performance['max_drawdown']:.1f}%")
        
        return "\n".join(summary)