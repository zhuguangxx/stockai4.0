"""
StockAI 2.0 - 单标的回测引擎
支持从stockai.db读取日线数据进行历史回测
"""

import sqlite3
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Callable, Tuple
from dataclasses import dataclass, field
from enum import Enum
import json
import os


class TradeAction(Enum):
    """交易动作"""
    BUY = "买入"
    SELL = "卖出"
    HOLD = "持有"


@dataclass
class Trade:
    """交易记录"""
    date: str
    action: TradeAction
    price: float
    shares: int
    value: float
    reason: str = ""
    commission: float = 0.0
    
    def to_dict(self) -> Dict:
        return {
            'date': self.date,
            'action': self.action.value,
            'price': round(self.price, 3),
            'shares': self.shares,
            'value': round(self.value, 2),
            'reason': self.reason,
            'commission': round(self.commission, 2)
        }


@dataclass
class Position:
    """持仓记录"""
    code: str
    shares: int = 0
    avg_cost: float = 0.0
    current_price: float = 0.0
    
    @property
    def market_value(self) -> float:
        return self.shares * self.current_price
    
    @property
    def unrealized_pnl(self) -> float:
        if self.shares > 0:
            return self.shares * (self.current_price - self.avg_cost)
        return 0.0
    
    @property
    def unrealized_pnl_pct(self) -> float:
        if self.shares > 0 and self.avg_cost > 0:
            return (self.current_price - self.avg_cost) / self.avg_cost * 100
        return 0.0


@dataclass
class DailySnapshot:
    """每日账户快照"""
    date: str
    cash: float
    positions_value: float
    total_value: float
    daily_pnl: float
    daily_return: float
    benchmark_value: float
    trades: List[Trade] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            'date': self.date,
            'cash': round(self.cash, 2),
            'positions_value': round(self.positions_value, 2),
            'total_value': round(self.total_value, 2),
            'daily_pnl': round(self.daily_pnl, 2),
            'daily_return': round(self.daily_return, 4),
            'benchmark_value': round(self.benchmark_value, 2),
            'trades': [t.to_dict() for t in self.trades]
        }


