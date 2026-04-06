#!/usr/bin/env python3
"""
测试脚本
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.entry import on_message

def test_new_user():
    """测试新用户"""
    print("=== 测试1: 新用户 ===")
    
    # 首条消息
    msg = {"sender_id": "test_new_001", "content": "你好", "msg_type": "text"}
    result = on_message(msg)
    print(f"首条消息响应: {result[:50]}...")
    assert "欢迎" in result, "应返回欢迎语"
    
    # 回答名字
    msg = {"sender_id": "test_new_001", "content": "张三", "msg_type": "text"}
    result = on_message(msg)
    print(f"回答名字响应: {result[:50]}...")
    assert "股票" in result, "应返回股票问题"
    
    print("✅ 新用户测试通过\n")

def test_help():
    """测试帮助"""
    print("=== 测试2: 帮助指令 ===")
    
    # 先模拟完成问卷
    from src.services.identity import IdentityService
    from src.services.onboarding import OnboardingService
    from src.services.user_memory import UserMemoryService
    
    identity = IdentityService()
    onboarding = OnboardingService()
    user_memory = UserMemoryService()
    
    open_id = "test_active_001"
    user = identity.get_or_create_user(open_id)
    user_id = user["user_id"]
    
    # 完成问卷
    answers = ["李四", "000001.SZ", "1", "2", "1", "1,2"]
    for ans in answers:
        onboarding.process_answer(open_id, ans)
    
    # 激活用户
    identity.update_user_status(open_id, "active")
    user_memory.save_profile(user_id, {
        "name": "李四",
        "experience": "intermediate",
        "risk_level": "moderate",
        "style": "value",
        "focus_sectors": ["tech", "finance"]
    })
    
    # 测试帮助
    msg = {"sender_id": open_id, "content": "帮助", "msg_type": "text"}
    result = on_message(msg)
    print(f"帮助响应: {result[:80]}...")
    assert "指令" in result, "应返回指令列表"
    
    print("✅ 帮助测试通过\n")

def test_stock_analysis():
    """测试股票分析"""
    print("=== 测试3: 股票分析 ===")
    
    msg = {"sender_id": "test_active_001", "content": "000001", "msg_type": "text"}
    result = on_message(msg)
    print(f"股票分析响应长度: {len(result)} 字符")
    assert len(result) > 100, "应返回分析报告"
    
    print("✅ 股票分析测试通过\n")

def test_watchlist():
    """测试自选股"""
    print("=== 测试4: 自选股 ===")
    
    # 添加自选
    msg = {"sender_id": "test_active_001", "content": "添加 600519.SH", "msg_type": "text"}
    result = on_message(msg)
    print(f"添加自选响应: {result}")
    assert "已添加" in result or "已在" in result
    
    # 查看自选
    msg = {"sender_id": "test_active_001", "content": "自选", "msg_type": "text"}
    result = on_message(msg)
    print(f"查看自选响应: {result[:80]}...")
    assert "自选股" in result
    
    print("✅ 自选股测试通过\n")

if __name__ == "__main__":
    print("=" * 50)
    print("StockAI 4.0 功能测试")
    print("=" * 50 + "\n")
    
    try:
        test_new_user()
        test_help()
        test_stock_analysis()
        test_watchlist()
        
        print("=" * 50)
        print("✅ 所有测试通过")
        print("=" * 50)
    except AssertionError as e:
        print(f"❌ 测试失败: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 测试出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
