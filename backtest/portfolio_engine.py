"""
StockAI 3.0 - 多标的组合回测引擎
支持多股票组合的历史回测，含再平衡、组合风险指标计算
"""

import sqlite3
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed


class RebalanceFrequency(Enum):
    """再平衡频率"""
    MONTHLY = "monthly"      # 月度
    QUARTERLY = "quarterly"  # 季度
    NONE = "none"            # 不再平衡


@dataclass
class PortfolioAllocation:
    """组合配置"""
    code: str
    weight: float           # 目标权重 (0-1)
    shares: int = 0         # 持仓股数
    current_value: float = 0.0  # 当前市值
    
    def get_actual_weight(self, total_value: float) -> float:
        """实际权重"""
        return self.current_value / total_value if total_value > 0 else 0


@dataclass
class PortfolioTrade:
    """组合交易记录"""
    date: str
    code: str
    action: str  # BUY/SELL/REBALANCE
    shares: int
    price: float
    value: float
    reason: str = ""
    commission: float = 0.0
    
    def to_dict(self) -> Dict:
        return {
            'date': self.date,
            'code': self.code,
            'action': self.action,
            'shares': self.shares,
            'price': round(self.price, 3),
            'value': round(self.value, 2),
            'commission': round(self.commission, 2),
            'reason': self.reason
        }


@dataclass
class PortfolioSnapshot:
    """组合每日快照"""
    date: str
    total_value: float
    cash: float
    positions_value: float
    daily_pnl: float
    daily_return: float
    weights: Dict[str, float]  # 各股票实际权重
    trades: List[PortfolioTrade] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            'date': self.date,
            'total_value': round(self.total_value, 2),
            'cash': round(self.cash, 2),
            'positions_value': round(self.positions_value, 2),
            'daily_pnl': round(self.daily_pnl, 2),
            'daily_return': round(self.daily_return, 4),
            'weights': {k: round(v, 4) for k, v in self.weights.items()},
            'trades': [t.to_dict() for t in self.trades]
        }


@dataclass
class PortfolioResult:
    """组合回测结果"""
    portfolio: Dict[str, float]  # 原始配置
    start_date: str
    end_date: str
    initial_capital: float
    final_value: float
    
    # 收益指标
    total_return: float
    total_return_pct: float
    annualized_return: float
    
    # 组合风险指标
    volatility: float          # 组合波动率
    beta: float               # Beta系数
    alpha: float              # Alpha超额收益
    sharpe_ratio: float
    max_drawdown: float
    max_drawdown_duration: int
    
    # 高级风险指标
    tracking_error: float      # 跟踪误差
    information_ratio: float   # 信息比率
    treynor_ratio: float       # Treynor比率
    sortino_ratio: float       # Sortino比率
    
    # 再平衡统计
    rebalance_count: int
    rebalance_cost: float
    
    # 成分表现
    stock_returns: Dict[str, float]  # 各股票收益率
    stock_weights_history: List[Dict[str, float]]  # 权重历史
    
    # 详细数据
    trades: List[PortfolioTrade]
    snapshots: List[PortfolioSnapshot]
    equity_curve: List[Dict]
    
    def to_dict(self) -> Dict:
        return {
            'portfolio': self.portfolio,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'initial_capital': self.initial_capital,
            'final_value': round(self.final_value, 2),
            'total_return': round(self.total_return, 2),
            'total_return_pct': round(self.total_return_pct, 2),
            'annualized_return': round(self.annualized_return, 2),
            'volatility': round(self.volatility, 4),
            'beta': round(self.beta, 4),
            'alpha': round(self.alpha, 4),
            'sharpe_ratio': round(self.sharpe_ratio, 2),
            'max_drawdown': round(self.max_drawdown, 4),
            'max_drawdown_duration': self.max_drawdown_duration,
            'tracking_error': round(self.tracking_error, 4),
            'information_ratio': round(self.information_ratio, 2),
            'treynor_ratio': round(self.treynor_ratio, 2),
            'sortino_ratio': round(self.sortino_ratio, 2),
            'rebalance_count': self.rebalance_count,
            'rebalance_cost': round(self.rebalance_cost, 2),
            'stock_returns': {k: round(v, 2) for k, v in self.stock_returns.items()},
            'trades_count': len(self.trades),
            'equity_curve': self.equity_curve
        }
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


