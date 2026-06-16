"""
对话状态机

管理用户的多步骤交互状态。
每个用户（user_id）在任意时刻最多有一个活跃的对话状态。
超时自动清理（默认 10 分钟）。
"""

import time
from typing import Optional
from dataclasses import dataclass, field

from .intent import (
    STATE_IDLE,
    STATE_WAITING_CONFIRM,
    STATE_WAITING_SEARCH_PICK,
    STATE_WAITING_MESSAGE,
    STATE_WAITING_DATE,
    STATE_WAITING_POSITION,
)


@dataclass
class ConversationData:
    """对话过程中收集的数据"""
    # 歌曲信息
    link: Optional[str] = None
    song_info: Optional[dict] = None  # check API 返回的歌曲信息
    search_results: Optional[list] = None  # 搜索结果列表

    # 用户填写的信息
    message: Optional[str] = None
    play_date: Optional[str] = None
    play_position: Optional[int] = None


@dataclass
class ConversationState:
    """用户的对话状态"""
    state: str = STATE_IDLE
    data: ConversationData = field(default_factory=ConversationData)
    last_active: float = field(default_factory=time.time)

    def update_activity(self):
        self.last_active = time.time()

    def is_expired(self, timeout: int) -> bool:
        return (time.time() - self.last_active) > timeout

    def reset(self):
        self.state = STATE_IDLE
        self.data = ConversationData()
        self.last_active = time.time()


class ConversationManager:
    """
    对话管理器

    管理所有用户的对话状态，支持超时清理。
    """

    def __init__(self, timeout: int = 600):
        self.timeout = timeout
        self._states: dict[str, ConversationState] = {}

    def get_state(self, user_id: str) -> ConversationState:
        """获取用户的对话状态，不存在则返回默认 IDLE 状态"""
        state = self._states.get(user_id)

        if state is None:
            state = ConversationState()
            self._states[user_id] = state
            return state

        # 检查超时
        if state.is_expired(self.timeout):
            state.reset()

        return state

    def set_state(self, user_id: str, new_state: str) -> ConversationState:
        """设置用户的对话状态"""
        state = self.get_state(user_id)
        state.state = new_state
        state.update_activity()
        return state

    def get_data(self, user_id: str) -> ConversationData:
        """获取用户的数据收集对象"""
        return self.get_state(user_id).data

    def set_data_field(self, user_id: str, field_name: str, value):
        """设置数据字段"""
        data = self.get_data(user_id)
        if hasattr(data, field_name):
            setattr(data, field_name, value)
        self.get_state(user_id).update_activity()

    def clear_user(self, user_id: str):
        """清除用户对话状态（取消或完成时调用）"""
        if user_id in self._states:
            del self._states[user_id]

    def cleanup_expired(self) -> list:
        """
        清理所有超时的对话状态。

        Returns:
            被清理的 user_id 列表
        """
        expired_users = []
        for user_id, state in list(self._states.items()):
            if state.is_expired(self.timeout):
                expired_users.append(user_id)
                del self._states[user_id]
        return expired_users

    @property
    def active_count(self) -> int:
        """当前活跃对话数"""
        return len(self._states)

    def get_all_states(self) -> dict:
        """获取所有用户状态（调试用）"""
        return {uid: s.state for uid, s in self._states.items()}
