"""
自然语言意图识别

基于关键词 + 对话状态上下文匹配，无需 LLM。
支持语音消息（到达时已是文本）和普通文字消息。
"""

import re
from datetime import datetime, timedelta
from typing import Optional


# ========== 意图类型 ==========

INTENT_CONFIRM = "CONFIRM"
INTENT_CANCEL = "CANCEL"
INTENT_SKIP = "SKIP"
INTENT_DATE_SELECT = "DATE_SELECT"
INTENT_NUMBER_PICK = "NUMBER_PICK"
INTENT_SEARCH = "SEARCH"
INTENT_NAME = "NAME"
INTENT_CLASS = "CLASS"
INTENT_USERNAME = "USERNAME"
INTENT_MESSAGE = "MESSAGE"
INTENT_UNKNOWN = "UNKNOWN"

# ========== 对话状态 ==========

STATE_IDLE = "IDLE"
STATE_WAITING_INPUT = "WAITING_INPUT"
STATE_WAITING_CONFIRM = "WAITING_CONFIRM"
STATE_WAITING_SEARCH_PICK = "WAITING_SEARCH_PICK"
STATE_WAITING_USERNAME = "WAITING_USERNAME"
STATE_WAITING_CLASS = "WAITING_CLASS"
STATE_WAITING_MESSAGE = "WAITING_MESSAGE"
STATE_WAITING_DATE = "WAITING_DATE"
STATE_WAITING_POSITION = "WAITING_POSITION"

# ========== 关键词表 ==========

CONFIRM_KEYWORDS = [
    "确认", "确定", "好的", "没问题", "提交", "就这个", "对的",
    "是", "好", "行", "可以", "嗯", "ok", "OK", "yes", "对",
    "就这样", "就这样吧", "没问题", "通过", "同意",
]

CANCEL_KEYWORDS = [
    "取消", "算了", "不要了", "退出", "不点", "不提交了",
    "不了", "作罢", "不", "放弃", "不选", "算了不点了",
]

SKIP_KEYWORDS = [
    "跳过", "不用了", "没有", "不填", "不要了", "无", "空",
    "不需要", "不用", "略过", "没有留言", "不想填",
]

# 中文数字映射
CN_NUM_MAP = {
    "一": 1, "二": 2, "三": 3, "四": 4, "五": 5,
    "两": 2, "壹": 1, "贰": 2, "叁": 3, "肆": 4, "伍": 5,
}

# 星期映射（偏移量，周一=0）
WEEKDAY_KEYWORDS = {
    "周一": 0, "星期一": 0, "礼拜一": 0,
    "周二": 1, "星期二": 1, "礼拜二": 1,
    "周三": 2, "星期三": 2, "礼拜三": 2,
    "周四": 3, "星期四": 3, "礼拜四": 3,
    "周五": 4, "星期五": 4, "礼拜五": 4,
}

# 日期相对词
RELATIVE_DATE_KEYWORDS = {
    "今天": 0,
    "明天": 1,
    "后天": 2,
    "大后天": 3,
}


# ========== 意图解析函数 ==========

def parse_intent(text: str, state: str) -> tuple:
    """
    解析用户输入的意图。

    Args:
        text: 用户输入的文本（已去除首尾空白）
        state: 当前对话状态

    Returns:
        (intent_type, value) 元组
        - intent_type: 意图类型字符串
        - value: 关联值（如日期、编号、关键词等）
    """
    text = text.strip()

    if not text:
        return (INTENT_UNKNOWN, None)

    # --- 全局优先匹配（任何状态下都生效）---

    # 1. 取消（最高优先级，任何状态都能取消）
    if _matches_keywords(text, CANCEL_KEYWORDS):
        return (INTENT_CANCEL, None)

    # --- 根据状态进行语义解析 ---

    if state == STATE_WAITING_CONFIRM:
        return _parse_confirm_state(text)

    elif state == STATE_WAITING_SEARCH_PICK:
        return _parse_search_pick_state(text)

    elif state == STATE_WAITING_USERNAME:
        return _parse_name_state(text)

    elif state == STATE_WAITING_CLASS:
        return _parse_class_state(text)

    elif state == STATE_WAITING_MESSAGE:
        return _parse_message_state(text)

    elif state == STATE_WAITING_DATE:
        return _parse_date_state(text)

    elif state == STATE_WAITING_POSITION:
        return _parse_position_state(text)

    elif state == STATE_WAITING_INPUT:
        return _parse_waiting_input_state(text)

    elif state == STATE_IDLE:
        return (INTENT_UNKNOWN, None)  # IDLE 状态下不解析，需先执行命令

    else:
        return (INTENT_UNKNOWN, None)


