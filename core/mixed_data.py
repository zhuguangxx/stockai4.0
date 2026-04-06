#!/usr/bin/env python3
"""
StockAI 混合数据源方案 (Baostock版本)
- 本地SQLite: 历史数据
- Baostock: 实时数据
"""

import baostock as bs
import pandas as pd
import sqlite3
import time
from datetime import datetime, timedelta
from data_fetcher import DB_PATH, init_db, login, logout, get_stock_code

def get_local_history(code, days=200):
    """从本地数据库获取历史数据"""
    conn = sqlite3.connect(DB_PATH)
    try:
        query = f"""
            SELECT * FROM kline 
            WHERE code = '{code}' 
            ORDER BY date DESC 
            LIMIT {days}
        """
        df = pd.read_sql(query, conn)
        if not df.empty:
            df = df.sort_values('date').reset_index(drop=True)
            return df
    except:
        pass
    finally:
        conn.close()
    return None

def get_realtime_spot(code):
    """获取实时数据（Baostock）"""
    try:
        lg = bs.login()
        if lg.error_code != '0':
            return None
        
        bs_code = get_stock_code(code)
        today = datetime.now().strftime('%Y-%m-%d')
        
        rs = bs.query_history_k_data_plus(
            bs_code,
            "date,open,high,low,close,volume,amount",
            start_date=today,
            end_date=today,
            frequency="d",
            adjustflag="3"
        )
        
        data = None
        while (rs.error_code == '0') & rs.next():
            row = rs.get_row_data()
            data = {
                'code': code,
                'date': row[0],
                'open': float(row[1]) if row[1] else 0,
                'high': float(row[2]) if row[2] else 0,
                'low': float(row[3]) if row[3] else 0,
                'close': float(row[4]) if row[4] else 0,
                'volume': int(float(row[5])) if row[5] else 0,
                'amount': float(row[6]) if row[6] else 0
            }
        
        bs.logout()
        return data
        
    except Exception as e:
        print(f"❌ Baostock失败: {e}")
        return None

def get_mixed_data(code, days=200):
    """
    获取混合数据：本地历史 + Baostock实时
    返回: DataFrame
    """
    print(f"🔍 获取 {code} 混合数据...")
    
    # 1. 获取本地历史
    df_history = get_local_history(code, days=days)
    
    if df_history is None or len(df_history) < 60:
        print("  ⚠️  本地数据不足，从Baostock获取全量数据...")
        from data_fetcher import fetch_history
        return fetch_history(code, days=days)
    
    print(f"  ✅ 本地历史: {len(df_history)} 天")
    
    # 2. 获取实时数据
    print("  🔄 获取实时数据...")
    realtime = get_realtime_spot(code)
    
    if realtime is None:
        print("  ⚠️  实时数据获取失败，使用历史数据")
        return df_history
    
    print(f"  ✅ 实时价格: ¥{realtime['close']}")
    
    # 3. 检查是否已有今日数据
    today = datetime.now().strftime('%Y-%m-%d')
    if df_history['date'].iloc[-1] == today:
        # 已有今日数据，更新它
        print("  📝 更新今日数据")
        for key, value in realtime.items():
            df_history.loc[df_history.index[-1], key] = value
        return df_history
    
    # 4. 拼接新数据
    print("  📝 拼接实时数据")
    new_row = pd.DataFrame([realtime])
    df_mixed = pd.concat([df_history, new_row], ignore_index=True)
    
    return df_mixed

def update_local_with_realtime(code):
    """将实时数据存入本地数据库（用于每日更新）"""
    realtime = get_realtime_spot(code)
    if realtime is None:
        return False
    
    conn = sqlite3.connect(DB_PATH)
    conn.execute('''
        INSERT OR REPLACE INTO kline (code, date, open, high, low, close, volume, amount)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (realtime['code'], realtime['date'], realtime['open'], 
          realtime['high'], realtime['low'], realtime['close'],
          realtime['volume'], realtime['amount']))
    conn.commit()
    conn.close()
    
    return True

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        code = sys.argv[1]
        df = get_mixed_data(code)
        if df is not None:
            print(f"\n📊 最终数据: {len(df)} 天")
            print(df.tail(3))
    else:
        # 测试茅台
        df = get_mixed_data("600519")
        if df is not None:
            print(f"\n📊 最终数据: {len(df)} 天")
            print(f"最新价格: ¥{df['close'].iloc[-1]}")
