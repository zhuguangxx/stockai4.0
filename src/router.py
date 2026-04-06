#!/usr/bin/env python3
"""
StockAI 4.0 - 消息路由器
统一 Main Agent 核心 - 修复版
修复内容：
1. 完善 _normalize_stock_code 支持北京交易所
2. 集成 SubAgentDispatcher
3. 添加深度研究功能
"""
import re
from typing import Dict, Any, Optional
from dataclasses import dataclass

from src.services.identity import IdentityService
from src.services.onboarding import OnboardingService
from src.services.user_memory import UserMemoryService
from src.services.stock_analysis import StockAnalysisService
from src.services.subagent_dispatcher import SubAgentDispatcher
from src.services.indicator_detail import IndicatorDetailService  # 新增：指标详情


@dataclass
class UserContext:
    """用户上下文"""
    user_id: str
    open_id: str
    name: str
    status: str
    profile: Optional[Dict] = None


@dataclass
class Message:
    """消息对象"""
    sender_id: str
    content: str
    msg_type: str
    timestamp: Optional[str] = None


class MessageRouter:
    """消息路由器"""
    
    def __init__(self):
        self.identity = IdentityService()
        self.onboarding = OnboardingService()
        self.user_memory = UserMemoryService()
        self.stock_analyzer = StockAnalysisService()
        self.subagent_dispatcher = SubAgentDispatcher()
        self.indicator_detail = IndicatorDetailService()  # 新增：指标详情服务
    
    def handle_message(self, message: Message) -> str:
        """主处理入口"""
        if not message.sender_id:
            return "系统错误：无法识别用户"
        
        if not message.content:
            return "请输入内容"
        
        try:
            user = self._identify_user(message.sender_id)
            self.identity.update_last_active(user.open_id)
            
            if user.status == "new":
                return self._handle_new_user(user)
            elif user.status == "onboarding":
                return self._handle_onboarding(user, message)
            elif user.status == "active":
                return self._handle_active_user(user, message)
            elif user.status == "inactive":
                self.identity.update_user_status(user.open_id, "active")
                return self._handle_active_user(user, message)
            else:
                return f"用户状态异常: {user.status}"
                
        except Exception as e:
            return f"处理出错: {str(e)[:100]}"
    
    def _identify_user(self, open_id: str) -> UserContext:
        """识别用户"""
        user_data = self.identity.get_or_create_user(open_id)
        
        return UserContext(
            user_id=user_data["user_id"],
            open_id=user_data["open_id"],
            name=user_data.get("name", "用户"),
            status=user_data["status"]
        )
    
    def _handle_new_user(self, user: UserContext) -> str:
        """处理新用户"""
        self.identity.update_user_status(user.open_id, "onboarding")
        question = self.onboarding.get_current_question(user.open_id)
        
        if question:
            return question["question"]
        else:
            return "欢迎！请稍后再试。"
    
    def _handle_onboarding(self, user: UserContext, message: Message) -> str:
        """处理问卷中用户"""
        result = self.onboarding.process_answer(user.open_id, message.content)
        
        if result["completed"]:
            self._complete_onboarding(user.open_id)
            return "问卷完成！欢迎加入 StockAI。\n\n发送帮助查看指令。"
        
        return result.get("next_question", "请继续回答问题。")
    
    def _complete_onboarding(self, open_id: str):
        """完成问卷处理"""
        user_data = self.identity.get_user_by_open_id(open_id)
        if not user_data:
            return
        
        user_id = user_data["user_id"]
        answers = self.onboarding.get_answers(open_id)
        
        if answers:
            self.user_memory.save_profile(user_id, {
                "name": answers.get("name", "用户"),
                "experience": answers.get("experience", "intermediate"),
                "risk_level": answers.get("risk_level", "moderate"),
                "style": answers.get("style", "value"),
                "focus_sectors": answers.get("focus_sectors", [])
            })
            
            watchlist_str = answers.get("watchlist", "")
            if watchlist_str:
                codes = [c.strip() for c in watchlist_str.split(",") if c.strip()]
                for code in codes:
                    if self._is_stock_code(code):
                        self.user_memory.add_watchlist(user_id, code.upper())
        
        self.identity.update_user_status(open_id, "active")
    
    def _handle_active_user(self, user: UserContext, message: Message) -> str:
        """处理活跃用户"""
        content = message.content.strip()
        content_lower = content.lower()
        
        # 帮助指令
        if content_lower in ["帮助", "help", "?", "菜单", "menu"]:
            return self._get_help_message()
        
        # 股票代码分析
        if self._is_stock_code(content):
            return self._analyze_stock(user.user_id, content)
        
        # 自选股管理
        if content_lower == "自选" or content_lower == "watchlist":
            return self._get_watchlist(user.user_id)
        
        if content_lower.startswith("添加 "):
            code = content[3:].strip()
            return self._add_watchlist(user.user_id, code)
        
        if content_lower.startswith("删除 "):
            code = content[3:].strip()
            return self._remove_watchlist(user.user_id, code)
        
        # 持仓管理
        if content_lower == "持仓" or content_lower == "position":
            return self._get_positions(user.user_id)
        
        # 深度研究（调用 Sub-Agent）
        if content_lower.startswith("深度") or content_lower.startswith("研究"):
            stock_code = content[2:].strip() if len(content) > 2 else ""
            if self._is_stock_code(stock_code):
                return self._deep_research(user.user_id, stock_code)
        
        # 指标详情（菜单选项1）
        if content_lower == "1" or content_lower == "指标":
            # 获取用户最近分析的股票
            last_stock = self.user_memory.get_last_analyzed_stock(user.user_id)
            if last_stock:
                return self._show_indicator_detail(user.user_id, last_stock)
            else:
                return "请先发送股票代码进行分析，再查看指标详情。"
        
        # 回测（菜单选项2）
        if content_lower == "2" or content_lower.startswith("回测"):
            return self._handle_backtest_request(user.user_id, content)
        
        # 专家观点（菜单选项3）
        if content_lower == "3" or content_lower == "专家":
            last_stock = self.user_memory.get_last_analyzed_stock(user.user_id)
            if last_stock:
                return self._show_expert_views(user.user_id, last_stock)
            else:
                return "请先发送股票代码进行分析，再查看专家观点。"
        
        # 画像
        if content_lower in ["画像", "profile", "我的画像"]:
            return self._get_profile(user.user_id)
        
        # 默认回复
        return f"收到: {content[:20]}...\n\n发送帮助查看支持的指令。"
    
    def _is_stock_code(self, text: str) -> bool:
        """检查是否为股票代码"""
        text = text.strip().upper()
        # 完整格式: 000001.SZ / 600519.SH / 430047.BJ
        if re.match(r'^\d{6}\.(SZ|SH|BJ)$', text):
            return True
        # 纯数字: 000001 / 600519 / 430047
        if re.match(r'^\d{6}$', text):
            return True
        return False
    
    def _normalize_stock_code(self, code: str) -> str:
        """标准化股票代码（自动识别交易所）- 修复版支持北京交易所"""
        code = code.strip().upper()
        if "." in code:
            return code
        
        # 上海: 600/601/603/605/688(科创)
        if code.startswith("6"):
            return code + ".SH"
        # 深圳: 000/001/002/003/300/301
        elif code.startswith("0") or code.startswith("3"):
            return code + ".SZ"
        # 北京: 430/831/832/833/834/835/836/837/838/839
        elif code.startswith("4") or code.startswith("8"):
            return code + ".BJ"
        else:
            return code + ".SZ"
    
    def _analyze_stock(self, user_id: str, stock_code: str) -> str:
        """分析股票 - 修复版使用标准化代码，并保存分析记录"""
        # 标准化代码（支持北京交易所）
        stock_code = self._normalize_stock_code(stock_code)
        
        # 保存最后分析的股票（用于菜单选项）
        self.user_memory.set_last_analyzed_stock(user_id, stock_code)
        
        profile = self.user_memory.get_profile(user_id)
        risk_level = profile.risk_level if profile else "moderate"
        
        try:
            result = self.stock_analyzer.analyze(stock_code, risk_level=risk_level)
            
            # 添加菜单提示
            report = result.report if hasattr(result, 'report') else str(result)
            menu_hint = "\n\n━━━━━━━━━━━━━━━━━━━━━━\n📋 快捷操作:\n【1】六大指标详情 【2】回测 【3】专家观点\n━━━━━━━━━━━━━━━━━━━━━━"
            
            return report + menu_hint
        except Exception as e:
            return f"分析 {stock_code} 失败: {str(e)[:50]}"
    
    def _deep_research(self, user_id: str, stock_code: str) -> str:
        """深度研究 - 调用 Sub-Agent 使用 sessions_spawn"""
        stock_code = self._normalize_stock_code(stock_code)
        profile = self.user_memory.get_profile(user_id)
        
        user_context = {
            "risk_level": profile.risk_level if profile else "moderate",
            "style": profile.style if profile else "value",
            "experience": profile.experience if profile else "intermediate"
        }
        
        return self.subagent_dispatcher.deep_research(stock_code, user_context)
    
    def _show_indicator_detail(self, user_id: str, stock_code: str) -> str:
        """显示六大指标详情 - 菜单选项1"""
        stock_code = self._normalize_stock_code(stock_code)
        result = self.indicator_detail.get_indicator_detail(stock_code)
        
        if result.success:
            return result.report
        else:
            return f"❌ 获取指标详情失败: {result.error}"
    
    def _handle_backtest_request(self, user_id: str, content: str) -> str:
        """处理回测请求 - 菜单选项2"""
        # 解析回测指令
        # 格式: "回测 600519 2024-01-01 2024-12-31" 或 "2"
        if content.strip() == "2":
            # 获取用户最近分析的股票
            last_stock = self.user_memory.get_last_analyzed_stock(user_id)
            if last_stock:
                return self._run_backtest(user_id, last_stock, "2024-01-01", "2024-12-31")
            else:
                return "请先发送股票代码进行分析，或输入：回测 600519 2024-01-01 2024-12-31"
        
        # 解析完整指令
        parts = content.split()
        if len(parts) >= 2:
            stock_code = parts[1]
            start_date = parts[2] if len(parts) > 2 else "2024-01-01"
            end_date = parts[3] if len(parts) > 3 else "2024-12-31"
            
            if self._is_stock_code(stock_code):
                return self._run_backtest(user_id, stock_code, start_date, end_date)
        
        return "回测格式错误。请使用：回测 600519 2024-01-01 2024-12-31"
    
    def _run_backtest(self, user_id: str, stock_code: str, start_date: str, end_date: str) -> str:
        """执行回测"""
        try:
            from backtest.engine import BacktestEngine
            from backtest.report import BacktestReport
            
            stock_code = self._normalize_stock_code(stock_code)
            
            # 创建回测引擎
            engine = BacktestEngine(
                initial_capital=100000,
                commission_rate=0.0003
            )
            
            # 使用MACD策略进行回测
            from strategies.macd_strategy import MACDStrategy
            strategy = MACDStrategy()
            
            # 运行回测
            result = engine.run(
                stock_code=stock_code,
                strategy=strategy,
                start_date=start_date,
                end_date=end_date
            )
            
            # 生成报告
            reporter = BacktestReport(result)
            return reporter.generate_text_report()
            
        except ImportError as e:
            return f"⚠️ 回测模块加载失败: {str(e)}\n\n请确保策略文件存在: strategies/macd_strategy.py"
        except Exception as e:
            return f"❌ 回测执行失败: {str(e)[:100]}"
    
    def _show_expert_views(self, user_id: str, stock_code: str) -> str:
        """显示专家观点 - 菜单选项3"""
        stock_code = self._normalize_stock_code(stock_code)
        
        try:
            # 获取股票数据
            from core.data_access import DataAccess
            data_access = DataAccess()
            df = data_access.get_stock_data(stock_code, days=60)
            
            if df is None or df.empty:
                return f"无法获取 {stock_code} 的数据"
            
            # 调用六大专家
            from core.experts import ExpertSystem
            expert = ExpertSystem(df)
            results = expert.analyze_all()
            
            # 生成专家观点对比报告
            report = f"⚔️ {stock_code} 六大专家观点对比\n"
            report += "━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            
            # 统计多空观点
            bullish_experts = []
            bearish_experts = []
            neutral_experts = []
            
            for name, result in results.items():
                result_str = str(result).lower()
                if '金叉' in result_str or '买入' in result_str or '看涨' in result_str or '看多' in result_str:
                    bullish_experts.append(name)
                elif '死叉' in result_str or '卖出' in result_str or '看跌' in result_str or '看空' in result_str:
                    bearish_experts.append(name)
                else:
                    neutral_experts.append(name)
            
            # 显示阵营
            report += "📊 专家阵营\n"
            report += "-" * 30 + "\n"
            report += f"🟢 看多: {', '.join(bullish_experts) if bullish_experts else '无'} ({len(bullish_experts)}/6)\n"
            report += f"🔴 看空: {', '.join(bearish_experts) if bearish_experts else '无'} ({len(bearish_experts)}/6)\n"
            report += f"⚪ 中性: {', '.join(neutral_experts) if neutral_experts else '无'} ({len(neutral_experts)}/6)\n"
            
            report += "\n📋 详细观点\n"
            report += "-" * 30 + "\n"
            for name, result in results.items():
                report += f"\n{name}:\n{result}\n"
            
            # 总结
            report += "\n💡 专家共识\n"
            report += "-" * 30 + "\n"
            if len(bullish_experts) > len(bearish_experts) and len(bullish_experts) >= 3:
                report += "多数专家（≥3位）看多，市场偏多。\n"
            elif len(bearish_experts) > len(bullish_experts) and len(bearish_experts) >= 3:
                report += "多数专家（≥3位）看空，建议谨慎。\n"
            else:
                report += "专家观点分歧较大，建议观望或结合基本面分析。\n"
            
            report += "\n⚠️ 免责声明：专家观点仅供参考，不构成投资建议。"
            
            return report
            
        except Exception as e:
            return f"❌ 获取专家观点失败: {str(e)[:100]}"
    
    def _get_watchlist(self, user_id: str) -> str:
        """获取自选股"""
        stocks = self.user_memory.get_watchlist(user_id)
        if not stocks:
            return "自选股为空\n\n发送添加 000001.SZ 添加股票"
        
        result = "我的自选股：\n\n"
        for stock in stocks:
            result += f"• {stock}\n"
        return result
    
    def _add_watchlist(self, user_id: str, stock_code: str) -> str:
        """添加自选 - 修复版使用标准化代码"""
        if not self._is_stock_code(stock_code):
            return "股票代码格式错误，应为 000001.SZ 或 600519.SH"
        
        stock_code = self._normalize_stock_code(stock_code)
        success = self.user_memory.add_watchlist(user_id, stock_code)
        
        if success:
            return f"已添加 {stock_code} 到自选股"
        else:
            return f"{stock_code} 已在自选股"
    
    def _remove_watchlist(self, user_id: str, stock_code: str) -> str:
        """删除自选"""
        stock_code = stock_code.upper()
        self.user_memory.remove_watchlist(user_id, stock_code)
        return f"已从自选股删除 {stock_code}"
    
    def _get_positions(self, user_id: str) -> str:
        """获取持仓"""
        positions = self.user_memory.get_positions(user_id)
        if not positions:
            return "当前无持仓"
        
        result = "我的持仓：\n\n"
        for pos in positions:
            result += f"• {pos.stock_code}: {pos.shares}股 @ {pos.avg_cost:.2f}元\n"
        return result
    
    def _get_profile(self, user_id: str) -> str:
        """获取画像"""
        profile = self.user_memory.get_profile(user_id)
        if not profile:
            return "暂无投资画像"
        
        return f"""我的投资画像

名称: {profile.name}
经验: {profile.experience}
风险偏好: {profile.risk_level}
投资风格: {profile.style}
关注行业: {', '.join(profile.focus_sectors) if profile.focus_sectors else '未设置'}"""
    
    def _get_help_message(self) -> str:
        """帮助信息 - 包含菜单选项"""
        return """StockAI 指令列表

【股票分析】
直接发送股票代码，如: 000001 或 600519.SH

【深度研究】
发送"深度 000001"调用AI深度分析（使用 Sub-Agent）

【六大指标详情 - 菜单选项1】
回复数字 1 或发送"指标"查看最近分析股票的指标详情

【回测功能 - 菜单选项2】
回复数字 2 或发送"回测 600519 2024-01-01 2024-12-31"

【专家观点 - 菜单选项3】
回复数字 3 或发送"专家"查看六大专家观点对比

【自选股管理】
- 自选 - 查看自选股
- 添加 000001.SZ - 添加自选
- 删除 000001.SZ - 删除自选

【持仓管理】
- 持仓 - 查看持仓

【个人信息】
- 画像 - 查看投资画像
- 帮助 - 显示本菜单"""
