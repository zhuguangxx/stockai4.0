#!/usr/bin/env python3
"""
StockAI 真实计算版 - 数据获取模块 (Baostock)
获取原始K线数据，存入SQLite
"""

import baostock as bs
import pandas as pd
import sqlite3
from datetime import datetime, timedelta
import os

DB_PATH = '/data/stockai/db/stock.db'

def init_db():
    """初始化数据库"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS kline (
            code TEXT,
            date TEXT,
            open REAL,
            high REAL,
            low REAL,
            close REAL,
            volume INTEGER,
            amount REAL,
            PRIMARY KEY (code, date)
        )
    ''')
    conn.commit()
    conn.close()

def login():
    """登录Baostock"""
    lg = bs.login()
    if lg.error_code != '0':
        print(f"登录失败: {lg.error_msg}")
        return False
    return True

def logout():
    """登出"""
    bs.logout()

def get_stock_code(code):
    """格式化股票代码"""
    if code.startswith('6'):
        return f"sh.{code}"
    elif code.startswith('0') or code.startswith('3'):
        return f"sz.{code}"
    return code

def fetch_history(code, days=200):
    """获取历史K线数据"""
    init_db()
    
    if not login():
        return None
    
    bs_code = get_stock_code(code)
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    
    print(f"📊 获取 {code} 从 {start_date} 到 {end_date} 的数据...")
    
    rs = bs.query_history_k_data_plus(
        bs_code,
        "date,open,high,low,close,volume,amount",
        start_date=start_date,
        end_date=end_date,
        frequency="d",
        adjustflag="3"  # 复权
    )
    
    if rs.error_code != '0':
        print(f"获取数据失败: {rs.error_msg}")
        logout()
        return None
    
    # 读取数据
    data_list = []
    while (rs.error_code == '0') & rs.next():
        row = rs.get_row_data()
        data_list.append({
            'code': code,
            'date': row[0],
            'open': float(row[1]) if row[1] else 0,
            'high': float(row[2]) if row[2] else 0,
            'low': float(row[3]) if row[3] else 0,
            'close': float(row[4]) if row[4] else 0,
            'volume': int(float(row[5])) if row[5] else 0,
            'amount': float(row[6]) if row[6] else 0
        })
    
    logout()
    
    if not data_list:
        print("❌ 无数据返回")
        return None
    
    df = pd.DataFrame(data_list)
    
    # 存入数据库
    conn = sqlite3.connect(DB_PATH)
    df.to_sql('kline', conn, if_exists='append', index=False)
    conn.close()
    
    print(f"✅ 获取 {len(df)} 条数据，已存入数据库")
    return df

def get_from_db(code, days=60):
    """从数据库获取数据"""
    init_db()  # 确保数据库和表存在
    
    conn = sqlite3.connect(DB_PATH)
    try:
        query = f"""
            SELECT * FROM kline 
            WHERE code = '{code}' 
            ORDER BY date DESC 
            LIMIT {days}
        """
        df = pd.read_sql(query, conn)
    except:
        df = pd.DataFrame()  # 表不存在或查询失败
    finally:
        conn.close()
    
    if df.empty:
        return None
    
    df = df.sort_values('date').reset_index(drop=True)
    return df

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        code = sys.argv[1]
        df = fetch_history(code)
        if df is not None:
            print(df.tail())
    else:
        # 测试茅台
        df = fetch_history("600519")
        if df is not None:
            print(df.tail())
