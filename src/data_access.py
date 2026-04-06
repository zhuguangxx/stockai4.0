#!/usr/bin/env python3
"""
StockAI 4.0 数据访问层
整合：本地5年数据库 + kimi_finance 实时数据
"""
import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

# 五年数据库路径（R720）
STOCK_DB_PATH = "/data/stockai/db/stock.db"


class DataAccessLayer:
    """
    数据访问层
    
    策略：
    1. 历史数据（5年）→ 本地 SQLite（零延迟、无限流）
    2. 实时行情 → kimi_finance（实时但有限流）
    3. 分析计算 → 本地 indicators
    """
    
    def __init__(self):
        self.db_path = STOCK_DB_PATH
        self._local_cache = {}
    
    def _get_conn(self):
        """获取数据库连接"""
        return sqlite3.connect(self.db_path)
    
    def get_stock_data(
        self, 
        stock_code: str, 
        days: int = 60,
        end_date: Optional[str] = None
    ) -> Optional[pd.DataFrame]:
        """
        获取股票历史数据（本地5年数据库）
        
        Args:
            stock_code: 股票代码（如 000001.SZ）
            days: 获取天数
            end_date: 结束日期（默认今天）
            
        Returns:
            DataFrame with columns: date, open, high, low, close, volume
        """
        try:
            conn = self._get_conn()
            
            if end_date is None:
                end_date = datetime.now().strftime('%Y-%m-%d')
            
            start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
            
            # 查询本地数据库
            query = """
                SELECT date, open, high, low, close, volume
                FROM stock_daily
                WHERE code = ? AND date BETWEEN ? AND ?
                ORDER BY date ASC
            """
            
            df = pd.read_sql_query(query, conn, params=(stock_code, start_date, end_date))
            conn.close()
            
            if df.empty:
                return None
            
            # 转换数据类型
            for col in ['open', 'high', 'low', 'close', 'volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            return df
            
        except Exception as e:
            print(f"[DataAccess] 获取历史数据失败: {e}")
            return None
    
    def get_realtime_quote(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """
        获取实时行情（使用 kimi_finance）
        
        Args:
            stock_code: 股票代码
            
        Returns:
            {
                'price': float,
                'change_pct': float,
                'volume': int,
                'timestamp': str
            }
        """
        try:
            # 这里调用 kimi_finance
            # 为了演示，先返回模拟数据
            # 实际部署时替换为真实调用
            
            # 从本地获取最新数据作为基础
            df = self.get_stock_data(stock_code, days=1)
            if df is not None and not df.empty:
                latest = df.iloc[-1]
                return {
                    'price': float(latest['close']),
                    'change_pct': 0.0,  # 需要实时数据计算
                    'volume': int(latest['volume']),
                    'timestamp': datetime.now().isoformat()
                }
            return None
            
        except Exception as e:
            print(f"[DataAccess] 获取实时行情失败: {e}")
            return None
    
    def get_stock_list(self) -> List[str]:
        """获取股票列表"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT code FROM stock_daily LIMIT 1000")
            stocks = [row[0] for row in cursor.fetchall()]
            conn.close()
            return stocks
        except Exception as e:
            print(f"[DataAccess] 获取股票列表失败: {e}")
            return []
    
    def search_stock(self, keyword: str) -> List[Dict]:
        """搜索股票"""
        try:
            conn = self._get_conn()
            cursor = conn.cursor()
            
            # 假设有 stock_info 表
            cursor.execute(
                "SELECT code, name FROM stock_info WHERE code LIKE ? OR name LIKE ? LIMIT 10",
                (f"%{keyword}%", f"%{keyword}%")
            )
            results = [{"code": row[0], "name": row[1]} for row in cursor.fetchall()]
            conn.close()
            return results
        except Exception as e:
            print(f"[DataAccess] 搜索股票失败: {e}")
            return []


class KimiFinanceAdapter:
    """
    kimi_finance 适配器
    
    用于获取实时数据，作为本地数据库的补充
    """
    
    def __init__(self):
        self.enabled = True
    
    def get_realtime_price(self, stock_code: str) -> Optional[Dict]:
        """
        获取实时价格
        
        实际调用:
        from kimi_finance import kimi_finance
        result = kimi_finance(
            ticker=stock_code,
            time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            type='realtime_price'
        )
        """
        # TODO: 实际部署时接入 kimi_finance
        return None
    
    def get_intraday(self, stock_code: str) -> Optional[pd.DataFrame]:
        """获取当日分时数据"""
        # TODO: 接入 kimi_finance
        return None


# 全局实例
data_layer = DataAccessLayer()
kimi_adapter = KimiFinanceAdapter()


def get_stock_data(stock_code: str, days: int = 60) -> Optional[pd.DataFrame]:
    """便捷函数：获取股票数据"""
    return data_layer.get_stock_data(stock_code, days)


def get_realtime_quote(stock_code: str) -> Optional[Dict]:
    """便捷函数：获取实时行情"""
    return data_layer.get_realtime_quote(stock_code)
