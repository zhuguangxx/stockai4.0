#!/usr/bin/env python3
"""
MACD策略 - 回测用
基于MACD金叉/死叉产生交易信号
"""
from typing import Dict, Any
import pandas as pd


class MACDStrategy:
    """
    MACD金叉买入，死叉卖出策略
    
    参数:
    - fast_period: 快线周期 (默认12)
    - slow_period: 慢线周期 (默认26)
    - signal_period: 信号线周期 (默认9)
    """
    
    def __init__(self, fast_period: int = 12, slow_period: int = 26, signal_period: int = 9):
        self.fast_period = fast_period
        self.slow_period = slow_period
        self.signal_period = signal_period
        self.name = f"MACD策略({fast_period},{slow_period},{signal_period})"
    
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        生成交易信号
        
        Args:
            df: DataFrame with columns ['open', 'high', 'low', 'close', 'volume']
            
        Returns:
            DataFrame with added columns ['macd_dif', 'macd_dea', 'macd_hist', 'signal']
        """
        df = df.copy()
        
        # 计算MACD
        exp1 = df['close'].ewm(span=self.fast_period, adjust=False).mean()
        exp2 = df['close'].ewm(span=self.slow_period, adjust=False).mean()
        df['macd_dif'] = exp1 - exp2
        df['macd_dea'] = df['macd_dif'].ewm(span=self.signal_period, adjust=False).mean()
        df['macd_hist'] = 2 * (df['macd_dif'] - df['macd_dea'])
        
        # 生成信号
        df['signal'] = 0
        
        # 金叉: DIF上穿DEA (买入信号)
        golden_cross = (df['macd_dif'] > df['macd_dea']) & (df['macd_dif'].shift(1) <= df['macd_dea'].shift(1))
        df.loc[golden_cross, 'signal'] = 1
        
        # 死叉: DIF下穿DEA (卖出信号)
        dead_cross = (df['macd_dif'] < df['macd_dea']) & (df['macd_dif'].shift(1) >= df['macd_dea'].shift(1))
        df.loc[dead_cross, 'signal'] = -1
        
        return df
    
    def get_signal_description(self, signal: int) -> str:
        """获取信号描述"""
        if signal == 1:
            return "买入 (MACD金叉)"
        elif signal == -1:
            return "卖出 (MACD死叉)"
        else:
            return "持有"
    
    def get_parameters(self) -> Dict[str, Any]:
        """获取策略参数"""
        return {
            "name": self.name,
            "fast_period": self.fast_period,
            "slow_period": self.slow_period,
            "signal_period": self.signal_period
        }
