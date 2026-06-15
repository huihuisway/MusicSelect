# 数据模型文档

> MusicSelect 使用 [lowdb](https://github.com/typicode/lowdb) 作为数据库，数据以 JSON 格式存储在 `data/db.json`。

---

## 目录

- [概览](#概览)
- [数据集合](#数据集合)
  - [Songs — 歌曲](#songs--歌曲)
  - [Comments — 评论](#comments--评论)
  - [SongArchives — 歌曲归档](#songarchives--歌曲归档)
  - [DownloadRecords — 下载记录](#downloadrecords--下载记录)
- [集合关系图](#集合关系图)
- [数据库操作封装](#数据库操作封装)
- [注意事项](#注意事项)

---

## 概览

```json
{
  "songs": [],
  "comments": [],
  "songArchives": [],
  "downloadRecords": []
}
```

| 集合 | 说明 | 生命周期 |
|------|------|----------|
| songs | 当前及未来周期的歌曲 | 每周归档后清空该周数据 |
| comments | 歌曲评论 | 随歌曲一起归档后清空 |
| songArchives | 历史歌曲（永久保存） | 只增不改 |
| downloadRecords | 每周下载状态 | 只增不改 |

---

## 数据集合

### Songs — 歌曲

存储当前周期内的所有歌曲数据。

```typescript
interface Song {
  songId: string;          // 网易云歌曲 ID（唯一标识）
  title: string;           // 歌名
  artist: string;          // 歌手（多个用 " / " 分隔）
  album: string;           // 专辑名
  coverUrl: string;        // 封面图片 URL
  submitterName: string;   // 提交者姓名
  submitterClass: string;  // 提交者班级
  message: string;         // 留言内容
  submitTime: string;      // 提交时间（ISO 8601）
  weekStart: string;       // 所属周期，播放周周一日期 "YYYY-MM-DD"
  playDate: string | null; // 播放日期 "YYYY-MM-DD"（可选）
  playPosition: number | null; // 播放位置 1-5（可选）
  status: "pending" | "approved"; // 歌曲状态
}
```

**字段说明：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|:----:|------|
| songId | string | ✅ | 网易云音乐歌曲 ID，从 URL 中提取 |
| title | string | ✅ | 从网易云 API 获取 |
| artist | string | ✅ | 从网易云 API 获取，多歌手用 ` / ` 分隔 |
| album | string | ✅ | 从网易云 API 获取 |
| coverUrl | string | ✅ | 网易云封面图 URL |
| submitterName | string | ✅ | 由 AstrBot 传入 |
| submitterClass | string | ✅ | 由 AstrBot 传入 |
| message | string | ✅ | 提交者留言 |
| submitTime | string | ✅ | ISO 8601 格式，由后端生成 |
| weekStart | string | ✅ | 播放周期周一日期，由后端计算 |
| playDate | string | ❌ | 用户期望的播放日期 |
| playPosition | number | ❌ | 用户期望的播放位置（1-5） |
| status | string | ✅ | `pending`=待审核，`approved`=已批准 |

**唯一性约束：** 同一 `weekStart` 下 `songId` 唯一（防止重复提交）。

**状态流转：**

```
pending ──→ approved
  │
  │  （周重置时自动批准所有 pending 歌曲）
  │
  └──→ 归档到 SongArchives
```

---

### Comments — 评论

存储歌曲评论。一条评论关联一首歌曲。

```typescript
interface Comment {
  id: string;           // 评论唯一 ID（格式：c_<timestamp>_<random>）
  songId: string;       // 关联的网易云歌曲 ID
  authorName: string;   // 评论者姓名
  authorClass: string;  // 评论者班级
  content: string;      // 评论内容
  createTime: string;   // 创建时间（ISO 8601）
}
```

**字段说明：**

| 字段 | 类型 | 必填 | 说明 |
|------|------|:----:|------|
| id | string | ✅ | 格式：`c_{Date.now()}_{random6}` |
| songId | string | ✅ | 关联到 Songs 集合的 songId |
| authorName | string | ✅ | 由 AstrBot 传入 |
| authorClass | string | ✅ | 由 AstrBot 传入 |
| content | string | ✅ | 评论正文 |
| createTime | string | ✅ | ISO 8601 格式 |

---

### SongArchives — 歌曲归档

历史歌曲的永久存档。结构与 `Songs` 完全相同，额外增加 `archivedAt` 字段。

```typescript
interface SongArchive extends Song {
  archivedAt: string;   // 归档时间（ISO 8601）
}
```

归档操作在每周五 19:05 由定时任务执行：
1. 将上周 `songs` 中所有歌曲标记为 `approved`
2. 复制到 `songArchives`（加上 `archivedAt`）
3. 从 `songs` 中删除

---

### DownloadRecords — 下载记录

记录每周歌曲的下载状态，防止重复下载。

```typescript
interface DownloadRecord {
  weekStart: string;     // 周期 "YYYY-MM-DD"
  downloadedAt: string;  // 下载完成时间（ISO 8601）
}
```

---

## 集合关系图

```
┌─────────────────┐         ┌─────────────────┐
│     Songs       │         │    Comments     │
│─────────────────│  1:N    │─────────────────│
│ songId (唯一)    │◄────────│ songId          │
│ weekStart       │         │ id (唯一)        │
│ status          │         │ authorName      │
│ submitterName   │         │ content         │
│ ...             │         │ ...             │
└────────┬────────┘         └─────────────────┘
         │
         │ 归档（周五 19:05）
         ▼
┌─────────────────┐         ┌─────────────────┐
│  SongArchives   │         │ DownloadRecords │
│─────────────────│         │─────────────────│
│ (同 Songs)      │         │ weekStart (唯一) │
│ + archivedAt    │         │ downloadedAt    │
└─────────────────┘         └─────────────────┘
```

---

## 数据库操作封装

所有数据库操作封装在 `server/database/db.js`，主要函数：

### Songs

| 函数 | 说明 |
|------|------|
| `findSongs(filter)` | 按条件查询歌曲，返回数组 |
| `findOneSong(filter)` | 查询单首歌曲 |
| `countSongs(filter)` | 统计歌曲数量 |
| `addSong(song)` | 添加歌曲 |
| `updateSongs(filter, updates)` | 批量更新歌曲字段 |
| `removeSongs(filter)` | 删除符合条件的歌曲 |
| `archiveSongs(weekStart)` | 归档指定周的所有歌曲 |

### Comments

| 函数 | 说明 |
|------|------|
| `findComments(filter)` | 按条件查询评论 |
| `addComment(comment)` | 添加评论 |
| `removeComments(filter)` | 删除评论 |

### Archives

| 函数 | 说明 |
|------|------|
| `findArchives(filter)` | 查询归档歌曲 |
| `getArchiveWeeks()` | 获取所有归档周列表 |

### Download Records

| 函数 | 说明 |
|------|------|
| `findDownloadRecord(weekStart)` | 查询某周是否已下载 |
| `addDownloadRecord(weekStart)` | 记录下载完成 |

---

## 注意事项

1. **并发写入**：lowdb 是单进程同步写入，不支持并发。如果将来需要并发写入，考虑切换到 SQLite 或添加写入锁。

2. **数据备份**：`data/db.json` 是全部数据，建议定期备份。

3. **数据大小**：lowdb 适合小数据量场景（< 10MB）。如果数据量增长明显，考虑迁移到 SQLite。

4. **时区**：所有日期字段使用 ISO 8601 格式（UTC），业务逻辑中通过 `dateUtils.js` 转换到 UTC+8。

5. **敏感信息**：v2 版本已移除 IP 地址存储，不存在隐私风险。
