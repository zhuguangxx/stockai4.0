"""
StockAI 2.0 - 回测报告生成模块
生成Markdown格式的回测统计报告
"""

import json
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass
import os


@dataclass
class ReportConfig:
    """报告配置"""
    title: str = "回测报告"
    author: str = "StockAI 2.0"
    include_charts: bool = True
    include_trades: bool = True
    max_trades_in_report: int = 50
    language: str = "zh"


class BacktestReport:
    """回测报告生成器"""
    
    def __init__(self, config: ReportConfig = None):
        self.config = config or ReportConfig()
    
    def generate(self, result, output_path: str = None) -> str:
        """
        生成回测报告
        
        Args:
            result: BacktestResult对象
            output_path: 输出文件路径
            
        Returns:
            Markdown格式的报告内容
        """
        report_lines = []
        
        # 报告标题
        report_lines.extend(self._generate_header(result))
        
        # 执行摘要
        report_lines.extend(self._generate_summary(result))
        
        # 收益指标
        report_lines.extend(self._generate_return_metrics(result))
        
        # 风险指标
        report_lines.extend(self._generate_risk_metrics(result))
        
        # 交易统计
        report_lines.extend(self._generate_trade_statistics(result))
        
        # 基准对比
        report_lines.extend(self._generate_benchmark_comparison(result))
        
        # 月度收益表
        report_lines.extend(self._generate_monthly_returns(result))
        
        # 交易明细
        if self.config.include_trades:
            report_lines.extend(self._generate_trade_details(result))
        
        # 报告尾部
        report_lines.extend(self._generate_footer())
        
        report_content = '\n'.join(report_lines)
        
        # 保存到文件
        if output_path:
            os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else '.', exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(report_content)
        
        return report_content
    
    def _generate_header(self, result) -> List[str]:
        """生成报告头部"""
        lines = [
            f"# {self.config.title}",
            "",
            f"**策略名称**: {result.strategy_name}  ",
            f"**股票代码**: {result.code} ({result.stock_name})  ",
            f"**回测周期**: {result.start_date} ~ {result.end_date}  ",
            f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ",
            f"**报告版本**: StockAI 2.0**",
            "",
            "---",
            ""
        ]
        return lines
    
    def _generate_summary(self, result) -> List[str]:
        """生成执行摘要"""
        total_return_emoji = "🟢" if result.total_return_pct > 0 else "🔴" if result.total_return_pct < 0 else "⚪"
        alpha_emoji = "🟢" if result.alpha > 0 else "🔴" if result.alpha < 0 else "⚪"
        
        lines = [
            "## 📊 执行摘要",
            "",
            "| 指标 | 数值 | 评价 |",
            "|------|------|------|",
            f"| 初始资金 | ¥{result.initial_capital:,.0f} | - |",
            f"| 最终资产 | ¥{result.final_value:,.2f} | - |",
            f"| **总收益率** | **{total_return_emoji} {result.total_return_pct:+.2f}%** | {'跑赢基准' if result.alpha > 0 else '跑输基准'} |",
            f"| **年化收益率** | **{result.annualized_return:+.2f}%** | {'优秀' if result.annualized_return > 20 else '良好' if result.annualized_return > 10 else '一般' if result.annualized_return > 0 else '亏损'} |",
            f"| 基准收益 (沪深300) | {result.benchmark_return:+.2f}% | - |",
            f"| **超额收益 (Alpha)** | **{alpha_emoji} {result.alpha:+.2f}%** | {'正向' if result.alpha > 0 else '负向'} |",
            f"| 最大回撤 | {result.max_drawdown*100:.2f}% | {'可控' if result.max_drawdown < 0.15 else '较高' if result.max_drawdown < 0.25 else '高风险'} |",
            f"| 夏普比率 | {result.sharpe_ratio:.2f} | {'优秀' if result.sharpe_ratio > 2 else '良好' if result.sharpe_ratio > 1 else '一般'} |",
            f"| 交易次数 | {result.total_trades}次 | {'活跃' if result.total_trades > 20 else '适中' if result.total_trades > 5 else '低频'} |",
            f"| 胜率 | {result.win_rate:.1f}% | {'优秀' if result.win_rate > 60 else '良好' if result.win_rate > 50 else '需改进'} |",
            "",
            "---",
            ""
        ]
        return lines
    
    def _generate_return_metrics(self, result) -> List[str]:
        """生成收益指标"""
        lines = [
            "## 💰 收益指标",
            "",
            "### 绝对收益",
            "",
            "| 指标 | 数值 | 说明 |",
            "|------|------|------|",
            f"| 初始资金 | ¥{result.initial_capital:,.0f} | 回测起始资金 |",
            f"| 最终资产 | ¥{result.final_value:,.2f} | 回测结束资产 |",
            f"| 总盈亏额 | ¥{result.total_return:,.2f} | 绝对收益金额 |",
            f"| 总收益率 | {result.total_return_pct:+.2f}% | 整个回测周期收益率 |",
            f"| 年化收益率 | {result.annualized_return:+.2f}% | 按252个交易日年化 |",
            "",
            "### 相对收益",
            "",
            "| 指标 | 数值 | 说明 |",
            "|------|------|------|",
            f"| 基准收益 (沪深300) | {result.benchmark_return:+.2f}% | 同期沪深300收益 |",
            f"| 超额收益 (Alpha) | {result.alpha:+.2f}% | 策略超越基准的收益 |",
            f"| 相对强弱 | {result.total_return_pct - result.benchmark_return:+.2f}% | 策略相对基准的优势 |",
            "",
            "---",
            ""
        ]
        return lines
    
    def _generate_risk_metrics(self, result) -> List[str]:
        """生成风险指标"""
        # 风险等级评估
        if result.max_drawdown < 0.1:
            risk_level = "低风险 🟢"
        elif result.max_drawdown < 0.2:
            risk_level = "中等风险 🟡"
        elif result.max_drawdown < 0.3:
            risk_level = "较高风险 🟠"
        else:
            risk_level = "高风险 🔴"
        
        lines = [
            "## ⚠️ 风险指标",
            "",
            "### 风险评估",
            "",
            f"**风险等级**: {risk_level}",
            "",
            "| 指标 | 数值 | 说明 | 评价 |",
            "|------|------|------|------|",
            f"| 最大回撤 | {result.max_drawdown*100:.2f}% | 从历史峰值的最大亏损 | {'优秀' if result.max_drawdown < 0.1 else '可接受' if result.max_drawdown < 0.2 else '偏高'} |",
            f"| 回撤持续期 | {result.max_drawdown_duration}天 | 最大回撤持续交易日数 | - |",
            f"| 波动率 | {result.volatility*100:.2f}% | 日收益率年化标准差 | {'稳定' if result.volatility < 0.15 else '适中' if result.volatility < 0.25 else '波动大'} |",
            f"| 夏普比率 | {result.sharpe_ratio:.2f} | (年化收益-无风险利率)/波动率 | {'优秀' if result.sharpe_ratio > 2 else '良好' if result.sharpe_ratio > 1 else '一般'} |",
            f"| 索提诺比率 | {result.sortino_ratio:.2f} | (年化收益-无风险利率)/下行波动率 | {'优秀' if result.sortino_ratio > 2 else '良好' if result.sortino_ratio > 1 else '一般'} |",
            "",
            "### 风险调整后收益",
            "",
            "| 指标 | 数值 | 说明 |",
            "|------|------|------|",
            f"| 收益回撤比 | {abs(result.total_return_pct / (result.max_drawdown * 100)):.2f} | 总收益/最大回撤 |",
            f"| 卡玛比率 | {abs(result.annualized_return / (result.max_drawdown * 100)):.2f} | 年化收益/最大回撤 |",
            "",
            "---",
            ""
        ]
        return lines
    
    def _generate_trade_statistics(self, result) -> List[str]:
        """生成交易统计"""
        lines = [
            "## 📈 交易统计",
            "",
            "### 交易概览",
            "",
            "| 指标 | 数值 | 说明 |",
            "|------|------|------|",
            f"| 总交易次数 | {result.total_trades} | 买入+卖出次数 |",
            f"| 盈利交易 | {result.winning_trades} | 平仓盈利次数 |",
            f"| 亏损交易 | {result.losing_trades} | 平仓亏损次数 |",
            f"| 胜率 | {result.win_rate:.2f}% | 盈利交易/总交易 |",
            f"| 盈亏比 | {result.profit_loss_ratio:.2f} | 平均盈利/平均亏损 |",
            f"| 平均盈利 | ¥{result.avg_profit:,.2f} | 盈利交易的平均收益 |",
            f"| 平均亏损 | ¥{result.avg_loss:,.2f} | 亏损交易的平均损失 |",
            f"| 期望收益 | ¥{result.avg_profit * result.win_rate/100 - result.avg_loss * (100-result.win_rate)/100:,.2f} | 单笔交易期望 |",
            "",
            "### 交易评价",
            ""
        ]
        
        # 交易评价
        if result.win_rate >= 60 and result.profit_loss_ratio >= 1.5:
            evaluation = "🌟 优秀策略 - 高胜率且盈亏比合理"
        elif result.win_rate >= 50 and result.profit_loss_ratio >= 1:
            evaluation = "✅ 良好策略 - 胜率与盈亏比均衡"
        elif result.win_rate < 40 and result.profit_loss_ratio >= 2:
            evaluation = "⚠️ 趋势策略 - 低胜率但盈亏比高，需配合严格止损"
        elif result.win_rate >= 50 and result.profit_loss_ratio < 1:
            evaluation = "⚠️ 风险较高 - 胜率高但盈亏比不足，盈亏不对称"
        else:
            evaluation = "❌ 需改进 - 胜率与盈亏比均需优化"
        
        lines.extend([
            f"**综合评价**: {evaluation}",
            "",
            "---",
            ""
        ])
        
        return lines
    
    def _generate_benchmark_comparison(self, result) -> List[str]:
        """生成基准对比"""
        # 绘制简单的权益曲线对比（使用ASCII图表）
        lines = [
            "## 📊 基准对比分析",
            "",
            f"**对比基准**: 沪深300指数 (000300.SH)",
            "",
            "### 收益对比",
            "",
            "| 指标 | 策略 | 沪深300 | 差额 |",
            "|------|------|---------|------|",
            f"| 总收益率 | {result.total_return_pct:+.2f}% | {result.benchmark_return:+.2f}% | {result.total_return_pct - result.benchmark_return:+.2f}% |",
            f"| 最终资产 | ¥{result.final_value:,.2f} | ¥{result.initial_capital * (1 + result.benchmark_return/100):,.2f} | ¥{result.total_return - (result.initial_capital * (result.benchmark_return/100)):,.2f} |",
            ""
        ]
        
        # 权益曲线对比表（取关键点）
        if result.equity_curve:
            lines.extend([
                "### 权益曲线关键节点",
                "",
                "| 日期 | 策略净值 | 沪深300净值 | 相对强弱 |",
                "|------|----------|-------------|----------|"
            ])
            
            # 取起始、25%、50%、75%、结束五个点
            n = len(result.equity_curve)
            indices = [0, n//4, n//2, 3*n//4, n-1]
            
            for idx in indices:
                point = result.equity_curve[idx]
                strategy_nav = 1 + point['return_pct'] / 100
                benchmark_nav = 1 + point['benchmark_pct'] / 100
                relative = point['return_pct'] - point['benchmark_pct']
                
                lines.append(
                    f"| {point['date']} | {strategy_nav:.4f} | {benchmark_nav:.4f} | {relative:+.2f}% |"
                )
            
            lines.append("")
        
        # 结论
        if result.alpha > 5:
            conclusion = "🎯 策略显著跑赢基准，具备alpha能力"
        elif result.alpha > 0:
            conclusion = "✅ 策略小幅跑赢基准，有一定超额收益"
        elif result.alpha > -5:
            conclusion = "⚠️ 策略跑输基准，需优化策略逻辑"
        else:
            conclusion = "❌ 策略大幅跑输基准，建议重新审视策略"
        
        lines.extend([
            f"**对比结论**: {conclusion}",
            "",
            "---",
            ""
        ])
        
        return lines
    
    def _generate_monthly_returns(self, result) -> List[str]:
        """生成月度收益表"""
        if not result.daily_snapshots or len(result.daily_snapshots) < 20:
            return []
        
        # 计算月度收益
        monthly_data = {}
        for snapshot in result.daily_snapshots:
            month_key = snapshot.date[:7]  # YYYY-MM
            if month_key not in monthly_data:
                monthly_data[month_key] = {'start': snapshot.total_value, 'end': snapshot.total_value}
            monthly_data[month_key]['end'] = snapshot.total_value
        
        lines = [
            "## 📅 月度收益统计",
            "",
            "| 月份 | 起始净值 | 结束净值 | 月收益率 | 状态 |",
            "|------|----------|----------|----------|------|"
        ]
        
        for month, data in sorted(monthly_data.items()):
            monthly_return = (data['end'] / data['start'] - 1) * 100
            status = "🟢" if monthly_return > 0 else "🔴" if monthly_return < 0 else "⚪"
            
            lines.append(
                f"| {month} | ¥{data['start']:,.2f} | ¥{data['end']:,.2f} | {monthly_return:+.2f}% | {status} |"
            )
        
        lines.extend([
            "",
            "---",
            ""
        ])
        
        return lines
    
    def _generate_trade_details(self, result) -> List[str]:
        """生成交易明细"""
        if not result.trades:
            return ["## 📋 交易明细", "", "*本回测周期内无交易记录*", "", "---", ""]
        
        lines = [
            "## 📋 交易明细",
            "",
            f"*共 {len(result.trades)} 笔交易，显示前 {min(self.config.max_trades_in_report, len(result.trades))} 笔*",
            "",
            "| 序号 | 日期 | 动作 | 价格 | 数量 | 金额 | 手续费 | 说明 |",
            "|------|------|------|------|------|------|--------|------|"
        ]
        
        for i, trade in enumerate(result.trades[:self.config.max_trades_in_report], 1):
            action_emoji = "🟢" if trade.action.value == "买入" else "🔴"
            lines.append(
                f"| {i} | {trade.date} | {action_emoji} {trade.action.value} | "
                f"¥{trade.price:.2f} | {trade.shares} | ¥{trade.value:,.2f} | "
                f"¥{trade.commission:.2f} | {trade.reason} |"
            )
        
        if len(result.trades) > self.config.max_trades_in_report:
            lines.append(f"| ... | ... | ... | ... | ... | ... | ... | ... |")
            lines.append(f"| - | - | - | - | - | - | - | *还有 {len(result.trades) - self.config.max_trades_in_report} 笔交易未显示* |")
        
        lines.extend([
            "",
            "---",
            ""
        ])
        
        return lines
    
    def _generate_footer(self) -> List[str]:
        """生成报告尾部"""
        lines = [
            "## 📝 免责声明",
            "",
            "1. **回测结果仅供参考**，历史表现不代表未来收益",
            "2. 本报告基于历史数据模拟，未考虑流动性、市场冲击等因素",
            "3. 实际交易中可能存在滑点、延迟、无法成交等情况",
            "4. 投资有风险，入市需谨慎",
            "",
            "---",
            "",
            f"*报告由 {self.config.author} 生成*  ",
            f"*生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*",
            ""
        ]
        return lines
    
    def generate_json_report(self, result, output_path: str = None) -> str:
        """生成JSON格式的报告"""
        report_data = {
            'meta': {
                'title': self.config.title,
                'author': self.config.author,
                'generated_at': datetime.now().isoformat(),
                'version': '2.0'
            },
            'backtest_result': result.to_dict()
        }
        
        json_content = json.dumps(report_data, ensure_ascii=False, indent=2)
        
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(json_content)
        
        return json_content


def generate_report(result, output_dir: str = None, format: str = 'markdown') -> str:
    """
    便捷函数：生成回测报告
    
    Args:
        result: BacktestResult对象
        output_dir: 输出目录
        format: 报告格式 ('markdown' 或 'json')
        
    Returns:
        报告文件路径
    """
    config = ReportConfig(
        title=f"{result.strategy_name} - {result.code}回测报告"
    )
    reporter = BacktestReport(config)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    if output_dir is None:
        output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'reports')
    
    os.makedirs(output_dir, exist_ok=True)
    
    if format == 'json':
        output_path = os.path.join(output_dir, f"backtest_{result.code}_{timestamp}.json")
        reporter.generate_json_report(result, output_path)
    else:
        output_path = os.path.join(output_dir, f"backtest_{result.code}_{timestamp}.md")
        reporter.generate(result, output_path)
    
    return output_path


if __name__ == '__main__':
    # 测试报告生成
    from engine import BacktestEngine, SimpleMAStrategy
    
    engine = BacktestEngine()
    strategy = SimpleMAStrategy(short_window=5, long_window=20)
    
    result = engine.run(
        code='000001.SZ',
        strategy=strategy,
        start_date='2024-01-01',
        end_date='2024-12-31',
        initial_capital=1000000,
        commission_rate=0.0003,
        slippage=0.0001
    )
    
    # 生成报告
    report_path = generate_report(result)
    print(f"报告已生成: {report_path}")
