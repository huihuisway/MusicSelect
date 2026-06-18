"""
消息模板引擎

负责：
1. 加载默认模板 + 用户覆盖
2. 安全渲染（缺失变量优雅降级）
3. 验证模板合法性
4. 提供管理接口
"""

import re
import logging
from collections import defaultdict
from typing import Dict, Optional, List, Any

# 支持相对导入和绝对导入
try:
    from .templates import TEMPLATE_REGISTRY
except ImportError:
    from templates import TEMPLATE_REGISTRY

logger = logging.getLogger(__name__)


class SafeDict(defaultdict):
    """
    安全的格式化字典：缺失的键返回 {key_name} 而非报错。

    >>> d = SafeDict(title="晴天")
    >>> "🎵 {title} - {artist}".format_map(d)
    '🎵 晴天 - {artist}'
    """
    def __missing__(self, key: str) -> str:
        return "{" + key + "}"


class TemplateEngine:
    """消息模板引擎"""

    def __init__(self, overrides: Optional[Dict[str, str]] = None):
        """
        Args:
            overrides: 用户自定义模板覆盖 {key: template_string}
        """
        self._overrides: Dict[str, str] = overrides or {}
        self._cache: Dict[str, str] = {}  # resolved templates cache
        self._build_cache()

    def _build_cache(self):
        """构建解析后的模板缓存"""
        self._cache.clear()
        for key, template_def in TEMPLATE_REGISTRY.items():
            # 优先使用覆盖，否则用默认
            self._cache[key] = self._overrides.get(key, template_def.default)

    def render(self, key: str, **variables) -> str:
        """
        渲染模板。

        Args:
            key: 模板键名
            **variables: 模板变量

        Returns:
            渲染后的字符串，缺失变量保留 {var_name} 形式
        """
        template = self._cache.get(key)
        if template is None:
            logger.warning(f"[TemplateEngine] 未知模板键: {key}")
            return f"[未知模板: {key}]"

        try:
            safe_vars = SafeDict()
            safe_vars.update(variables)
            return template.format_map(safe_vars)
        except (KeyError, ValueError, IndexError) as e:
            logger.warning(f"[TemplateEngine] 渲染模板 '{key}' 失败: {e}")
            return template  # 返回未渲染的原始模板

    def get_raw(self, key: str) -> Optional[str]:
        """获取原始模板字符串（未渲染）"""
        return self._cache.get(key)

    def get_default(self, key: str) -> Optional[str]:
        """获取默认模板字符串"""
        template_def = TEMPLATE_REGISTRY.get(key)
        return template_def.default if template_def else None

    def get_definition(self, key: str):
        """获取模板定义（含变量元数据）"""
        return TEMPLATE_REGISTRY.get(key)

    def update(self, key: str, template: str) -> bool:
        """
        更新模板覆盖。

        Returns:
            True 如果成功，False 如果验证失败
        """
        if key not in TEMPLATE_REGISTRY:
            return False

        # 验证：检查模板中的变量是否都在允许列表中
        is_valid, errors = self.validate(key, template)
        if not is_valid:
            logger.warning(f"[TemplateEngine] 模板验证失败: {errors}")
            return False

        self._overrides[key] = template
        self._cache[key] = template
        return True

    def reset(self, key: str) -> bool:
        """重置单个模板为默认值"""
        if key not in TEMPLATE_REGISTRY:
            return False
        self._overrides.pop(key, None)
        template_def = TEMPLATE_REGISTRY[key]
        self._cache[key] = template_def.default
        return True

    def reset_all(self):
        """重置所有模板为默认值"""
        self._overrides.clear()
        self._build_cache()

    def get_overrides(self) -> Dict[str, str]:
        """获取当前所有覆盖（用于持久化到配置）"""
        return dict(self._overrides)

    def validate(self, key: str, template: str) -> tuple[bool, List[str]]:
        """
        验证模板。

        Returns:
            (is_valid, list_of_errors)
        """
        template_def = TEMPLATE_REGISTRY.get(key)
        if not template_def:
            return False, [f"未知模板键: {key}"]

        # 提取模板中使用的变量
        used_vars = set(re.findall(r'\{(\w+)\}', template))
        allowed_vars = {v.name for v in template_def.variables}

        invalid_vars = used_vars - allowed_vars
        if invalid_vars:
            return False, [f"未知变量: {{{v}}}" for v in invalid_vars]

        # 检查语法错误（不匹配的括号等）
        try:
            # 用空值测试语法
            test_vars = {v: "" for v in allowed_vars}
            template.format_map(test_vars)
        except (ValueError, IndexError, KeyError) as e:
            return False, [f"模板语法错误: {e}"]

        return True, []

    def list_templates(self, category: Optional[str] = None) -> List[dict]:
        """
        列出所有模板（含当前值和默认值）。

        Returns:
            [{key, description, category, current, default, variables, is_overridden}, ...]
        """
        result = []
        for key, tdef in TEMPLATE_REGISTRY.items():
            if category and tdef.category != category:
                continue
            result.append({
                "key": key,
                "description": tdef.description,
                "category": tdef.category,
                "current": self._cache.get(key, ""),
                "default": tdef.default,
                "variables": [
                    {"name": v.name, "description": v.description, "example": v.example}
                    for v in tdef.variables
                ],
                "is_overridden": key in self._overrides,
            })
        return result

    def preview(self, key: str) -> str:
        """
        用示例值预览模板渲染效果。
        """
        template_def = TEMPLATE_REGISTRY.get(key)
        if not template_def:
            return f"[未知模板: {key}]"

        example_vars = {v.name: v.example for v in template_def.variables}
        return self.render(key, **example_vars)
