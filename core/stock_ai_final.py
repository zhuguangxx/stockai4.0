#!/usr/bin/env python3
"""
StockAI 完整版 - 混合数据源 + 六大专家
支持: 本地历史 + 实时快照 + 真实计算
"""

import sys
import re
from mixed_data import get_mixed_data
from experts import ExpertSystem

# 股票名称映射
STOCK_NAME_MAP = {
    '茅台': ('600519', '贵州茅台'),
    '贵州茅台': ('600519', '贵州茅台'),
    '平安': ('000001', '平安银行'),
    '平安银行': ('000001', '平安银行'),
    '五粮液': ('000858', '五粮液'),
    '比亚迪': ('002594', '比亚迪'),
    '宁德时代': ('300750', '宁德时代'),
    '招商银行': ('600036', '招商银行'),
    '中信证券': ('600030', '中信证券'),
    '东方财富': ('300059', '东方财富'),
    '中国平安': ('601318', '中国平安'),
    '恒瑞医药': ('600276', '恒瑞医药'),
    '海康威视': ('002415', '海康威视'),
}

def parse_input(msg):
    """解析用户输入"""
    msg = msg.strip().replace('查', '').replace('怎么样', '').replace('如何', '')
    
    # 6位数字代码
    codes = re.findall(r'\b(\d{6})\b', msg)
    if codes:
        code = codes[0]
        if code.startswith('6') or code.startswith('0') or code.startswith('3'):
            return code, None
    
    # 名称匹配
    for name, (code, full_name) in STOCK_NAME_MAP.items():
        if name in msg:
            return code, full_name
    
    return None, None

def analyze_stock(code, name=None, single_expert=None):
    """
    分析股票 - 混合数据源版本
    code: 股票代码
    name: 股票名称
    single_expert: 指定专家名称，None则全部
    """
    stock_name = name or code
    
    print(f"🔍 正在分析 {stock_name}({code})...")
    
    # 1. 获取混合数据（本地历史 + 实时快照）
    df = get_mixed_data(code, days=200)
    
    if df is None or len(df) < 30:
        return f"❌ 无法获取 {code} 的足够数据"
    
    print(f"✅ 数据就绪: {len(df)} 天 (含实时)")
    
    # 2. 专家分析（真实计算！）
    expert = ExpertSystem(df)
    results = expert.analyze_all()
    
    # 3. 获取最新价格信息
    current_price = df['close'].iloc[-1]
    prev_price = df['close'].iloc[-2]
    change = (current_price / prev_price - 1) * 100
    today_high = df['high'].iloc[-1]
    today_low = df['low'].iloc[-1]
    today_volume = df['volume'].iloc[-1]
    
    if single_expert:
        # 单个专家报告
        if single_expert.upper() in results:
            report = f"""
📊 【{stock_name}】{code}
💰 当前: ¥{current_price:.2f} ({change:+.2f}%) | 最高: ¥{today_high:.2f} | 最低: ¥{today_low:.2f}
📊 成交量: {today_volume:,}

{results[single_expert.upper()]['analysis']}

⚠️ 免责声明: 以上分析仅供参考，不构成投资建议。
💾 数据来源: 本地历史+实时快照 (真实计算)
"""
            return report
        else:
            return f"❌ 未知的专家名称: {single_expert}"
    
    # 4. 完整综合报告
    summary = expert.generate_summary()
    
    report = f"""
{'='*60}
📊 【{stock_name}】{code} 技术分析报告
{'='*60}
💰 当前价格: ¥{current_price:.2f} ({change:+.2f}%)
📊 今日区间: ¥{today_low:.2f} - ¥{today_high:.2f}
📊 成交量: {today_volume:,}
{'='*60}

{summary['overall']}
{summary['suggestion']}

{'─'*60}
📈 六大专家简评 (基于真实计算):
{'─'*60}

🔹 MACD专家: {results['MACD']['data']['signal']} (评分: {'+' if results['MACD']['score'] > 0 else ''}{results['MACD']['score']})
   DIF:{results['MACD']['data']['DIF']} DEA:{results['MACD']['data']['DEA']} MACD:{results['MACD']['data']['MACD']}

🔹 KDJ专家:  {results['KDJ']['data']['signal']} (评分: {'+' if results['KDJ']['score'] > 0 else ''}{results['KDJ']['score']})
   K:{results['KDJ']['data']['K']} D:{results['KDJ']['data']['D']} J:{results['KDJ']['data']['J']}

🔹 MA专家:   {results['MA']['data']['signal']} (评分: {'+' if results['MA']['score'] > 0 else ''}{results['MA']['score']})
   MA5:{results['MA']['data']['MA5']} MA20:{results['MA']['data']['MA20']}

🔹 BOLL专家: {results['BOLL']['data']['signal']} (评分: {'+' if results['BOLL']['score'] > 0 else ''}{results['BOLL']['score']})
   上轨:{results['BOLL']['data']['upper']} 中轨:{results['BOLL']['data']['mid']} 下轨:{results['BOLL']['data']['lower']}

🔹 RSI专家:  {results['RSI']['data']['signal']} (评分: {'+' if results['RSI']['score'] > 0 else ''}{results['RSI']['score']})
   RSI6:{results['RSI']['data']['RSI6']} RSI12:{results['RSI']['data']['RSI12']}

🔹 CCI专家:  {results['CCI']['data']['signal']} (评分: {'+' if results['CCI']['score'] > 0 else ''}{results['CCI']['score']})
   CCI:{results['CCI']['data']['CCI']}

{'─'*60}
💡 综合评分: {summary['total_score']:+d}/6
{'─'*60}

⚠️ 免责声明: 以上分析仅供参考，不构成投资建议。
💾 数据: 本地历史({len(df)-1}天) + 实时快照 (真实计算)
{'='*60}
"""
    
    return report

def main():
    """主入口"""
    if len(sys.argv) > 1:
        msg = ' '.join(sys.argv[1:])
        code, name = parse_input(msg)
        
        if code:
            single_expert = None
            for expert in ['MACD', 'KDJ', 'MA', 'BOLL', 'RSI', 'CCI']:
                if expert in msg.upper():
                    single_expert = expert
                    break
            
            print(analyze_stock(code, name, single_expert))
        else:
            print("❌ 无法识别股票，请发送:\n• 6位数字代码（如 600519）\n• 股票名称（如 茅台）\n• 指定专家（如 600519 MACD）")
    else:
        print("🧪 测试模式: 分析茅台")
        print(analyze_stock('600519', '贵州茅台'))

if __name__ == "__main__":
    main()
