# 双侧边栏设计实施计划

## 概述

基于 `docs/superpowers/specs/2026-07-26-double-sidebar-design.md` 设计规范，将当前单一边栏重构为 L1（图标栏）+ L2（内容面板）双侧边栏架构，并分三个阶段逐步实施。

---

## 阶段 1：双侧边栏（L1 + L2）

### 目标

将当前 `AppSidebar.vue`（单侧边栏，272px，包含图标菜单+对话列表）拆分为两个独立侧边栏：

- **L1 Sidebar**：52px 宽，纯图标导航栏，始终可见
- **L2 Sidebar**：可折叠的内容面板（240-440px），根据 L1 选中项切换内容

### 1.1 新增 Pinia Store：`useNavigationStore`

**新建文件**：`frontend/src/stores/useNavigationStore.js`

```
状态：
- activeNav: ref('chat')          // 当前 L1 激活项：'chat' | 'kb' | 'team' | 'settings'
- l2Expanded: ref(true)           // L2 是否展开
- l2Width: ref(240)               // L2 宽度（可拖拽调整）
- mobileSidebarOpen: ref(false)   // 移动端 Sheet 开关

动作：
- setActiveNav(nav)               // 切换 L1 激活项
- toggleL2()                      // 展开/收起 L2
- setL2Width(width)               // 设置 L2 宽度
- toggleMobileSidebar()           // 移动端切换
```

### 1.2 新建 L1 Sidebar 组件

**新建文件**：`frontend/src/features/navigation/L1Sidebar.vue`

结构（自上而下）：
1. **Logo 区域**：52px 居中，Sparkles 图标，可复用现有圆角图标
2. **主导航图标组**（纵向排列，间距 2px）：
   - `MessageSquare` → chat（默认激活，tool-tip "对话"）
   - `Database` → kb（tool-tip "知识库"）
   - `Users` → team（tool-tip "团队"）
   - `Settings` → settings（tool-tip "设置"）
3. **底部操作区**（border-t 分隔）：
   - 折叠/展开按钮（`PanelLeftClose` / `PanelLeftOpen`）
   - 用户头像按钮（打开退出菜单）
4. **Tooltip**：复用现有 `components/ui/tooltip.vue`（radix TooltipRoot）

样式规范：
- 宽度固定 52px
- `bg-sidebar` 背景
- 图标按钮：36×36px，`rounded-lg`，hover `bg-sidebar-accent`
- 激活态：`bg-sidebar-accent text-sidebar-accent-foreground` + 左侧 3px `bg-primary` 竖条

### 1.3 重构 L2 Sidebar 组件

**新建文件**：`frontend/src/features/navigation/L2Sidebar.vue`

这是一个容器组件，根据 `navigationStore.activeNav` 切换内容面板。

**Props**：
- `width: number` — 当前宽度
- `expanded: boolean` — 是否展开

**模板结构**：
```vue
<div v-show="expanded" :style="{ width: width + 'px' }">
  <!-- 拖拽调整手柄 -->
  <div class="resize-handle" @mousedown="startResize" />

  <!-- 根据 activeNav 渲染不同面板 -->
  <ChatPanel v-if="activeNav === 'chat'" />
  <KbPanel v-else-if="activeNav === 'kb'" />
  <TeamPanel v-else-if="activeNav === 'team'" />
  <SettingsPanel v-else-if="activeNav === 'settings'" />
</div>
```

#### 1.3.1 ChatPanel（对话模式）

**新建文件**：`frontend/src/features/navigation/panels/ChatPanel.vue`

从现有 `AppSidebar.vue` 提取对话相关内容：

**Header 区域**：
- "对话" 标题文字
- 右侧两个图标按钮：新建对话（`Plus`）、搜索（`Search`）

**Body 区域**：
- 复用现有 `ConversationList.vue`，但需要重构以支持：
  - 搜索过滤（后续在阶段 2 添加右键菜单）
  - 分组显示（当前对话、历史对话）
  - 空态保持现有样式

**Footer 区域**：
- 当前对话信息行
- 主题切换按钮（`Sun`/`Moon`）
- 模型选择器（保留占位，展示当前模型名）

**收起态**（L2 折叠时，L1 激活 chat 时）：
- 在 L1 下方显示 mini 浮动面板，包含"新对话"按钮 + 最近 3 条对话头像