@dataclass
class BacktestResult:
    """回测结果"""
    strategy_name: str
    code: str
    stock_name: str
    start_date: str
    end_date: str
    
    # 收益指标
    initial_capital: float
    final_value: float
    total_return: float
    total_return_pct: float
    annualized_return: float
    
    # 风险指标
    volatility: float
    sharpe_ratio: float
    sortino_ratio: float
    max_drawdown: float
    max_drawdown_duration: int
    
    # 交易统计
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    avg_profit: float
    avg_loss: float
    profit_loss_ratio: float
    
    # 与基准对比
    benchmark_return: float
    alpha: float
    
    # 详细数据
    trades: List[Trade]
    daily_snapshots: List[DailySnapshot]
    equity_curve: List[Dict]
    
    def to_dict(self) -> Dict:
        """转换为字典格式"""
        return {
            'strategy_name': self.strategy_name,
            'code': self.code,
            'stock_name': self.stock_name,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'initial_capital': self.initial_capital,
            'final_value': round(self.final_value, 2),
            'total_return': round(self.total_return, 2),
            'total_return_pct': round(self.total_return_pct, 2),
            'annualized_return': round(self.annualized_return, 2),
            'volatility': round(self.volatility, 4),
            'sharpe_ratio': round(self.sharpe_ratio, 2),
            'sortino_ratio': round(self.sortino_ratio, 2),
            'max_drawdown': round(self.max_drawdown, 4),
            'max_drawdown_duration': self.max_drawdown_duration,
            'total_trades': self.total_trades,
            'winning_trades': self.winning_trades,
            'losing_trades': self.losing_trades,
            'win_rate': round(self.win_rate, 2),
            'avg_profit': round(self.avg_profit, 2),
            'avg_loss': round(self.avg_loss, 2),
            'profit_loss_ratio': round(self.profit_loss_ratio, 2),
            'benchmark_return': round(self.benchmark_return, 2),
            'alpha': round(self.alpha, 2),
            'trades': [t.to_dict() for t in self.trades],
            'equity_curve': self.equity_curve
        }
    
    def to_json(self) -> str:
        """转换为JSON字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


class SignalGenerator:
    """
    信号生成器基类
    子类需实现generate_signal方法
    """
    
    def generate_signal(self, data, current_idx: int) -> Tuple[TradeAction, str]:
        """
        生成交易信号
        
        Args:
            data: 历史数据DataFrame
            current_idx: 当前索引
            
        Returns:
            (交易动作, 信号原因)
        """
        raise NotImplementedError("子类必须实现generate_signal方法")


class SimpleMAStrategy(SignalGenerator):
    """简单均线策略示例"""
    
    def __init__(self, short_window: int = 5, long_window: int = 20):
        self.short_window = short_window
        self.long_window = long_window
    
    def generate_signal(self, data, current_idx: int) -> Tuple[TradeAction, str]:
        if current_idx < self.long_window:
            return TradeAction.HOLD, "数据不足"
        
        # 计算均线
        short_ma = data['close'].iloc[current_idx-self.short_window:current_idx].mean()
        long_ma = data['close'].iloc[current_idx-self.long_window:current_idx].mean()
        
        # 金叉买入，死叉卖出
        prev_short_ma = data['close'].iloc[current_idx-self.short_window-1:current_idx-1].mean()
        prev_long_ma = data['close'].iloc[current_idx-self.long_window-1:current_idx-1].mean()
        
        if prev_short_ma <= prev_long_ma and short_ma > long_ma:
            return TradeAction.BUY, f"金叉: MA{self.short_window}上穿MA{self.long_window}"
        elif prev_short_ma >= prev_long_ma and short_ma < long_ma:
            return TradeAction.SELL, f"死叉: MA{self.short_window}下穿MA{self.long_window}"
        
        return TradeAction.HOLD, "无信号"


class BacktestEngine:
    """回测引擎"""
    
    def __init__(self, db_path: str = None):
        """
        初始化回测引擎
        
        Args:
            db_path: 数据库路径，默认使用项目标准路径
        """
        if db_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            db_path = '/data/stockai/db/stock.db'
        
        self.db_path = db_path
        self.position = None
        self.cash = 0.0
        self.trades = []
        self.daily_snapshots = []
        self.initial_capital = 0.0
        
    def _load_stock_data(self, code: str, start_date: str, end_date: str) -> List[Dict]:
        """从数据库加载股票数据"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT code, date, open, high, low, close, volume, amount
            FROM kline
            WHERE code = ? AND date BETWEEN ? AND ?
            ORDER BY date ASC
        """, (code, start_date, end_date))
        
        columns = ['code', 'date', 'open', 'high', 'low', 'close', 'volume', 'amount']
        data = [dict(zip(columns, row)) for row in cursor.fetchall()]
        conn.close()
        
        return data
    
    def _load_benchmark_data(self, start_date: str, end_date: str) -> Dict[str, float]:
        """加载沪深300基准数据（使用000300.SH）"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 尝试获取沪深300数据
        cursor.execute("""
            SELECT date, close
            FROM kline
            WHERE code = '000300.SH' AND date BETWEEN ? AND ?
            ORDER BY date ASC
        """, (start_date, end_date))
        
        data = cursor.fetchall()
        conn.close()
        
        if data:
            base_price = data[0][1]
            return {row[0]: row[1] / base_price for row in data}
        
        # 如果没有沪深300数据，返回空字典
        return {}
    
    def _get_stock_name(self, code: str) -> str:
        """获取股票名称"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM stocks WHERE code = ?", (code,))
            result = cursor.fetchone()
            conn.close()
            return result[0] if result else code
        except sqlite3.OperationalError:
            # stocks表不存在，返回代码作为名称
            return code
    
    def _calculate_commission(self, value: float, commission_rate: float) -> float:
        """计算手续费"""
        return max(value * commission_rate, 5.0)  # 最低5元
    
    def _execute_trade(self, date: str, action: TradeAction, price: float, 
                       position: Position, cash: float, 
                       commission_rate: float, slippage: float) -> Tuple[Optional[Trade], float]:
        """
        执行交易
        
        Args:
            date: 交易日期
            action: 交易动作
            price: 当前价格
            position: 当前持仓
            cash: 当前现金
            commission_rate: 手续费率
            slippage: 滑点
            
        Returns:
            (交易记录, 剩余现金) 如果不交易则返回 (None, 原现金)
        """
        if action == TradeAction.HOLD:
            return None, cash
        
        # 应用滑点
        if action == TradeAction.BUY:
            executed_price = price * (1 + slippage)
        else:  # SELL
            executed_price = price * (1 - slippage)
        
        if action == TradeAction.BUY:
            # 计算可买入股数（100股为1手）
            max_shares = int(cash / executed_price / 100) * 100
            
            if max_shares <= 0:
                return None, cash
            
            # 全仓买入
            value = max_shares * executed_price
            commission = self._calculate_commission(value, commission_rate)
            total_cost = value + commission
            
            if total_cost > cash:
                max_shares = int((cash - commission) / executed_price / 100) * 100
                if max_shares <= 0:
                    return None, cash
                value = max_shares * executed_price
                commission = self._calculate_commission(value, commission_rate)
            
            # 更新持仓
            if position.shares == 0:
                position.avg_cost = executed_price
            else:
                total_cost_basis = position.shares * position.avg_cost + max_shares * executed_price
                position.avg_cost = total_cost_basis / (position.shares + max_shares)
            
            position.shares += max_shares
            cash -= (max_shares * executed_price + commission)
            
            trade = Trade(
                date=date,
                action=TradeAction.BUY,
                price=executed_price,
                shares=max_shares,
                value=max_shares * executed_price,
                commission=commission
            )
            
        else:  # SELL
            if position.shares <= 0:
                return None, cash
            
            # 卖出全部持仓
            value = position.shares * executed_price
            commission = self._calculate_commission(value, commission_rate)
            
            cash += value - commission
            
            trade = Trade(
                date=date,
                action=TradeAction.SELL,
                price=executed_price,
                shares=position.shares,
                value=value,
                commission=commission
            )
            
            position.shares = 0
            position.avg_cost = 0
        
        return trade, cash
    
    def run(self, 
            code: str,
            strategy: SignalGenerator,
            start_date: str,
            end_date: str,
            initial_capital: float = 1000000.0,
            commission_rate: float = 0.0003,
            slippage: float = 0.0001,
            price_type: str = 'open') -> BacktestResult:
        """
        运行回测
        
        Args:
            code: 股票代码
            strategy: 策略信号生成器
            start_date: 开始日期 (YYYY-MM-DD)
            end_date: 结束日期 (YYYY-MM-DD)
            initial_capital: 初始资金 (默认100万)
            commission_rate: 手续费率 (默认0.03%)
            slippage: 滑点 (默认0.01%)
            price_type: 成交价格类型 ('open'开盘价, 'close'收盘价)
            
        Returns:
            BacktestResult: 回测结果
        """
        # 加载数据
        stock_data = self._load_stock_data(code, start_date, end_date)
        if len(stock_data) < 20:
            raise ValueError(f"数据不足，仅获取到{len(stock_data)}条数据")
        
        benchmark_data = self._load_benchmark_data(start_date, end_date)
        stock_name = self._get_stock_name(code)
        
        # 初始化
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.position = Position(code=code)
        self.trades = []
        self.daily_snapshots = []
        
        # 转换为pandas DataFrame用于策略计算
        try:
            import pandas as pd
            df = pd.DataFrame(stock_data)
        except ImportError:
            # 如果没有pandas，创建一个简单的替代类
            class SimpleDataFrame:
                def __init__(self, data):
                    self.data = data
                
                def __getitem__(self, key):
                    return SimpleSeries([d[key] for d in self.data])
                
                @property
                def iloc(self):
                    return self
                
                def __getitem__(self, key):
                    if isinstance(key, slice):
                        return SimpleDataFrame(self.data[key])
                    return self.data[key]
            
            class SimpleSeries:
                def __init__(self, values):
                    self.values = values
                
                def mean(self):
                    return sum(self.values) / len(self.values) if self.values else 0
                
                def __getitem__(self, idx):
                    return self.values[idx]
            
            df = SimpleDataFrame(stock_data)
        
        # 回测主循环
        for i, day_data in enumerate(stock_data):
            date = day_data['date']
            price = day_data[price_type]
            
            # 更新持仓当前价格
            self.position.current_price = price
            
            # 生成交易信号
            action, reason = strategy.generate_signal(df, i)
            
            # 执行交易
            trade, self.cash = self._execute_trade(
                date, action, price,
                self.position, self.cash,
                commission_rate, slippage
            )
            
            if trade:
                trade.reason = reason
                self.trades.append(trade)
            
            # 计算当日市值
            positions_value = self.position.market_value
            total_value = self.cash + positions_value
            
            # 获取基准值
            benchmark_value = benchmark_data.get(date, 1.0) * initial_capital if benchmark_data else initial_capital
            
            # 计算当日收益
            if i == 0:
                daily_pnl = 0
                daily_return = 0
            else:
                prev_value = self.daily_snapshots[-1].total_value if self.daily_snapshots else initial_capital
                daily_pnl = total_value - prev_value
                daily_return = daily_pnl / prev_value if prev_value > 0 else 0
            
            # 记录每日快照
            snapshot = DailySnapshot(
                date=date,
                cash=self.cash,
                positions_value=positions_value,
                total_value=total_value,
                daily_pnl=daily_pnl,
                daily_return=daily_return,
                benchmark_value=benchmark_value,
                trades=[trade] if trade else []
            )
            self.daily_snapshots.append(snapshot)
        
        # 计算回测统计指标
        return self._calculate_metrics(code, stock_name, strategy.__class__.__name__, 
                                       start_date, end_date, benchmark_data)
    
    def _calculate_metrics(self, code: str, stock_name: str, strategy_name: str,
                          start_date: str, end_date: str, benchmark_data: Dict) -> BacktestResult:
        """计算回测统计指标"""
        
        if not self.daily_snapshots:
            raise ValueError("没有回测数据")
        
        # 基本收益指标
        initial_value = self.initial_capital
        final_value = self.daily_snapshots[-1].total_value
        total_return = final_value - initial_value
        total_return_pct = (final_value / initial_value - 1) * 100
        
        # 年化收益率
        days = len(self.daily_snapshots)
        years = days / 252  # 假设一年252个交易日
        if years > 0:
            annualized_return = ((final_value / initial_value) ** (1/years) - 1) * 100
        else:
            annualized_return = 0
        
        # 日收益率序列
        daily_returns = [s.daily_return for s in self.daily_snapshots[1:]]
        
        # 波动率 (年化)
        if len(daily_returns) > 1:
            volatility = np.std(daily_returns) * np.sqrt(252)
        else:
            volatility = 0
        
        # 夏普比率 (假设无风险利率为3%)
        risk_free_rate = 0.03
        if volatility > 0 and years > 0:
            sharpe_ratio = (annualized_return/100 - risk_free_rate) / volatility
        else:
            sharpe_ratio = 0
        
        # 索提诺比率 (只考虑下行波动)
        downside_returns = [r for r in daily_returns if r < 0]
        if downside_returns:
            downside_std = np.std(downside_returns) * np.sqrt(252)
            sortino_ratio = (annualized_return/100 - risk_free_rate) / downside_std if downside_std > 0 else 0
        else:
            sortino_ratio = 0
        
        # 最大回撤
        max_drawdown = 0
        max_drawdown_duration = 0
        peak = initial_value
        peak_date_idx = 0
        
        for i, snapshot in enumerate(self.daily_snapshots):
            if snapshot.total_value > peak:
                peak = snapshot.total_value
                peak_date_idx = i
            
            drawdown = (peak - snapshot.total_value) / peak
            if drawdown > max_drawdown:
                max_drawdown = drawdown
                max_drawdown_duration = i - peak_date_idx
        
        # 交易统计
        total_trades = len(self.trades)
        
        # 计算盈亏
        trade_pnls = []
        position_shares = 0
        position_cost = 0
        
        for trade in self.trades:
            if trade.action == TradeAction.BUY:
                position_shares += trade.shares
                position_cost += trade.value + trade.commission
            else:  # SELL
                if position_shares > 0:
                    # 简化计算，按FIFO
                    avg_cost_per_share = position_cost / position_shares
                    pnl = trade.value - trade.shares * avg_cost_per_share - trade.commission
                    trade_pnls.append(pnl)
                    position_shares -= trade.shares
                    position_cost = position_shares * avg_cost_per_share if position_shares > 0 else 0
        
        winning_trades = len([pnl for pnl in trade_pnls if pnl > 0])
        losing_trades = len([pnl for pnl in trade_pnls if pnl <= 0])
        win_rate = winning_trades / len(trade_pnls) * 100 if trade_pnls else 0
        
        profits = [pnl for pnl in trade_pnls if pnl > 0]
        losses = [abs(pnl) for pnl in trade_pnls if pnl <= 0]
        
        avg_profit = sum(profits) / len(profits) if profits else 0
        avg_loss = sum(losses) / len(losses) if losses else 0
        profit_loss_ratio = avg_profit / avg_loss if avg_loss > 0 else (float('inf') if avg_profit > 0 else 0)
        
        # 基准收益
        if benchmark_data:
            benchmark_return = (list(benchmark_data.values())[-1] / list(benchmark_data.values())[0] - 1) * 100
        else:
            benchmark_return = 0
        
        # Alpha (超额收益)
        alpha = total_return_pct - benchmark_return
        
        # 权益曲线
        equity_curve = [
            {
                'date': s.date,
                'value': round(s.total_value, 2),
                'return_pct': round((s.total_value / initial_value - 1) * 100, 2),
                'benchmark_pct': round((s.benchmark_value / initial_value - 1) * 100, 2) if s.benchmark_value else 0
            }
            for s in self.daily_snapshots
        ]
        
        return BacktestResult(
            strategy_name=strategy_name,
            code=code,
            stock_name=stock_name,
            start_date=start_date,
            end_date=end_date,
            initial_capital=initial_value,
            final_value=final_value,
            total_return=total_return,
            total_return_pct=total_return_pct,
            annualized_return=annualized_return,
            volatility=volatility,
            sharpe_ratio=sharpe_ratio,
            sortino_ratio=sortino_ratio,
            max_drawdown=max_drawdown,
            max_drawdown_duration=max_drawdown_duration,
            total_trades=total_trades,
            winning_trades=winning_trades,
            losing_trades=losing_trades,
            win_rate=win_rate,
            avg_profit=avg_profit,
            avg_loss=avg_loss,
            profit_loss_ratio=profit_loss_ratio,
            benchmark_return=benchmark_return,
            alpha=alpha,
            trades=self.trades,
            daily_snapshots=self.daily_snapshots,
            equity_curve=equity_curve
        )


# 导入pandas用于策略实现
try:
    import pandas as pd
except ImportError:
    pd = None


if __name__ == '__main__':
    # 测试回测引擎
    engine = BacktestEngine()
    
    # 使用简单均线策略
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
    
    print(f"回测结果: {result.total_return_pct:.2f}%")
    print(f"年化收益: {result.annualized_return:.2f}%")
    print(f"最大回撤: {result.max_drawdown*100:.2f}%")
    print(f"夏普比率: {result.sharpe_ratio:.2f}")
