#!/usr/bin/env python3
"""
指标详情服务 - 展示六大指标详细分析
调用 core/experts.py 生成专业报告
"""
from typing import Dict, Optional
from dataclasses import dataclass

# 导入核心模块
try:
    from core.experts import ExpertSystem
    from core.data_access import DataAccess
    MODULES_AVAILABLE = True
except ImportError:
    MODULES_AVAILABLE = False
    print("[IndicatorDetailService] 警告: 核心模块未找到")


@dataclass
class IndicatorDetailResult:
    """指标详情结果"""
    success: bool
    report: str
    indicator_data: Optional[Dict] = None
    error: Optional[str] = None


class IndicatorDetailService:
    """
    六大指标详情服务
    
    为用户提供每个技术指标的详细解读：
    - MACD: 趋势动能分析
    - KDJ: 超买超卖分析  
    - MA: 均线系统分析
    - BOLL: 布林带分析
    - RSI: 相对强弱分析
    - CCI: 顺势指标分析
    """
    
    def __init__(self):
        self.data_access = DataAccess() if MODULES_AVAILABLE else None
    
    def get_indicator_detail(
        self, 
        stock_code: str, 
        indicator_name: Optional[str] = None
    ) -> IndicatorDetailResult:
        """
        获取指标详情
        
        Args:
            stock_code: 股票代码（如 600519.SH）
            indicator_name: 指定指标名称（如 MACD），None则返回全部
            
        Returns:
            IndicatorDetailResult: 包含详细报告或错误信息
        """
        if not MODULES_AVAILABLE:
            return IndicatorDetailResult(
                success=False,
                report="",
                error="核心模块未加载"
            )
        
        try:
            # 1. 获取股票数据
            df = self.data_access.get_stock_data(stock_code, days=60)
            
            if df is None or df.empty:
                return IndicatorDetailResult(
                    success=False,
                    report="",
                    error=f"无法获取 {stock_code} 的数据"
                )
            
            # 2. 调用六大专家系统
            expert = ExpertSystem(df)
            results = expert.analyze_all()
            
            # 3. 生成报告
            if indicator_name and indicator_name.upper() in results:
                # 返回单个指标详情
                report = self._format_single_indicator(
                    stock_code, 
                    indicator_name.upper(), 
                    results[indicator_name.upper()]
                )
            else:
                # 返回全部指标详情
                report = self._format_all_indicators(stock_code, results)
            
            return IndicatorDetailResult(
                success=True,
                report=report,
                indicator_data=results
            )
            
        except Exception as e:
            return IndicatorDetailResult(
                success=False,
                report="",
                error=f"分析失败: {str(e)}"
            )
    
    def _format_single_indicator(
        self, 
        stock_code: str, 
        indicator: str, 
        result
    ) -> str:
        """格式化单个指标报告"""
        report = f"""📊 {stock_code} - {indicator}指标详情
━━━━━━━━━━━━━━━━━━━━━━━━━━━

{result}

━━━━━━━━━━━━━━━━━━━━━━━━━━━
💡 解读建议

该指标基于最近60个交易日的数据计算得出。
建议结合其他指标综合判断，单一指标可能存在局限性。

⚠️ 免责声明：本分析仅供参考，不构成投资建议。"""
        return report
    
    def _format_all_indicators(self, stock_code: str, results: Dict) -> str:
        """格式化全部指标报告"""
        report = f"📊 {stock_code} 六大技术指标详情\n"
        report += "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        # 技术指标概览
        report += "📈 指标概览\n"
        report += "-" * 30 + "\n"
        for indicator in ['MACD', 'KDJ', 'MA', 'BOLL', 'RSI', 'CCI']:
            if indicator in results:
                signal = getattr(results[indicator], 'signal', '分析完成')
                report += f"• {indicator}: {signal}\n"
        
        report += "\n"
        
        # 详细分析
        for indicator in ['MACD', 'KDJ', 'MA', 'BOLL', 'RSI', 'CCI']:
            if indicator in results:
                report += f"\n{results[indicator]}\n"
                report += "-" * 30 + "\n"
        
        # 综合建议
        report += "\n💡 综合分析\n"
        report += "-" * 30 + "\n"
        
        bullish_count = 0
        bearish_count = 0
        
        for indicator, result in results.items():
            result_str = str(result).lower()
            if '金叉' in result_str or '买入' in result_str or '看涨' in result_str:
                bullish_count += 1
            elif '死叉' in result_str or '卖出' in result_str or '看跌' in result_str:
                bearish_count += 1
        
        if bullish_count > bearish_count:
            report += f"多数指标({bullish_count}/6)显示偏多信号，建议关注。\n"
        elif bearish_count > bullish_count:
            report += f"多数指标({bearish_count}/6)显示偏空信号，建议谨慎。\n"
        else:
            report += "指标信号分化，建议观望或结合基本面分析。\n"
        
        report += "\n⚠️ 免责声明：本分析仅供参考，不构成投资建议。"
        
        return report
    
    def get_indicator_list(self) -> list:
        """获取支持的指标列表"""
        return ['MACD', 'KDJ', 'MA', 'BOLL', 'RSI', 'CCI']


# 便捷函数
def get_indicator_detail(stock_code: str, indicator: Optional[str] = None) -> str:
    """便捷函数：获取指标详情"""
    service = IndicatorDetailService()
    result = service.get_indicator_detail(stock_code, indicator)
    
    if result.success:
        return result.report
    else:
        return f"❌ 获取指标详情失败: {result.error}"
