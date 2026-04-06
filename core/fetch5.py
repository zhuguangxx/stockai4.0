#!/usr/bin/env python3
"""
StockAI 5年数据采集 - 优化版
只登录一次，批量获取
"""

import baostock as bs
import pandas as pd
import sqlite3
import time
import os
from datetime import datetime, timedelta

DB_PATH = '/data/stockai/db/stock.db'

def main():
    # 计算日期
    days = 365 * 5
    start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    end_date = datetime.now().strftime('%Y-%m-%d')
    
    print(f"StockAI 5-Year Data Fetch")
    print(f"Range: {start_date} to {end_date}")
    print("-" * 50)
    
    # 初始化数据库
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''CREATE TABLE IF NOT EXISTS kline (
        code TEXT, date TEXT, open REAL, high REAL, low REAL, close REAL, 
        volume INTEGER, amount REAL, PRIMARY KEY (code, date))''')
    conn.commit()
    
    # 登录Baostock
    lg = bs.login()
    if lg.error_code != '0':
        print(f"Login failed: {lg.error_msg}")
        return
    print("Login OK")
    
    # 获取股票列表
    rs = bs.query_all_stock(day=end_date)
    stocks = []
    while rs.next():
        stocks.append(rs.get_row_data()[0])
    print(f"Stocks: {len(stocks)}")
    print("-" * 50)
    
    # 批量采集
    success = fail = records = 0
    
    for i, code in enumerate(stocks):
        short = code.replace('sh.', '').replace('sz.', '')
        print(f"[{i+1}/{len(stocks)}] {short} ... ", end='', flush=True)
        
        try:
            rs = bs.query_history_k_data_plus(
                code, "date,open,high,low,close,volume,amount",
                start_date=start_date, end_date=end_date,
                frequency="d", adjustflag="3"
            )
            
            data_list = []
            while rs.next():
                row = rs.get_row_data()
                data_list.append((
                    short, row[0], float(row[1]) if row[1] else 0,
                    float(row[2]) if row[2] else 0, float(row[3]) if row[3] else 0,
                    float(row[4]) if row[4] else 0, int(float(row[5])) if row[5] else 0,
                    float(row[6]) if row[6] else 0
                ))
            
            if data_list:
                cursor.executemany('''INSERT OR REPLACE INTO kline 
                    (code, date, open, high, low, close, volume, amount) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)''', data_list)
                conn.commit()
                print(f"OK {len(data_list)}")
                success += 1
                records += len(data_list)
            else:
                print("Empty")
                fail += 1
                
        except Exception as e:
            print(f"Error: {e}")
            fail += 1
        
        time.sleep(1.5)  # 延迟防过载
    
    bs.logout()
    conn.close()
    
    print("-" * 50)
    print(f"Done! Success:{success} Fail:{fail} Records:{records}")

if __name__ == "__main__":
    main()
