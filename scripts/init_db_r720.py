#!/usr/bin/env python3
"""
StockAI 4.0 数据库初始化
R720 部署版本
"""
import sqlite3
import os

# R720 数据库路径
DB_PATH = "/opt/stockai4.0/data/stockai.db"
STOCK_DB_PATH = "/data/stockai/db/stock.db"

def init_user_database():
    """初始化用户数据库"""
    print(f"初始化用户数据库: {DB_PATH}")
    
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
            last_analyzed_stock TEXT,
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
    
    # 6. 查询历史表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS query_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            stock_code TEXT,
            query_type TEXT DEFAULT 'analysis',
            result_summary TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
        )
    """)
    
    # 创建索引
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_open_id ON users(open_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_status ON users(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_watchlists_user ON watchlists(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_positions_user ON positions(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_query_history_user ON query_history(user_id)")
    
    conn.commit()
    conn.close()
    
    print("✅ 用户数据库初始化完成")


def check_stock_database():
    """检查股票数据库"""
    print(f"\n检查股票数据库: {STOCK_DB_PATH}")
    
    if not os.path.exists(STOCK_DB_PATH):
        print(f"❌ 股票数据库不存在: {STOCK_DB_PATH}")
        print("请从备份恢复:")
        print(f"  cp /data/stock_backup_*.db {STOCK_DB_PATH}")
        return False
    
    size_mb = os.path.getsize(STOCK_DB_PATH) / (1024 * 1024)
    print(f"✅ 股票数据库存在，大小: {size_mb:.1f} MB")
    
    try:
        conn = sqlite3.connect(STOCK_DB_PATH)
        cursor = conn.cursor()
        
        # 检查表
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        print(f"   表: {', '.join(tables[:5])}...")
        
        # 检查数据量
        if 'stock_daily' in tables:
            cursor.execute("SELECT COUNT(*) FROM stock_daily")
            count = cursor.fetchone()[0]
            print(f"   股票日数据: {count:,} 条")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ 检查股票数据库失败: {e}")
        return False


def verify_setup():
    """验证部署"""
    print("\n" + "="*50)
    print("部署验证")
    print("="*50)
    
    # 检查用户数据库
    if os.path.exists(DB_PATH):
        size = os.path.getsize(DB_PATH)
        print(f"✅ 用户数据库: {DB_PATH} ({size} bytes)")
    else:
        print(f"❌ 用户数据库不存在: {DB_PATH}")
    
    # 检查股票数据库
    if os.path.exists(STOCK_DB_PATH):
        size_mb = os.path.getsize(STOCK_DB_PATH) / (1024 * 1024)
        print(f"✅ 股票数据库: {STOCK_DB_PATH} ({size_mb:.1f} MB)")
    else:
        print(f"❌ 股票数据库不存在: {STOCK_DB_PATH}")
    
    print("\n下一步:")
    print("1. 配置 OpenClaw: ~/.openclaw/openclaw.json")
    print("2. 测试: python3 tests/test_basic.py")
    print("3. 部署到 R720")


if __name__ == "__main__":
    print("="*50)
    print("StockAI 4.0 数据库初始化 (R720)")
    print("="*50)
    
    init_user_database()
    check_stock_database()
    verify_setup()