class PortfolioBacktest:
    """
    多标的组合回测引擎
    
    功能特性:
    1. 多股票组合配置与权重管理
    2. 按权重分配初始资金
    3. 独立回测每只股票
    4. 加权计算组合收益
    5. 组合风险指标 (Beta, Alpha, 信息比率等)
    6. 定期再平衡 (月度/季度)
    """
    
    def __init__(self, db_path: str = None, initial_capital: float = 1000000.0):
        """
        初始化组合回测引擎
        
        Args:
            db_path: 数据库路径
            initial_capital: 初始资金 (默认100万)
        """
        if db_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            db_path = os.path.join(base_dir, 'data', 'stockai.db')
        
        self.db_path = db_path
        self.initial_capital = initial_capital
        self.cash = initial_capital
        
        # 组合状态
        self.allocations: Dict[str, PortfolioAllocation] = {}
        self.trades: List[PortfolioTrade] = []
        self.snapshots: List[PortfolioSnapshot] = []
        
        # 数据缓存
        self._price_data: Dict[str, pd.DataFrame] = {}
        self._benchmark_data: pd.DataFrame = None
        
    def _load_stock_data(self, code: str, start_date: str, end_date: str) -> pd.DataFrame:
        """加载股票数据"""
        conn = sqlite3.connect(self.db_path)
        query = """
            SELECT date, open, high, low, close, volume, amount, change_pct
            FROM daily_prices
            WHERE code = ? AND date BETWEEN ? AND ?
            ORDER BY date ASC
        """
        df = pd.read_sql_query(query, conn, params=(code, start_date, end_date))
        conn.close()
        
        if df.empty:
            raise ValueError(f"未找到股票 {code} 在 {start_date} 到 {end_date} 的数据")
        
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)
        return df
    
    def _load_benchmark_data(self, start_date: str, end_date: str) -> pd.DataFrame:
        """加载沪深300基准数据"""
        conn = sqlite3.connect(self.db_path)
        query = """
            SELECT date, close, change_pct
            FROM daily_prices
            WHERE code = '000300.SH' AND date BETWEEN ? AND ?
            ORDER BY date ASC
        """
        df = pd.read_sql_query(query, conn, params=(start_date, end_date))
        conn.close()
        
        if df.empty:
            # 如果找不到沪深300，使用等权组合作为基准
            return None
        
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)
        df['return'] = df['change_pct'] / 100
        return df
    
    def _load_all_data(self, portfolio: Dict[str, float], start_date: str, end_date: str):
        """加载所有股票和基准数据"""
        # 加载各股票数据
        for code in portfolio.keys():
            self._price_data[code] = self._load_stock_data(code, start_date, end_date)
        
        # 加载基准数据
        self._benchmark_data = self._load_benchmark_data(start_date, end_date)
        
        # 对齐数据日期
        common_dates = None
        for code, df in self._price_data.items():
            if common_dates is None:
                common_dates = set(df.index)
            else:
                common_dates = common_dates.intersection(set(df.index))
        
        if not common_dates:
            raise ValueError("股票数据没有共同交易日")
        
        common_dates = sorted(list(common_dates))
        
        # 过滤数据到共同日期
        for code in self._price_data:
            self._price_data[code] = self._price_data[code].loc[common_dates]
    
    def _calculate_commission(self, value: float, commission_rate: float = 0.0003) -> float:
        """计算手续费"""
        return max(value * commission_rate, 5.0)
    
    def _should_rebalance(self, current_date: datetime, last_rebalance: datetime, 
                          frequency: RebalanceFrequency) -> bool:
        """判断是否需要再平衡"""
        if frequency == RebalanceFrequency.NONE:
            return False
        
        if last_rebalance is None:
            return True
        
        months_diff = (current_date.year - last_rebalance.year) * 12 + \
                      (current_date.month - last_rebalance.month)
        
        if frequency == RebalanceFrequency.MONTHLY:
            return months_diff >= 1
        elif frequency == RebalanceFrequency.QUARTERLY:
            return months_diff >= 3
        
        return False
    
    def _rebalance_portfolio(self, date: datetime, prices: Dict[str, float],
                            commission_rate: float) -> List[PortfolioTrade]:
        """
        执行组合再平衡
        
        策略:
        1. 计算当前总市值
        2. 根据目标权重计算各股票目标市值
        3. 计算需要买卖的股数
        4. 执行交易
        """
        trades = []
        total_value = self.cash + sum(
            alloc.shares * prices[alloc.code] 
            for alloc in self.allocations.values()
        )
        
        for code, alloc in self.allocations.items():
            price = prices[code]
            target_value = total_value * alloc.weight
            target_shares = int(target_value / price / 100) * 100
            
            diff_shares = target_shares - alloc.shares
            
            if diff_shares > 0:
                # 需要买入
                value = diff_shares * price
                commission = self._calculate_commission(value, commission_rate)
                
                if value + commission <= self.cash:
                    self.cash -= (value + commission)
                    alloc.shares += diff_shares
                    alloc.current_value = alloc.shares * price
                    
                    trades.append(PortfolioTrade(
                        date=date.strftime('%Y-%m-%d'),
                        code=code,
                        action='REBALANCE_BUY',
                        shares=diff_shares,
                        price=price,
                        value=value,
                        commission=commission,
                        reason='再平衡'
                    ))
            
            elif diff_shares < 0:
                # 需要卖出
                sell_shares = abs(diff_shares)
                value = sell_shares * price
                commission = self._calculate_commission(value, commission_rate)
                
                self.cash += (value - commission)
                alloc.shares -= sell_shares
                alloc.current_value = alloc.shares * price
                
                trades.append(PortfolioTrade(
                    date=date.strftime('%Y-%m-%d'),
                    code=code,
                    action='REBALANCE_SELL',
                    shares=sell_shares,
                    price=price,
                    value=value,
                    commission=commission,
                    reason='再平衡'
                ))
        
        return trades
    
    def _initialize_portfolio(self, portfolio: Dict[str, float], 
                             first_prices: Dict[str, float],
                             commission_rate: float) -> List[PortfolioTrade]:
        """初始化组合持仓"""
        trades = []
        
        for code, weight in portfolio.items():
            allocation = PortfolioAllocation(code=code, weight=weight)
            price = first_prices[code]
            
            # 按权重分配资金
            target_value = self.initial_capital * weight
            shares = int(target_value / price / 100) * 100
            value = shares * price
            commission = self._calculate_commission(value, commission_rate)
            
            # 确保不超过可用资金
            while value + commission > self.cash and shares > 0:
                shares -= 100
                value = shares * price
                commission = self._calculate_commission(value, commission_rate)
            
            if shares > 0:
                self.cash -= (value + commission)
                allocation.shares = shares
                allocation.current_value = value
                self.allocations[code] = allocation
                
                trades.append(PortfolioTrade(
                    date=self._price_data[code].index[0].strftime('%Y-%m-%d'),
                    code=code,
                    action='INIT_BUY',
                    shares=shares,
                    price=price,
                    value=value,
                    commission=commission,
                    reason='初始建仓'
                ))
        
        return trades
    
    def run(self, portfolio: Dict[str, float], start_date: str, end_date: str,
            rebalance: str = "monthly", commission_rate: float = 0.0003) -> PortfolioResult:
        """
        运行组合回测
        
        Args:
            portfolio: 组合配置 {股票代码: 权重}
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            rebalance: 再平衡频率 ("monthly"/"quarterly"/"none")
            commission_rate: 手续费率
            
        Returns:
            PortfolioResult: 回测结果
        """
        # 验证组合权重
        total_weight = sum(portfolio.values())
        if not 0.99 <= total_weight <= 1.01:
            raise ValueError(f"组合权重总和必须为1，当前为 {total_weight}")
        
        # 解析再平衡频率
        rebalance_freq = RebalanceFrequency(rebalance)
        
        # 加载数据
        self._load_all_data(portfolio, start_date, end_date)
        
        # 获取共同交易日
        dates = list(self._price_data[list(portfolio.keys())[0]].index)
        
        # 重置状态
        self.cash = self.initial_capital
        self.allocations = {}
        self.trades = []
        self.snapshots = []
        
        # 初始建仓
        first_prices = {code: df.iloc[0]['open'] for code, df in self._price_data.items()}
        init_trades = self._initialize_portfolio(portfolio, first_prices, commission_rate)
        self.trades.extend(init_trades)
        
        # 再平衡跟踪
        last_rebalance = dates[0]
        rebalance_count = 0
        rebalance_cost = 0.0
        
        # 回测主循环
        for i, date in enumerate(dates):
            # 获取当日价格
            prices = {code: df.loc[date, 'close'] for code, df in self._price_data.items()}
            
            # 更新持仓市值
            positions_value = 0
            current_weights = {}
            for code, alloc in self.allocations.items():
                alloc.current_value = alloc.shares * prices[code]
                positions_value += alloc.current_value
            
            total_value = self.cash + positions_value
            
            # 计算实际权重
            for code, alloc in self.allocations.items():
                current_weights[code] = alloc.current_value / total_value if total_value > 0 else 0
            
            # 检查是否需要再平衡
            daily_trades = []
            if self._should_rebalance(date, last_rebalance, rebalance_freq) and i > 0:
                rb_trades = self._rebalance_portfolio(date, prices, commission_rate)
                daily_trades.extend(rb_trades)
                self.trades.extend(rb_trades)
                last_rebalance = date
                rebalance_count += 1
                rebalance_cost += sum(t.commission for t in rb_trades)
            
            # 计算当日收益
            if i == 0:
                daily_pnl = 0
                daily_return = 0
            else:
                prev_value = self.snapshots[-1].total_value
                daily_pnl = total_value - prev_value
                daily_return = daily_pnl / prev_value if prev_value > 0 else 0
            
            # 记录快照
            snapshot = PortfolioSnapshot(
                date=date.strftime('%Y-%m-%d'),
                total_value=total_value,
                cash=self.cash,
                positions_value=positions_value,
                daily_pnl=daily_pnl,
                daily_return=daily_return,
                weights=current_weights.copy(),
                trades=daily_trades
            )
            self.snapshots.append(snapshot)
        
        # 计算回测结果
        return self._calculate_result(portfolio, start_date, end_date, 
                                     rebalance_count, rebalance_cost)
    
    def _calculate_result(self, portfolio: Dict[str, float], start_date: str, 
                         end_date: str, rebalance_count: int, 
                         rebalance_cost: float) -> PortfolioResult:
        """计算回测结果指标"""
        
        if not self.snapshots:
            raise ValueError("没有回测数据")
        
        # 基本收益指标
        initial_value = self.initial_capital
        final_value = self.snapshots[-1].total_value
        total_return = final_value - initial_value
        total_return_pct = (final_value / initial_value - 1) * 100
        
        # 年化收益率
        days = len(self.snapshots)
        years = days / 252
        if years > 0:
            annualized_return = ((final_value / initial_value) ** (1/years) - 1) * 100
        else:
            annualized_return = 0
        
        # 日收益率序列
        daily_returns = pd.Series([s.daily_return for s in self.snapshots[1:]])
        
        # 组合波动率 (年化)
        if len(daily_returns) > 1:
            volatility = daily_returns.std() * np.sqrt(252)
        else:
            volatility = 0
        
        # 各股票收益率
        stock_returns = {}
        for code, alloc in self.allocations.items():
            first_price = self._price_data[code].iloc[0]['open']
            last_price = self._price_data[code].iloc[-1]['close']
            stock_returns[code] = (last_price / first_price - 1) * 100
        
        # Beta和Alpha计算
        beta = 0
        alpha = 0
        tracking_error = 0
        information_ratio = 0
        treynor_ratio = 0
        risk_free_rate = 0.03  # 无风险利率3%
        
        if self._benchmark_data is not None and len(daily_returns) > 1:
            # 对齐基准数据
            bench_returns = self._benchmark_data['return'].reindex(
                [pd.to_datetime(s.date) for s in self.snapshots[1:]]
            ).fillna(0)
            
            # Beta计算
            covariance = daily_returns.cov(bench_returns)
            benchmark_variance = bench_returns.var()
            if benchmark_variance > 0:
                beta = covariance / benchmark_variance
            
            # Alpha计算 (年化)
            benchmark_total_return = (self._benchmark_data['close'].iloc[-1] / 
                                     self._benchmark_data['close'].iloc[0] - 1) * 100
            if years > 0:
                benchmark_annual = ((self._benchmark_data['close'].iloc[-1] / 
                                    self._benchmark_data['close'].iloc[0]) ** (1/years) - 1) * 100
                alpha = annualized_return - (risk_free_rate * 100 + beta * (benchmark_annual - risk_free_rate * 100))
            
            # 跟踪误差
            tracking_diff = daily_returns - bench_returns.values
            tracking_error = tracking_diff.std() * np.sqrt(252)
            
            # 信息比率
            if tracking_error > 0 and years > 0:
                excess_return = (annualized_return - benchmark_total_return / years) / 100
                information_ratio = excess_return / tracking_error
            
            # Treynor比率
            if beta > 0:
                treynor_ratio = (annualized_return / 100 - risk_free_rate) / beta
        
        # 夏普比率
        if volatility > 0:
            sharpe_ratio = (annualized_return / 100 - risk_free_rate) / volatility
        else:
            sharpe_ratio = 0
        
        # Sortino比率
        downside_returns = daily_returns[daily_returns < 0]
        if len(downside_returns) > 0:
            downside_std = downside_returns.std() * np.sqrt(252)
            sortino_ratio = (annualized_return / 100 - risk_free_rate) / downside_std if downside_std > 0 else 0
        else:
            sortino_ratio = 0
        
        # 最大回撤
        max_drawdown = 0
        max_drawdown_duration = 0
        peak = initial_value
        peak_idx = 0
        
        for i, snapshot in enumerate(self.snapshots):
            if snapshot.total_value > peak:
                peak = snapshot.total_value
                peak_idx = i
            
            drawdown = (peak - snapshot.total_value) / peak
            if drawdown > max_drawdown:
                max_drawdown = drawdown
                max_drawdown_duration = i - peak_idx
        
        # 权重历史
        stock_weights_history = [s.weights for s in self.snapshots]
        
        # 权益曲线
        equity_curve = [
            {
                'date': s.date,
                'value': round(s.total_value, 2),
                'return_pct': round((s.total_value / initial_value - 1) * 100, 2)
            }
            for s in self.snapshots
        ]
        
        return PortfolioResult(
            portfolio=portfolio,
            start_date=start_date,
            end_date=end_date,
            initial_capital=initial_value,
            final_value=final_value,
            total_return=total_return,
            total_return_pct=total_return_pct,
            annualized_return=annualized_return,
            volatility=volatility,
            beta=beta,
            alpha=alpha,
            sharpe_ratio=sharpe_ratio,
            max_drawdown=max_drawdown,
            max_drawdown_duration=max_drawdown_duration,
            tracking_error=tracking_error,
            information_ratio=information_ratio,
            treynor_ratio=treynor_ratio,
            sortino_ratio=sortino_ratio,
            rebalance_count=rebalance_count,
            rebalance_cost=rebalance_cost,
            stock_returns=stock_returns,
            stock_weights_history=stock_weights_history,
            trades=self.trades,
            snapshots=self.snapshots,
            equity_curve=equity_curve
        )
    
    def calculate_metrics(self, returns: pd.Series) -> Dict[str, float]:
        """
        计算风险指标
        
        Args:
            returns: 收益率序列 (日收益率)
            
        Returns:
            指标字典
        """
        if len(returns) < 2:
            return {
                'volatility': 0,
                'sharpe_ratio': 0,
                'sortino_ratio': 0,
                'max_drawdown': 0,
                'calmar_ratio': 0
            }
        
        # 年化波动率
        volatility = returns.std() * np.sqrt(252)
        
        # 年化收益率
        total_return = (1 + returns).prod() - 1
        years = len(returns) / 252
        annualized_return = (1 + total_return) ** (1/years) - 1 if years > 0 else 0
        
        # 夏普比率
        risk_free_rate = 0.03
        sharpe = (annualized_return - risk_free_rate) / volatility if volatility > 0 else 0
        
        # Sortino比率
        downside_returns = returns[returns < 0]
        downside_std = downside_returns.std() * np.sqrt(252) if len(downside_returns) > 0 else 0
        sortino = (annualized_return - risk_free_rate) / downside_std if downside_std > 0 else 0
        
        # 最大回撤
        cumulative = (1 + returns).cumprod()
        running_max = cumulative.expanding().max()
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = drawdown.min()
        
        # Calmar比率
        calmar = annualized_return / abs(max_drawdown) if max_drawdown < 0 else 0
        
        return {
            'volatility': round(volatility, 4),
            'annualized_return': round(annualized_return * 100, 2),
            'sharpe_ratio': round(sharpe, 2),
            'sortino_ratio': round(sortino, 2),
            'max_drawdown': round(max_drawdown, 4),
            'calmar_ratio': round(calmar, 2)
        }


