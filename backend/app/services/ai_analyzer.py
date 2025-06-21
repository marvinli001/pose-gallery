import openai
from openai import OpenAI
import json
import logging
from typing import Dict, List, Optional
from ..config import settings
import time
import re
import requests
from PIL import Image
import io

logger = logging.getLogger(__name__)

class AIAnalyzer:
    """AI图片分析服务"""
    
    def __init__(self):
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.model = settings.openai_model
        self.max_tokens = settings.openai_max_tokens
        self.temperature = settings.openai_temperature
    
    def analyze_pose_image(self, image_url: str, retry_count: int = 0) -> Optional[Dict]:
        """分析姿势图片"""
        try:
            # 验证图片URL可访问性
            if not self._validate_image_url(image_url):
                logger.error(f"图片URL不可访问: {image_url}")
                return None
            
            prompt = self._build_analysis_prompt()
            
            logger.info(f"开始AI分析图片: {image_url}")
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": image_url,
                                    "detail": "high"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            
            result_text = response.choices[0].message.content
            analysis = self._parse_analysis_result(result_text)
            
            if analysis:
                logger.info(f"AI分析成功: {analysis.get('title', 'Unknown')}")
                return analysis
            else:
                logger.error(f"AI分析结果解析失败")
                return None
                
        except Exception as e:
            logger.error(f"AI分析失败 {image_url}: {e}")
            
            # 重试机制
            if retry_count < settings.max_retries:
                logger.info(f"开始第 {retry_count + 1} 次重试...")
                time.sleep(settings.processing_delay * (retry_count + 1))
                return self.analyze_pose_image(image_url, retry_count + 1)
            
            return None
    
    def _validate_image_url(self, image_url: str) -> bool:
        """验证图片URL是否可访问"""
        try:
            response = requests.head(image_url, timeout=10)
            if response.status_code == 200:
                content_type = response.headers.get('content-type', '')
                if content_type.startswith('image/'):
                    return True
                else:
                    logger.warning(f"URL不是图片类型: {content_type}")
                    return False
            else:
                logger.warning(f"URL访问失败，状态码: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"验证URL失败: {e}")
            return False
    
    def _build_analysis_prompt(self) -> str:
        """构建分析提示词"""
        return """
请仔细分析这张摄影姿势图片，按照以下JSON格式返回分析结果：

{
    "title": "简洁的标题",
    "description": "详细的姿势描述",
    "scene_category": "场景分类",
    "angle": "拍摄角度", 
    "tags": ["标签1", "标签2", ...],
    "props": ["道具1", "道具2", ...],
    "shooting_tips": "拍摄建议和技巧",
    "confidence": 0.95
}

**分析要求：**

1. **title**: 3-8个字的简洁标题，如"森系少女写真"、"咖啡厅慵懒时光"

2. **description**: 50-100字的详细描述，包括人物状态、动作、表情等

3. **scene_category**: 必须从以下选项中选择一个：
   - 室内 (包括家居、工作室等)
   - 户外 (公园、街道、自然环境等)
   - 咖啡厅 (咖啡馆、茶室等)
   - 商场 (购物中心、商店等)
   - 学校 (校园、教室、图书馆等)
   - 办公室 (工作场所)
   - 海边 (海滩、海岸等)
   - 森林 (树林、公园绿地等)
   - 城市 (都市街景、建筑等)
   - 其他

4. **angle**: 必须从以下选项中选择一个：
   - 正面 (面向镜头)
   - 侧面 (侧身或半侧身)
   - 背面 (背对镜头)
   - 俯视 (从上往下拍摄)
   - 仰视 (从下往上拍摄)
   - 斜角 (倾斜角度)

5. **tags**: 5-15个中文关键词，包括：
   - 情绪标签：如"清新"、"文艺"、"性感"、"可爱"、"优雅"
   - 动作标签：如"坐姿"、"站立"、"躺下"、"行走"、"倚靠"
   - 风格标签：如"日系"、"韩系"、"复古"、"现代"、"简约"
   - 服装标签：如"连衣裙"、"牛仔"、"西装"、"休闲"
   - 其他特征标签

6. **props**: 画面中的道具和物品，如"咖啡杯"、"书本"、"花束"、"帽子"等

7. **shooting_tips**: 实用的拍摄建议，包括构图、光线、角度等技巧

8. **confidence**: 分析结果的置信度(0.0-1.0)

请确保返回的是有效的JSON格式，所有字段都要填写。
"""
    
    def _parse_analysis_result(self, result_text: str) -> Optional[Dict]:
        """解析AI分析结果"""
        try:
            # 尝试提取JSON部分
            if '```json' in result_text:
                json_str = result_text.split('```json')[1].split('```')[0]
            elif '```' in result_text:
                json_str = result_text.split('```')[1]
            else:
                json_str = result_text
            
            # 清理和验证JSON
            json_str = json_str.strip()
            result = json.loads(json_str)
            
            # 验证必要字段
            required_fields = ['title', 'description', 'scene_category', 'angle', 'tags']
            for field in required_fields:
                if field not in result:
                    logger.warning(f"缺少必要字段: {field}")
                    return None
            
            # 标准化字段
            result = self._normalize_result(result)
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {e}")
            logger.error(f"原始文本: {result_text}")
            return None
        except Exception as e:
            logger.error(f"结果解析失败: {e}")
            return None
    
    def _normalize_result(self, result: Dict) -> Dict:
        """标准化分析结果"""
        # 标准化场景分类
        scene_mapping = {
            '室内': '室内', '家居': '室内', '工作室': '室内', '房间': '室内',
            '户外': '户外', '室外': '户外', '公园': '户外', '街道': '户外', '自然': '户外',
            '咖啡厅': '咖啡厅', '咖啡馆': '咖啡厅', '茶室': '咖啡厅', '餐厅': '咖啡厅',
            '商场': '商场', '购物中心': '商场', '商店': '商场', '店铺': '商场',
            '学校': '学校', '校园': '学校', '教室': '学校', '图书馆': '学校',
            '办公室': '办公室', '工作场所': '办公室', '公司': '办公室',
            '海边': '海边', '海滩': '海边', '海岸': '海边', '沙滩': '海边',
            '森林': '森林', '树林': '森林', '公园绿地': '森林', '山林': '森林',
            '城市': '城市', '都市': '城市', '建筑': '城市', '街景': '城市'
        }
        
        scene = result.get('scene_category', '其他')
        result['scene_category'] = scene_mapping.get(scene, '其他')
        
        # 标准化角度
        angle_mapping = {
            '正面': '正面', '正脸': '正面', '面向镜头': '正面', '正对': '正面',
            '侧面': '侧面', '侧身': '侧面', '半侧身': '侧面', '侧脸': '侧面',
            '背面': '背面', '背影': '背面', '背对镜头': '背面', '后背': '背面',
            '俯视': '俯视', '从上往下': '俯视', '俯拍': '俯视', '鸟瞰': '俯视',
            '仰视': '仰视', '从下往上': '仰视', '仰拍': '仰视', '仰角': '仰视',
            '斜角': '斜角', '倾斜': '斜角', '斜拍': '斜角'
        }
        
        angle = result.get('angle', '正面')
        result['angle'] = angle_mapping.get(angle, '正面')
        
        # 确保tags是列表
        if isinstance(result.get('tags'), str):
            result['tags'] = [tag.strip() for tag in result['tags'].split(',') if tag.strip()]
        
        # 确保props是列表
        if isinstance(result.get('props'), str):
            result['props'] = [prop.strip() for prop in result['props'].split(',') if prop.strip()]
        
        # 设置默认值
        result.setdefault('props', [])
        result.setdefault('shooting_tips', '')
        result.setdefault('confidence', 0.8)
        
        # 限制标签数量
        if len(result['tags']) > 15:
            result['tags'] = result['tags'][:15]
        
        return result