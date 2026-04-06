"""
StockAI 2.0/3.0 - 回测模块
提供单标的回测引擎、组合回测引擎和报告生成功能
"""

from .engine import BacktestEngine, SignalGenerator, SimpleMAStrategy, TradeAction
from .report import BacktestReport, ReportConfig, generate_report
from .portfolio_engine import (
    PortfolioBacktest,
    PortfolioResult,
    PortfolioAllocation,
    PortfolioTrade,
    PortfolioSnapshot,
    RebalanceFrequency,
    run_portfolio_backtest
)

__all__ = [
    # 2.0 单标的回测
    'BacktestEngine',
    'SignalGenerator',
    'SimpleMAStrategy',
    'TradeAction',
    'BacktestReport',
    'ReportConfig',
    'generate_report',
    # 3.0 组合回测
    'PortfolioBacktest',
    'PortfolioResult',
    'PortfolioAllocation',
    'PortfolioTrade',
    'PortfolioSnapshot',
    'RebalanceFrequency',
    'run_portfolio_backtest'
]
