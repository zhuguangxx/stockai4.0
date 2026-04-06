# StockAI 4.0

统一 Main Agent 架构的股票分析助手。

## 架构特点

- **单一 Main Agent**: 所有微信绑定到 Main，无需动态创建 Client Agent
- **静态配置**: openclaw.json 永不修改，无需 Gateway reload
- **用户识别**: open_id + 数据库上下文隔离
- **复杂计算**: sessions_spawn Sub-Agent（临时，无绑定）

## 快速开始

```bash
# 1. 初始化数据库
python3 scripts/init_db.py

# 2. 运行测试
python3 tests/test_basic.py

# 3. 配置 OpenClaw (openclaw.json)
{
  "agents": {
    "list": [
      { "id": "main", "workspace": "...", "default": true }
    ]
  },
  "bindings": [
    { "agentId": "main", "match": { "channel": "openclaw-weixin" } }
  ]
}

# 4. 入口函数
from src.entry import on_message
```

## 项目结构

```
004-stockai4.0/
├── docs/                       # 设计文档
│   ├── architecture-v2.md      # 架构设计
│   ├── database-v2.md          # 数据库设计
│   ├── interface-design.md     # 接口设计
│   └── VALIDATION_SUMMARY_v2.md
├── src/                        # 源码
│   ├── entry.py                # 入口
│   ├── router.py               # 路由器
│   └── services/               # 服务层
│       ├── identity.py
│       ├── onboarding.py
│       ├── user_memory.py
│       └── stock_analysis.py
├── scripts/
│   └── init_db.py              # 数据库初始化
├── tests/
│   └── test_basic.py           # 基础测试
└── README.md
```

## 设计文档

- [架构设计](docs/architecture-v2.md)
- [数据库设计](docs/database-v2.md)
- [接口设计](docs/interface-design.md)

## 与 003 的核心差异

| 维度 | 003 (Multi-Agent) | 004 (Unified Main) |
|------|------------------|-------------------|
| Agent 数量 | 1 Main + N Client | 仅 1 Main |
| 微信绑定 | 每个用户绑定 Client | 统一绑定 Main |
| 配置稳定性 | 动态修改，频繁 reload | 静态，永不 reload |
| 数据库表 | 12 张 | 5 张 |
| 用户隔离 | 进程级 | 逻辑级（上下文） |

## License

MIT
