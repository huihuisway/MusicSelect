"""
MusicSelect AstrBot 插件配置
"""


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

        # 消息模板覆盖
        self.message_templates: dict = config.get("message_templates", {})