# ========== 各状态的解析逻辑 ==========

def _parse_waiting_input_state(text: str) -> tuple:
    """WAITING_INPUT 状态（/点歌 后）：必须以「搜索」开头才触发搜索，链接由 on_message 处理"""
    text = text.strip()
    # 以「搜索」开头 → 去掉前缀后作为搜索关键词
    m = re.match(r'^搜索\s*(.+)', text)
    if m:
        return (INTENT_SEARCH, m.group(1).strip())
    return (INTENT_UNKNOWN, None)


def _parse_confirm_state(text: str) -> tuple:
    """WAITING_CONFIRM 状态：等待确认/取消"""
    if _matches_keywords(text, CONFIRM_KEYWORDS):
        return (INTENT_CONFIRM, None)
    if _matches_keywords(text, SKIP_KEYWORDS):
        return (INTENT_SKIP, None)
    # 其他输入视为取消
    return (INTENT_CANCEL, None)


def _parse_search_pick_state(text: str) -> tuple:
    """WAITING_SEARCH_PICK 状态：选择搜索结果编号"""
    # 尝试匹配纯数字
    num = _extract_number(text)
    if num is not None and 1 <= num <= 20:
        return (INTENT_NUMBER_PICK, num)

    # 确认类（选择第一个）
    if _matches_keywords(text, CONFIRM_KEYWORDS):
        return (INTENT_NUMBER_PICK, 1)

    return (INTENT_UNKNOWN, None)


def _parse_name_state(text: str) -> tuple:
    """WAITING_USERNAME 状态：输入姓名"""
    if _matches_keywords(text, SKIP_KEYWORDS):
        return (INTENT_SKIP, None)
    if len(text) <= 20:
        return (INTENT_NAME, text)
    return (INTENT_UNKNOWN, None)


def _parse_class_state(text: str) -> tuple:
    """WAITING_CLASS 状态：输入班级"""
    if _matches_keywords(text, SKIP_KEYWORDS):
        return (INTENT_SKIP, None)
    if len(text) <= 30:
        return (INTENT_CLASS, text)
    return (INTENT_UNKNOWN, None)


def _parse_message_state(text: str) -> tuple:
    """WAITING_MESSAGE 状态：输入留言"""
    if _matches_keywords(text, SKIP_KEYWORDS):
        return (INTENT_SKIP, None)
    # 非跳过则视为留言
    if len(text) <= 100:
        return (INTENT_MESSAGE, text)
    return (INTENT_UNKNOWN, None)


def _parse_date_state(text: str) -> tuple:
    """WAITING_DATE 状态：选择播放日期（支持序号 1-5、周几、相对日期）"""
    if _matches_keywords(text, SKIP_KEYWORDS):
        return (INTENT_SKIP, None)

    # 尝试解析数字 1-5 → 映射为周一到周五
    num = _extract_number(text)
    if num is not None and 1 <= num <= 5 and text.strip().isdigit():
        return (INTENT_DATE_SELECT, f"WEEKDAY:{num - 1}")

    # 尝试解析日期文本
    date_str = _extract_date(text)
    if date_str:
        return (INTENT_DATE_SELECT, date_str)

    return (INTENT_UNKNOWN, None)


def _parse_position_state(text: str) -> tuple:
    """WAITING_POSITION 状态：选择播放位置 1-5"""
    if _matches_keywords(text, SKIP_KEYWORDS):
        return (INTENT_SKIP, None)

    num = _extract_number(text)
    if num is not None and 1 <= num <= 5:
        return (INTENT_NUMBER_PICK, num)

    return (INTENT_UNKNOWN, None)


def _parse_idle_state(text: str) -> tuple:
    """IDLE 状态：自然语言输入 → 搜索"""
    # 清理常见前缀词
    cleaned = _clean_search_text(text)
    if cleaned:
        return (INTENT_SEARCH, cleaned)
    return (INTENT_UNKNOWN, None)


# ========== 辅助函数 ==========

