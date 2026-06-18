# 消息模板系统实施报告

## 完成时间
2026-06-19 00:40

## 实施内容

### 1. 核心文件

#### template_engine.py（6.2 KB）
- **TemplateEngine 类**：模板引擎核心
  - `render(key, **variables)`: 渲染模板，支持变量替换
  - `validate(key, template)`: 验证模板合法性
  - `update(key, template)`: 更新模板覆盖
  - `reset(key)`: 重置单个模板为默认值
  - `reset_all()`: 重置所有模板
  - `list_templates(category)`: 列出所有模板
  - `preview(key)`: 预览模板渲染效果
  
- **SafeDict 类**：安全的格式化字典
  - 缺失的变量返回 `{key_name}` 而非报错
  - 确保模板渲染的健壮性

#### templates.py（16.4 KB）
- **49 个可配置模板**，分为 11 个分类：
  - `song`（4个）：歌曲信息、确认提示、提交成功、周限制
  - `search`（2个）：搜索结果、无结果
  - `playlist`（2个）：歌单标题、空歌单
  - `status`（5个）：状态信息、倒计时、跳周状态
  - `history`（3个）：历史列表、空历史
  - `date`（3个）：日期选择、关闭日期、满员
  - `position`（2个）：位置选择、位置占用
  - `flow`（13个）：流程消息（进入模式、取消、超时等）
  - `help`（1个）：帮助文本
  - `admin`（9个）：管理员命令响应
  - `error`（3个）：错误消息

- 每个模板包含：
  - `key`: 唯一标识符
  - `description`: 人类可读的描述
  - `default`: 默认模板字符串
  - `variables`: 可用变量列表（name, description, example）
  - `category`: 分类

### 2. 配置集成

#### config.py
```python
self.message_templates: dict = config.get("message_templates", {})
```

#### _conf_schema.json
```json
"message_templates": {
  "description": "消息模板覆盖",
  "type": "object",
  "hint": "自定义消息模板。键为模板名称，值为模板字符串。留空使用默认模板。支持 {变量} 占位符。",
  "default": {}
}
```

### 3. 管理员命令

在 `/管理` 命令下添加了 `模板` 子命令：

```
/管理 模板                    # 列出所有模板
/管理 模板 查看 <key>         # 查看模板详情
/管理 模板 预览 <key>         # 预览渲染效果
/管理 模板 修改 <key> <模板>  # 修改模板
/管理 模板 重置 <key>         # 重置单个模板
/管理 模板 重置 全部          # 重置所有模板
```

### 4. 使用示例

#### 查看模板列表
```
用户: /管理 模板
机器人:
📝 消息模板列表

📂 admin:
    admin_date_closed_success — 关闭日期成功
    admin_date_format_error — 日期格式错误
    ...

📂 song:
    song_info — 歌曲信息展示
    submit_success — 提交成功消息
    ...

💡 /管理 模板 查看 <key> — 查看模板详情
💡 /管理 模板 修改 <key> <新模板> — 修改模板
...
```

#### 查看模板详情
```
用户: /管理 模板 查看 submit_success
机器人:
📝 模板: submit_success
📖 提交成功消息

当前值（默认）:
  ✅ 点歌成功！

🎧 {title} - {artist}
💬 {message}

可用变量:
  {title} — 歌曲名（例: 晴天）
  {artist} — 歌手名（例: 周杰伦）
  {message} — 用户留言（例: 毕业快乐！）
```

#### 修改模板
```
用户: /管理 模板 修改 cancelled 已取消操作
机器人:
✅ 模板 cancelled 已更新

预览:
已取消操作
```

#### 预览模板
```
用户: /管理 模板 预览 submit_success
机器人:
👀 模板预览 [submit_success]:

✅ 点歌成功！

🎧 晴天 - 周杰伦
💬 毕业快乐！
```

## 技术特点

### 1. 安全性
- 使用 Python 的 `str.format()` 方法，不执行任意代码
- 模板验证确保只使用声明的变量
- 管理员权限检查

### 2. 健壮性
- SafeDict 确保缺失变量不会导致崩溃
- 模板语法错误会被捕获并报告
- 未知模板键返回 `[未知模板: key]` 而非异常

### 3. 灵活性
- 支持运行时修改，无需重启
- 支持 AstrBot 管理面板和聊天命令两种配置方式
- 支持部分覆盖（只修改需要的模板）

### 4. 可维护性
- 模板定义与引擎分离
- 清晰的分类和元数据
- 完整的文档和示例

## 测试

所有测试通过：
1. ✅ 基本渲染
2. ✅ 带变量渲染
3. ✅ 缺失变量处理
4. ✅ 模板覆盖
5. ✅ 验证合法模板
6. ✅ 验证非法模板
7. ✅ 预览功能
8. ✅ 模板列表（49个模板）
9. ✅ 分类统计（11个分类）

## 后续工作

当前实施的是**第一阶段**：基础设施和核心功能。

### 待完成：
1. **逐步迁移现有消息**：将 main.py 和 message_builder.py 中的硬编码消息替换为模板调用
2. **持久化配置**：当前模板修改仅在内存中，需要实现持久化到 AstrBot 配置
3. **Web 管理界面**（可选）：在 web/ 前端添加可视化模板编辑器

### 迁移示例：

**修改前**：
```python
await self._send_text(event, CANCELLED)
```

**修改后**：
```python
await self._send_text(event, self.templates.render("cancelled"))
```

**带变量的修改前**：
```python
await self._send_text(event, f"✅ 已关闭 {month}月{day}日 的点歌")
```

**带变量的修改后**：
```python
await self._send_text(
    event, 
    self.templates.render("admin_date_closed_success", month=month, day=day)
)
```

## 文件统计

- 新增文件：2 个（template_engine.py, templates.py）
- 修改文件：4 个（config.py, _conf_schema.json, main.py, .gitignore）
- 新增代码：757 行
- 模板总数：49 个
- 分类总数：11 个

## 提交信息

```
feat: 实现消息模板系统

commit 187e225
Author: Claude
Date: 2026-06-19
```

---

**状态**：✅ 第一阶段完成，核心功能可用
**下一步**：逐步迁移现有硬编码消息到模板系统
