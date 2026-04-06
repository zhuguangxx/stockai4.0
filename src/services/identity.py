#!/usr/bin/env python3
"""
身份识别服务
"""
import sqlite3
import uuid
import hashlib
from datetime import datetime
from typing import Optional, Dict, Any

DB_PATH = "/opt/stockai4.0/data/stockai.db"


class IdentityService:
    """身份识别服务"""
    
    def _get_conn(self):
        """获取数据库连接"""
        return sqlite3.connect(DB_PATH)
    
    def _generate_user_id(self, open_id: str) -> str:
        """根据 open_id 生成 user_id"""
        # 使用 MD5 前8位作为后缀，保证同一 open_id 始终生成同一 user_id
        hash_suffix = hashlib.md5(open_id.encode()).hexdigest()[:8]
        return f"user_{hash_suffix}"
    
    def get_or_create_user(self, open_id: str) -> Dict[str, Any]:
        """获取或创建用户"""
        # 先查询
        user = self.get_user_by_open_id(open_id)
        if user:
            return user
        
        # 创建新用户
        return self.create_user(open_id)
    
    def get_user_by_open_id(self, open_id: str) -> Optional[Dict]:
        """通过 open_id 查询用户"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT user_id, open_id, name, status, created_at, last_active FROM users WHERE open_id = ?",
            (open_id,)
        )
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                "user_id": row[0],
                "open_id": row[1],
                "name": row[2],
                "status": row[3],
                "created_at": row[4],
                "last_active": row[5]
            }
        return None
    
    def create_user(self, open_id: str) -> Dict:
        """创建新用户"""
        user_id = self._generate_user_id(open_id)
        now = datetime.now().isoformat()
        
        conn = self._get_conn()
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "INSERT INTO users (user_id, open_id, status, created_at) VALUES (?, ?, ?, ?)",
                (user_id, open_id, "new", now)
            )
            conn.commit()
        except sqlite3.IntegrityError:
            # 已存在（并发情况）
            pass
        finally:
            conn.close()
        
        return {
            "user_id": user_id,
            "open_id": open_id,
            "name": "用户",
            "status": "new",
            "created_at": now,
            "last_active": None
        }
    
    def update_user_status(self, open_id: str, status: str) -> bool:
        """更新用户状态"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE users SET status = ? WHERE open_id = ?",
            (status, open_id)
        )
        conn.commit()
        updated = cursor.rowcount > 0
        conn.close()
        
        return updated
    
    def update_last_active(self, open_id: str) -> bool:
        """更新最后活跃时间"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        now = datetime.now().isoformat()
        cursor.execute(
            "UPDATE users SET last_active = ? WHERE open_id = ?",
            (now, open_id)
        )
        conn.commit()
        updated = cursor.rowcount > 0
        conn.close()
        
        return updated
