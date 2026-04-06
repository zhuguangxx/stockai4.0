#!/usr/bin/env python3
"""
用户记忆服务
"""
import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

DB_PATH = "/opt/stockai4.0/data/stockai.db"


@dataclass
class UserProfile:
    name: str
    experience: str
    risk_level: str
    style: str
    focus_sectors: List[str]


@dataclass
class Position:
    stock_code: str
    shares: float
    avg_cost: float


class UserMemoryService:
    """用户记忆服务"""
    
    def _get_conn(self):
        return sqlite3.connect(DB_PATH)
    
    # ========== 画像管理 ==========
    def save_profile(self, user_id: str, profile: Dict) -> bool:
        """保存用户画像"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        focus_sectors = profile.get("focus_sectors", [])
        if isinstance(focus_sectors, list):
            focus_sectors = json.dumps(focus_sectors)
        
        try:
            cursor.execute(
                """INSERT OR REPLACE INTO user_profiles 
                   (user_id, name, experience, risk_level, style, focus_sectors, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    user_id,
                    profile.get("name", "用户"),
                    profile.get("experience", "intermediate"),
                    profile.get("risk_level", "moderate"),
                    profile.get("style", "value"),
                    focus_sectors,
                    datetime.now().isoformat()
                )
            )
            conn.commit()
            return True
        except Exception:
            return False
        finally:
            conn.close()
    
    def get_profile(self, user_id: str) -> Optional[UserProfile]:
        """获取用户画像"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT name, experience, risk_level, style, focus_sectors FROM user_profiles WHERE user_id = ?",
            (user_id,)
        )
        row = cursor.fetchone()
        conn.close()
        
        if row:
            focus_sectors = row[4]
            if focus_sectors:
                try:
                    focus_sectors = json.loads(focus_sectors)
                except:
                    focus_sectors = []
            else:
                focus_sectors = []
            
            return UserProfile(
                name=row[0],
                experience=row[1],
                risk_level=row[2],
                style=row[3],
                focus_sectors=focus_sectors
            )
        return None
    
    # ========== 自选管理 ==========
    def add_watchlist(self, user_id: str, stock_code: str) -> bool:
        """添加自选"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "INSERT INTO watchlists (user_id, stock_code) VALUES (?, ?)",
                (user_id, stock_code)
            )
            conn.commit()
            return True
        except sqlite3.IntegrityError:
            # 已存在
            return False
        finally:
            conn.close()
    
    def remove_watchlist(self, user_id: str, stock_code: str) -> bool:
        """删除自选"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute(
            "DELETE FROM watchlists WHERE user_id = ? AND stock_code = ?",
            (user_id, stock_code)
        )
        conn.commit()
        deleted = cursor.rowcount > 0
        conn.close()
        return deleted
    
    def get_watchlist(self, user_id: str) -> List[str]:
        """获取自选列表"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT stock_code FROM watchlists WHERE user_id = ? ORDER BY added_at DESC",
            (user_id,)
        )
        rows = cursor.fetchall()
        conn.close()
        
        return [r[0] for r in rows]
    
    def is_in_watchlist(self, user_id: str, stock_code: str) -> bool:
        """检查是否在自选"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT 1 FROM watchlists WHERE user_id = ? AND stock_code = ?",
            (user_id, stock_code)
        )
        exists = cursor.fetchone() is not None
        conn.close()
        return exists
    
    # ========== 持仓管理 ==========
    def add_position(self, user_id: str, stock_code: str, shares: float, price: float) -> bool:
        """买入/加仓"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        try:
            # 查询现有持仓
            cursor.execute(
                "SELECT shares, avg_cost FROM positions WHERE user_id = ? AND stock_code = ?",
                (user_id, stock_code)
            )
            row = cursor.fetchone()
            
            if row:
                # 更新持仓（加权平均）
                old_shares, old_cost = row
                total_shares = old_shares + shares
                total_cost = old_shares * old_cost + shares * price
                new_avg_cost = total_cost / total_shares if total_shares > 0 else 0
                
                cursor.execute(
                    "UPDATE positions SET shares = ?, avg_cost = ?, updated_at = ? WHERE user_id = ? AND stock_code = ?",
                    (total_shares, new_avg_cost, datetime.now().isoformat(), user_id, stock_code)
                )
            else:
                # 新建持仓
                cursor.execute(
                    "INSERT INTO positions (user_id, stock_code, shares, avg_cost) VALUES (?, ?, ?, ?)",
                    (user_id, stock_code, shares, price)
                )
            
            conn.commit()
            return True
        except Exception:
            return False
        finally:
            conn.close()
    
    def reduce_position(self, user_id: str, stock_code: str, shares: float) -> Dict:
        """卖出/减仓"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        try:
            # 查询持仓
            cursor.execute(
                "SELECT shares FROM positions WHERE user_id = ? AND stock_code = ?",
                (user_id, stock_code)
            )
            row = cursor.fetchone()
            
            if not row:
                return {"success": False, "message": "没有该股票持仓"}
            
            current_shares = row[0]
            
            if shares >= current_shares:
                # 全部卖出
                cursor.execute(
                    "DELETE FROM positions WHERE user_id = ? AND stock_code = ?",
                    (user_id, stock_code)
                )
            else:
                # 部分卖出
                cursor.execute(
                    "UPDATE positions SET shares = shares - ?, updated_at = ? WHERE user_id = ? AND stock_code = ?",
                    (shares, datetime.now().isoformat(), user_id, stock_code)
                )
            
            conn.commit()
            return {"success": True, "message": f"已卖出 {shares} 股"}
        except Exception as e:
            return {"success": False, "message": str(e)}
        finally:
            conn.close()
    
    def get_positions(self, user_id: str) -> List[Position]:
        """获取持仓列表"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT stock_code, shares, avg_cost FROM positions WHERE user_id = ? AND shares > 0",
            (user_id,)
        )
        rows = cursor.fetchall()
        conn.close()
        
        return [Position(stock_code=r[0], shares=r[1], avg_cost=r[2]) for r in rows]
    
    def get_position(self, user_id: str, stock_code: str) -> Optional[Position]:
        """获取单只股票持仓"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT shares, avg_cost FROM positions WHERE user_id = ? AND stock_code = ?",
            (user_id, stock_code)
        )
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return Position(stock_code=stock_code, shares=row[0], avg_cost=row[1])
        return None
    
    # ========== 最后分析的股票（用于菜单选项） ==========
    def set_last_analyzed_stock(self, user_id: str, stock_code: str) -> bool:
        """保存用户最后分析的股票"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        try:
            # 使用用户画像表存储最后分析的股票
            cursor.execute(
                """INSERT OR REPLACE INTO user_profiles 
                   (user_id, name, experience, risk_level, style, focus_sectors, updated_at, last_analyzed_stock)
                   SELECT user_id, name, experience, risk_level, style, focus_sectors, ?, ?
                   FROM user_profiles WHERE user_id = ?""",
                (datetime.now().isoformat(), stock_code, user_id)
            )
            conn.commit()
            return True
        except Exception as e:
            print(f"保存最后分析股票失败: {e}")
            return False
        finally:
            conn.close()
    
    def get_last_analyzed_stock(self, user_id: str) -> Optional[str]:
        """获取用户最后分析的股票"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "SELECT last_analyzed_stock FROM user_profiles WHERE user_id = ?",
                (user_id,)
            )
            row = cursor.fetchone()
            if row and row[0]:
                return row[0]
            return None
        except Exception as e:
            print(f"获取最后分析股票失败: {e}")
            return None
        finally:
            conn.close()