#### 1.3.2 KbPanel（知识库模式）

**新建文件**：`frontend/src/features/navigation/panels/KbPanel.vue`

展示知识库列表，每个知识库可展开查看文档。

**Header**：标题 "知识库" + 新建按钮（`Plus`）
**Body**：
- 知识库卡片列表（从 `useKbStore` 读取）
- 每个卡片显示：名称、文档数量、进度条（处理中时）
- 单击卡片 → 在右侧主内容区打开详情（或弹出 KnowledgebaseDrawer）
- 展开箭头 → 展示该知识库下的文档列表

**Footer**：固定操作按钮 — "管理知识库"（打开 KnowledgebaseDrawer）

#### 1.3.3 TeamPanel（团队模式）

**新建文件**：`frontend/src/features/navigation/panels/TeamPanel.vue`

**Header**：标题 "团队" + 新建邀请按钮
**Body**：
- 在线成员列表（头像 + 名称 + 状态点）
- 成员卡片（角色、知识库数量、最近活跃时间）
- 单击成员 → 显示详情面板

#### 1.3.4 SettingsPanel（设置模式）

**新建文件**：`frontend/src/features/navigation/panels/SettingsPanel.vue`

聚合现有分散的设置入口：

- 模型管理（`Cpu` 图标，打开 ModelManager）
- 文档管理（`FileText` 图标，打开 DocumentDrawer）
- 标签知识库（`Tags` 图标，打开 TagKbDrawer）
- RAG 设置（`Settings` 图标，打开 RagSettingsDrawer）
- 知识图谱（`Network` 图标，打开 GraphViewer）
- 评测看板（`BarChart3` 图标，打开 EvalDashboard）
- 退出登录

### 1.4 重构 App.vue 布局

**修改文件**：`frontend/src/App.vue`

**变更要点**：
1. 移除现有的单 `<aside>` 块（包含 AppSidebar）
2. 替换为 L1Sidebar + L2Sidebar 的双列结构
3. 移动端：使用 Sheet 包裹 L1Sidebar + L2Sidebar（保持现有 Sheet 侧滑模式）
4. 保留所有现有的 Drawer/Dialog/Modal 不变
5. 从 App.vue 移除各功能的 `showXxx` ref，改由 L2 面板或 SettingsPanel 内部管理

**新布局结构**：
```vue
<div class="flex h-full">
  <!-- L1: 图标栏，始终可见 -->
  <L1Sidebar class="hidden lg:flex" />

  <!-- L2: 内容面板，可折叠 -->
  <L2Sidebar class="hidden lg:block" />

  <!-- 主内容区 -->
  <main class="flex-1">
    <ChatShell />
  </main>

  <!-- 移动端 Sheet：L1+L2 整合 -->
  <Sheet side="left" class="lg:hidden">
    <L1Sidebar />
    <L2Sidebar :expanded="true" />
  </Sheet>
</div>
```

### 1.5 清理旧 Sidebar

**删除/归档文件**：
- `frontend/src/features/conversations/AppSidebar.vue` — 功能拆分到 L1Sidebar + ChatPanel
- `frontend/src/features/conversations/ConversationList.vue` — 移入 ChatPanel 或保留为子组件

**保留文件**（不变）：
- 所有 Drawer 组件（DocumentDrawer, ModelManager 等）
- ChatShell 及其子组件
- 所有 Pinia stores

### 1.6 更新 CSS 变量

**修改文件**：`frontend/src/styles/globals.css`

确保 sidebar 相关 token 适配新的双侧边栏：
- `--sidebar-*` 变量应用于 L1
- L2 使用 `--card` / `--background` 系列变量
- 拖拽手柄样式：`hover:bg-primary/50`，宽度 1px，hover 区域 4px

### 1.7 关键决策点

| 决策 | 选项 | 推荐 |
|------|------|------|
| L2 折叠动画 | CSS transition vs. v-if | CSS width transition（与现有侧边栏动画一致） |
| L1 tooltip 方向 | right vs. auto | right（固定在 L1 右侧弹出） |
| 拖拽调整实现 | 自定义 mousedown vs. 第三方库 | 自定义（@vueuse/core 的 useResizeObserver + mousedown 事件） |
| KB 面板点击行为 | 直接展开文档 vs. 打开 Drawer | 单击展开内联文档列表 + "管理"按钮打开 Drawer |
| 移动端 Sheet 内 L1 可见性 | 显示 L1 vs. 不显示 | 不显示 L1（移动端 Sheet 只展示 L2 内容，L1 图标无意义） |

