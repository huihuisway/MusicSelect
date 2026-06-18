# AstrBot 集成指南

> 本文档面向 AstrBot 插件开发者，说明如何通过 HTTP API 实现企业微信客服中的点歌、评论、查歌等交互。

---

## 目录

- [概览](#概览)
- [环境要求](#环境要求)
- [插件配置](#插件配置)
- [用户注册流程](#用户注册流程)
- [点歌流程](#点歌流程)
- [评论流程](#评论流程)
- [查询歌曲流程](#查询歌曲流程)
- [生成图片列表](#生成图片列表)
- [错误处理](#错误处理)
- [完整交互流程图](#完整交互流程图)

---

## 概览

```
┌─────────────┐     HTTP API      ┌──────────────────┐     网易云 API     ┌──────────────┐
│  企业微信    │ ◄──────────────► │  MusicSelect     │ ◄──────────────► │  Netease     │
│  用户       │    AstrBot        │  Backend :4000   │                  │  API :3030   │
│  (学生)     │    (插件)         │                  │                  │              │
└─────────────┘                   └──────────────────┘                  └──────────────┘
```

- 用户通过企业微信客服与 AstrBot 交互
- AstrBot 解析用户指令，调用 MusicSelect 后端 API
- 后端返回数据，AstrBot 格式化后回复用户（文字或图片）

---

## 环境要求

| 项目 | 要求 |
|------|------|
| MusicSelect 后端 | 运行在可达的 IP/域名，默认端口 4000 |
| 网络 | AstrBot 所在机器能访问 MusicSelect API（内网即可） |
| NeteaseCloudMusicApiEnhanced | 运行在 MusicSelect 配置的地址（默认 `localhost:3030`） |

---

## 插件配置

安装插件后，在 AstrBot 管理面板中进入插件设置页面，可配置以下参数：

| 配置项 | 类型 | 默认值 | 说明 |
|--------|------|--------|------|
| `api_base_url` | string | `http://localhost:4000/api` | MusicSelect 后端 API 地址 |
| `timeout` | int | `10` | HTTP 请求超时时间（秒） |
| `search_limit` | int | `5` | 搜索结果最大数量 |
| `conversation_timeout` | int | `600` | 多步对话超时时间（秒） |

### Docker 部署配置

当 AstrBot 运行在 Docker 容器中时，`localhost` 指向容器自身而非宿主机，需要将 `api_base_url` 修改为宿主机可达地址：

| 部署场景 | `api_base_url` 示例 |
|----------|---------------------|
| Docker Desktop（macOS/Windows） | `http://host.docker.internal:4000/api` |
| Linux Docker（同机） | `http://172.17.0.1:4000/api` 或 `http://<宿主机IP>:4000/api` |
| 跨机器部署 | `http://<后端服务IP>:4000/api` |

> **提示：** 也可在启动 AstrBot 容器时通过 `--add-host` 参数自定义主机名，如 `docker run --add-host musicselect:host-gateway ...`，然后配置为 `http://musicselect:4000/api`。

---

## 点歌流程

### 交互流程

```
用户: 点歌
Bot:  🎵 点歌
      请发送网易云音乐链接，并附上留言。
      格式：链接 + 留言
      例如：https://music.163.com/song?id=123456 祝大家考试顺利！

      当前剩余名额：13/25

用户: https://music.163.com/song?id=123456 祝大家考试顺利！
Bot:  [调用 POST /song/check 检查歌曲]
      → 如果失败：❌ 找不到该歌曲 / 本周已有人点过这首歌
      → 如果成功：

      🎵 确认提交？
      歌曲：夜曲 - 周杰伦
      专辑：十一月的萧邦
      留言：祝大家考试顺利！

      回复「确认」提交，回复「取消」放弃。

用户: 确认
Bot:  [调用 POST /song/submit]
      → 成功：✅ 点歌成功！
               《夜曲》- 周杰伦
               已加入本周歌单 🎉
      → 失败：❌ 点歌失败：本周名额已满
```

### API 调用步骤

**Step 1：检查歌曲（可选但推荐）**

```javascript
const checkRes = await fetch(`${API_BASE}/api/song/check`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ link: userLink }),
});
const checkData = await checkRes.json();

if (!checkData.success) {
  // 回复错误信息
  return;
}
if (checkData.data.alreadySubmitted) {
  // 回复：本周已有人点过这首歌
  return;
}
if (!checkData.data.isAvailable) {
  // 回复：该歌曲暂不可用
  return;
}
// 展示歌曲信息，等待用户确认
```

**Step 2：提交点歌**

```javascript
const user = userStore.get(wxUserId); // { submitterName, submitterClass }

const submitRes = await fetch(`${API_BASE}/api/song/submit`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    link: userLink,
    message: userMessage,
    uid: wxUserId,
  }),
});
const submitData = await submitRes.json();

if (submitData.success) {
  // 回复成功
} else {
  // 回复失败原因：submitData.message
}
```

### 解析用户消息

```javascript
function parseSongSubmission(text) {
  // 匹配网易云链接
  const linkMatch = text.match(/https?:\/\/[^\s]*music\.163\.com[^\s]*/);
  if (!linkMatch) return null;

  const link = linkMatch[0];
  // 链接后面的文字作为留言
  const message = text.replace(link, '').trim();

  return { link, message: message || null };
}
```

> **注意**：`message` 是可选字段。如果用户只发了链接没写留言，也可以提交。

---

## 评论流程

### 交互流程

```
用户: 本周歌曲 / 今日歌曲 / 上周歌曲
Bot:  [调用 GET /song/list 或 GET /song/calendar]
      [生成图片列表（见下方）]
      📅 本周歌单（2026-06-15）

      周一 06-15
      ① 夜曲 - 周杰伦
      ② 晴天 - 周杰伦
      ③ 稻香 - 周杰伦

      周二 06-16
      ① 起风了 - 买辣椒不用券
      ② ...

      💡 回复「评论 + 序号」可评论该歌曲
      例如：评论 14

用户: 评论 14
Bot:  你选择评论的是：
      《稻香》- 周杰伦（周一 第3首）

      请输入评论内容：

用户: 这首歌太棒了！每天听心情都好
Bot:  [调用 POST /comment]
      ✅ 评论成功！
      「这首歌太棒了！每天听心情都好」
```

### API 调用步骤

**Step 1：获取歌曲列表（带序号）**

```javascript
// 本周歌曲
const res = await fetch(`${API_BASE}/api/song/calendar`);
const data = await res.json();

// 为每首歌分配全局序号
let globalIndex = 0;
const songList = [];
for (const day of data.data.days) {
  for (const song of day.songs) {
    globalIndex++;
    songList.push({
      index: globalIndex,
      date: day.date,
      dayLabel: day.dayLabel,
      ...song,
    });
  }
}
// songList[13] 就是序号 14 的歌曲（0-indexed）
```

**Step 2：提交评论**

```javascript
const targetSong = songList[userIndex - 1]; // userIndex 是用户输入的序号（1-based）

const commentRes = await fetch(`${API_BASE}/api/comment`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    songId: targetSong.songId,
    content: userComment,
  }),
});
const commentData = await commentRes.json();
```

---

## 查询歌曲流程

### 支持的指令

| 指令 | 说明 | 调用的 API |
|------|------|-----------|
| 本周歌曲 / 歌单 | 当前周期全部歌曲 | `GET /song/calendar` |
| 今日歌曲 / 今天的歌 | 今天播放的歌曲 | `GET /song/list?date=YYYY-MM-DD` |
| 上周歌曲 | 上一个已归档周期 | `GET /song/history` → 取最后一个 week → `GET /song/history?week=xxx` |
| 剩余名额 / 统计 | 本周使用情况 | `GET /song/stats` |
| 点歌窗口 / 还能点歌吗 | 窗口是否开放 | `GET /song/current-cycle` |

### 回复示例

```
用户: 剩余名额
Bot:  📊 本周统计
      已提交：12/25
      剩余名额：13
      点歌窗口：开放中 ✅
      距关闭：48小时0分0秒
```

---

## 生成图片列表

企业微信中纯文字列表不够直观，建议将歌曲列表渲染为图片发送。

### 推荐方案

使用 `canvas`（Node.js `canvas` 库）或 `puppeteer` 将 HTML 渲染为图片。

### 列表布局参考

```
┌─────────────────────────────────┐
│  📅 本周歌单  2026-06-15        │
│  ─────────────────────────────  │
│                                 │
│  周一 06-15                     │
│  ┌──────────────────────────┐  │
│  │ 1. 夜曲     周杰伦       │  │
│  │    高三1班 张三           │  │
│  │ 2. 晴天     周杰伦       │  │
│  │    高二2班 王五           │  │
│  │ 3. 稻香     周杰伦       │  │
│  │    高三3班 赵六           │  │
│  └──────────────────────────┘  │
│                                 │
│  周二 06-16                     │
│  ┌──────────────────────────┐  │
│  │ 4. 起风了   买辣椒不用券  │  │
│  │    高一1班 孙七           │  │
│  │ ...                       │  │
│  └──────────────────────────┘  │
│                                 │
│  已提交 12/25                   │
└─────────────────────────────────┘
```

### 序号分配规则

按照日历顺序（周一→周五），每天按 playPosition 排序，全局递增编号：
- 周一第1首 = 序号 1
- 周一第2首 = 序号 2
- ...
- 周二第1首 = 序号 6（如果周一有5首）

**注意**：序号仅用于 Bot 交互中的引用，后端 API 使用 `songId` 标识歌曲。

---

## 错误处理

### 常见错误及回复建议

| API 返回 code | 场景 | Bot 回复建议 |
|---------------|------|-------------|
| 400 | 链接格式错误 | ❌ 链接格式有误，请检查是否为网易云音乐链接 |
| 400 | 缺少必填字段 | ❌ 信息不完整，请重新发送 |
| 403 | 不在窗口期 | ❌ 当前不在点歌时间内哦，请等待窗口开放 |
| 404 | 歌曲不存在 | ❌ 找不到这首歌，请检查链接是否正确 |
| 409 | 重复提交 | ⚠️ 这首歌本周已经有人点过了，换一首试试？ |
| 429 | 名额已满 | ❌ 本周名额已用完，请下周再来～ |
| 500 | 服务器错误 | ❌ 服务器出了点问题，请稍后再试 |

### 重试策略

```javascript
async function callApiWithRetry(url, options, maxRetries = 2) {
  for (let i = 0; i <= maxRetries; i++) {
    try {
      const res = await fetch(url, options);
      return await res.json();
    } catch (err) {
      if (i === maxRetries) throw err;
      await new Promise((r) => setTimeout(r, 1000 * (i + 1)));
    }
  }
}
```

---

## 完整交互流程图

```
                    ┌─────────┐
                    │  用户   │
                    └────┬────┘
                         │
            ┌────────────┼────────────────┐
            ▼            ▼                ▼
       「点歌」     「本周歌曲」      「评论 N」
            │            │                │
            │        ┌───┴───┐            │
            │        │ 已注册?│            │
            │        └───┬───┘            │
            │      否 ↙    ↘ 是           │
            ▼   提示注册    ▼              │
      等待注册输入   GET /calendar         │
            │        │                     │
            │     返回图片列表              │
            │        │                     │
            ▼        ▼                     ▼
      POST /submit  展示歌曲          POST /comment
            │                              │
            ▼                              ▼
       回复成功/失败                   回复评论成功
```

### AstrBot 插件状态机

```
States:
  IDLE              → 空闲，等待指令
  WAITING_REG_CLASS → 等待注册（班级+姓名）
  WAITING_SONG_LINK → 等待点歌链接
  WAITING_SONG_CONFIRM → 等待点歌确认
  WAITING_COMMENT_INPUT → 等待评论内容

Transitions:
  IDLE + 「点歌」 + 未注册       → WAITING_REG_CLASS
  IDLE + 「点歌」 + 已注册       → WAITING_SONG_LINK
  IDLE + 「本周歌曲」等查询      → IDLE（直接回复）
  IDLE + 「评论 N」              → WAITING_COMMENT_INPUT
  WAITING_REG_CLASS + 文本输入   → IDLE（注册完成）
  WAITING_SONG_LINK + 链接输入   → WAITING_SONG_CONFIRM（先 check）
  WAITING_SONG_CONFIRM + 「确认」→ IDLE（submit）
  WAITING_SONG_CONFIRM + 「取消」→ IDLE
  WAITING_COMMENT_INPUT + 文本   → IDLE（comment）
```