# 便捷函数
def run_portfolio_backtest(portfolio: Dict[str, float], start_date: str, end_date: str,
                           db_path: str = None, initial_capital: float = 1000000,
                           rebalance: str = "monthly") -> PortfolioResult:
    """
    便捷函数：运行组合回测
    
    Args:
        portfolio: 组合配置 {股票代码: 权重}
        start_date: 开始日期
        end_date: 结束日期
        db_path: 数据库路径
        initial_capital: 初始资金
        rebalance: 再平衡频率
        
    Returns:
        PortfolioResult
    """
    engine = PortfolioBacktest(db_path=db_path, initial_capital=initial_capital)
    return engine.run(portfolio, start_date, end_date, rebalance=rebalance)


if __name__ == '__main__':
    # 测试组合回测
    portfolio = {
        "000001.SZ": 0.3,
        "000858.SZ": 0.4,
        "600519.SH": 0.3
    }
    
    engine = PortfolioBacktest(initial_capital=1000000)
    result = engine.run(
        portfolio=portfolio,
        start_date='2024-01-01',
        end_date='2024-12-31',
        rebalance='monthly'
    )
    
    print("=" * 50)
    print("组合回测结果")
    print("=" * 50)
    print(f"组合配置: {portfolio}")
    print(f"回测期间: {result.start_date} 至 {result.end_date}")
    print(f"初始资金: {result.initial_capital:,.0f}")
    print(f"最终市值: {result.final_value:,.2f}")
    print(f"总收益率: {result.total_return_pct:.2f}%")
    print(f"年化收益: {result.annualized_return:.2f}%")
    print(f"组合波动率: {result.volatility:.4f}")
    print(f"Beta系数: {result.beta:.4f}")
    print(f"Alpha超额: {result.alpha:.4f}")
    print(f"夏普比率: {result.sharpe_ratio:.2f}")
    print(f"信息比率: {result.information_ratio:.2f}")
    print(f"最大回撤: {result.max_drawdown*100:.2f}%")
    print(f"再平衡次数: {result.rebalance_count}")
    print(f"再平衡成本: {result.rebalance_cost:.2f}")
    print("=" * 50)