---

## 阶段 2：对话上下文菜单

### 目标

为 `ConversationList` 中的对话项添加右键上下文菜单，支持 6 个操作。

### 2.1 新建 ContextMenu 组件

**新建文件**：`frontend/src/components/ui/context-menu.vue`

基于 radix-vue 的 `ContextMenuRoot` 构建（与现有 dropdown-menu 模式一致）：

```vue
<!-- context-menu.vue — 包装 ContextMenuRoot -->
<!-- context-menu-content.vue — 包装 ContextMenuContent -->
<!-- context-menu-item.vue — 包装 ContextMenuItem -->
```

**样式**：复用 dropdown-content 的样式规范（`bg-popover`, `rounded-md`, `shadow-md`），宽度 `w-52`。

### 2.2 增强 ConversationItem

**修改文件**：`frontend/src/features/conversations/ConversationList.vue`（或重构后的 ChatPanel）

为每个对话项包裹 `ContextMenu`：

```
右键菜单项：
├─ 重命名       (Pencil icon)     → 内联编辑标题
├─ 收藏/取消收藏  (Star icon)       → 切换 conv.is_favorite
├─ 复制         (Copy icon)       → 调用 API 复制对话
├─ 归档         (Archive icon)    → 调用 API 归档
├─ 分享         (Share2 icon)     → 复制分享链接
└─ ──────────
└─ 删除         (Trash2 icon)     → 二次确认后删除
```

**移动端长按**：在移动端使用 Sheet（bottom-sheet）展示相同菜单项。

### 2.3 后端 API 扩展

需要为以下操作添加后端支持：

| 操作 | API 变更 | 说明 |
|------|---------|------|
| 重命名 | `PATCH /conversations/{id}` | 新增 `title` 字段 |
| 收藏 | `PATCH /conversations/{id}` | 新增 `is_favorite` 布尔字段 |
| 复制 | `POST /conversations/{id}/duplicate` | 新增端点 |
| 归档 | `PATCH /conversations/{id}` | 新增 `status` 字段（active/archived） |
| 分享 | `POST /conversations/{id}/share` | 新增端点，返回分享链接 |
| 删除 | `DELETE /conversations/{id}` | 已有 |

**数据库迁移**：`conversations` 表新增 `is_favorite`（BOOLEAN）、`status`（VARCHAR，default 'active'）、`shared_token`（VARCHAR，nullable）列。

### 2.4 更新 ConversationStore

**修改文件**：`frontend/src/stores/useConversationStore.js`

新增方法：
- `renameConversation(id, newTitle)`
- `toggleFavorite(id)`
- `duplicateConversation(id)`
- `archiveConversation(id)`
- `shareConversation(id)`
- 更新 `fetchConversations()` 过滤逻辑（默认只加载 status='active'）

### 2.5 内联重命名实现

在 `ConversationList.vue` 中：
- 点击"重命名"后，将 `<span>` 替换为 `<input>`
- Enter 保存，Escape 取消，失焦保存
- 调用 `conversationStore.renameConversation()`

---

## 阶段 3：移动端 Sheet 详情增强

### 目标

在移动端（<768px）点击对话项时，显示详情 Sheet 底部抽屉。

### 3.1 新建 MobileDetailSheet 组件

**新建文件**：`frontend/src/features/conversations/MobileDetailSheet.vue`

使用现有 `Sheet` 组件（`side="bottom"`），高度 60vh：

```
内容结构：
├─ 拖拽指示条（40×4px，居中灰色条）
├─ 对话标题（可编辑）
├─ 元信息（创建时间、消息数、模型名称）
├─ 操作按钮组（2列网格）：
│   收藏 | 复制 | 归档 | 分享 | 删除
└─ 取消按钮
```

### 3.2 集成到 ChatPanel / ConversationList

- 检测 `window.innerWidth < 768`（或使用 CSS 媒体查询 + JS 检测）
- 移动端单击对话项 → 打开 MobileDetailSheet（而不是直接切换对话）
- 桌面端单击行为不变（直接切换对话）

