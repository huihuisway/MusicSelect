# MusicSelect — 校园音乐选择工具

基于 Node.js + Express + React + MagicUI 的 musicselect。学生通过 **AstrBot 企业微信客服** 提交点歌和评论，前端提供只读展示页面（当前歌单、日历视图、历史歌单、评论）。

## ✨ 功能特性

### 核心功能

- 🎵 **周期点歌**：每周五 19:00 — 周日 20:00 开放点歌窗口
- 📅 **可视化日历**：日历视图展示每天歌曲分布和剩余空位
- 💬 **评论系统**：每首歌支持多条评论，同学之间互动
- 📜 **历史歌单**：查看往期所有歌曲和评论
- 📥 **MP3 下载**：自动下载歌曲并转码为 320kbps MP3
- 🤖 **AstrBot 集成**：通过企业微信客服完成所有用户交互

### 业务规则

- 每周最多提交 25 首歌曲（可配置）
- 每天最多播放 5 首歌曲（位置 1-5）
- 点歌窗口外自动关闭提交
- 每周自动归档并重置

## 🛠️ 技术栈

| 层 | 技术 |
|----|------|
| 后端 | Node.js >= 18, Express.js (ES Modules) |
| 数据库 | lowdb (JSON 文件存储) |
| 前端 | React 18 + Vite + Tailwind CSS + Framer Motion |
| 音频处理 | ffmpeg-static (MP3 320kbps 转码) |
| 定时任务 | node-cron |
| 缓存 | node-cache |
| 外部 API | NeteaseCloudMusicApiEnhanced |

## 📦 安装

### 1. 克隆项目

```bash
git clone <repo-url> MusicSelect
cd MusicSelect
```

### 2. 安装依赖

```bash
# 安装后端依赖
npm install

# 安装前端依赖
cd web && npm install && npm run build && cd ..
```

或者一键安装：

```bash
npm run setup
```

### 3. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 文件
```

### 4. 启动网易云 API 服务

```bash
git clone https://github.com/NeteaseCloudMusicApiEnhanced/api-enhanced.git
cd api-enhanced && npm install && npm start
```

### 5. 启动 MusicSelect

```bash
# 生产模式
npm start

# 开发模式
npm run dev
```

访问 http://localhost:4000

## 📡 API 概览

| 接口 | 方法 | 用途 |
|------|------|------|
| `/api/song/submit` | POST | 提交点歌 |
| `/api/song/check` | POST | 检查歌曲 |
| `/api/song/list` | GET | 获取歌曲列表 |
| `/api/song/current-cycle` | GET | 当前周期信息 |
| `/api/song/calendar` | GET | 日历视图数据 |
| `/api/song/history` | GET | 历史歌单 |
| `/api/song/stats` | GET | 本周统计 |
| `/api/song/download/:songId` | GET | 下载 MP3 |
| `/api/comment` | POST / GET | 评论 |
| `/api/health` | GET | 健康检查 |

> 完整 API 文档见 [docs/API.md](docs/API.md)
> AstrBot 集成指南见 [docs/ASTRBOT_INTEGRATION.md](docs/ASTRBOT_INTEGRATION.md)

## 📁 项目结构

```
MusicSelect/
├── server/
│   ├── index.js              # Express 主入口
│   ├── database/db.js        # lowdb 数据层
│   ├── routes/               # API 路由
│   │   ├── songRoutes.js     # 歌曲 API
│   │   ├── commentRoutes.js  # 评论 API
│   │   └── downloadRoutes.js # 下载 API
│   ├── utils/                # 工具函数
│   │   ├── dateUtils.js      # 周期计算 (UTC+8)
│   │   ├── neteaseApi.js     # 网易云 API
│   │   └── songDownloader.js # 下载 + ffmpeg 转码
│   └── tasks/cronJobs.js     # 定时任务
├── web/                       # React 前端
│   ├── src/
│   │   ├── pages/            # 页面组件
│   │   ├── components/       # UI 组件
│   │   └── api/              # API 请求封装
│   ├── vite.config.js
│   └── tailwind.config.js
├── data/db.json              # 数据库文件
├── downloader/               # MP3 下载目录
├── docs/                     # 文档
│   ├── API.md                # API 完整文档
│   ├── ASTRBOT_INTEGRATION.md # AstrBot 集成指南
│   ├── DATA_MODEL.md         # 数据模型文档
│   └── DEPLOYMENT.md         # 部署指南
├── .env                      # 环境变量
├── package.json
└── CLAUDE.md                 # AI 辅助开发指南
```

## 📚 文档

| 文档 | 说明 |
|------|------|
| [API 文档](docs/API.md) | 所有接口详细说明，含请求/响应示例 |
| [AstrBot 集成指南](docs/ASTRBOT_INTEGRATION.md) | 插件开发者指南，交互流程、调用示例 |
| [数据模型文档](docs/DATA_MODEL.md) | 数据库结构、字段说明 |
| [部署指南](docs/DEPLOYMENT.md) | 环境要求、安装步骤、配置说明 |

## ⚠️ 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| PORT | 服务器端口 | 4000 |
| WEEKLY_QUOTA | 每周歌曲配额 | 25 |
| NETEASE_API_BASE | 网易云 API 地址 | http://localhost:3030 |
| NODE_ENV | 运行环境 | development |

## ⏰ 定时任务

| 任务 | 时间 | 说明 |
|------|------|------|
| 自动下载歌曲 | 每 30 分钟检查 | 窗口关闭后下载本周歌曲 |
| 周重置 | 每周五 19:05 | 归档上周歌曲、批准遗留 pending |

## 📄 License

MIT
