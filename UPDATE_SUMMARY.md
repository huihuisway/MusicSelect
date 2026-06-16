# AstrBot 插件更新总结

## 修复的 Bug

### 1. 提交成功但显示"请求错误" ✅
**原因：** `api_client.py` 的 `_request` 方法只处理 HTTP 200 状态码，但后端返回 201 表示创建成功。

**修复：** 修改状态码判断，同时接受 200 和 201。
```python
if response.status_code in (200, 201):
```

### 2. `/歌单` 命令不显示已点歌曲 ✅
**原因：** 后端 `/api/song/list` 在非点歌窗口期只返回 `approved` 状态的歌曲，但新提交的歌曲是 `pending` 状态。

**修复：** 移除基于窗口期的状态过滤，始终返回本周所有歌曲。

## 新增功能

### 3. 日期选择显示进度条 ✅
- 显示格式：`1. 周一 (06-16)  ███░░ 3/5`
- 满员标记：`2. 周二 (06-17)  █████ 5/5 已满`
- 休息日标记：`3. 周三 (06-18)  🚫 休息日`
- 禁止选择已满或休息的日期

### 4. 位置选择显示当天歌曲列表 ✅
选择日期后，显示该日期所有 5 个位置的状态：
```
📍 2026-06-16 当前位置：

  1. 🎵 晴天 - 周杰伦
  2. ⬜ (空)
  3. 🎵 七里香 - 周杰伦
  4. ⬜ (空)
  5. ⬜ (空)

💡 回复数字选择位置（如：2）
💡 回复「跳过」自动分配
```

- 禁止选择已被占用的位置
- 显示已有歌曲的名称和歌手

## 修改的文件

### 后端
- `server/routes/songRoutes.js`
  - 移除 `/submit` 的窗口期检查
  - 添加过去日期检查（12:00 截止）
  - 添加关闭日期检查
  - 新增 `/closed-dates` API 端点
  - 修改 `/current-cycle` 返回 `closedDates`
  - 修改 `/list` 移除状态过滤

- `server/database/db.js`
  - 添加 `closedDates` 集合
  - 新增关闭日期 CRUD 方法

### 插件
- `astrbot-plugin/api_client.py`
  - 修复 201 状态码处理
  - 新增 `user_class` 参数
  - 新增关闭日期 API 方法

- `astrbot-plugin/main.py`
  - 修复双重提示问题
  - 搜索命令需要"搜索"前缀
  - 歌曲确认分 3 条消息发送
  - 姓名和班级分两步输入
  - 新增 `/管理` 命令
  - 日期选择验证满员状态
  - 新增 `_ask_position` 方法
  - 位置选择验证占用状态

- `astrbot-plugin/message_builder.py`
  - 拆分歌曲信息为 3 条消息
  - 日期选择添加进度条
  - 新增 `format_position_selection` 函数
  - 修复 400 错误消息

- `astrbot-plugin/intent.py`
  - 新增 `STATE_WAITING_CLASS` 状态
  - 新增 `INTENT_NAME` 和 `INTENT_CLASS` 意图

- `astrbot-plugin/conversation.py`
  - 新增 `user_class` 字段

- `astrbot-plugin/config.py`
  - 新增 `admin_id` 配置

- `astrbot-plugin/_conf_schema.json`
  - 新增管理员配置项

## 部署说明

### 1. 重启后端
```bash
cd server
npm install  # 如果有新依赖
npm run dev  # 或 npm start
```

### 2. 更新插件
1. 在 AstrBot 管理面板卸载旧插件
2. 上传新的 `astrbot-plugin.zip`
3. 安装并配置管理员 ID
4. 重启 AstrBot

### 3. 配置管理员
在 AstrBot 插件配置页面设置 `admin_id`，或使用命令：
- `/管理` - 查看状态
- `/管理 关 MMDD` - 关闭日期（如 `/管理 关 0701`）
- `/管理 开 MMDD` - 开放日期

## 测试建议

1. **提交流程测试**
   - 完整走一遍点歌流程
   - 验证提交成功消息正确显示

2. **歌单显示测试**
   - 执行 `/歌单` 命令
   - 验证显示所有已点歌曲

3. **日期选择测试**
   - 查看日期进度条是否正确
   - 尝试选择已满日期（应被拒绝）
   - 尝试选择休息日（应被拒绝）

4. **位置选择测试**
   - 选择日期后查看位置列表
   - 验证已有歌曲正确显示
   - 尝试选择已占用位置（应被拒绝）

5. **管理功能测试**
   - 使用 `/管理 关 0701` 关闭日期
   - 验证日期选择时该日期显示为休息日
   - 使用 `/管理 开 0701` 重新开放
