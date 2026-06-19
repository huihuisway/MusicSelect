"""
MusicSelect musicselect AstrBot 插件

支持方式：
1. 自动识别消息中的网易云链接
2. 命令式：/点歌 /搜索 /歌单 /状态 /历史 /点歌帮助
3. 语音/自然语言：直接说话名搜索点歌
"""

import re
import json
import logging
from typing import Optional
from datetime import datetime, timedelta

from astrbot.api import star
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.message_components import Plain, Image
from astrbot.core.message.message_event_result import MessageChain

from .config import Config
from .api_client import MusicSelectApiClient, ApiError
from .conversation import ConversationManager, ConversationData
from .template_engine import TemplateEngine
from .intent import (
    parse_intent,
    resolve_weekday_to_date,
    INTENT_CONFIRM, INTENT_CANCEL, INTENT_SKIP,
    INTENT_DATE_SELECT, INTENT_NUMBER_PICK,
    INTENT_SEARCH, INTENT_MESSAGE,
    INTENT_UNKNOWN,
    STATE_IDLE, STATE_WAITING_INPUT, STATE_WAITING_CONFIRM,
    STATE_WAITING_SEARCH_PICK,
    STATE_WAITING_MESSAGE, STATE_WAITING_DATE, STATE_WAITING_POSITION,
)
from .message_builder import (
    format_song_info, format_confirm_prompt, format_submit_success,
    format_search_results, format_playlist,
    format_cycle_status, format_history_weeks, format_history_songs,
    format_date_prompt, format_position_selection, HELP_TEXT,
    format_api_error, NOT_IN_SUBMISSION_WINDOW,
    CANCELLED, CONVERSATION_EXPIRED,
)

logger = logging.getLogger(__name__)

# 网易云链接正则（匹配分享文本中的链接）
NETEASE_URL_PATTERN = (
    r'https?://(?:music\.163\.com[^\s]*?id=\d+|163cn\.tv/[a-zA-Z0-9]+)'
)


