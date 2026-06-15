"""
消息格式化工具

将 API 返回的数据格式化为用户友好的消息文本。
同时提供封面图 URL，供主程序发送图片消息。
"""

from typing import Optional
from datetime import datetime, timedelta


# ========== 日期工具 ==========

WEEKDAY_NAMES = {
    0: "周一",
    1: "周二",
    2: "周三",
    3: "周四",
    4: "周五",
    5: "周六",
    6: "周日",
}


def _parse_date(date_str: str) -> Optional[datetime]:
    """解析 YYYY-MM-DD 格式日期"""
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except (ValueError, TypeError):
        return None


def _format_short_date(date_str: str) -> str:
    """将 2024-04-01 格式化为 04-01(周一)"""
    dt = _parse_date(date_str)
    if dt:
        weekday = WEEKDAY_NAMES.get(dt.weekday(), "")
        return f"{dt.strftime('%m-%d')}({weekday})"
    return date_str


# ========== 歌曲信息 ==========

def format_song_info(song_info: dict) -> tuple[str, Optional[str]]:
    """
    格式化歌曲信息（用于确认阶段）

    Args:
        song_info: {title, artist, coverUrl, album?, duration?}

    Returns:
        (text, cover_url)
    """
    title = song_info.get("title", "未知歌曲")
    artist = song_info.get("artist", "未知歌手")
    album = song_info.get("album", "")
    duration = song_info.get("duration", 0)
    cover_url = song_info.get("coverUrl", "")

    lines = [
        f"🎵 {title}",
        f"🎤 {artist}",
    ]
    if album:
        lines.append(f"💿 {album}")
    if duration:
        minutes = duration // 60000 if duration > 1000 else duration // 60
        seconds = (duration % 60000) // 1000 if duration > 1000 else duration % 60
        lines.append(f"⏱ {minutes}:{seconds:02d}")

    lines.append("")
    lines.append("✅ 回复「确认」提交 | ❌ 回复「取消」放弃")

    return "\n".join(lines), cover_url


def format_submit_success(song_data: dict, username: str, message: str) -> str:
    """
    格式化提交成功消息

    Args:
        song_data: {title, artist, ...}
        username: 提交者姓名
        message: 留言
    """
    title = song_data.get("title", "未知歌曲")
    artist = song_data.get("artist", "未知歌手")

    lines = [
        "✅ 点歌成功！",
        "",
        f"🎧 {title} - {artist}",
        f"👤 {username}",
    ]
    if message:
        lines.append(f"💬 {message}")

    return "\n".join(lines)


# ========== 搜索结果 ==========

def format_search_results(
    results: list, keywords: str
) -> str:
    """
    格式化搜索结果列表

    Args:
        results: [{songId, title, artist, album, ...}, ...]
        keywords: 搜索关键词
    """
    if not results:
        return f"🔍 未找到与「{keywords}」相关的歌曲，请换个关键词试试"

    lines = [f"🔍 「{keywords}」搜索结果：", ""]

    for i, song in enumerate(results, 1):
        title = song.get("title", "未知")
        artist = song.get("artist", "未知")
        lines.append(f"{i}. {title} - {artist}")

    lines.append("")
    lines.append("💡 回复编号选择歌曲（如：1）")
    lines.append("💡 回复「取消」放弃")

    return "\n".join(lines)


# ========== 歌单 ==========

def format_playlist(playlist_data: dict) -> str:
    """
    格式化当前周期歌单

    Args:
        playlist_data: {weekStart, songs: [{...}]}
    """
    week_start = playlist_data.get("weekStart", "")
    songs = playlist_data.get("songs", [])

    if not songs:
        return f"📋 本周（{week_start}）暂无歌曲，快来点一首吧！"

    lines = [f"📋 本周歌单（{week_start} 周）", ""]

    # 按日期分组
    songs_by_date = {}
    for song in songs:
        play_date = song.get("playDate")
        if play_date:
            songs_by_date.setdefault(play_date, []).append(song)
        else:
            songs_by_date.setdefault("未安排", []).append(song)

    for date_key in sorted(songs_by_date.keys()):
        date_songs = songs_by_date[date_key]
        if date_key == "未安排":
            date_label = "📅 未安排播放日期"
        else:
            date_label = f"📅 {_format_short_date(date_key)}"

        lines.append(date_label)
        for song in date_songs:
            title = song.get("title", "未知")
            artist = song.get("artist", "未知")
            username = song.get("username", "")
            position = song.get("playPosition")
            pos_str = f"[{position}]" if position else ""
            user_str = f" 👤{username}" if username else ""
            lines.append(f"  {pos_str}🎧 {title} - {artist}{user_str}")
        lines.append("")

    return "\n".join(lines)


# ========== 周期状态 ==========

