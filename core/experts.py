#!/usr/bin/env python3
"""
StockAI 真实计算版 - 六大专家系统
每个专家独立分析，生成单独报告
"""

from indicators import TechnicalIndicators

class ExpertSystem:
    """六大专家分析系统"""
    
    def __init__(self, df):
        """
        初始化
        df: DataFrame with open/high/low/close/volume
        """
        self.df = df
        self.calc = TechnicalIndicators()
        self.results = {}
    
    def analyze_all(self):
        """运行所有专家分析"""
        self.results['MACD'] = self.macd_expert()
        self.results['KDJ'] = self.kdj_expert()
        self.results['MA'] = self.ma_expert()
        self.results['BOLL'] = self.boll_expert()
        self.results['RSI'] = self.rsi_expert()
        self.results['CCI'] = self.cci_expert()
        return self.results
    
    def macd_expert(self):
        """MACD专家 - 趋势动能分析"""
        result = self.calc.macd(self.df)
        
        analysis = f"""
📈 MACD专家报告
━━━━━━━━━━━━━━━━
当前状态: {result['signal']}

技术指标:
• DIF: {result['DIF']}
• DEA: {result['DEA']}
• MACD柱: {result['MACD']}

专业解读:
"""
        if '金叉' in result['signal']:
            analysis += "DIF线上穿DEA线形成金叉，短期上涨动能增强，建议关注。"
        elif '死叉' in result['signal']:
            analysis += "DIF线下穿DEA线形成死叉，短期回调风险加大，建议谨慎。"
        elif '多头' in result['signal']:
            analysis += "DIF线在DEA线上方运行，多头趋势延续，动能偏强。"
        else:
            analysis += "DIF线在DEA线下方运行，空头趋势，动能偏弱。"
        
        analysis += f"\n\n操作建议: {'买入/持有' if result['MACD'] > 0 else '观望/减仓'}"
        
        return {
            'data': result,
            'analysis': analysis,
            'score': 1 if result['MACD'] > 0 else -1
        }
    
    def kdj_expert(self):
        """KDJ专家 - 超买超卖分析"""
        result = self.calc.kdj(self.df)
        
        analysis = f"""
📊 KDJ专家报告
━━━━━━━━━━━━━━━━
当前状态: {result['signal']}

技术指标:
• K值: {result['K']}
• D值: {result['D']}
• J值: {result['J']}

专业解读:
"""
        if '超买' in result['signal']:
            analysis += f"J值达到{result['J']}，进入超买区域，短期可能回调，不建议追高。"
        elif '超卖' in result['signal']:
            analysis += f"J值跌至{result['J']}，进入超卖区域，可能存在反弹机会，可关注。"
        elif '金叉' in result['signal']:
            analysis += "K线上穿D线形成金叉，短期买入信号出现。"
        else:
            analysis += "KDJ指标中性，无明显买卖信号，建议观望。"
        
        analysis += f"\n\n操作建议: {'减仓' if '超买' in result['signal'] else '关注' if '超卖' in result['signal'] else '观望'}"
        
        score = -1 if '超买' in result['signal'] else 1 if '超卖' in result['signal'] else 0
        
        return {
            'data': result,
            'analysis': analysis,
            'score': score
        }
    
    def ma_expert(self):
        """均线专家 - 趋势方向分析"""
        result = self.calc.ma(self.df)
        
        analysis = f"""
📉 均线专家报告
━━━━━━━━━━━━━━━━
当前状态: {result['signal']}

技术指标:
• 当前价: ¥{result['current']}
• MA5: ¥{result['MA5']}
• MA10: ¥{result['MA10']}
• MA20: ¥{result['MA20']}
• MA60: ¥{result['MA60']}

专业解读:
"""
        if '多头' in result['signal']:
            analysis += "股价站上所有均线，形成多头排列，中长期趋势向好。"
        elif '空头' in result['signal']:
            analysis += "股价跌破所有均线，形成空头排列，中长期趋势偏弱。"
        elif '站上' in result['signal']:
            analysis += "股价站上短期均线，短期趋势转强，可积极关注。"
        else:
            analysis += "股价跌破短期均线，短期趋势转弱，建议谨慎。"
        
        score = 1 if '多头' in result['signal'] or '站上' in result['signal'] else -1
        
        return {
            'data': result,
            'analysis': analysis,
            'score': score
        }
    
    def boll_expert(self):
        """布林带专家 - 波动区间分析"""
        result = self.calc.boll(self.df)
        
        analysis = f"""
🎯 布林带专家报告
━━━━━━━━━━━━━━━━
当前状态: {result['signal']}

技术指标:
• 上轨: ¥{result['upper']}
• 中轨: ¥{result['mid']}
• 下轨: ¥{result['lower']}
• 带宽: {result['bandwidth']}%

专业解读:
"""
        if '上轨' in result['signal']:
            analysis += "股价触及布林带上轨，处于高位，注意回调风险。"
        elif '下轨' in result['signal']:
            analysis += "股价触及布林带下轨，处于低位，可能存在反弹机会。"
        elif '上方' in result['signal']:
            analysis += "股价在中轨上方运行，强势特征明显。"
        else:
            analysis += "股价在中轨下方运行，弱势特征明显。"
        
        analysis += f"\n带宽{result['bandwidth']}%，{'波动较大' if result['bandwidth'] > 10 else '波动较小'}。"
        
        score = -1 if '上轨' in result['signal'] else 1 if '下轨' in result['signal'] else 0
        
        return {
            'data': result,
            'analysis': analysis,
            'score': score
        }
    
    def rsi_expert(self):
        """RSI专家 - 强弱分析"""
        result = self.calc.rsi(self.df)
        
        analysis = f"""
💪 RSI专家报告
━━━━━━━━━━━━━━━━
当前状态: {result['signal']}

技术指标:
• RSI(6): {result['RSI6']}
• RSI(12): {result['RSI12']}
• RSI(24): {result['RSI24']}

专业解读:
"""
        if '超买' in result['signal']:
            analysis += f"RSI6达到{result['RSI6']}，显示市场过热，短期可能调整。"
        elif '超卖' in result['signal']:
            analysis += f"RSI6跌至{result['RSI6']}，显示市场过冷，可能存在反弹。"
        else:
            analysis += f"RSI6为{result['RSI6']}，处于中性区域，无明显信号。"
        
        score = -1 if '超买' in result['signal'] else 1 if '超卖' in result['signal'] else 0
        
        return {
            'data': result,
            'analysis': analysis,
            'score': score
        }
    
    def cci_expert(self):
        """CCI专家 - 顺势分析"""
        result = self.calc.cci(self.df)
        
        analysis = f"""
🌊 CCI专家报告
━━━━━━━━━━━━━━━━
当前状态: {result['signal']}

技术指标:
• CCI(14): {result['CCI']}

专业解读:
"""
        if result['CCI'] > 100:
            analysis += f"CCI为{result['CCI']}，进入强势区域，多头力量占优。"
        elif result['CCI'] < -100:
            analysis += f"CCI为{result['CCI']}，进入弱势区域，空头力量占优。"
        else:
            analysis += f"CCI为{result['CCI']}，处于震荡区域，方向不明。"
        
        score = 1 if result['CCI'] > 100 else -1 if result['CCI'] < -100 else 0
        
        return {
            'data': result,
            'analysis': analysis,
            'score': score
        }
    
    def generate_summary(self):
        """生成综合报告"""
        if not self.results:
            self.analyze_all()
        
        total_score = sum(r['score'] for r in self.results.values())
        
        if total_score >= 3:
            overall = "🟢 强烈看多"
            suggestion = "多数指标显示积极信号，可考虑逢低布局。"
        elif total_score >= 1:
            overall = "🟡 谨慎看多"
            suggestion = "部分指标向好，但存在分歧，建议小仓位试探。"
        elif total_score <= -3:
            overall = "🔴 强烈看空"
            suggestion = "多数指标显示风险，建议减仓观望。"
        elif total_score <= -1:
            overall = "🟠 谨慎看空"
            suggestion = "部分指标走弱，建议控制仓位，等待企稳。"
        else:
            overall = "⚪ 中性观望"
            suggestion = "指标分化严重，方向不明，建议观望。"
        
        return {
            'total_score': total_score,
            'overall': overall,
            'suggestion': suggestion
        }

if __name__ == "__main__":
    from data_fetcher import fetch_history
    
    df = fetch_history("600519", days=100)
    if df is not None:
        expert = ExpertSystem(df)
        results = expert.analyze_all()
        
        # 打印单个专家报告
        print(results['MACD']['analysis'])
        print("\n" + "="*50 + "\n")
        
        # 打印综合评分
        summary = expert.generate_summary()
        print(f"综合评分: {summary['total_score']}")
        print(f"总体判断: {summary['overall']}")
        print(f"操作建议: {summary['suggestion']}")