def _matches_keywords(text: str, keywords: list) -> bool:
    """检查文本是否匹配关键词列表中的任意一个"""
    text_lower = text.lower().strip()
    for kw in keywords:
        if kw == text_lower or kw in text:
            return True
    return False


def _extract_number(text: str) -> Optional[int]:
    """
    从文本中提取数字。

    支持格式：
    - 纯数字: "1", "3"
    - 中文数字: "第一个", "选三"
    - 混合: "选1"
    """
    # 纯数字
    num_match = re.search(r'(\d+)', text)
    if num_match:
        return int(num_match.group(1))

    # "第X个" 中文数字
    cn_match = re.search(r'第([一二三四五两])', text)
    if cn_match:
        return CN_NUM_MAP.get(cn_match.group(1))

    return None


def _extract_date(text: str) -> Optional[str]:
    """
    从文本中提取日期，返回 YYYY-MM-DD 格式。

    支持格式：
    - 周几: "周一", "星期二"
    - 相对日期: "明天", "后天"
    - 完整日期: "2024-04-01", "4月1日"
    """
    text_lower = text.strip()

    # 星期关键词（需要基于当前周期计算具体日期）
    for kw, offset in WEEKDAY_KEYWORDS.items():
        if kw in text_lower:
            # 返回占位符，由调用方根据周期计算具体日期
            return f"WEEKDAY:{offset}"

    # 相对日期
    for kw, days_ahead in RELATIVE_DATE_KEYWORDS.items():
        if kw in text_lower:
            target_date = datetime.now() + timedelta(days=days_ahead)
            return target_date.strftime("%Y-%m-%d")

    # YYYY-MM-DD 格式
    date_match = re.search(r'(\d{4})-(\d{1,2})-(\d{1,2})', text)
    if date_match:
        year, month, day = date_match.groups()
        try:
            dt = datetime(int(year), int(month), int(day))
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            pass

    # MM-DD 或 M月D日 格式（假设今年）
    date_match2 = re.search(r'(\d{1,2})月(\d{1,2})[日号]?', text)
    if date_match2:
        month, day = date_match2.groups()
        year = datetime.now().year
        try:
            dt = datetime(year, int(month), int(day))
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            pass

    return None


def _clean_search_text(text: str) -> Optional[str]:
    """
    清理搜索文本，去除常见的无关前缀词。

    "帮我点一首周杰伦的晴天" → "周杰伦 晴天"
    "我想听周杰伦的晴天" → "周杰伦 晴天"
    "搜索周杰伦晴天" → "周杰伦 晴天"
    """
    # 去除常见前缀
    prefixes = [
        r'^帮我点(一)?首?',
        r'^点(一)?首?',
        r'^我想听',
        r'^我想点',
        r'^帮我搜(索)?',
        r'^搜(索)?',
        r'^找(一)?(?:首|个)?',
        r'^查(一)?(?:首|个)?',
        r'^播放',
        r'^来一?首?',
        r'^我要听',
        r'^我要点',
    ]

    cleaned = text
    for prefix in prefixes:
        cleaned = re.sub(prefix, '', cleaned).strip()

    # 去除 "的歌" / "的歌曲" / "那首歌" 等后缀
    suffixes = [
        r'的?歌(?:曲)?$',
        r'那首歌$',
        r'这首$',
    ]
    for suffix in suffixes:
        cleaned = re.sub(suffix, '', cleaned).strip()

    # 如果清理后为空，使用原文
    if not cleaned:
        cleaned = text

    # 将 "的" 替换为空格（"周杰伦的晴天" → "周杰伦 晴天"）
    cleaned = cleaned.replace("的", " ").strip()

    # 去除多余空格
    cleaned = re.sub(r'\s+', ' ', cleaned)

    return cleaned if cleaned else None


def resolve_weekday_to_date(weekday_offset: int, week_start: str) -> Optional[str]:
    """
    将星期偏移量（0=周一）转换为具体日期。

    Args:
        weekday_offset: 0-4 表示周一到周五
        week_start: 当前周期的 weekStart (YYYY-MM-DD)

    Returns:
        YYYY-MM-DD 格式的日期，或 None（如果超出范围）
    """
    if not (0 <= weekday_offset <= 4):
        return None

    try:
        start_date = datetime.strptime(week_start, "%Y-%m-%d")
        target_date = start_date + timedelta(days=weekday_offset)
        return target_date.strftime("%Y-%m-%d")
    except ValueError:
        return None
