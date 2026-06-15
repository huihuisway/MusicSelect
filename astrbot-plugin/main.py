"""
MusicSelect 校园点歌 AstrBot 插件

支持方式：
1. 自动识别消息中的网易云链接
2. 命令式：/点歌 /搜索 /歌单 /状态 /历史 /点歌帮助
3. 语音/自然语言：直接说话名搜索点歌
"""

import re
import logging
from typing import Optional

from astrbot.api import star
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.message_components import Plain, Image
from astrbot.core.message.message_event_result import MessageChain

from .config import Config
from .api_client import MusicSelectApiClient, ApiError
from .conversation import ConversationManager, ConversationData
from .intent import (
    parse_intent,
    resolve_weekday_to_date,
    INTENT_CONFIRM, INTENT_CANCEL, INTENT_SKIP,
    INTENT_DATE_SELECT, INTENT_NUMBER_PICK,
    INTENT_SEARCH, INTENT_USERNAME, INTENT_MESSAGE,
    INTENT_UNKNOWN,
    STATE_IDLE, STATE_WAITING_INPUT, STATE_WAITING_CONFIRM,
    STATE_WAITING_SEARCH_PICK, STATE_WAITING_USERNAME,
    STATE_WAITING_MESSAGE, STATE_WAITING_DATE, STATE_WAITING_POSITION,
)
from .message_builder import (
    format_song_info, format_submit_success,
    format_search_results, format_playlist,
    format_cycle_status, format_history_weeks, format_history_songs,
    format_date_prompt, HELP_TEXT,
    format_api_error, NOT_IN_SUBMISSION_WINDOW,
    CANCELLED, CONVERSATION_EXPIRED,
)

logger = logging.getLogger(__name__)

# 网易云链接正则（匹配分享文本中的链接）
NETEASE_URL_PATTERN = (
    r'https?://(?:music\.163\.com[^\s]*?id=\d+|163cn\.tv/[a-zA-Z0-9]+)'
)


