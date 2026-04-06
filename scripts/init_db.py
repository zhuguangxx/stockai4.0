#!/usr/bin/env python3
"""
数据库初始化脚本
"""
import sqlite3
import os

DB_PATH = "/opt/stockai4.0/data/stockai.db"

def init_database():
    """初始化数据库"""
    # 确保目录存在
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 1. 用户主表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            open_id TEXT UNIQUE NOT NULL,
            name TEXT DEFAULT '用户',
            status TEXT DEFAULT 'new',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_active TIMESTAMP,
            CHECK (status IN ('new', 'onboarding', 'active', 'inactive'))
        )
    """)
    
    # 2. 问卷进度表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS onboarding_progress (
            open_id TEXT PRIMARY KEY,
            current_question INTEGER DEFAULT 0,
            answers TEXT,
            status TEXT DEFAULT 'in_progress',
            start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            complete_time TIMESTAMP,
            CHECK (current_question BETWEEN 0 AND 6),
            CHECK (status IN ('in_progress', 'completed'))
        )
    """)
    
    # 3. 用户画像表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_profiles (
            user_id TEXT PRIMARY KEY,
            name TEXT DEFAULT '用户',
            experience TEXT,
            risk_level TEXT,
            style TEXT,
            focus_sectors TEXT,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CHECK (experience IN ('newbie', 'junior', 'intermediate', 'expert')),
            CHECK (risk_level IN ('conservative', 'moderate', 'aggressive', 'radical')),
            CHECK (style IN ('value', 'growth', 'dividend', 'swing', 'daytrade')),
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
        )
    """)
    
    # 4. 自选股表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS watchlists (
            user_id TEXT,
            stock_code TEXT,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, stock_code),
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
        )
    """)
    
    # 5. 持仓表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS positions (
            user_id TEXT,
            stock_code TEXT,
            shares REAL DEFAULT 0,
            avg_cost REAL DEFAULT 0,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (user_id, stock_code),
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
            CHECK (shares >= 0),
            CHECK (avg_cost >= 0)
        )
    """)
    
    # 创建索引
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_open_id ON users(open_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_status ON users(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_watchlists_user ON watchlists(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_positions_user ON positions(user_id)")
    
    conn.commit()
    conn.close()
    
    print(f"✅ 数据库初始化完成: {DB_PATH}")

if __name__ == "__main__":
    init_database()
