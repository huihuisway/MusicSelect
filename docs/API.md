# MusicSelect API 文档

> **Base URL**: `http://<服务器地址>:4000/api`
>
> **版本**: v2.0.0
>
> **鉴权**: 无（内网信任）
>
> **响应格式**: 所有接口统一返回 JSON

---

## 目录

- [通用响应格式](#通用响应格式)
- [错误码一览](#错误码一览)
- [歌曲接口](#歌曲接口)
  - [POST /song/submit — 提交点歌](#post-songsubmit--提交点歌)
  - [POST /song/check — 检查歌曲](#post-songcheck--检查歌曲)
  - [GET /song/list — 获取歌曲列表](#get-songlist--获取歌曲列表)
  - [GET /song/current-cycle — 当前周期信息](#get-songcurrent-cycle--当前周期信息)
  - [GET /song/calendar — 日历视图数据](#get-songcalendar--日历视图数据)
  - [GET /song/history — 历史歌单](#get-songhistory--历史歌单)
  - [GET /song/stats — 本周统计](#get-songstats--本周统计)
- [评论接口](#评论接口)
  - [POST /comment — 提交评论](#post-comment--提交评论)
  - [GET /comment — 获取评论列表](#get-comment--获取评论列表)
- [下载接口](#下载接口)
  - [GET /song/download/:songId — 下载单首 MP3](#get-songdownloadidsongid--下载单首-mp3)
  - [POST /song/download — 批量下载周歌曲](#post-songdownload--批量下载周歌曲)
- [健康检查](#健康检查)
  - [GET /health — 健康检查](#get-health--健康检查)

---

## 通用响应格式

**成功：**

```json
{
  "success": true,
  "data": { ... }
}
```

**失败：**

```json
{
  "success": false,
  "code": 400,
  "message": "错误描述"
}
```

---

## 错误码一览

| HTTP 状态码 | 含义 | 常见场景 |
|-------------|------|----------|
| 400 | 请求参数错误 | 缺少必填字段、链接格式错误、播放位置不在 1-5 |
| 403 | 操作被禁止 | 不在点歌窗口期内 |
| 404 | 资源不存在 | 歌曲 ID 不存在 |
| 409 | 冲突 | 歌曲已在本周歌单中 / 本周歌曲已下载 / 该用户本周已点过（每人每周一首） |
| 429 | 配额已满 | 本周名额已满 / 当日空位已满 |
| 500 | 服务器内部错误 | 未知异常 |

---

## 歌曲接口

### POST /song/submit — 提交点歌

提交一首歌曲到当前点歌周期。

**请求头：**

| Header | 值 |
|--------|-----|
| Content-Type | application/json |

**请求体：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|:----:|------|
| link | string | ✅ | 网易云音乐链接 |
| submitterName | string | ✅ | 提交者姓名 |
| submitterClass | string | ✅ | 提交者班级 |
| message | string | ✅ | 留言内容 |
| uid | string | ❌ | 用户唯一标识（企业微信 userId 等），用于每人每周限点一首 |
| preferredPlayDate | string | ❌ | 期望播放日期 `YYYY-MM-DD` |
| preferredPlayPosition | number | ❌ | 期望播放位置 `1-5` |

**成功响应** `201 Created`：

```json
{
  "success": true,
  "data": {
    "songId": "123456789",
    "title": "夜曲",
    "artist": "周杰伦",
    "album": "十一月的萧邦",
    "coverUrl": "https://p1.music.126.net/xxx.jpg",
    "submitTime": "2026-06-15T12:00:00.000Z"
  }
}
```

**失败响应示例：**

```json
// 403 — 不在点歌窗口期
{ "success": false, "code": 403, "message": "当前不在点歌窗口期内" }

// 409 — 重复提交
{ "success": false, "code": 409, "message": "该歌曲已在本周歌单中" }

// 409 — 该用户本周已点过
{ "success": false, "code": 409, "message": "你本周已经点过一首歌了，每人每周限点一首" }

// 429 — 名额已满
{ "success": false, "code": 429, "message": "本周点歌名额已满" }
```

**调用示例：**

```bash
curl -X POST http://localhost:4000/api/song/submit \
  -H "Content-Type: application/json" \
  -d '{
    "link": "https://music.163.com/song?id=123456789",
    "submitterName": "张三",
    "submitterClass": "高三1班",
    "message": "祝大家考试顺利！"
  }'
```

```javascript
const res = await fetch('http://localhost:4000/api/song/submit', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    link: 'https://music.163.com/song?id=123456789',
    submitterName: '张三',
    submitterClass: '高三1班',
    message: '祝大家考试顺利！',
  }),
});
const data = await res.json();
```

---

### POST /song/check — 检查歌曲

在提交前检查歌曲是否有效、是否已提交、是否可下载。不会写入数据库。

**请求体：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|:----:|------|
| link | string | ✅ | 网易云音乐链接 |
| uid | string | ❌ | 用户唯一标识，用于检查本周是否已点过 |

**成功响应** `200`：

```json
{
  "success": true,
  "data": {
    "songId": "123456789",
    "title": "夜曲",
    "artist": "周杰伦",
    "album": "十一月的萧邦",
    "coverUrl": "https://p1.music.126.net/xxx.jpg",
    "alreadySubmitted": false,
    "isAvailable": true,
    "hasSubmittedThisWeek": false
  }
}
```

> `hasSubmittedThisWeek`：当传入 `uid` 时返回，表示该用户本周是否已点过歌。未传 `uid` 时为 `false`。

---

### GET /song/list — 获取歌曲列表

获取当前周期或指定周期的歌曲列表。

**查询参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|:----:|------|
| week | string | ❌ | 周期 `YYYY-MM-DD`（默认当前周期） |
| date | string | ❌ | 筛选日期 `YYYY-MM-DD` |

**成功响应** `200`：

```json
{
  "success": true,
  "data": {
    "weekStart": "2026-06-15",
    "isSubmissionOver": false,
    "count": 12,
    "songs": [
      {
        "songId": "123456789",
        "title": "夜曲",
        "artist": "周杰伦",
        "album": "十一月的萧邦",
        "coverUrl": "https://p1.music.126.net/xxx.jpg",
        "submitterName": "张三",
        "submitterClass": "高三1班",
        "message": "祝大家考试顺利！",
        "submitTime": "2026-06-13T19:30:00.000Z",
        "weekStart": "2026-06-15",
        "playDate": "2026-06-17",
        "playPosition": 3,
        "status": "pending"
      }
    ]
  }
}
```

> **注意**：当点歌窗口关闭后，接口只返回 `status: "approved"` 的歌曲。

---

### GET /song/current-cycle — 当前周期信息

**成功响应** `200`：

```json
{
  "success": true,
  "data": {
    "weekStart": "2026-06-15",
    "submissionOpen": true,
    "submittedCount": 12,
    "weeklyQuota": 25,
    "remaining": 13,
    "countdown": {
      "total": 172800,
      "hours": 48,
      "minutes": 0,
      "seconds": 0,
      "text": "48小时0分0秒"
    }
  }
}
```

---

### GET /song/calendar — 日历视图数据

返回当前（或指定）周期每天 5 个位置的歌曲分布。

**查询参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|:----:|------|
| week | string | ❌ | 周期 `YYYY-MM-DD` |

**成功响应** `200`：

```json
{
  "success": true,
  "data": {
    "weekStart": "2026-06-15",
    "days": [
      {
        "date": "2026-06-15",
        "dayOfWeek": 1,
        "dayLabel": "周一",
        "songs": [ ... ],
        "count": 3,
        "remaining": 2
      },
      {
        "date": "2026-06-16",
        "dayOfWeek": 2,
        "dayLabel": "周二",
        "songs": [],
        "count": 0,
        "remaining": 5
      }
    ],
    "total": 12,
    "remaining": 13
  }
}
```

---

### GET /song/history — 历史歌单

不传 `week` 返回历史周期列表；传 `week` 返回该周歌曲。

**查询参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|:----:|------|
| week | string | ❌ | 指定周期 `YYYY-MM-DD` |

**获取历史周列表** — `GET /song/history`：

```json
{
  "success": true,
  "data": {
    "weeks": ["2026-06-01", "2026-06-08", "2026-06-15"]
  }
}
```

**获取指定周歌曲** — `GET /song/history?week=2026-06-08`：

```json
{
  "success": true,
  "data": {
    "weekStart": "2026-06-08",
    "count": 20,
    "songs": [ ... ]
  }
}
```

---

### GET /song/stats — 本周统计

**成功响应** `200`：

```json
{
  "success": true,
  "data": {
    "weekStart": "2026-06-15",
    "weeklyQuota": 25,
    "submittedCount": 12,
    "remaining": 13,
    "isOpen": true
  }
}
```

---

## 评论接口

### POST /comment — 提交评论

为指定歌曲添加评论。

**请求体：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|:----:|------|
| songId | string | ✅ | 网易云歌曲 ID |
| authorName | string | ✅ | 评论者姓名 |
| authorClass | string | ✅ | 评论者班级 |
| content | string | ✅ | 评论内容 |

**成功响应** `201 Created`：

```json
{
  "success": true,
  "data": {
    "id": "c_1718438400000_a1b2c3",
    "songId": "123456789",
    "authorName": "李四",
    "authorClass": "高二3班",
    "content": "这首歌太棒了！",
    "createTime": "2026-06-15T14:00:00.000Z"
  }
}
```

**失败响应：**

```json
// 404 — 歌曲不存在
{ "success": false, "code": 404, "message": "歌曲不存在" }
```

**调用示例：**

```bash
curl -X POST http://localhost:4000/api/comment \
  -H "Content-Type: application/json" \
  -d '{
    "songId": "123456789",
    "authorName": "李四",
    "authorClass": "高二3班",
    "content": "这首歌太棒了！"
  }'
```

---

### GET /comment — 获取评论列表

**查询参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|:----:|------|
| songId | string | ✅ | 网易云歌曲 ID |

**成功响应** `200`：

```json
{
  "success": true,
  "data": {
    "songId": "123456789",
    "count": 3,
    "comments": [
      {
        "id": "c_1718438400000_a1b2c3",
        "songId": "123456789",
        "authorName": "李四",
        "authorClass": "高二3班",
        "content": "这首歌太棒了！",
        "createTime": "2026-06-15T14:00:00.000Z"
      }
    ]
  }
}
```

> 评论按创建时间倒序排列（最新在前）。

---

## 下载接口

### GET /song/download/:songId — 下载单首 MP3

下载指定歌曲的 MP3 文件（320kbps），由 ffmpeg 实时转码。

**路径参数：**

| 参数 | 类型 | 说明 |
|------|------|------|
| songId | string | 网易云歌曲 ID |

**成功响应** `200`：

直接返回 MP3 文件流（`Content-Type: application/octet-stream`）。

**失败响应：**

```json
{ "success": false, "code": 404, "message": "歌曲不存在" }
{ "success": false, "code": 500, "message": "下载失败" }
```

---

### POST /song/download — 批量下载周歌曲

下载指定周期所有已批准歌曲的 MP3 文件。

**请求体：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|:----:|------|
| weekStart | string | ❌ | 周期 `YYYY-MM-DD`（默认当前周期） |

**成功响应** `200`：

```json
{
  "success": true,
  "data": {
    "weekStart": "2026-06-15",
    "total": 20,
    "successCount": 18,
    "failCount": 2,
    "results": [
      { "songId": "123456789", "title": "夜曲", "index": 1, "success": true, "filePath": "..." },
      { "songId": "987654321", "title": "晴天", "index": 2, "success": false, "error": "未获取到下载链接" }
    ]
  }
}
```

> 同一周期重复调用会返回 `409`。

---

## 健康检查

### GET /health — 健康检查

**成功响应** `200`：

```json
{ "success": true, "message": "ok" }
```
