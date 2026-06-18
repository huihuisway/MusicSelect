"""
消息模板注册表

定义所有可配置的消息模板及其元数据。
"""

from dataclasses import dataclass, field
from typing import List


@dataclass
class TemplateVar:
    """模板变量定义"""
    name: str
    description: str
    example: str


@dataclass
class TemplateDef:
    """模板定义"""
    key: str
    description: str
    default: str
    variables: List[TemplateVar] = field(default_factory=list)
    category: str = "general"


# 所有模板的注册表
TEMPLATE_REGISTRY = {
    # ===== 歌曲流程 =====
    "song_info": TemplateDef(
        key="song_info",
        description="歌曲信息展示（检测到歌曲后显示）",
        default="🎵 {title}\n🎤 {artist}\n💿 {album}\n⏱ {duration}",
        variables=[
            TemplateVar("title", "歌曲名", "晴天"),
            TemplateVar("artist", "歌手名", "周杰伦"),
            TemplateVar("album", "专辑名", "叶惠美"),
            TemplateVar("duration", "时长", "4:30"),
        ],
        category="song",
    ),
    "song_info_compact": TemplateDef(
        key="song_info_compact",
        description="歌曲信息展示（简化版，无专辑时长）",
        default="🎵 {title}\n🎤 {artist}",
        variables=[
            TemplateVar("title", "歌曲名", "晴天"),
            TemplateVar("artist", "歌手名", "周杰伦"),
        ],
        category="song",
    ),
    "confirm_prompt": TemplateDef(
        key="confirm_prompt",
        description="确认提交提示",
        default="✅ 回复「确认」提交 | ❌ 回复「取消」放弃",
        variables=[],
        category="song",
    ),
    "submit_success": TemplateDef(
        key="submit_success",
        description="提交成功消息",
        default="✅ 点歌成功！\n\n🎧 {title} - {artist}\n💬 {message}",
        variables=[
            TemplateVar("title", "歌曲名", "晴天"),
            TemplateVar("artist", "歌手名", "周杰伦"),
            TemplateVar("message", "用户留言", "毕业快乐！"),
        ],
        category="song",
    ),
    "weekly_limit_reached": TemplateDef(
        key="weekly_limit_reached",
        description="本周已点过歌提示",
        default="🚫 你本周已经点过一首歌了，每人每周限点一首哦～\n下周再来点吧！",
        variables=[],
        category="song",
    ),

    # ===== 搜索 =====
    "search_results": TemplateDef(
        key="search_results",
        description="搜索结果列表",
        default="🔍 「{keywords}」搜索结果：\n\n{results_list}\n\n💡 回复编号选择歌曲（如：1）\n💡 回复「取消」放弃",
        variables=[
            TemplateVar("keywords", "搜索关键词", "周杰伦"),
            TemplateVar("results_list", "格式化的结果列表（自动生成）", "1. 晴天 - 周杰伦\n2. ..."),
        ],
        category="search",
    ),
    "search_not_found": TemplateDef(
        key="search_not_found",
        description="搜索无结果",
        default="🔍 未找到与「{keywords}」相关的歌曲，请换个关键词试试",
        variables=[
            TemplateVar("keywords", "搜索关键词", "不存在的歌"),
        ],
        category="search",
    ),

    # ===== 歌单 & 状态 =====
    "playlist_header": TemplateDef(
        key="playlist_header",
        description="歌单标题行",
        default="📋 本周歌单（{week_start} 周）",
        variables=[TemplateVar("week_start", "周起始日期", "2024-04-01")],
        category="playlist",
    ),
    "playlist_empty": TemplateDef(
        key="playlist_empty",
        description="歌单为空",
        default="📋 本周（{week_start}）暂无歌曲，快来点一首吧！",
        variables=[TemplateVar("week_start", "周起始日期", "2024-04-01")],
        category="playlist",
    ),
    "cycle_status_header": TemplateDef(
        key="cycle_status_header",
        description="状态信息头部",
        default="📊 当前状态",
        variables=[],
        category="status",
    ),
    "cycle_status_line": TemplateDef(
        key="cycle_status_line",
        description="状态信息提交进度",
        default="🎵 已提交：{submitted}/{quota}（剩余 {remaining} 首）",
        variables=[
            TemplateVar("submitted", "已提交数", "10"),
            TemplateVar("quota", "周限额", "25"),
            TemplateVar("remaining", "剩余名额", "15"),
        ],
        category="status",
    ),
    "cycle_status_countdown_open": TemplateDef(
        key="cycle_status_countdown_open",
        description="状态-点歌进行中",
        default="⏰ 点歌进行中 | 距离截止：{remaining_time}",
        variables=[TemplateVar("remaining_time", "倒计时文本", "2天3小时")],
        category="status",
    ),
    "cycle_status_countdown_closed": TemplateDef(
        key="cycle_status_countdown_closed",
        description="状态-点歌未开始",
        default="⏰ 点歌未开始 | 距离下次开放：{remaining_time}",
        variables=[TemplateVar("remaining_time", "倒计时文本", "5天")],
        category="status",
    ),
    "cycle_status_skipped": TemplateDef(
        key="cycle_status_skipped",
        description="状态-管理员已跳周",
        default="⏰ {remaining_time}\n🔀 管理员已跳周",
        variables=[TemplateVar("remaining_time", "倒计时文本", "2天")],
        category="status",
    ),

    # ===== 历史 =====
    "history_weeks_header": TemplateDef(
        key="history_weeks_header",
        description="历史周列表头部",
        default="📚 历史歌单列表",
        variables=[],
        category="history",
    ),
    "history_empty": TemplateDef(
        key="history_empty",
        description="无历史记录",
        default="📚 暂无历史歌单",
        variables=[],
        category="history",
    ),
    "history_week_empty": TemplateDef(
        key="history_week_empty",
        description="指定周无记录",
        default="📚 {week_start} 周暂无歌曲记录",
        variables=[TemplateVar("week_start", "周起始日期", "2024-04-01")],
        category="history",
    ),

    # ===== 日期 & 位置 =====
    "date_prompt_header": TemplateDef(
        key="date_prompt_header",
        description="日期选择提示头部",
        default="📅 请选择播放日期（回复序号 1-5，回复「跳过」自动分配）：",
        variables=[],
        category="date",
    ),
    "date_closed": TemplateDef(
        key="date_closed",
        description="日期已满/关闭提示",
        default="🚫 {date} 是休息日，不能点歌哦，请选择其他日期",
        variables=[TemplateVar("date", "日期", "2024-04-03")],
        category="date",
    ),
    "date_full": TemplateDef(
        key="date_full",
        description="日期已满（5/5）",
        default="❌ {date} 已满（5/5），不能点歌了，请选择其他日期",
        variables=[
            TemplateVar("date", "日期", "2024-04-03"),
        ],
        category="date",
    ),
    "position_selection_header": TemplateDef(
        key="position_selection_header",
        description="位置选择头部",
        default="📍 {date} 当前位置：",
        variables=[TemplateVar("date", "日期", "2024-04-03")],
        category="position",
    ),
    "position_occupied_hint": TemplateDef(
        key="position_occupied_hint",
        description="位置被占用提示",
        default="❌ 位置 {position} 已被占用，请选择其他位置或回复「跳过」",
        variables=[TemplateVar("position", "位置编号", "3")],
        category="position",
    ),

    # ===== 流程 / 对话 =====
    "entry_mode": TemplateDef(
        key="entry_mode",
        description="进入点歌模式",
        default="🎵 已进入点歌模式\n\n💡 回复「搜索 歌名」搜索歌曲\n💡 或直接发送网易云音乐链接\n💡 回复「取消」退出点歌模式",
        variables=[],
        category="flow",
    ),
    "ask_message": TemplateDef(
        key="ask_message",
        description="请求输入留言",
        default="💬 请输入留言（20字以内，回复「跳过」可不填）",
        variables=[],
        category="flow",
    ),
    "cancelled": TemplateDef(
        key="cancelled",
        description="用户取消操作",
        default="✅ 已取消",
        variables=[],
        category="flow",
    ),
    "conversation_expired": TemplateDef(
        key="conversation_expired",
        description="对话超时",
        default="⏰ 对话已超时（10分钟），请重新开始\n💡 发送 /点歌帮助 查看使用方法",
        variables=[],
        category="flow",
    ),
    "state_error": TemplateDef(
        key="state_error",
        description="状态异常重置",
        default="⚠️ 状态异常，已重置。请发送 /点歌帮助 查看使用方法",
        variables=[],
        category="flow",
    ),
    "data_lost": TemplateDef(
        key="data_lost",
        description="提交数据丢失",
        default="❌ 提交数据丢失，请重新开始（/点歌）",
        variables=[],
        category="flow",
    ),
    "not_in_window": TemplateDef(
        key="not_in_window",
        description="不在提交时间窗口",
        default="❌ 当前不在允许时间\n⏰ 点歌时间为每周五 19:00 ~ 周日 20:00\n💡 发送 /状态 查看当前周期信息",
        variables=[],
        category="flow",
    ),
    "idle_unrecognized": TemplateDef(
        key="idle_unrecognized",
        description="IDLE状态无法识别输入",
        default="💡 我不太明白你的意思\n📖 发送 /点歌帮助 查看使用方法",
        variables=[],
        category="flow",
    ),
    "waiting_input_hint": TemplateDef(
        key="waiting_input_hint",
        description="等待输入模式提示",
        default="💡 请回复「搜索 歌名」搜索歌曲\n💡 或直接发送网易云音乐链接\n💡 回复「取消」退出点歌模式",
        variables=[],
        category="flow",
    ),
    "search_prefix_missing": TemplateDef(
        key="search_prefix_missing",
        description="搜索缺少关键词",
        default="🔍 请提供搜索关键词\n💡 格式：/搜索 歌名 或 歌手 歌名",
        variables=[],
        category="flow",
    ),
    "message_too_long": TemplateDef(
        key="message_too_long",
        description="留言超长",
        default="❌ 留言不能超过 100 字，或回复「跳过」",
        variables=[],
        category="flow",
    ),
    "number_out_of_range": TemplateDef(
        key="number_out_of_range",
        description="编号超出范围",
        default="❌ 编号超出范围，请输入 1-{max} 之间的数字",
        variables=[TemplateVar("max", "最大编号", "5")],
        category="flow",
    ),
    "date_invalid": TemplateDef(
        key="date_invalid",
        description="日期无效",
        default="❌ 日期无效，请重新选择或回复「跳过」",
        variables=[],
        category="flow",
    ),
    "cycle_info_failed": TemplateDef(
        key="cycle_info_failed",
        description="获取周期信息失败",
        default="❌ 获取周期信息失败，请重试",
        variables=[],
        category="flow",
    ),

    # ===== 帮助 =====
    "help_text": TemplateDef(
        key="help_text",
        description="点歌帮助",
        default="""📖 点歌帮助

1️⃣ /点歌 - 进入点歌模式
2️⃣ /搜索 关键词 - 直接搜索歌曲
3️⃣ /歌单 - 查看本周歌单
4️⃣ /状态 - 查看点歌状态
5️⃣ /历史 - 查看历史歌单

💡 进入点歌模式后：
  · 回复「搜索 歌名」搜索歌曲
  · 发送网易云链接直接点歌
  · 搜索结果回复编号选择
  · 可选择播放日期和位置（均可跳过）

⏰ 随时可点歌，但当天 12:00 后不能点当天的歌
📋 每周限额：25 首
📅 每天最多播放 5 首""",
        variables=[],
        category="help",
    ),

    # ===== 管理员 =====
    "admin_no_permission": TemplateDef(
        key="admin_no_permission",
        description="非管理员无法执行",
        default="🚫 你不是管理员，无法执行此操作",
        variables=[],
        category="admin",
    ),
    "admin_panel": TemplateDef(
        key="admin_panel",
        description="管理面板显示",
        default="🔧 管理面板\n\n📌 管理员 ID：{admin_id}\n📌 本周关闭日期：\n    {closed_dates}\n📌 跳周状态：{skip_status}\n\n💡 命令：\n  /管理 关 MMDD — 关闭指定日期（如 /管理 关 0701）\n  /管理 开 MMDD — 重新开放指定日期\n  /管理 跳周 — 跳到下一周并开放点歌\n  /管理 撤销跳周 — 撤销跳周操作\n  /管理 模板 — 管理消息模板",
        variables=[
            TemplateVar("admin_id", "管理员ID", "123456"),
            TemplateVar("closed_dates", "关闭日期列表", "2024-07-01\n    2024-07-02"),
            TemplateVar("skip_status", "跳周状态", "未激活"),
        ],
        category="admin",
    ),
    "admin_skip_week_success": TemplateDef(
        key="admin_skip_week_success",
        description="跳周成功",
        default="✅ 已跳到下一周（{week_start}）\n🎉 点歌窗口已开放，用户可以开始点歌了！\n\n💡 如需撤销，请使用：/管理 撤销跳周",
        variables=[TemplateVar("week_start", "新周起始日期", "2024-04-08")],
        category="admin",
    ),
    "admin_unskip_success": TemplateDef(
        key="admin_unskip_success",
        description="撤销跳周成功",
        default="✅ 已撤销跳周\n🔄 恢复正常周期计算",
        variables=[],
        category="admin",
    ),
    "admin_date_closed_success": TemplateDef(
        key="admin_date_closed_success",
        description="关闭日期成功",
        default="✅ 已关闭 {month}月{day}日 的点歌",
        variables=[
            TemplateVar("month", "月份", "7"),
            TemplateVar("day", "日期", "1"),
        ],
        category="admin",
    ),
    "admin_date_opened_success": TemplateDef(
        key="admin_date_opened_success",
        description="重新开放日期成功",
        default="✅ 已重新开放 {month}月{day}日 的点歌",
        variables=[
            TemplateVar("month", "月份", "7"),
            TemplateVar("day", "日期", "1"),
        ],
        category="admin",
    ),
    "admin_date_format_error": TemplateDef(
        key="admin_date_format_error",
        description="日期格式错误",
        default="❌ 日期格式错误\n💡 正确格式：/管理 关 0701（7月1日）",
        variables=[],
        category="admin",
    ),
    "admin_date_invalid": TemplateDef(
        key="admin_date_invalid",
        description="日期无效",
        default="❌ 日期无效：{month}月{day}日 不存在",
        variables=[
            TemplateVar("month", "月份", "13"),
            TemplateVar("day", "日期", "32"),
        ],
        category="admin",
    ),
    "admin_unknown_command": TemplateDef(
        key="admin_unknown_command",
        description="无法识别的管理命令",
        default="❌ 无法识别的管理命令\n💡 可用命令：\n  /管理 关 MMDD — 关闭日期（如 /管理 关 0701）\n  /管理 开 MMDD — 开放日期\n  /管理 跳周 — 跳到下一周并开放点歌\n  /管理 撤销跳周 — 撤销跳周操作\n  /管理 模板 — 管理消息模板",
        variables=[],
        category="admin",
    ),

    # ===== 错误 =====
    "error_429": TemplateDef(
        key="error_429",
        description="配额已满",
        default="满了，等下周提交",
        variables=[],
        category="error",
    ),
    "error_500": TemplateDef(
        key="error_500",
        description="服务器错误",
        default="服务器被大运创飞了，请稍后重试",
        variables=[],
        category="error",
    ),
    "error_503": TemplateDef(
        key="error_503",
        description="服务不可用",
        default="服务暂时不可用，请稍后重试",
        variables=[],
        category="error",
    ),
}
