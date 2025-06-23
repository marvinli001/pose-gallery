from typing import Dict, List, Optional
from ..config import settings
from .ai_analyzer import AIAnalyzer
import json
import logging

logger = logging.getLogger(__name__)

class AISearchService:
    """AI搜索服务"""
    
    def __init__(self):
        self.ai_analyzer = AIAnalyzer()
    
    def optimize_search_query(self, user_query: str) -> Dict:
        """使用AI优化搜索查询"""
        try:
            prompt = self._build_search_optimization_prompt(user_query)
            
            response = self.ai_analyzer.client.chat.completions.create(
                model="gpt-4.1-2025-04-14",  # 使用更快的模型进行搜索优化
                messages=[
                    {"role": "system", "content": "你是一个专业的摄影姿势搜索助手。"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.3
            )
            
            result_text = response.choices[0].message.content
            return self._parse_optimization_result(result_text, user_query)
            
        except Exception as e:
            logger.error(f"AI搜索优化失败: {e}")
            return {
                "optimized_query": user_query,
                "expanded_queries": [user_query],
                "suggestions": [],
                "explanation": "AI搜索暂时不可用，使用原始查询"
            }
    
    def _build_search_optimization_prompt(self, user_query: str) -> str:
        """构建搜索优化提示词"""
        return f"""
请分析并优化以下摄影姿势搜索查询："{user_query}"

请以JSON格式返回优化建议：
{{
    "optimized_query": "优化后的主要搜索词",
    "expanded_queries": ["相关搜索词1", "相关搜索词2", "相关搜索词3"],
    "suggestions": ["建议词1", "建议词2", "建议词3"],
    "explanation": "优化说明"
}}

优化规则：
1. 理解用户意图：是想要特定姿势、场景、风格还是情绪表达？
2. 扩展相关词汇：增加同义词、相关概念、具体场景描述
3. 优化搜索精度：使用更准确的摄影术语
4. 考虑中文语境：理解中文表达习惯和摄影文化

示例：
- "可爱" → "俏皮可爱", ["甜美", "清新", "少女感", "活泼"]
- "拍照姿势" → "写真姿势", ["人像摄影", "摆拍技巧", "镜头感"]
- "咖啡厅" → "咖啡厅拍照", ["室内拍摄", "文艺范", "日系风格"]

请确保返回有效的JSON格式。
"""
    
    def _parse_optimization_result(self, result_text: str, original_query: str) -> Dict:
        """解析AI优化结果"""
        try:
            # 尝试解析JSON
            if "```json" in result_text:
                json_start = result_text.find("```json") + 7
                json_end = result_text.find("```", json_start)
                result_text = result_text[json_start:json_end].strip()
            elif "```" in result_text:
                json_start = result_text.find("```") + 3
                json_end = result_text.rfind("```")
                result_text = result_text[json_start:json_end].strip()
            
            result = json.loads(result_text)
            
            # 验证必要字段
            if not result.get("optimized_query"):
                result["optimized_query"] = original_query
            
            if not result.get("expanded_queries"):
                result["expanded_queries"] = [result["optimized_query"]]
            
            if not result.get("suggestions"):
                result["suggestions"] = []
                
            return result
            
        except Exception as e:
            logger.error(f"解析AI优化结果失败: {e}")
            return {
                "optimized_query": original_query,
                "expanded_queries": [original_query],
                "suggestions": [],
                "explanation": "AI解析失败，使用原始查询"
            }