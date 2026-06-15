# 部署指南

> MusicSelect 部署文档，涵盖环境要求、安装步骤和配置说明。

---

## 目录

- [环境要求](#环境要求)
- [安装步骤](#安装步骤)
- [配置说明](#配置说明)
- [启动服务](#启动服务)
- [Nginx 反向代理（可选）](#nginx-反向代理可选)
- [目录说明](#目录说明)
- [备份建议](#备份建议)
- [常见问题](#常见问题)

---

## 环境要求

| 项目 | 版本要求 | 说明 |
|------|---------|------|
| Node.js | >= 18.0.0 | 运行时 |
| npm | >= 8.x | 包管理器 |
| ffmpeg | 由 ffmpeg-static 提供 | 无需单独安装，npm 依赖自带 |
| NeteaseCloudMusicApiEnhanced | 最新版 | 网易云音乐 API 服务 |

**操作系统**：Linux / macOS / Windows 均可。

---

## 安装步骤

### 1. 克隆 / 获取代码

```bash
git clone <repo-url> MusicSelect
cd MusicSelect
```

### 2. 安装后端依赖

```bash
npm install
```

### 3. 安装前端依赖并构建

```bash
cd web
npm install
npm run build
cd ..
```

> 构建产物在 `web/dist/`，后端在生产模式下会自动托管。

### 4. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env（见下方配置说明）
```

### 5. 安装并启动网易云 API 服务

```bash
# 在另一个目录
git clone https://github.com/NeteaseCloudMusicApiEnhanced/api-enhanced.git
cd api-enhanced
npm install
npm start  # 默认端口 3030
```

---

## 配置说明

编辑 `.env` 文件：

```env
# 后端服务端口
PORT=4000

# 每周歌曲配额上限
WEEKLY_QUOTA=25

# 网易云 API 服务地址
NETEASE_API_BASE=http://localhost:3030

# 运行环境（production = 托管前端静态文件）
NODE_ENV=production
```

| 变量 | 必填 | 默认值 | 说明 |
|------|:----:|-------|------|
| PORT | ❌ | 4000 | 后端 HTTP 端口 |
| WEEKLY_QUOTA | ❌ | 25 | 每周最多提交歌曲数 |
| NETEASE_API_BASE | ❌ | http://localhost:3030 | 网易云 API 地址 |
| NODE_ENV | ❌ | development | 设为 `production` 时后端会托管前端 |

---

## 启动服务

### 生产模式

```bash
npm start
```

后端启动后：
- API 服务：`http://localhost:4000/api`
- 前端页面：`http://localhost:4000`（由后端托管 `web/dist/`）
- 健康检查：`http://localhost:4000/api/health`

### 开发模式

```bash
# 终端 1：启动后端（热重载）
npm run dev

# 终端 2：启动前端开发服务器
npm run client
```

- 后端 API：`http://localhost:4000/api`
- 前端开发：`http://localhost:5173`（自动代理 `/api` 到后端）

### 使用 systemd（Linux 推荐）

```ini
# /etc/systemd/system/musicselect.service
[Unit]
Description=MusicSelect Backend
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/MusicSelect
ExecStart=/usr/bin/node server/index.js
Restart=on-failure
Environment=NODE_ENV=production
EnvironmentFile=/opt/MusicSelect/.env

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl enable musicselect
sudo systemctl start musicselect
sudo systemctl status musicselect
```

---

## Nginx 反向代理（可选）

```nginx
server {
    listen 80;
    server_name music.yourschool.edu.cn;

    location / {
        proxy_pass http://127.0.0.1:4000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

## 目录说明

```
MusicSelect/
├── server/            # 后端源码
├── web/               # 前端源码 + 构建配置
│   └── dist/          # 前端构建产物（npm run build 后生成）
├── data/
│   └── db.json        # lowdb 数据文件（自动创建）
├── downloader/        # MP3 下载目录（自动创建）
│   └── YYYY-MM-DD/    # 按周期组织
├── docs/              # 文档
├── .env               # 环境配置
├── package.json       # 后端依赖
└── CLAUDE.md          # AI 辅助开发指南
```

---

## 备份建议

### 必须备份

| 文件/目录 | 说明 | 建议频率 |
|----------|------|---------|
| `data/db.json` | 全部数据（歌曲+评论+归档） | 每日 |
| `downloader/` | 已下载的 MP3 文件 | 每周 |
| `.env` | 环境配置 | 配置变更时 |

### 备份脚本示例

```bash
#!/bin/bash
BACKUP_DIR="/backup/musicselect/$(date +%Y%m%d)"
mkdir -p "$BACKUP_DIR"
cp data/db.json "$BACKUP_DIR/"
cp .env "$BACKUP_DIR/"
# 可选：备份下载的歌曲
# cp -r downloader/ "$BACKUP_DIR/"
echo "备份完成: $BACKUP_DIR"
```

---

## 常见问题

### Q: 网易云 API 服务连不上？

检查 `NETEASE_API_BASE` 配置是否正确，确保 NeteaseCloudMusicApiEnhanced 已启动：

```bash
curl http://localhost:3030/song/detail?ids=123456
```

### Q: 前端页面打不开？

确认已执行 `npm run build` 且 `NODE_ENV=production`。或者使用开发模式 `npm run client`。

### Q: MP3 下载失败？

`ffmpeg-static` 会在首次使用时下载 ffmpeg 二进制文件。确保网络可达。也可以手动安装 ffmpeg 并配置路径。

### Q: 数据文件损坏？

从备份恢复 `data/db.json`。如果没有备份，删除文件后重启服务会自动创建空数据库（历史数据将丢失）。

### Q: 定时任务不执行？

确保 `node-cron` 正常加载。查看控制台日志中是否有 `[cron] 定时任务已启动` 消息。时区基于服务器系统时间。
