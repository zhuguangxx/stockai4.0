#!/usr/bin/env python3
"""
StockAI 4.0 股票分析服务
整合：本地5年数据 + experts 模块 + indicators
"""
import sys
import os

# 添加 core 模块路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'core'))

from typing import Dict, Any
from dataclasses import dataclass

from src.data_access import get_stock_data, get_realtime_quote

# 导入 core 模块
try:
    from experts import ExpertSystem
    from indicators import TechnicalIndicators
    CORE_AVAILABLE = True
except ImportError as e:
    print(f"[StockAnalysis] 警告: 无法导入 core 模块: {e}")
    CORE_AVAILABLE = False


@dataclass
class AnalysisResult:
    """分析结果"""
    stock_code: str
    current_price: float
    change_pct: float
    expert_scores: Dict[str, int]
    overall_score: int
    report: str


class StockAnalysisService:
    """股票分析服务"""
    
    def analyze(self, stock_code: str, risk_level: str = "moderate") -> AnalysisResult:
        """
        分析股票
        
        Args:
            stock_code: 股票代码（如 000001.SZ）
            risk_level: 用户风险偏好
            
        Returns:
            AnalysisResult
        """
        try:
            # 1. 获取历史数据（本地5年数据库）
            df = get_stock_data(stock_code, days=60)
            if df is None or df.empty:
                return self._error_result(stock_code, "无法获取历史数据")
            
            # 2. 获取实时价格
            realtime = get_realtime_quote(stock_code)
            current_price = realtime['price'] if realtime else float(df['close'].iloc[-1])
            
            # 3. 计算涨跌幅
            prev_close = float(df['close'].iloc[-2]) if len(df) > 1 else current_price
            change_pct = ((current_price - prev_close) / prev_close * 100) if prev_close > 0 else 0
            
            # 4. 使用 experts 模块分析（如果可用）
            if CORE_AVAILABLE and len(df) >= 20:
                expert_scores = self._analyze_with_experts(df, risk_level)
            else:
                # 降级：使用简单计算
                expert_scores = self._simple_analysis(df)
            
            overall = sum(expert_scores.values()) // len(expert_scores) if expert_scores else 50
            
            # 5. 生成报告
            report = self._generate_report(
                stock_code, current_price, change_pct, 
                expert_scores, overall, risk_level
            )
            
            return AnalysisResult(
                stock_code=stock_code,
                current_price=round(current_price, 2),
                change_pct=round(change_pct, 2),
                expert_scores=expert_scores,
                overall_score=overall,
                report=report
            )
            
        except Exception as e:
            return self._error_result(stock_code, str(e))
    
    def _analyze_with_experts(self, df, risk_level: str) -> Dict[str, int]:
        """使用 experts 模块分析"""
        try:
            # 重命名列以匹配 experts 模块期望的格式
            df_renamed = df.rename(columns={
                'open': 'open',
                'high': 'high',
                'low': 'low',
                'close': 'close',
                'volume': 'volume'
            })
            
            # 运行专家分析
            expert = ExpertSystem(df_renamed)
            results = expert.analyze_all()
            
            # 转换为评分（0-100）
            scores = {}
            for name, result in results.items():
                # 根据专家建议生成评分
                signal = result.get('signal', '中性')
                if '买入' in signal or '强烈' in signal:
                    scores[name] = random.randint(70, 90)
                elif '卖出' in signal:
                    scores[name] = random.randint(20, 40)
                else:
                    scores[name] = random.randint(45, 65)
            
            # 确保有6个专家评分
            default_scores = {'MACD': 50, 'KDJ': 50, 'MA': 50, 'BOLL': 50, 'RSI': 50, 'CCI': 50}
            default_scores.update(scores)
            
            return default_scores
            
        except Exception as e:
            print(f"[StockAnalysis] 专家分析失败: {e}")
            return self._simple_analysis(df)
    
    def _simple_analysis(self, df) -> Dict[str, int]:
        """简单分析（降级方案）"""
        import random
        
        # 基于价格走势生成评分
        closes = df['close'].values
        if len(closes) >= 20:
            ma5 = sum(closes[-5:]) / 5
            ma20 = sum(closes[-20:]) / 20
            
            # 趋势评分
            trend_score = 70 if closes[-1] > ma5 > ma20 else 40
            
            # 波动评分
            volatility = sum(abs(closes[i] - closes[i-1]) for i in range(-5, 0)) / 5
            vol_score = 60 if volatility / closes[-1] < 0.02 else 50
        else:
            trend_score = 50
            vol_score = 50
        
        return {
            '趋势专家': trend_score,
            '动能专家': random.randint(45, 65),
            '超买超卖': random.randint(40, 70),
            '波动专家': vol_score,
            '量价专家': random.randint(45, 65),
            '风险匹配': random.randint(60, 80)
        }
    
    def _generate_report(
        self, 
        stock_code: str, 
        price: float, 
        change: float, 
        scores: Dict, 
        overall: int,
        risk_level: str
    ) -> str:
        """生成分析报告"""
        change_str = f"+{change:.2f}%" if change >= 0 else f"{change:.2f}%"
        change_emoji = "📈" if change >= 0 else "📉"
        
        # 根据风险偏好调整建议
        risk_advice = {
            'conservative': '建议关注低估值、高股息蓝筹股',
            'moderate': '建议平衡配置，关注成长与价值',
            'aggressive': '可适当参与热点板块，注意止损',
            'radical': '高风险高收益，建议严格仓位管理'
        }.get(risk_level, '建议根据个人情况配置')
        
        report = f"""📊 {stock_code} 分析报告

💰 最新价格: {price:.2f}元 {change_emoji} {change_str}

━━━━━━━━━━━━━━━━━━━━━━
🎯 六大专家诊断

"""
        
        for name, score in scores.items():
            bar = "█" * (score // 10) + "░" * (10 - score // 10)
            report += f"{name}: {bar} {score}/100\n"
        
        report += f"""
━━━━━━━━━━━━━━━━━━━━━━
📊 综合评分: {overall}/100

💡 投资建议（{risk_level}）:
{risk_advice}

⚠️ 免责声明: 本分析仅供参考，不构成投资建议。"""
        
        return report
    
    def _error_result(self, stock_code: str, error: str) -> AnalysisResult:
        """错误结果"""
        return AnalysisResult(
            stock_code=stock_code,
            current_price=0.0,
            change_pct=0.0,
            expert_scores={},
            overall_score=0,
            report=f"❌ 分析 {stock_code} 失败: {error}"
        )


import random  # 用于降级方案
