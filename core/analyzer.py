#!/usr/bin/env python3
"""
StockAI Core Analyzer - 微信对接版
对接微信消息和agent_memory.db
"""

import sys
import os
import re
import sqlite3
import json
from datetime import datetime

# 添加core目录到路径
sys.path.insert(0, '/data/stockai/core')

from stock_ai_final import analyze_stock, parse_input, STOCK_NAME_MAP

# 数据库路径
AGENT_MEMORY_DB = '/root/.openclaw/data/agent_memory.db'
STOCK_DB = '/data/stockai/db/stock.db'

# 股票名称映射（扩展）
STOCK_NAME_MAP_EXT = {
    **STOCK_NAME_MAP,
    '腾讯': ('00700', '腾讯控股'),
    '阿里': ('09988', '阿里巴巴'),
    '美团': ('03690', '美团'),
    '小米': ('01810', '小米集团'),
}

def init_agent_memory():
    """初始化agent_memory.db"""
    os.makedirs(os.path.dirname(AGENT_MEMORY_DB), exist_ok=True)
    conn = sqlite3.connect(AGENT_MEMORY_DB)
    cursor = conn.cursor()
    
    # 创建分析记录表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS stock_analysis (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            stock_code TEXT,
            stock_name TEXT,
            query_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            result TEXT,
            score INTEGER
        )
    ''')
    
    # 创建用户偏好表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_preferences (
            user_id TEXT PRIMARY KEY,
            fav_stocks TEXT,  -- JSON数组
            risk_profile TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()

def save_analysis(user_id, code, name, result, score):
    """保存分析记录"""
    conn = sqlite3.connect(AGENT_MEMORY_DB)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO stock_analysis (user_id, stock_code, stock_name, result, score)
        VALUES (?, ?, ?, ?, ?)
    ''', (user_id, code, name, result, score))
    conn.commit()
    conn.close()

def get_user_history(user_id, limit=5):
    """获取用户历史查询"""
    conn = sqlite3.connect(AGENT_MEMORY_DB)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT stock_code, stock_name, query_time FROM stock_analysis
        WHERE user_id = ? ORDER BY query_time DESC LIMIT ?
    ''', (user_id, limit))
    rows = cursor.fetchall()
    conn.close()
    return rows

def parse_input_extended(msg):
    """扩展的股票代码解析"""
    msg = msg.strip().replace('查', '').replace('怎么样', '').replace('如何', '')
    
    # 6位数字代码（A股）
    codes = re.findall(r'\b(\d{6})\b', msg)
    if codes:
        code = codes[0]
        if code.startswith('6') or code.startswith('0') or code.startswith('3'):
            return code, None
    
    # 5位数字代码（港股）
    hk_codes = re.findall(r'\b(\d{5})\b', msg)
    if hk_codes:
        return hk_codes[0], None
    
    # 名称匹配
    for name, (code, full_name) in STOCK_NAME_MAP_EXT.items():
        if name in msg:
            return code, full_name
    
    return None, None

def format_for_weixin(report):
    """格式化报告为微信消息格式"""
    # 简化格式，适合微信阅读
    lines = report.split('\n')
    simplified = []
    
    for line in lines:
        # 保留关键行
        if any(k in line for k in ['【', '💰', '📊', '综合评分', '免责声明']):
            simplified.append(line)
        # 保留专家简评
        elif line.startswith('🔹'):
            simplified.append(line)
    
    return '\n'.join(simplified[:30])  # 限制长度

def analyze_for_weixin(user_id, message):
    """
    主入口：微信消息分析
    user_id: 用户微信ID
    message: 用户消息内容
    """
    init_agent_memory()
    
    # 解析股票代码
    code, name = parse_input_extended(message)
    
    if not code:
        # 尝试获取用户历史
        history = get_user_history(user_id)
        if history:
            hist_str = '\n'.join([f"• {h[1]}({h[0]}) - {h[2][:10]}" for h in history])
            return f"❓ 请发送股票代码或名称\n\n您近期查询过:\n{hist_str}"
        else:
            return "❓ 请发送股票代码（如600519）或名称（如茅台）"
    
    # 检查是否指定专家
    single_expert = None
    for expert in ['MACD', 'KDJ', 'MA', 'BOLL', 'RSI', 'CCI']:
        if expert in message.upper():
            single_expert = expert
            break
    
    try:
        # 执行分析
        report = analyze_stock(code, name, single_expert)
        
        # 提取评分
        score = 0
        if '综合评分:' in report:
            match = re.search(r'综合评分:\s*([+-]?\d+)/6', report)
            if match:
                score = int(match.group(1))
        
        # 保存到记忆
        save_analysis(user_id, code, name or code, report[:500], score)
        
        # 格式化微信输出
        wx_report = format_for_weixin(report)
        
        return wx_report + generate_menu(code)
        
    except Exception as e:
        return f"❌ 分析出错: {str(e)}\n请稍后重试或联系管理员"

def main():
    """命令行入口"""
    if len(sys.argv) >= 3:
        # 参数: analyzer.py <user_id> <message>
        user_id = sys.argv[1]
        message = ' '.join(sys.argv[2:])
        print(analyze_for_weixin(user_id, message))
    elif len(sys.argv) >= 2:
        # 测试模式
        message = sys.argv[1]
        print(analyze_for_weixin("test_user", message))
    else:
        # 默认测试
        print("🧪 测试模式: 分析茅台")
        print(analyze_for_weixin("test_user", "600519"))

def generate_menu(code, in_watchlist=False):
    """生成分析报告后的操作菜单"""
    watchlist_status = "✅" if in_watchlist else "⬜"
    menu = f"""
━━━━━━━━━━━━━━━━━━━━━━
📋 下一步操作:

【1】查看六大指标详情
【2】查看回测数据
【3】专家观点辩论
【4】{watchlist_status} 加入自选股

💡 回复数字 1-4 选择操作
━━━━━━━━━━━━━━━━━━━━━━
"""
    return menu

# ============ 微信菜单功能 ============
# ============ 微信菜单功能 ============

if __name__ == "__main__":
    main()
