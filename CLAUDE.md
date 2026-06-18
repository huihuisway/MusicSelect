# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**MusicSelect** —— 校园音乐选择工具。后端提供 RESTful API，前端为只读展示页（React + MagicUI/Tailwind）。所有用户交互（点歌、评论）通过 **AstrBot 企业微信客服** 完成，AstrBot 作为 HTTP 客户端调用后端 API。

## Commands

```bash
# 后端
npm install            # 安装后端依赖
npm run dev            # 开发模式（热重载，端口 4000）
npm start              # 生产模式

# 前端（在 web/ 目录下）
cd web && npm install  # 安装前端依赖
cd web && npm run dev  # 前端开发服务器（端口 5173，自动代理 /api 到后端）
cd web && npm run build # 构建生产版本到 web/dist/

# 一键安装所有依赖
npm run setup

# 健康检查
curl http://localhost:4000/api/health
```

## Tech Stack

| 层 | 技术 |
|----|------|
| 后端 | Node.js >= 18, Express.js (ES Modules) |
| 数据库 | lowdb 7.x (JSON 文件: `data/db.json`) |
| 前端 | React 18 + Vite + Tailwind CSS 3 + Framer Motion |
| 音频 | ffmpeg-static (MP3 320kbps 转码) |
| 定时 | node-cron |
| 缓存 | node-cache (1h TTL) |
| 外部 API | NeteaseCloudMusicApiEnhanced (`NETEASE_API_BASE`, 默认 :3030) |
| 客户端 | AstrBot (企业微信客服) |

## Architecture

```
server/
├── index.js                  # Express 入口: 中间件、路由、静态托管、错误处理
├── database/db.js            # lowdb 封装: Songs/Comments/Archives/DownloadRecords CRUD
├── routes/
│   ├── songRoutes.js         # 歌曲 API (submit/check/list/calendar/history/stats)
│   ├── commentRoutes.js      # 评论 API (post/get)
│   └── downloadRoutes.js     # MP3 下载 API (单首/批量)
├── utils/
│   ├── dateUtils.js          # UTC+8 周期计算, 窗口判断, 倒计时, 链接解析
│   ├── neteaseApi.js         # 网易云 API (song/detail, download/url) 带缓存
│   └── songDownloader.js     # axios 下载 → ffmpeg 转码 → 保存 downloader/
└── tasks/cronJobs.js         # 定时: 每30min检查下载, 每周五19:05归档

web/                          # React + Vite + Tailwind (只读展示)
├── src/
│   ├── App.jsx               # 路由: /, /day/:date, /history, /history/:week
│   ├── pages/                # Home, DayDetail, History, WeekDetail
│   ├── components/           # Layout, Calendar, SongCard, CommentList
│   └── api/index.js          # axios 封装
└── vite.config.js            # 开发代理 /api → localhost:4000
```

## Key Design Decisions

- **无鉴权**：内网信任，AstrBot 直接调用 API
- **无 IP 限流 / 无验证码**：已完全移除
- **无后台管理 / 无网页提交**：所有写入操作由 AstrBot 完成
- **用户身份**：AstrBot 通过 `uid` 标识用户，后端信任
- **评论模型**：独立 Comments 集合，一首歌可有多条评论
- **所有时间基于 UTC+8 (北京时间)**
- **周期规则**：点歌窗口周五 19:00 — 周日 20:00，播放周期下周一至周五
- **weekStart**：播放周期周一日期 (YYYY-MM-DD)

## Data Models

### Songs (`data/db.json → songs[]`)
```json
{
  "songId": "123456", "title": "歌名", "artist": "歌手", "album": "专辑",
  "coverUrl": "封面URL",
  "message": "留言", "uid": "用户ID|null", "submitTime": "ISO", "weekStart": "YYYY-MM-DD",
  "playDate": "YYYY-MM-DD|null", "playPosition": "1-5|null", "status": "pending|approved"
}
```

### Comments (`data/db.json → comments[]`)
```json
{
  "id": "c_<timestamp>_<random>", "songId": "123456",
  "authorName": "姓名", "authorClass": "班级",
  "content": "评论内容", "createTime": "ISO"
}
```

## API Endpoints Summary

| 接口 | 方法 | 用途 |
|------|------|------|
| `/api/song/submit` | POST | 提交点歌 (link, ?message, ?playDate, ?playPosition) |
| `/api/song/check` | POST | 检查歌曲 (link) → 歌曲信息 + 是否已提交 + 是否可下载 |
| `/api/song/list` | GET | 歌曲列表 (?week, ?date) |
| `/api/song/current-cycle` | GET | 当前周期 + 倒计时 |
| `/api/song/calendar` | GET | 日历数据 (?week) → 每天 5 个位置 |
| `/api/song/history` | GET | 无 week → 周列表; 有 week → 归档歌曲 |
| `/api/song/stats` | GET | 本周统计 |
| `/api/song/download/:songId` | GET | 下载单首 MP3 |
| `/api/song/download` | POST | 批量下载周歌曲 |
| `/api/comment` | POST | 提交评论 (songId, authorName, authorClass, content) |
| `/api/comment?songId=x` | GET | 获取评论列表 |
| `/api/health` | GET | 健康检查 |

> 完整文档: `docs/API.md` | AstrBot 集成: `docs/ASTRBOT_INTEGRATION.md`

## Documentation (必须同步维护!)

| 文档 | 路径 | 面向 |
|------|------|------|
| API 文档 | `docs/API.md` | AstrBot 插件开发者 |
| AstrBot 集成指南 | `docs/ASTRBOT_INTEGRATION.md` | AstrBot 插件开发者 |
| 数据模型文档 | `docs/DATA_MODEL.md` | 后端开发者 |
| 部署指南 | `docs/DEPLOYMENT.md` | 运维 |

**每个 API 接口文档必须包含**: 路径+方法、参数说明、成功/失败响应示例、curl+JS 调用示例。

## Cron Jobs

- `*/30 * * * *` — 检查并自动下载本周歌曲（周日 20:00 后触发）
- `5 11 * * 5` (UTC) = 每周五 19:05 (UTC+8) — 归档上周歌曲、批准遗留 pending

## Code Conventions

- ES6+ Modules (`import`/`export`), 不使用 CommonJS
- 异步代码 `async`/`await`, 错误处理 `try`/`catch`
- 后端文件: 小驼峰 `.js`; 前端组件: 大驼峰 `.jsx`
- 提交规范: `feat:`, `fix:`, `docs:`, `refactor:` 前缀
- **新功能/接口必须同步更新 docs/ 下对应文档**

## Environment Variables

| 变量 | 说明 | 默认值 |
|------|------|--------|
| PORT | 后端端口 | 4000 |
| WEEKLY_QUOTA | 每周配额 | 25 |
| NETEASE_API_BASE | 网易云 API | http://localhost:3030 |
| NODE_ENV | 运行环境 | development |
