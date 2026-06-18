"""
MusicSelect AstrBot 插件配置
"""

import json
import logging

logger = logging.getLogger(__name__)


class Config:
    """插件配置，支持从 AstrBot 配置系统读取"""

    def __init__(self, plugin_config: dict = None):
        config = plugin_config or {}

        # MusicSelect 后端 API 地址
        self.api_base_url: str = config.get(
            "api_base_url",
            "http://localhost:4000/api"
        )

        # HTTP 请求超时（秒）
        self.timeout: int = config.get("timeout", 10)

        # 搜索结果数量
        self.search_limit: int = config.get("search_limit", 5)

        # 对话超时（秒），默认 10 分钟
        self.conversation_timeout: int = config.get("conversation_timeout", 600)

        # 管理员 ID（为空则无管理员）
        self.admin_id: str = config.get("admin_id", "")

        # 消息模板覆盖（从 JSON 字符串解析）
        message_templates_raw = config.get("message_templates", "")
        self.message_templates: dict = {}

        if message_templates_raw:
            if isinstance(message_templates_raw, dict):
                # 已经是字典（可能是从旧版本迁移）
                self.message_templates = message_templates_raw
            elif isinstance(message_templates_raw, str) and message_templates_raw.strip():
                # 是 JSON 字符串，需要解析
                try:
                    parsed = json.loads(message_templates_raw)
                    if isinstance(parsed, dict):
                        self.message_templates = parsed
                    else:
                        logger.warning(f"[Config] message_templates 解析结果不是字典: {type(parsed)}")
                except json.JSONDecodeError as e:
                    logger.error(f"[Config] message_templates JSON 解析失败: {e}")
                    logger.error(f"[Config] 原始值: {message_templates_raw}")
