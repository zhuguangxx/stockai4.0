#!/usr/bin/env python3
"""
StockAI 真实计算版 - 技术指标计算模块
基于原始K线数据，真实计算6大指标
"""

import pandas as pd
import numpy as np

class TechnicalIndicators:
    """技术指标计算器"""
    
    @staticmethod
    def macd(df, fast=12, slow=26, signal=9):
        """
        MACD指标计算
        输入: DataFrame (含close列)
        返回: dict with DIF, DEA, MACD, signal
        """
        close = df['close']
        
        # 计算EMA
        ema_fast = close.ewm(span=fast, adjust=False).mean()
        ema_slow = close.ewm(span=slow, adjust=False).mean()
        
        # DIF = EMA12 - EMA26
        dif = ema_fast - ema_slow
        
        # DEA = DIF的EMA9
        dea = dif.ewm(span=signal, adjust=False).mean()
        
        # MACD柱 = (DIF - DEA) * 2
        macd_bar = (dif - dea) * 2
        
        # 信号判断
        current_dif = dif.iloc[-1]
        current_dea = dea.iloc[-1]
        prev_dif = dif.iloc[-2]
        prev_dea = dea.iloc[-2]
        
        if current_dif > current_dea and prev_dif <= prev_dea:
            signal = "金叉买入💚"
        elif current_dif < current_dea and prev_dif >= prev_dea:
            signal = "死叉卖出❌"
        elif current_dif > current_dea:
            signal = "多头趋势📈"
        else:
            signal = "空头趋势📉"
        
        return {
            'DIF': round(current_dif, 3),
            'DEA': round(current_dea, 3),
            'MACD': round(macd_bar.iloc[-1], 3),
            'signal': signal,
            'trend': '上涨' if macd_bar.iloc[-1] > 0 else '下跌'
        }
    
    @staticmethod
    def kdj(df, n=9, m1=3, m2=3):
        """
        KDJ指标计算
        输入: DataFrame (含high, low, close)
        返回: dict with K, D, J, signal
        """
        low_list = df['low'].rolling(window=n, min_periods=n).min()
        high_list = df['high'].rolling(window=n, min_periods=n).max()
        rsv = (df['close'] - low_list) / (high_list - low_list) * 100
        
        k = rsv.ewm(com=m1-1, adjust=False).mean()
        d = k.ewm(com=m2-1, adjust=False).mean()
        j = 3 * k - 2 * d
        
        k_val = k.iloc[-1]
        d_val = d.iloc[-1]
        j_val = j.iloc[-1]
        
        # 信号判断
        if j_val > 100:
            signal = "严重超买⚠️"
        elif j_val > 80:
            signal = "超买区域🟡"
        elif j_val < 0:
            signal = "严重超卖💡"
        elif j_val < 20:
            signal = "超卖区域🟢"
        elif k_val > d_val:
            signal = "金叉多头📈"
        else:
            signal = "死叉空头📉"
        
        return {
            'K': round(k_val, 2),
            'D': round(d_val, 2),
            'J': round(j_val, 2),
            'signal': signal
        }
    
    @staticmethod
    def ma(df):
        """
        均线系统
        输入: DataFrame (含close)
        返回: dict with MA5/10/20/60 and signal
        """
        close = df['close']
        ma5 = close.rolling(5).mean().iloc[-1]
        ma10 = close.rolling(10).mean().iloc[-1]
        ma20 = close.rolling(20).mean().iloc[-1]
        ma60 = close.rolling(60).mean().iloc[-1]
        current = close.iloc[-1]
        
        # 判断多头排列
        if current > ma5 > ma10 > ma20 > ma60:
            signal = "多头排列💪"
        elif current < ma5 < ma10 < ma20 < ma60:
            signal = "空头排列😰"
        elif current > ma5:
            signal = "站上短期均线📈"
        else:
            signal = "跌破短期均线📉"
        
        return {
            'MA5': round(ma5, 2),
            'MA10': round(ma10, 2),
            'MA20': round(ma20, 2),
            'MA60': round(ma60, 2),
            'current': round(current, 2),
            'signal': signal
        }
    
    @staticmethod
    def boll(df, n=20, k=2):
        """
        布林带
        输入: DataFrame (含close)
        返回: dict with upper, mid, lower, signal
        """
        close = df['close']
        mid = close.rolling(n).mean()
        std = close.rolling(n).std()
        upper = mid + k * std
        lower = mid - k * std
        
        current = close.iloc[-1]
        upper_val = upper.iloc[-1]
        mid_val = mid.iloc[-1]
        lower_val = lower.iloc[-1]
        
        # 信号判断
        if current >= upper_val:
            signal = "触及上轨⚠️"
        elif current <= lower_val:
            signal = "触及下轨💡"
        elif current > mid_val:
            signal = "中轨上方📈"
        else:
            signal = "中轨下方📉"
        
        return {
            'upper': round(upper_val, 2),
            'mid': round(mid_val, 2),
            'lower': round(lower_val, 2),
            'bandwidth': round((upper_val - lower_val) / mid_val * 100, 2),  # 带宽%
            'signal': signal
        }
    
    @staticmethod
    def rsi(df, n=6):
        """
        RSI相对强弱指标
        输入: DataFrame (含close)
        返回: dict with RSI6/12/24, signal
        """
        close = df['close']
        delta = close.diff()
        
        def calc_rsi(period):
            gain = delta.where(delta > 0, 0).rolling(window=period).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
            rs = gain / loss
            return 100 - (100 / (1 + rs))
        
        rsi6 = calc_rsi(6).iloc[-1]
        rsi12 = calc_rsi(12).iloc[-1]
        rsi24 = calc_rsi(24).iloc[-1]
        
        # 信号判断
        if rsi6 > 80:
            signal = "严重超买⚠️"
        elif rsi6 > 70:
            signal = "超买区域🟡"
        elif rsi6 < 20:
            signal = "严重超卖💡"
        elif rsi6 < 30:
            signal = "超卖区域🟢"
        else:
            signal = "中性区域"
        
        return {
            'RSI6': round(rsi6, 2),
            'RSI12': round(rsi12, 2),
            'RSI24': round(rsi24, 2),
            'signal': signal
        }
    
    @staticmethod
    def cci(df, n=14):
        """
        CCI顺势指标
        输入: DataFrame (含high, low, close)
        返回: dict with CCI, signal
        """
        tp = (df['high'] + df['low'] + df['close']) / 3  # 典型价格
        ma_tp = tp.rolling(n).mean()
        md = tp.rolling(n).apply(lambda x: np.abs(x - x.mean()).mean())
        cci = (tp - ma_tp) / (0.015 * md)
        
        cci_val = cci.iloc[-1]
        
        # 信号判断
        if cci_val > 200:
            signal = "严重超买⚠️"
        elif cci_val > 100:
            signal = "强势区域💪"
        elif cci_val < -200:
            signal = "严重超卖💡"
        elif cci_val < -100:
            signal = "弱势区域😰"
        else:
            signal = "震荡区域"
        
        return {
            'CCI': round(cci_val, 2),
            'signal': signal
        }

if __name__ == "__main__":
    # 测试
    from data_fetcher import fetch_history
    
    df = fetch_history("600519", days=100)
    if df is not None:
        indicators = TechnicalIndicators()
        print("MACD:", indicators.macd(df))
        print("KDJ:", indicators.kdj(df))
        print("MA:", indicators.ma(df))
        print("BOLL:", indicators.boll(df))
        print("RSI:", indicators.rsi(df))
        print("CCI:", indicators.cci(df))
