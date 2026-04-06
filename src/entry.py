#!/usr/bin/env python3
"""
StockAI 4.0 - 统一 Main Agent 入口
被 OpenClaw Gateway 调用
"""
import sys
import os

# 添加项目路径
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from src.router import MessageRouter, Message

# 全局路由器实例（单例）
_router = None

def _get_router():
    global _router
    if _router is None:
        _router = MessageRouter()
    return _router

def on_message(payload: dict) -> str:
    """
    OpenClaw Gateway 消息入口
    
    Args:
        payload: {
            "sender_id": str,      # open_id (必需)
            "content": str,        # 消息内容 (必需)
            "msg_type": str,       # 消息类型 (必需)
            "timestamp": str,      # 时间戳 (可选)
            "channel": str,        # 渠道 (可选)
            "account_id": str      # 账号 (可选)
        }
    
    Returns:
        回复文本
    """
    try:
        # 构造消息对象
        message = Message(
            sender_id=payload.get("sender_id", ""),
            content=payload.get("content", "").strip(),
            msg_type=payload.get("msg_type", "text"),
            timestamp=payload.get("timestamp")
        )
        
        # 路由处理
        router = _get_router()
        response = router.handle_message(message)
        
        return response
        
    except Exception as e:
        # 捕获所有异常，返回友好错误
        return f"系统处理出错，请稍后重试。错误: {str(e)[:50]}"


# 兼容旧版调用
def handle_wechat_message(user_id: str, message: str) -> str:
    """兼容旧版接口"""
    return on_message({
        "sender_id": user_id,
        "content": message,
        "msg_type": "text"
    })


if __name__ == "__main__":
    # 测试
    test_payload = {
        "sender_id": "ou_test_user",
        "content": "帮助",
        "msg_type": "text"
    }
    print(on_message(test_payload))