### 3.3 移动端 Sheet 动画

- 底部 Sheet 使用现有 slide-in-from-bottom 动画
- 背景遮罩：`bg-black/40 backdrop-blur-sm`（与现有 Sheet 一致）
- 拖拽指示条：`w-10 h-1 rounded-full bg-muted-foreground/30 mx-auto`

---

## 文件变更清单

### 新建文件（9 个）

| 文件路径 | 说明 |
|---------|------|
| `frontend/src/stores/useNavigationStore.js` | 导航状态 store |
| `frontend/src/features/navigation/L1Sidebar.vue` | L1 图标侧边栏 |
| `frontend/src/features/navigation/L2Sidebar.vue` | L2 内容面板容器 |
| `frontend/src/features/navigation/panels/ChatPanel.vue` | 对话面板 |
| `frontend/src/features/navigation/panels/KbPanel.vue` | 知识库面板 |
| `frontend/src/features/navigation/panels/TeamPanel.vue` | 团队面板 |
| `frontend/src/features/navigation/panels/SettingsPanel.vue` | 设置面板 |
| `frontend/src/components/ui/context-menu.vue` | 右键菜单组件 |
| `frontend/src/features/conversations/MobileDetailSheet.vue` | 移动端详情 Sheet |

### 修改文件（6 个）

| 文件路径 | 变更 |
|---------|------|
| `frontend/src/App.vue` | 重构布局：单侧边栏 → L1+L2，移动端 Sheet 整合 |
| `frontend/src/features/conversations/ConversationList.vue` | 添加右键菜单、内联重命名、收藏排序 |
| `frontend/src/stores/useConversationStore.js` | 新增 rename/favorite/duplicate/archive/share 方法 |
| `frontend/src/styles/globals.css` | 新增 L1/L2 相关 CSS 变量和拖拽手柄样式 |
| `frontend/src/features/chat/ChatHeader.vue` | 可能移除文档/评测快捷按钮（已移入 SettingsPanel） |
| `backend/core/database.py` | conversations 表新增字段 |

### 删除/归档文件（1 个）

| 文件路径 | 说明 |
|---------|------|
| `frontend/src/features/conversations/AppSidebar.vue` | 功能已拆分，归档或删除 |

---

## 实施顺序建议

```
阶段 1（核心重构）— 预计 3-4 天
  ├─ 1.1 创建 useNavigationStore
  ├─ 1.2 创建 L1Sidebar
  ├─ 1.3 创建 L2Sidebar + ChatPanel（优先，确保对话功能不中断）
  ├─ 1.4 重构 App.vue 布局
  ├─ 1.3.2-1.3.4 创建 KbPanel / TeamPanel / SettingsPanel
  ├─ 1.5 清理旧 Sidebar
  └─ 1.6 更新 CSS 变量

阶段 2（上下文菜单）— 预计 1-2 天
  ├─ 2.1 创建 ContextMenu 组件
  ├─ 2.3 后端 API 扩展 + 数据库迁移
  ├─ 2.4 更新 ConversationStore
  ├─ 2.2 集成右键菜单到对话列表
  └─ 2.5 内联重命名

阶段 3（移动端增强）— 预计 1 天
  ├─ 3.1 创建 MobileDetailSheet
  ├─ 3.2 集成到对话列表
  └─ 3.3 动画和交互打磨
```

---

## 风险和注意事项

1. **回归风险**：阶段 1 是核心布局重构，所有现有功能（对话、文档、知识库等）必须在重构后继续正常工作。建议在每个子步骤后手动测试。
2. **Drawer 状态管理迁移**：当前 `showDocs`、`showModels` 等 ref 在 App.vue 中管理。迁移到 SettingsPanel 后，需确保 ChatHeader 中的快捷按钮仍能正常打开对应 Drawer。
3. **L2 宽度拖拽**：需要在 `mousedown` → `mousemove` → `mouseup` 过程中正确处理指针捕获，避免拖拽时文本选中。
4. **移动端 Sheet 内双侧边栏**：移动端不应显示 L1 图标栏（浪费空间），Sheet 内直接展示 L2 面板内容。
5. **后端 API 变更**：阶段 2 的数据库迁移需要与后端团队协调，conversation 新增字段需要 Alembic migration。
