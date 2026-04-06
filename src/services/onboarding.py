#!/usr/bin/env python3
"""
问卷服务
"""
import sqlite3
import json
from datetime import datetime
from typing import Dict, Any, Optional

DB_PATH = "/opt/stockai4.0/data/stockai.db"


class OnboardingService:
    """问卷服务"""
    
    # 6个问题定义
    QUESTIONS = [
        {
            "id": 1,
            "key": "name",
            "question": "👋 欢迎！请问怎么称呼您？",
            "type": "text"
        },
        {
            "id": 2,
            "key": "watchlist",
            "question": "📈 您关注哪些股票？（请输入股票代码，用逗号分隔，可跳过直接回车）",
            "type": "text"
        },
        {
            "id": 3,
            "key": "experience",
            "question": """🎯 您的投资经验如何？

1. 新手 - 刚开始接触股票
2. 初级 - 有1-2年经验
3. 中级 - 有3-5年经验
4. 资深 - 5年以上经验

请回复数字 1-4""",
            "type": "choice",
            "options": ["newbie", "junior", "intermediate", "expert"]
        },
        {
            "id": 4,
            "key": "risk_level",
            "question": """⚖️ 您的风险承受能力？

1. 保守型 - 优先保本，接受低收益
2. 稳健型 - 平衡风险与收益
3. 积极型 - 愿意承担较高风险
4. 激进型 - 追求高收益，能承受大波动

请回复数字 1-4""",
            "type": "choice",
            "options": ["conservative", "moderate", "aggressive", "radical"]
        },
        {
            "id": 5,
            "key": "style",
            "question": """🔄 您的投资风格？

1. 价值投资 - 长期持有优质股
2. 成长投资 - 寻找高增长潜力股
3. 股息投资 - 偏好高分红股票
4. 波段操作 - 中短线交易
5. 短线交易 - 日内或超短线

请回复数字 1-5""",
            "type": "choice",
            "options": ["value", "growth", "dividend", "swing", "daytrade"]
        },
        {
            "id": 6,
            "key": "focus_sectors",
            "question": """🏭 您关注的行业板块？（可多选，用逗号分隔）

1. 科技（AI、芯片、软件）
2. 金融（银行、保险、证券）
3. 医药（生物医药、医疗器械）
4. 新能源（光伏、锂电、储能）
5. 消费（白酒、家电、零售）
6. 制造（汽车、机械、军工）

请回复数字，如：1,3,5""",
            "type": "multi_choice",
            "options": ["tech", "finance", "healthcare", "energy", "consumer", "manufacturing"]
        }
    ]
    
    def _get_conn(self):
        return sqlite3.connect(DB_PATH)
    
    def get_current_question(self, open_id: str) -> Optional[Dict]:
        """获取当前问题"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        # 查询进度
        cursor.execute(
            "SELECT current_question, status FROM onboarding_progress WHERE open_id = ?",
            (open_id,)
        )
        row = cursor.fetchone()
        
        if row is None:
            # 初始化进度
            cursor.execute(
                "INSERT INTO onboarding_progress (open_id, current_question, answers, status) VALUES (?, 0, ?, ?)",
                (open_id, json.dumps({}), "in_progress")
            )
            conn.commit()
            current_q = 0
        else:
            current_q = row[0]
            if row[1] == "completed":
                conn.close()
                return None
        
        conn.close()
        
        if current_q < len(self.QUESTIONS):
            return self.QUESTIONS[current_q]
        return None
    
    def process_answer(self, open_id: str, answer: str) -> Dict[str, Any]:
        """处理答案"""
        conn = self._get_conn()
        cursor = conn.cursor()
        
        # 获取当前进度
        cursor.execute(
            "SELECT current_question, answers FROM onboarding_progress WHERE open_id = ?",
            (open_id,)
        )
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            return {"success": False, "message": "未开始问卷", "completed": False}
        
        current_q, answers_json = row
        answers = json.loads(answers_json) if answers_json else {}
        
        if current_q >= len(self.QUESTIONS):
            conn.close()
            return {"success": True, "completed": True, "message": "已完成"}
        
        question = self.QUESTIONS[current_q]
        key = question["key"]
        
        # 验证和转换答案
        validated_answer = self._validate_answer(answer, question)
        if validated_answer is None:
            conn.close()
            return {
                "success": False,
                "message": f"答案格式错误，请按提示回复",
                "completed": False,
                "next_question": question["question"]
            }
        
        # 保存答案
        answers[key] = validated_answer
        next_q = current_q + 1
        
        # 检查是否完成
        if next_q >= len(self.QUESTIONS):
            # 完成
            cursor.execute(
                "UPDATE onboarding_progress SET current_question = ?, answers = ?, status = ?, complete_time = ? WHERE open_id = ?",
                (next_q, json.dumps(answers), "completed", datetime.now().isoformat(), open_id)
            )
            conn.commit()
            conn.close()
            
            return {
                "success": True,
                "completed": True,
                "message": "问卷完成",
                "answers": answers
            }
        else:
            # 继续下一题
            cursor.execute(
                "UPDATE onboarding_progress SET current_question = ?, answers = ? WHERE open_id = ?",
                (next_q, json.dumps(answers), open_id)
            )
            conn.commit()
            conn.close()
            
            return {
                "success": True,
                "completed": False,
                "next_question": self.QUESTIONS[next_q]["question"],
                "progress": f"{next_q}/{len(self.QUESTIONS)}"
            }
    
    def _validate_answer(self, answer: str, question: Dict) -> Any:
        """验证和转换答案"""
        q_type = question["type"]
        answer = answer.strip()
        
        if q_type == "text":
            # 文本类型，直接返回
            return answer if answer else ""
        
        elif q_type == "choice":
            # 单选，验证数字
            try:
                choice_idx = int(answer) - 1
                options = question["options"]
                if 0 <= choice_idx < len(options):
                    return options[choice_idx]
            except ValueError:
                pass
            return None
        
        elif q_type == "multi_choice":
            # 多选，验证多个数字
            try:
                indices = [int(x.strip()) - 1 for x in answer.split(",")]
                options = question["options"]
                selected = []
                for idx in indices:
                    if 0 <= idx < len(options):
                        selected.append(options[idx])
                return selected if selected else []
            except ValueError:
                pass
            return []
        
        return answer
    
    def is_completed(self, open_id: str) -> bool:
        """检查是否完成"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT status FROM onboarding_progress WHERE open_id = ?",
            (open_id,)
        )
        row = cursor.fetchone()
        conn.close()
        return row is not None and row[0] == "completed"
    
    def get_answers(self, open_id: str) -> Optional[Dict]:
        """获取所有答案"""
        conn = self._get_conn()
        cursor = conn.cursor()
        cursor.execute(
            "SELECT answers FROM onboarding_progress WHERE open_id = ? AND status = ?",
            (open_id, "completed")
        )
        row = cursor.fetchone()
        conn.close()
        
        if row and row[0]:
            return json.loads(row[0])
        return None
