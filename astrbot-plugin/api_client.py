"""
MusicSelect 后端 API 客户端

封装所有与后端的 HTTP 通信，使用 httpx.AsyncClient 实现异步请求。
"""

import httpx
from typing import Optional


class ApiError(Exception):
    """API 调用异常"""

    def __init__(self, code: int, message: str):
        self.code = code
        self.message = message
        super().__init__(f"[{code}] {message}")


class MusicSelectApiClient:
    """MusicSelect 后端 API 客户端"""

    def __init__(self, base_url: str, timeout: int = 10):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(self.timeout),
            )
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def _request(
        self, method: str, path: str, **kwargs
    ) -> dict:
        """统一请求方法，自动处理错误"""
        client = await self._get_client()
        try:
            response = await client.request(method, path, **kwargs)

            # 处理成功响应（200 或 201）
            if response.status_code in (200, 201):
                data = response.json()
                if data.get("success"):
                    return data.get("data", {})
                else:
                    raise ApiError(
                        data.get("code", response.status_code),
                        data.get("message", "请求失败"),
                    )

            # 处理 HTTP 错误
            try:
                error_data = response.json()
                raise ApiError(
                    error_data.get("code", response.status_code),
                    error_data.get("message", "请求失败"),
                )
            except (ValueError, KeyError):
                raise ApiError(
                    response.status_code,
                    f"HTTP {response.status_code} 错误",
                )

        except httpx.ConnectError:
            raise ApiError(0, "无法连接到服务器，请联系管理员")
        except httpx.TimeoutException:
            raise ApiError(0, "请求超时，请稍后重试")
        except httpx.HTTPError as e:
            raise ApiError(0, f"网络错误：{str(e)}")

    # ========== 歌曲相关 ==========

    async def check_song(self, link: str, uid: Optional[str] = None) -> dict:
        """
        检查歌曲是否可提交

        Returns:
            {songId, alreadySubmitted, isAvailable, hasSubmittedThisWeek, title, artist, coverUrl}
        """
        payload = {"link": link}
        if uid:
            payload["uid"] = uid
        return await self._request(
            "POST",
            "/song/check",
            json=payload,
        )

    async def submit_song(
        self,
        link: str,
        message: Optional[str] = None,
        uid: Optional[str] = None,
        preferred_play_date: Optional[str] = None,
        preferred_play_position: Optional[int] = None,
    ) -> dict:
        """
        提交歌曲

        Returns:
            {songId, title, artist, coverUrl, submitTime}
        """
        payload = {"link": link}
        if message:
            payload["message"] = message
        if uid:
            payload["uid"] = uid
        if preferred_play_date:
            payload["preferredPlayDate"] = preferred_play_date
        if preferred_play_position:
            payload["preferredPlayPosition"] = preferred_play_position

        return await self._request(
            "POST",
            "/song/submit",
            json=payload,
        )

    async def search_songs(self, keywords: str, limit: int = 5) -> list:
        """
        搜索歌曲

        Returns:
            [{songId, title, artist, album, coverUrl, duration}, ...]
        """
        data = await self._request(
            "GET",
            "/song/search",
            params={"keywords": keywords, "limit": limit},
        )
        return data.get("results", [])

    # ========== 歌单 & 状态 ==========

    async def get_playlist(self) -> dict:
        """
        获取当前周期歌单

        Returns:
            {weekStart, songs: [{songId, title, artist, coverUrl, username, message, playDate, playPosition}, ...]}
        """
        return await self._request("GET", "/song/list")

    async def get_cycle_info(self) -> dict:
        """
        获取当前周期信息（含倒计时、每日分布等）

        Returns:
            {weekStart, weekEnd, submissionStart, submissionEnd,
             submittedCount, remaining, isSubmissionOpen, serverTime,
             songsByDay, countdown}
        """
        return await self._request("GET", "/song/current-cycle")

    async def get_stats(self) -> dict:
        """
        获取剩余名额统计

        Returns:
            {weekStart, weeklyQuota, submittedCount, remaining}
        """
        return await self._request("GET", "/song/stats")

    # ========== 历史 ==========

    async def get_history_weeks(self) -> list:
        """
        获取历史周列表

        Returns:
            [{weekStart, count}, ...]
        """
        data = await self._request("GET", "/song/history-weeks")
        return data.get("weeks", [])

    async def get_history(self, week_start: str) -> dict:
        """
        获取指定周的历史歌单

        Returns:
            {weekStart, songs: [...]}
        """
        return await self._request("GET", f"/song/history/{week_start}")

    # ========== 关闭日期 ==========

    async def get_closed_dates(self, week_start: Optional[str] = None) -> list:
        """
        获取关闭日期列表

        Returns:
            [{date, weekStart, reason}, ...]
        """
        params = {}
        if week_start:
            params["weekStart"] = week_start
        data = await self._request("GET", "/song/closed-dates", params=params)
        return data.get("closedDates", [])

    async def add_closed_date(self, date: str, week_start: str, reason: str = "") -> dict:
        """添加关闭日期"""
        return await self._request(
            "POST",
            "/song/closed-dates",
            json={"date": date, "weekStart": week_start, "reason": reason},
        )

    async def remove_closed_date(self, date: str) -> dict:
        """移除关闭日期"""
        return await self._request(
            "DELETE",
            "/song/closed-dates",
            json={"date": date},
        )