def format_cycle_status(cycle_info: dict, stats: dict) -> str:
    """
    格式化周期状态信息

    Args:
        cycle_info: {isSubmissionOpen, submittedCount, remaining, countdown, songsByDay, weekStart, ...}
        stats: {weeklyQuota, submittedCount, remaining}
    """
    is_open = cycle_info.get("isSubmissionOpen", False)
    submitted = stats.get("submittedCount", 0)
    quota = stats.get("weeklyQuota", 25)
    remaining = stats.get("remaining", 0)

    countdown = cycle_info.get("countdown", {})
    remaining_str = countdown.get("remainingStr", "")
    countdown_type = countdown.get("type", "")

    lines = ["📊 当前状态", ""]
    lines.append(f"🎵 已提交：{submitted}/{quota}（剩余 {remaining} 首）")

    if is_open:
        lines.append(f"⏰ 点歌进行中 | 距离截止：{remaining_str}")
    else:
        lines.append(f"⏰ 点歌未开始 | 距离下次开放：{remaining_str}")

    week_start = cycle_info.get("weekStart", "")
    if week_start:
        lines.append(f"📅 播放周：{week_start}")

    # 每日分布
    songs_by_day = cycle_info.get("songsByDay", {})
    if songs_by_day:
        lines.append("")
        lines.append("📅 每日歌曲分布：")
        for date_key, count in songs_by_day.items():
            day_name = _format_short_date(date_key)
            bar = "█" * count + "░" * (5 - count)
            lines.append(f"  {day_name} {bar} {count}/5")

    return "\n".join(lines)


# ========== 历史 ==========

def format_history_weeks(weeks: list) -> str:
    """格式化历史周列表"""
    if not weeks:
        return "📚 暂无历史歌单"

    lines = ["📚 历史歌单列表", ""]
    for i, week in enumerate(weeks[:10], 1):  # 最多显示 10 周
        week_start = week.get("weekStart", "")
        count = week.get("count", 0)
        lines.append(f"{i}. {week_start}（{count} 首）")

    lines.append("")
    lines.append("💡 回复 /历史 <周起始日期> 查看详情（如：/历史 2024-04-01）")

    return "\n".join(lines)


def format_history_songs(history_data: dict) -> str:
    """
    格式化历史歌单

    Args:
        history_data: {weekStart, songs: [...]}
    """
    week_start = history_data.get("weekStart", "")
    songs = history_data.get("songs", [])

    if not songs:
        return f"📚 {week_start} 周暂无歌曲记录"

    lines = [f"📚 {week_start} 周歌单", ""]

    for i, song in enumerate(songs, 1):
        title = song.get("title", "未知")
        artist = song.get("artist", "未知")
        play_date = song.get("playDate", "")
        date_str = f"({_format_short_date(play_date)})" if play_date else ""
        lines.append(f"{i}. 🎧 {title} - {artist} {date_str}")

    return "\n".join(lines)


# ========== 日期选择提示 ==========

def format_date_prompt(songs_by_day: dict, week_start: str) -> str:
    """
    格式化日期选择提示

    Args:
        songs_by_day: {date: count, ...}
        week_start: 本周起始日期
    """
    lines = ["📅 请选择播放日期（回复日期或「跳过」）：", ""]

    for date_key, count in sorted(songs_by_day.items()):
        day_label = _format_short_date(date_key)
        if count >= 5:
            status = "已满"
        else:
            status = f"{count}/5"
        lines.append(f"  {day_label}  {status}")

    return "\n".join(lines)


# ========== 帮助 ==========

HELP_TEXT = """📖 点歌帮助

1️⃣ /点歌 - 进入点歌模式，之后可自由输入
2️⃣ /搜索 关键词 - 直接搜索歌曲
3️⃣ /歌单 - 查看本周歌单
4️⃣ /状态 - 查看点歌状态
5️⃣ /历史 - 查看历史歌单

💡 进入点歌模式后：
  · 发送网易云链接 → 直接点歌
  · 发送歌名/歌手 → 自动搜索
  · 支持语音消息！

⏰ 点歌时间：周五 19:00 ~ 周日 20:00
📋 每周限额：25 首
📅 每天最多播放 5 首"""


# ========== 错误消息映射 ==========

def format_api_error(error_code: int, error_message: str) -> str:
    """
    将 API 错误码映射为用户友好的消息
    """
    error_map = {
        400: "链接格式错误，请检查后重试",
        403: error_message,  # 直接使用后端返回的消息（区分不同 403 场景）
        409: error_message,  # 歌曲重复 / 位置占用
        429: "本周名额已满，请下周再试",
        500: "服务器开小差了，请稍后重试",
        503: "服务暂时不可用，请稍后重试",
        0: error_message,  # 网络错误等自定义错误
    }

    return f"❌ {error_map.get(error_code, error_message)}"


# ========== 通用提示 ==========

NOT_IN_SUBMISSION_WINDOW = (
    "❌ 当前不在点歌时间\n"
    "⏰ 点歌时间为每周五 19:00 ~ 周日 20:00\n"
    "💡 发送 /状态 查看当前周期信息"
)

WEEKLY_ALREADY_SUBMITTED = (
    "❌ 你本周已点过歌了\n"
    "📅 每周只能点一首歌，下周再来吧"
)

CANCELLED = "✅ 已取消"

CONVERSATION_EXPIRED = "⏰ 对话已超时（10分钟），请重新开始\n💡 发送 /点歌帮助 查看使用方法"