class MusicSelectPlugin(star.Star):
    """校园点歌插件"""

    def __init__(self, context: star.Context, config: Optional[dict] = None):
        super().__init__(context, config)

        # 初始化配置（config 参数为插件专属配置）
        self.config = Config(config)

        # API 客户端
        self.api = MusicSelectApiClient(
            base_url=self.config.api_base_url,
            timeout=self.config.timeout,
        )

        # 对话管理器
        self.conversations = ConversationManager(
            timeout=self.config.conversation_timeout,
        )

        logger.info(f"[MusicSelect] 插件已加载，API: {self.config.api_base_url}")

    # ================================================================
    # 工具方法
    # ================================================================

    def _get_user_id(self, event: AstrMessageEvent) -> str:
        """从事件中提取用户唯一标识"""
        # 优先使用 AstrBot 提供的统一用户 ID
        if hasattr(event, 'message_obj') and hasattr(event.message_obj, 'session_id'):
            return str(event.message_obj.session_id)
        if hasattr(event, 'get_sender_id'):
            return str(event.get_sender_id())
        # 兜底：使用消息 ID
        return str(id(event))

    def _get_message_text(self, event: AstrMessageEvent) -> str:
        """从事件中提取纯文本内容"""
        if hasattr(event, 'message_str'):
            return event.message_str.strip()
        if hasattr(event, 'get_message_str'):
            return event.get_message_str().strip()
        return ""

    async def _send_text(self, event: AstrMessageEvent, text: str):
        """发送纯文本消息"""
        await event.send(MessageChain([Plain(text)]))

    async def _send_with_image(self, event: AstrMessageEvent, text: str, image_url: str):
        """发送带图片的消息"""
        if image_url:
            await event.send(MessageChain([Plain(text), Image.fromURL(image_url)]))
        else:
            await event.send(MessageChain([Plain(text)]))

    # ================================================================
    # 命令处理器
    # ================================================================

    @filter.command("点歌")
    async def cmd_dian_ge(self, event: AstrMessageEvent):
        """/点歌 - 进入点歌模式"""
        user_id = self._get_user_id(event)
        self.conversations.clear_user(user_id)
        self.conversations.set_state(user_id, STATE_WAITING_INPUT)

        await self._send_text(
            event,
            "🎵 已进入点歌模式\n\n"
            "请发送网易云音乐链接 或 直接说歌名搜索\n"
            "💡 回复「取消」退出点歌模式"
        )

    @filter.command("搜索")
    async def cmd_sou_suo(self, event: AstrMessageEvent):
        """/搜索 关键词 - 搜索歌曲"""
        user_id = self._get_user_id(event)
        text = self._get_message_text(event)

        # 提取搜索关键词（去掉命令前缀）
        keywords = re.sub(r'^[/！!]搜索\s*', '', text).strip()

        if not keywords:
            await self._send_text(event, "🔍 请提供搜索关键词\n💡 格式：/搜索 歌名 或 歌手 歌名")
            return

        await self._do_search(event, user_id, keywords)

    @filter.command("歌单")
    async def cmd_ge_dan(self, event: AstrMessageEvent):
        """/歌单 - 查看本周歌单"""
        try:
            playlist = await self.api.get_playlist()
            text = format_playlist(playlist)
            await self._send_text(event, text)
        except ApiError as e:
            await self._send_text(event, format_api_error(e.code, e.message))

    @filter.command("状态")
    async def cmd_zhuang_tai(self, event: AstrMessageEvent):
        """/状态 - 查看当前周期状态"""
        try:
            cycle_info = await self.api.get_cycle_info()
            stats = await self.api.get_stats()
            text = format_cycle_status(cycle_info, stats)
            await self._send_text(event, text)
        except ApiError as e:
            await self._send_text(event, format_api_error(e.code, e.message))

    @filter.command("历史")
    async def cmd_li_shi(self, event: AstrMessageEvent):
        """/历史 [weekStart] - 查看历史歌单"""
        text = self._get_message_text(event)
        # 提取日期参数
        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', text)

        if date_match:
            week_start = date_match.group(1)
            try:
                history = await self.api.get_history(week_start)
                result = format_history_songs(history)
                await self._send_text(event, result)
            except ApiError as e:
                await self._send_text(event, format_api_error(e.code, e.message))
        else:
            try:
                weeks = await self.api.get_history_weeks()
                result = format_history_weeks(weeks)
                await self._send_text(event, result)
            except ApiError as e:
                await self._send_text(event, format_api_error(e.code, e.message))

    @filter.command("点歌帮助")
    async def cmd_bang_zhu(self, event: AstrMessageEvent):
        """/点歌帮助 - 显示帮助"""
        await self._send_text(event, HELP_TEXT)

    # ================================================================
    # 消息统一处理（链接自动识别 + 自然语言对话）
    # ================================================================

    @filter.regex(r".+")
    async def on_message(self, event: AstrMessageEvent):
        """
        处理所有非命令的文本消息。

        仅在对话状态活跃时处理：
        - IDLE（默认）：忽略，用户需先执行命令
        - WAITING_INPUT（/点歌 后）：链接自动识别 或 搜索
        - 其他状态：继续对话流程
        """
        user_id = self._get_user_id(event)
        text = self._get_message_text(event)

        if not text:
            return

        # 获取当前对话状态
        conv = self.conversations.get_state(user_id)

        # IDLE 状态：忽略消息（用户需先执行命令）
        if conv.state == STATE_IDLE:
            return

        # 检查是否超时
        if conv.is_expired(self.config.conversation_timeout):
            self.conversations.clear_user(user_id)
            await self._send_text(event, "⏰ 对话已超时，请重新执行命令")
            return

        # WAITING_INPUT 状态：检测链接 或 搜索
        if conv.state == STATE_WAITING_INPUT:
            link_match = re.search(NETEASE_URL_PATTERN, text)
            if link_match:
                link = link_match.group(0)
                await self._do_check_and_confirm(event, user_id, link)
            else:
                # 当作搜索关键词
                _, keywords = parse_intent(text, STATE_WAITING_INPUT)
                if keywords:
                    await self._do_search(event, user_id, keywords)
            return

        # 其他活跃状态：检查链接优先（用户可能在对话中发链接）
        link_match = re.search(NETEASE_URL_PATTERN, text)
        if link_match:
            link = link_match.group(0)
            await self._do_check_and_confirm(event, user_id, link)
            return

        # 解析意图并分发
        intent, value = parse_intent(text, conv.state)
        logger.debug(f"[MusicSelect] user={user_id}, state={conv.state}, intent={intent}, value={value}")
        await self._dispatch_intent(event, user_id, intent, value, text)

    # ================================================================
    # 意图分发
    # ================================================================

    async def _dispatch_intent(
        self,
        event: AstrMessageEvent,
        user_id: str,
        intent: str,
        value,
        raw_text: str,
    ):
        """根据意图和当前状态分发处理"""
        conv = self.conversations.get_state(user_id)
        state = conv.state

        # 全局取消
        if intent == INTENT_CANCEL:
            self.conversations.clear_user(user_id)
            await self._send_text(event, CANCELLED)
            return

        if state == STATE_IDLE:
            await self._handle_idle(event, user_id, intent, value, raw_text)
        elif state == STATE_WAITING_CONFIRM:
            await self._handle_waiting_confirm(event, user_id, intent, value)
        elif state == STATE_WAITING_SEARCH_PICK:
            await self._handle_waiting_search_pick(event, user_id, intent, value)
        elif state == STATE_WAITING_USERNAME:
            await self._handle_waiting_username(event, user_id, intent, value)
        elif state == STATE_WAITING_MESSAGE:
            await self._handle_waiting_message(event, user_id, intent, value)
        elif state == STATE_WAITING_DATE:
            await self._handle_waiting_date(event, user_id, intent, value)
        elif state == STATE_WAITING_POSITION:
            await self._handle_waiting_position(event, user_id, intent, value)
        else:
            # 未知状态，重置
            self.conversations.clear_user(user_id)
            await self._send_text(event, "⚠️ 状态异常，已重置。请发送 /点歌帮助 查看使用方法")

    # ================================================================
    # 各状态处理
    # ================================================================

    async def _handle_idle(self, event, user_id, intent, value, raw_text):
        """IDLE 状态：自然语言搜索"""
        if intent == INTENT_SEARCH and value:
            await self._do_search(event, user_id, value)
        else:
            # 无法识别的输入
            await self._send_text(
                event,
                "💡 我不太明白你的意思\n"
                "📖 发送 /点歌帮助 查看使用方法"
            )

    async def _handle_waiting_confirm(self, event, user_id, intent, value):
        """WAITING_CONFIRM 状态：等待确认提交"""
        if intent == INTENT_CONFIRM:
            # 确认 → 进入姓名填写
            self.conversations.set_state(user_id, STATE_WAITING_USERNAME)
            await self._send_text(event, "👤 请输入你的姓名+班级（如：高三1班 张三）")
        elif intent == INTENT_SKIP:
            # 跳过确认 = 取消
            self.conversations.clear_user(user_id)
            await self._send_text(event, CANCELLED)
        else:
            # 其他输入视为取消
            self.conversations.clear_user(user_id)
            await self._send_text(event, CANCELLED)

    async def _handle_waiting_search_pick(self, event, user_id, intent, value):
        """WAITING_SEARCH_PICK 状态：选择搜索结果"""
        if intent == INTENT_NUMBER_PICK and value:
            conv = self.conversations.get_state(user_id)
            results = conv.data.search_results or []
            index = value - 1  # 转为 0-based

            if 0 <= index < len(results):
                song = results[index]
                song_id = song.get("songId", "")
                link = f"https://music.163.com/#/song?id={song_id}"
                await self._do_check_and_confirm(event, user_id, link)
            else:
                await self._send_text(event, f"❌ 编号超出范围，请输入 1-{len(results)} 之间的数字")
        else:
            await self._send_text(event, f"💡 请回复歌曲编号（1-{len(self.conversations.get_data(user_id).search_results or [])}）或「取消」")

    async def _handle_waiting_username(self, event, user_id, intent, value):
        """WAITING_USERNAME 状态：输入姓名"""
        if intent == INTENT_USERNAME and value:
            self.conversations.set_data_field(user_id, "username", value)
            self.conversations.set_state(user_id, STATE_WAITING_MESSAGE)
            await self._send_text(event, "💬 请输入留言（20字以内，回复「跳过」可不填）")
        elif intent == INTENT_SKIP:
            self.conversations.set_data_field(user_id, "username", None)
            self.conversations.set_state(user_id, STATE_WAITING_MESSAGE)
            await self._send_text(event, "💬 请输入留言（回复「跳过」可不填）")
        else:
            await self._send_text(event, "❌ 请输入有效的姓名（20字以内）或回复「跳过」")

    async def _handle_waiting_message(self, event, user_id, intent, value):
        """WAITING_MESSAGE 状态：输入留言"""
        if intent == INTENT_MESSAGE and value:
            self.conversations.set_data_field(user_id, "message", value)
            await self._ask_date(event, user_id)
        elif intent == INTENT_SKIP:
            self.conversations.set_data_field(user_id, "message", None)
            await self._ask_date(event, user_id)
        else:
            await self._send_text(event, "❌ 留言不能超过 100 字，或回复「跳过」")

    async def _handle_waiting_date(self, event, user_id, intent, value):
        """WAITING_DATE 状态：选择播放日期"""
        if intent == INTENT_DATE_SELECT and value:
            # 解析日期
            play_date = value
            if play_date.startswith("WEEKDAY:"):
                # 需要根据 weekStart 计算具体日期
                offset = int(play_date.split(":")[1])
                # 获取当前周期的 weekStart
                try:
                    cycle = await self.api.get_cycle_info()
                    week_start = cycle.get("weekStart", "")
                    play_date = resolve_weekday_to_date(offset, week_start)
                except ApiError:
                    await self._send_text(event, "❌ 获取周期信息失败，请重试")
                    return

            if play_date:
                self.conversations.set_data_field(user_id, "play_date", play_date)
                await self._send_text(event, f"📅 已选择 {play_date}，是否指定播放位置？（1-5，回复「跳过」自动分配）")
                self.conversations.set_state(user_id, STATE_WAITING_POSITION)
            else:
                await self._send_text(event, "❌ 日期无效，请重新选择或回复「跳过」")
        elif intent == INTENT_SKIP:
            # 跳过日期选择 → 直接提交
            await self._do_submit(event, user_id)
        else:
            await self._send_text(event, "💡 请回复日期（如：周一、明天）或「跳过」")

    async def _handle_waiting_position(self, event, user_id, intent, value):
        """WAITING_POSITION 状态：选择播放位置"""
        if intent == INTENT_NUMBER_PICK and value:
            self.conversations.set_data_field(user_id, "play_position", value)
            await self._do_submit(event, user_id)
        elif intent == INTENT_SKIP:
            await self._do_submit(event, user_id)
        else:
            await self._send_text(event, "💡 请回复位置编号（1-5）或「跳过」自动分配")

    # ================================================================
    # 核心流程方法
    # ================================================================

    async def _do_search(self, event: AstrMessageEvent, user_id: str, keywords: str):
        """执行搜索并展示结果"""
        try:
            results = await self.api.search_songs(keywords, self.config.search_limit)

            if not results:
                await self._send_text(
                    event,
                    f"🔍 未找到与「{keywords}」相关的歌曲，请换个关键词试试"
                )
                return

            # 保存搜索结果到对话数据
            data = self.conversations.get_data(user_id)
            data.search_results = results
            self.conversations.set_state(user_id, STATE_WAITING_SEARCH_PICK)

            text = format_search_results(results, keywords)
            await self._send_text(event, text)

        except ApiError as e:
            await self._send_text(event, format_api_error(e.code, e.message))

    async def _do_check_and_confirm(self, event: AstrMessageEvent, user_id: str, link: str):
        """检查歌曲并进入确认流程"""
        try:
            result = await self.api.check_song(link)

            # 保存数据
            data = self.conversations.get_data(user_id)
            data.link = link
            data.song_info = result
            self.conversations.set_state(user_id, STATE_WAITING_CONFIRM)

            # 格式化并发送
            text, cover_url = format_song_info(result)
            await self._send_with_image(event, text, cover_url)

        except ApiError as e:
            self.conversations.clear_user(user_id)
            await self._send_text(event, format_api_error(e.code, e.message))

    async def _ask_date(self, event: AstrMessageEvent, user_id: str):
        """询问播放日期选择"""
        try:
            cycle = await self.api.get_cycle_info()
            songs_by_day = cycle.get("songsByDay", {})
            week_start = cycle.get("weekStart", "")
            text = format_date_prompt(songs_by_day, week_start)
            self.conversations.set_state(user_id, STATE_WAITING_DATE)
            await self._send_text(event, text)
        except ApiError as e:
            # 获取周期信息失败，直接提交（不选日期）
            await self._do_submit(event, user_id)

    async def _do_submit(self, event: AstrMessageEvent, user_id: str):
        """执行最终提交"""
        data = self.conversations.get_data(user_id)

        if not data.link or not data.song_info:
            self.conversations.clear_user(user_id)
            await self._send_text(event, "❌ 提交数据丢失，请重新开始（/点歌）")
            return

        try:
            result = await self.api.submit_song(
                link=data.link,
                username=data.username,
                message=data.message,
                preferred_play_date=data.play_date,
                preferred_play_position=data.play_position,
            )

            # 提交成功
            self.conversations.clear_user(user_id)
            username_display = data.username or "未公开姓名班级"
            message_display = data.message or ""
            text = format_submit_success(result, username_display, message_display)
            await self._send_text(event, text)

        except ApiError as e:
            self.conversations.clear_user(user_id)
            await self._send_text(event, format_api_error(e.code, e.message))

    # ================================================================
    # 插件生命周期
    # ================================================================

    async def terminate(self):
        """插件卸载时清理资源"""
        await self.api.close()
        logger.info("[MusicSelect] 插件已卸载")