class MusicSelectPlugin(star.Star):
    """musicselect 插件"""

    def __init__(self, context: star.Context, config: Optional[dict] = None):
        super().__init__(context, config)

        # 初始化配置（config 参数为插件专属配置）
        try:
            self.config = Config(config)
        except Exception as e:
            logger.error(f"[MusicSelect] 配置初始化失败: {e}")
            self.config = Config({})

        # API 客户端
        self.api = MusicSelectApiClient(
            base_url=self.config.api_base_url,
            timeout=self.config.timeout,
        )

        # 对话管理器
        self.conversations = ConversationManager(
            timeout=self.config.conversation_timeout,
        )

        # 模板引擎
        try:
            self.templates = TemplateEngine(overrides=self.config.message_templates)
        except Exception as e:
            logger.error(f"[MusicSelect] 模板引擎初始化失败: {e}")
            self.templates = TemplateEngine(overrides={})

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

    def _save_config(self):
        """保存配置到文件（持久化模板修改等）"""
        try:
            # 更新配置对象中的模板覆盖（转换为 JSON 字符串）
            templates_dict = self.templates.get_overrides()
            # 创建一个用于保存的配置字典
            config_to_save = {
                "api_base_url": self.config.api_base_url,
                "timeout": self.config.timeout,
                "search_limit": self.config.search_limit,
                "conversation_timeout": self.config.conversation_timeout,
                "admin_id": self.config.admin_id,
                "message_templates": json.dumps(templates_dict, ensure_ascii=False) if templates_dict else "",
            }
            # 保存到文件
            if hasattr(self, 'astrbot') and hasattr(self.astrbot, 'save_config'):
                self.astrbot.save_config(self, "musicselect", config_to_save)
                logger.info("[MusicSelect] 配置已保存到文件")
            else:
                logger.warning("[MusicSelect] astrbot.save_config 不可用，配置仅保存在内存中")
        except Exception as e:
            logger.error(f"[MusicSelect] 保存配置失败: {e}")

    def _is_admin(self, user_id: str) -> bool:
        """检查用户是否为管理员"""
        return bool(self.config.admin_id) and user_id == self.config.admin_id

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
            "💡 回复「搜索 歌名」搜索歌曲\n"
            "💡 或直接发送网易云音乐链接\n"
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

    @filter.command("管理")
    async def cmd_guan_li(self, event: AstrMessageEvent):
        """/管理 - 管理员命令（关闭/开放日期）"""
        user_id = self._get_user_id(event)
        if not self._is_admin(user_id):
            await self._send_text(event, "🚫 你不是管理员，无法执行此操作")
            return

        text = self._get_message_text(event)
        # 去掉命令前缀（兼容 /管理、！管理、管理 等格式）
        args = re.sub(r'^[/！!]?\s*管理\s*', '', text).strip()

        if not args:
            # 显示当前状态和帮助
            try:
                cycle = await self.api.get_cycle_info()
                closed = await self.api.get_closed_dates(cycle.get("weekStart", ""))
                closed_str = "\n    ".join([c["date"] for c in closed]) if closed else "无"

                # 获取跳周状态
                skip_status = await self.api.get_skip_week_status()
                if skip_status.get("isActive"):
                    skip_info = skip_status.get("skipWeek", {})
                    skip_str = f"已激活（跳到 {skip_info.get('weekStart', '未知')}）"
                else:
                    skip_str = "未激活"
            except ApiError:
                closed_str = "（获取失败）"
                skip_str = "（获取失败）"

            await self._send_text(
                event,
                f"🔧 管理面板\n\n"
                f"📌 管理员 ID：{self.config.admin_id}\n"
                f"📌 本周关闭日期：\n    {closed_str}\n"
                f"📌 跳周状态：{skip_str}\n\n"
                f"💡 命令：\n"
                f"  /管理 关 MMDD — 关闭指定日期（如 /管理 关 0701）\n"
                f"  /管理 开 MMDD — 重新开放指定日期\n"
                f"  /管理 跳周 — 跳到下一周并开放点歌\n"
                f"  /管理 撤销跳周 — 撤销跳周操作"
            )
            return

        # 跳周命令
        if args in ("跳周", "跳"):
            try:
                result = await self.api.activate_skip_week(activated_by=user_id)
                week_start = result.get("weekStart", "未知")
                await self._send_text(
                    event,
                    f"✅ 已跳到下一周（{week_start}）\n"
                    f"🎉 点歌窗口已开放，用户可以开始点歌了！\n\n"
                    f"💡 如需撤销，请使用：/管理 撤销跳周"
                )
            except ApiError as e:
                await self._send_text(event, format_api_error(e.code, e.message))
            return

        # 撤销跳周命令
        if args in ("撤销跳周", "撤销跳", "取消跳周"):
            try:
                result = await self.api.deactivate_skip_week()
                await self._send_text(
                    event,
                    f"✅ 已撤销跳周\n"
                    f"🔄 恢复正常周期计算"
                )
            except ApiError as e:
                await self._send_text(event, format_api_error(e.code, e.message))
            return

        # 关闭/开启 日期（支持 关/开/关闭/开启）
        m = re.match(r'^(关|开|关闭|开启)\s*(\d{2,4})?(\d{2})?$', args)
        if m:
            action_raw = m.group(1)
            part1 = m.group(2) or ""
            part2 = m.group(3) or ""

            # 规范化动作
            action = "close" if action_raw in ("关", "关闭") else "open"

            # 解析日期
            date_str_full = part1 + part2
            if len(date_str_full) == 4:
                # MMDD 格式
                year = datetime.now().year
                month = int(date_str_full[:2])
                day = int(date_str_full[2:])
            elif len(date_str_full) == 6:
                # YYMMDD 格式
                year = 2000 + int(date_str_full[:2])
                month = int(date_str_full[2:4])
                day = int(date_str_full[4:])
            elif len(date_str_full) == 8:
                # YYYYMMDD 格式
                year = int(date_str_full[:4])
                month = int(date_str_full[4:6])
                day = int(date_str_full[6:])
            else:
                await self._send_text(
                    event,
                    "❌ 日期格式错误\n"
                    "💡 正确格式：/管理 关 0701（7月1日）"
                )
                return

            try:
                target_date = datetime(year, month, day)
                date_str = target_date.strftime("%Y-%m-%d")
            except ValueError:
                await self._send_text(event, f"❌ 日期无效：{month}月{day}日 不存在")
                return

            try:
                cycle = await self.api.get_cycle_info()
                week_start = cycle.get("weekStart", "")
            except ApiError as e:
                await self._send_text(event, format_api_error(e.code, e.message))
                return

            if action == "close":
                try:
                    await self.api.add_closed_date(date_str, week_start)
                    await self._send_text(event, f"✅ 已关闭 {month}月{day}日 的点歌")
                except ApiError as e:
                    await self._send_text(event, format_api_error(e.code, e.message))
            else:
                try:
                    await self.api.remove_closed_date(date_str)
                    await self._send_text(event, f"✅ 已重新开放 {month}月{day}日 的点歌")
                except ApiError as e:
                    await self._send_text(event, format_api_error(e.code, e.message))
            return

        # 模板管理命令
        if args.startswith("模板"):
            await self._handle_template_command(event, user_id, args[2:].strip())
            return

        await self._send_text(
            event,
            "❌ 无法识别的管理命令\n"
            "💡 可用命令：\n"
            "  /管理 关 MMDD — 关闭日期（如 /管理 关 0701）\n"
            "  /管理 开 MMDD — 开放日期\n"
            "  /管理 跳周 — 跳到下一周并开放点歌\n"
            "  /管理 撤销跳周 — 撤销跳周操作\n"
            "  /管理 模板 — 管理消息模板"
        )

    async def _handle_template_command(self, event: AstrMessageEvent, user_id: str, args: str):
        """处理模板管理子命令"""
        if not args or args == "列表":
            # 列出所有模板（按分类）
            all_templates = self.templates.list_templates()
            categories = {}
            for t in all_templates:
                categories.setdefault(t["category"], []).append(t)

            lines = ["📝 消息模板列表\n"]
            for cat, items in sorted(categories.items()):
                lines.append(f"📂 {cat}:")
                for item in items:
                    override_mark = "✏️" if item["is_overridden"] else "  "
                    lines.append(f"  {override_mark} {item['key']} — {item['description']}")
                lines.append("")
            lines.append("💡 /管理 模板 查看 <key> — 查看模板详情")
            lines.append("💡 /管理 模板 修改 <key> <新模板> — 修改模板")
            lines.append("💡 /管理 模板 重置 <key> — 重置为默认")
            lines.append("💡 /管理 模板 预览 <key> — 预览渲染效果")
            await self._send_text(event, "\n".join(lines))
            return

        parts = args.split(maxsplit=2)
        sub_cmd = parts[0] if parts else ""

        if sub_cmd == "查看" and len(parts) >= 2:
            key = parts[1]
            tdef = self.templates.get_definition(key)
            if not tdef:
                await self._send_text(event, f"❌ 未知模板: {key}")
                return

            current = self.templates.get_raw(key)
            default = tdef.default
            is_overridden = current != default

            lines = [f"📝 模板: {key}", f"📖 {tdef.description}", ""]
            lines.append(f"当前值{'（已覆盖）' if is_overridden else '（默认）'}:")
            lines.append(f"  {current}")
            if is_overridden:
                lines.append(f"\n默认值:")
                lines.append(f"  {default}")
            if tdef.variables:
                lines.append(f"\n可用变量:")
                for v in tdef.variables:
                    lines.append(f"  {{{v.name}}} — {v.description}（例: {v.example}）")

            await self._send_text(event, "\n".join(lines))
            return

        if sub_cmd == "预览" and len(parts) >= 2:
            key = parts[1]
            preview = self.templates.preview(key)
            await self._send_text(event, f"👀 模板预览 [{key}]:\n\n{preview}")
            return

        if sub_cmd == "修改" and len(parts) >= 3:
            key = parts[1]
            new_template = parts[2]

            is_valid, errors = self.templates.validate(key, new_template)
            if not is_valid:
                await self._send_text(event, f"❌ 模板验证失败:\n" + "\n".join(errors))
                return

            if self.templates.update(key, new_template):
                # 持久化到配置
                self._save_config()
                await self._send_text(event, f"✅ 模板 {key} 已更新\n\n预览:\n{self.templates.preview(key)}")
            else:
                await self._send_text(event, f"❌ 模板更新失败")
            return

        if sub_cmd == "重置" and len(parts) >= 2:
            key = parts[1]
            if key == "全部":
                self.templates.reset_all()
                # 持久化到配置
                self._save_config()
                await self._send_text(event, "✅ 所有模板已重置为默认值")
            else:
                if self.templates.reset(key):
                    # 持久化到配置
                    self._save_config()
                    await self._send_text(event, f"✅ 模板 {key} 已重置为默认值")
                else:
                    await self._send_text(event, f"❌ 未知模板: {key}")
            return

        await self._send_text(
            event,
            "❌ 无法识别的模板命令\n"
            "💡 可用命令：\n"
            "  /管理 模板 — 列出所有模板\n"
            "  /管理 模板 查看 <key> — 查看模板详情\n"
            "  /管理 模板 预览 <key> — 预览渲染效果\n"
            "  /管理 模板 修改 <key> <新模板> — 修改模板\n"
            "  /管理 模板 重置 <key> — 重置为默认\n"
            "  /管理 模板 重置 全部 — 重置所有模板"
        )

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

        # 跳过命令消息（由 @filter.command 处理，避免重复响应）
        if text.startswith(("/", "！", "!")):
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

        # WAITING_INPUT 状态：检测链接 或 要求「搜索」前缀
        if conv.state == STATE_WAITING_INPUT:
            link_match = re.search(NETEASE_URL_PATTERN, text)
            if link_match:
                link = link_match.group(0)
                await self._do_check_and_confirm(event, user_id, link)
            elif text.startswith("搜索"):
                # 去掉「搜索」前缀后作为关键词
                keywords = text[2:].strip()
                if keywords:
                    await self._do_search(event, user_id, keywords)
                else:
                    await self._send_text(event, "🔍 请提供搜索关键词\n💡 格式：搜索 歌名 或 搜索 歌手 歌名")
            else:
                await self._send_text(
                    event,
                    "💡 请回复「搜索 歌名」搜索歌曲\n"
                    "💡 或直接发送网易云音乐链接\n"
                    "💡 回复「取消」退出点歌模式"
                )
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
            # 确认 → 直接进入留言填写
            self.conversations.set_state(user_id, STATE_WAITING_MESSAGE)
            await self._send_text(event, "💬 请输入留言（20字以内，回复「跳过」可不填）")
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
            closed_dates = []
            songs_by_day = {}
            if play_date.startswith("WEEKDAY:"):
                # 需要根据 weekStart 计算具体日期
                offset = int(play_date.split(":")[1])
                # 获取当前周期的 weekStart
                try:
                    cycle = await self.api.get_cycle_info()
                    week_start = cycle.get("weekStart", "")
                    play_date = resolve_weekday_to_date(offset, week_start)
                    closed_dates = cycle.get("closedDates", [])
                    songs_by_day = cycle.get("songsByDay", {})
                except ApiError:
                    await self._send_text(event, "❌ 获取周期信息失败，请重试")
                    return

            if play_date:
                # 检查是否为关闭日期
                if play_date in closed_dates:
                    await self._send_text(event, f"🚫 {play_date} 是休息日，不能点歌哦，请选择其他日期")
                    return

                # 检查是否已满
                song_count = songs_by_day.get(play_date, 0)
                if song_count >= 5:
                    await self._send_text(event, f"❌ {play_date} 已满（5/5），不能点歌了，请选择其他日期")
                    return

                self.conversations.set_data_field(user_id, "play_date", play_date)
                # 显示位置选择（带已有歌曲列表）
                await self._ask_position(event, user_id)
            else:
                await self._send_text(event, "❌ 日期无效，请重新选择或回复「跳过」")
        elif intent == INTENT_SKIP:
            # 跳过日期选择 → 直接提交
            await self._do_submit(event, user_id)
        else:
            await self._send_text(event, "💡 请回复日期（如：1、周一、明天）或「跳过」")

    async def _handle_waiting_position(self, event, user_id, intent, value):
        """WAITING_POSITION 状态：选择播放位置"""
        if intent == INTENT_NUMBER_PICK and value:
            # 检查位置是否已被占用
            data = self.conversations.get_data(user_id)
            play_date = data.play_date

            if play_date:
                try:
                    playlist = await self.api.get_playlist()
                    songs = playlist.get("songs", [])
                    date_songs = [s for s in songs if s.get("playDate") == play_date]
                    occupied_positions = {s.get("playPosition") for s in date_songs if s.get("playPosition")}

                    if value in occupied_positions:
                        await self._send_text(event, f"❌ 位置 {value} 已被占用，请选择其他位置或回复「跳过」")
                        return
                except ApiError:
                    # 获取失败，继续提交（后端会处理）
                    pass

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
            result = await self.api.check_song(link, uid=user_id)

            # 检查用户本周是否已点过歌
            if result.get("hasSubmittedThisWeek"):
                self.conversations.clear_user(user_id)
                await self._send_text(event, "🚫 你本周已经点过一首歌了，每人每周限点一首哦～\n下周再来点吧！")
                return

            # 保存数据
            data = self.conversations.get_data(user_id)
            data.link = link
            data.song_info = result
            self.conversations.set_state(user_id, STATE_WAITING_CONFIRM)

            # 分三条消息发送
            # 1. 歌曲信息
            text = format_song_info(result)
            await self._send_text(event, text)
            # 2. 封面图片
            cover_url = result.get("coverUrl", "")
            if cover_url:
                await event.send(MessageChain([Image.fromURL(cover_url)]))
            # 3. 确认提示
            await self._send_text(event, format_confirm_prompt())

        except ApiError as e:
            self.conversations.clear_user(user_id)
            await self._send_text(event, format_api_error(e.code, e.message))

    async def _ask_date(self, event: AstrMessageEvent, user_id: str):
        """询问播放日期选择"""
        try:
            cycle = await self.api.get_cycle_info()
            songs_by_day = cycle.get("songsByDay", {})
            week_start = cycle.get("weekStart", "")
            closed_dates = cycle.get("closedDates", [])
            text = format_date_prompt(songs_by_day, week_start, closed_dates)
            self.conversations.set_state(user_id, STATE_WAITING_DATE)
            await self._send_text(event, text)
        except ApiError as e:
            # 获取周期信息失败，直接提交（不选日期）
            await self._do_submit(event, user_id)

    async def _ask_position(self, event: AstrMessageEvent, user_id: str):
        """询问播放位置选择（显示当天已有歌曲）"""
        data = self.conversations.get_data(user_id)
        play_date = data.play_date

        if not play_date:
            # 没有选择日期，直接提交
            await self._do_submit(event, user_id)
            return

        try:
            # 获取该日期的歌曲列表
            playlist = await self.api.get_playlist()
            songs = playlist.get("songs", [])
            date_songs = [s for s in songs if s.get("playDate") == play_date]

            text = format_position_selection(play_date, date_songs)
            self.conversations.set_state(user_id, STATE_WAITING_POSITION)
            await self._send_text(event, text)
        except ApiError as e:
            # 获取失败，直接提交（自动分配位置）
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
                message=data.message,
                uid=user_id,
                preferred_play_date=data.play_date,
                preferred_play_position=data.play_position,
            )

            # 提交成功
            self.conversations.clear_user(user_id)
            message_display = data.message or ""
            text = format_submit_success(result, message_display)
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
