# 双栏上下文感知侧边栏设计规格

> **项目**: DataPilotAI — RAG 智能问答平台  
> **日期**: 2026-07-26  
> **状态**: 待审阅  
> **技术栈**: Vue 3 + Tailwind CSS v4 + Pinia + Radix Vue + Vue Router 4（新增）

---

## 1. 背景与目标

### 当前问题

DataPilotAI 的侧边栏（`AppSidebar.vue`）存在以下不足：

1. **导航结构扁平**：底部 9 个功能按钮平铺无分组，视觉层级不清晰，用户需要扫描全部按钮才能找到目标功能。
2. **响应式粗糙**：仅有一个 `lg`（1024px）断点，缺少平板适配；移动端 Sheet 交互单一。
3. **操作效率低**：无搜索、无键盘快捷键、无最近访问记录，高频操作路径长。
4. **与主内容区脱节**：所有管理功能通过右侧 Drawer 弹出，无法独立访问、无法分享链接、侧边栏与主内容区无联动。
5. **折叠态功能弱**：56px 折叠态仅显示图标，失去上下文信息。

### 设计目标

引入**双栏上下文感知侧边栏 + Vue Router 独立页面 + 命令面板**，实现：

- 图标轨道作为全局导航锚点，始终可见
- 上下文面板根据当前路由动态切换内容
- 每个模块有独立 URL 和页面，支持浏览器前进/后退
- 命令面板（Ctrl+K）提供键盘优先的快速导航
- 三档响应式策略覆盖桌面、平板、移动端

---

## 2. 整体架构

### 布局拓扑

```
┌──────────────────────────────────────────────────────┐
│                    App Root                           │
│ ┌──────┬──────────────┬────────────────────────────┐ │
│ │ Icon │   Context    │       Main Content         │ │
│ │ Rail │   Panel      │       (Router View)        │ │
│ │ 48px │   240-280px  │       flex-1               │ │
│ │      │   可折叠      │                            │ │
│ └──────┴──────────────┴────────────────────────────┘ │
│        ↑ 固定在视口左侧，不随页面滚动                    │
└──────────────────────────────────────────────────────┘
```

### 组件树

```
App.vue
├── AppShell.vue                    ← 管理侧边栏 + 主内容的整体布局
│   ├── IconRail.vue                ← 左侧图标轨道（48px 固定）
│   ├── ContextPanel.vue            ← 上下文面板容器（根据路由切换内容）
│   │   ├── ConversationPanel.vue   ← 对话列表（从 AppSidebar 拆出）
│   │   ├── KnowledgePanel.vue      ← 知识库树
│   │   ├── DocumentPanel.vue       ← 文档目录
│   │   ├── ModelPanel.vue          ← 模型列表
│   │   ├── GraphPanel.vue          ← 图谱列表
│   │   ├── EvalPanel.vue           ← 评测任务列表
│   │   ├── TeamPanel.vue           ← 成员列表
│   │   └── SettingsPanel.vue       ← 设置分组导航
│   └── <router-view>              ← 主内容区，按路由渲染页面
├── CommandPalette.vue              ← 全局命令面板（Ctrl+K 触发）
├── LoginView.vue                   ← 保持不变
└── ToastContainer.vue              ← 从 App.vue 提取
```

### 与当前实现的对比

| 方面 | 当前 | 改进后 |
|------|------|--------|
| 侧边栏 | 单栏 `AppSidebar`（9 个平铺按钮） | 双栏：IconRail + ContextPanel |
| 路由 | 无（所有功能弹 Drawer） | Vue Router，每个模块有独立页面 |
| 状态管理 | 7 个 `showXxx` ref | `useSidebarStore` + 路由状态 |
| 模块切换 | 点按钮 → 弹 Drawer | 点图标 → 路由跳转 → 面板内容切换 |
| 移动端 | Sheet 包裹整个 AppSidebar | Sheet 包裹 IconRail + ContextPanel |

---

## 3. 图标轨道（Icon Rail）

### 布局

```
┌────────┐
│  ✦     │  ← App Logo（点击回到 /chat）
│        │
│  💬    │  ← 对话（Chat）
│  📚    │  ← 知识库（Knowledge Base）
│  📄    │  ← 文档（Documents）
│  🤖    │  ← 模型管理（Models）
│  🕸️    │  ← 知识图谱（Graph）
│  📊    │  ← 评测看板（Eval）
│        │
│  ───── │  ← 分隔线
│  👥    │  ← 团队管理（Team）
│  ⚙️    │  ← 设置（Settings）
│        │
│  ↕     │  ← 弹性空间
│        │
│  ?     │  ← 帮助（点击弹出快捷键帮助 Modal，非路由页面）
│  [头像] │  ← 用户头像（hover → 退出登录 Popover）
└────────┘
  48px
```

### 模块与路由映射

| 图标 | 模块标识 | 路由路径 | 上下文面板内容 |
|------|---------|----------|--------------|
| 💬 | `chat` | `/chat`, `/chat/:id` | 对话列表（搜索 + 新建 + 历史） |
| 📚 | `knowledge` | `/knowledge`, `/knowledge/:id` | 知识库树（分组 + 新建 + 搜索） |
| 📄 | `documents` | `/documents` | 文档目录（按知识库筛选 + 上传） |
| 🤖 | `models` | `/models` | 模型列表（当前模型 + 切换） |
| 🕸️ | `graph` | `/graph` | 图谱列表（选择 + 配置） |
| 📊 | `eval` | `/eval` | 评测任务列表 |
| 👥 | `team` | `/team` | 成员列表 + 角色切换 |
| ⚙️ | `settings` | `/settings/:section?` | 设置分组导航 |

### 交互细节

- **当前模块高亮**：选中图标有 `bg-accent` 背景 + 左侧 3px 主色指示条
- **Tooltip**：hover 时显示模块名称，延迟 300ms
- **Logo 点击**：回到 `/chat`，同时展开上下文面板
- **用户头像**：hover 弹出 Popover，包含"退出登录"
- **Badge 提示**：对话图标可显示未读数角标

### 分组逻辑

- **核心模块**（上方）：对话、知识库、文档、模型、图谱、评测
- **管理模块**（下方，分隔线后）：团队、设置

---

## 4. 上下文面板（Context Panel）

### 通用结构

每个面板遵循三段式布局：

- **顶部**：标题 + 主操作按钮
- **中间**：搜索/筛选栏（可选）
- **内容区**：`flex-1 overflow-y-auto` 列表
- **底部**：状态栏/快捷入口（可选）

### 宽度与折叠

- **默认宽度**：260px，可通过拖拽边框在 220-320px 间调整
- **折叠快捷键**：`Ctrl+B` 折叠/展开（图标轨道保留）
- **折叠态浮出**：hover 图标时面板临时浮出（overlay 模式，300ms 延迟）
- **宽度持久化**：localStorage 存储用户调整后的宽度

### 各模块面板

#### 对话面板（ConversationPanel）

- 对话按时间分组：今天 / 昨天 / 本周 / 更早
- 支持搜索（标题 + 内容模糊匹配）
- 右键菜单：置顶、重命名、删除
- 当前对话高亮（`bg-accent` + 左侧指示条）
- 底部：清空历史入口

#### 知识库面板（KnowledgePanel）

- 按分组展示：我的知识库 / 团队共享 / 标签知识库
- 每个知识库显示文档数量 badge
- 点击 → 主内容区显示该知识库的文档列表
- 右键菜单：编辑、删除、分享

#### 文档面板（DocumentPanel）

- 顶部筛选器：按知识库过滤
- 文档显示索引状态图标（✅ 已索引 / ⏳ 索引中 / ❌ 失败）
- 底部状态栏：索引进度概览

#### 设置面板（SettingsPanel）

- 纯导航列表：RAG 配置 / 模型配置 / 账户
- 点击后主内容区显示对应设置表单
- 当前选中项高亮

#### 其他面板（Model / Graph / Eval / Team）

- 遵循通用三段式结构
- 顶部标题 + 新建/刷新按钮
- 内容区为对应资源的列表
- 点击列表项路由到详情页

---

## 5. 响应式策略

### 三档断点

| 断点 | 范围 | 侧边栏行为 | 主内容区 |
|------|------|-----------|---------|
| **Desktop** | ≥1280px | 图标轨道 + 上下文面板同时可见 | `flex-1`，面板折叠时自动扩展 |
| **Tablet** | 768–1279px | 仅图标轨道可见，面板默认折叠；点击图标时面板以 overlay 浮出 | 占满剩余宽度 |
| **Mobile** | <768px | 侧边栏整体隐藏，汉堡菜单以 Sheet 滑出 | 全宽 |

### Tablet overlay 行为

- 点击图标轨道图标 → 上下文面板从左侧浮出（overlay 模式）
- 主内容区加半透明遮罩（`bg-black/30`）
- 点击遮罩或按 Esc 收回面板
- 面板宽度固定 260px，不支持拖拽调整

### Mobile Sheet 行为

- 复用当前 `components/ui/sheet.vue`（基于 Radix Vue DialogRoot），`side="left"`
- Sheet 宽度：`min(288px, 100vw-12px)`
- Sheet 内部包含图标轨道 + 当前模块的上下文面板，图标轨道和面板垂直堆叠（非水平），图标轨道在顶部作为 Tab 切换器
- 点击图标切换模块时 Sheet 内容随之变化（面板部分替换）
- 点击对话项/知识库项后自动关闭 Sheet（`v-model` 设为 false）并路由到对应页面
- 汉堡按钮位于主内容区顶部 ChatHeader 中（`lg:hidden`）
- Sheet 打开时自动聚焦第一个可交互元素

---

## 6. 主内容区页面规划

### 路由表

| 路由 | 页面组件 | 来源 |
|------|---------|------|
| `/chat` | `ChatView` | 从 `ChatShell` 迁移 |
| `/chat/:id` | `ChatView` | 加载指定对话 |
| `/knowledge` | `KnowledgeView` | 替代 `KnowledgebaseDrawer` |
| `/knowledge/:id` | `KnowledgeDetailView` | 单个知识库详情 |
| `/documents` | `DocumentsView` | 替代 `DocumentDrawer` |
| `/models` | `ModelsView` | 替代 `ModelManager` Drawer |
| `/graph` | `GraphView` | 替代 `GraphViewer` 弹窗 |
| `/eval` | `EvalView` | 替代 `EvalDashboard` |
| `/team` | `TeamView` | 替代 `TeamDrawer` |
| `/settings/:section?` | `SettingsView` | 替代 `RagSettingsDrawer` |

### 面包屑与快捷操作栏

主内容区顶部统一页面头：

```
┌──────────────────────────────────────────────┐
│ 📚 知识库 / RAG 系统文档        [上传] [设置] │
│──────────────────────────────────────────────│
│  ... 页面内容 ...                             │
└──────────────────────────────────────────────┘
```

- 面包屑：显示模块和子页面层级，可点击跳回
- 右侧操作栏：当前页面高频操作按钮
- 移动端精简为"返回 + 标题 + ⋯ 更多菜单"

### 页面切换过渡

- `<router-view>` 使用 fade 过渡（150ms）
- 全屏模式：对话页面支持 F11 或按钮进入全屏（隐藏侧边栏）

---

## 7. 交互增强

### 命令面板（Ctrl+K）

触发方式：`Ctrl+K` / `⌘K`

搜索结果分三组：
- **最近访问**：按时间排序的最近对话、知识库、文档
- **快捷操作**：新建对话、新建知识库、上传文档等功能命令
- **导航**：页面跳转

操作：`↑↓` 选择、`↵` 执行、`Esc` 关闭。支持 `>` 前缀过滤只显示命令。

### 键盘快捷键

| 快捷键 | 功能 | 适用范围 |
|--------|------|---------|
| `Ctrl+K` | 打开命令面板 | 全局 |
| `Ctrl+B` | 折叠/展开上下文面板 | 全局 |
| `Ctrl+N` | 新建对话 | 对话页 |
| `Ctrl+Shift+N` | 新建知识库 | 知识库页 |
| `Ctrl+/` | 显示快捷键帮助 | 全局 |
| `1`-`8` | 切换到对应模块（无输入框聚焦时） | 全局 |
| `Esc` | 关闭浮层 / 退出全屏 | 全局 |

### 右键上下文菜单

对话列表项和知识库项支持右键菜单：置顶、重命名、复制链接、删除。使用 Radix Vue 的 `DropdownMenu` 原语实现（`DropdownMenuContent` 配合 `DropdownMenuItem`）。减少列表项的视觉杂乱。

### 面板宽度拖拽

鼠标拖拽上下文面板右边缘，实时调整宽度（220-320px）。`cursor: col-resize` + 1px 指示条，hover 时变宽 3px。

### 状态持久化

| localStorage 键 | 存储内容 |
|-----------------|---------|
| `sidebar.panelCollapsed` | 上下文面板是否折叠 |
| `sidebar.panelWidth` | 面板宽度（px） |
| `sidebar.lastModule` | 上次访问的模块 |
| `sidebar.recentItems` | 最近访问的 10 个条目 |

### 无障碍

- 图标轨道每个图标必须有 `aria-label`
- 面板切换时焦点自动移到新面板的第一个可交互元素
- `Tab` 键在图标轨道 → 上下文面板 → 主内容区之间顺序导航
- 命令面板打开时焦点锁定在搜索框

---

## 8. 技术实现

### 依赖变更

| 操作 | 包名 | 说明 |
|------|------|------|
| 新增 | `vue-router@4` | 路由管理 |
| 保留 | `pinia`, `radix-vue`, `lucide-vue-next`, `clsx`, `tailwind-merge` | 不变 |

### 新增 Pinia Store

```js
// stores/useSidebarStore.js
export const useSidebarStore = defineStore('sidebar', {
  state: () => ({
    panelCollapsed: false,
    panelWidth: 260,
    activeModule: 'chat',
    recentItems: [],
    commandPaletteOpen: false,
  }),
  actions: {
    togglePanel() { this.panelCollapsed = !this.panelCollapsed },
    setModule(module) { this.activeModule = module },
    addRecentItem(item) { /* 最多保留 10 条 */ },
    setPanelWidth(width) { this.panelWidth = clamp(width, 220, 320) },
  },
})
```

### 删除的内容

- `App.vue` 中 7 个 `showXxx` ref 及对应的 Sheet/Drawer 声明
- `AppSidebar.vue`（整体替换为 IconRail + ContextPanel）
- 各 Drawer 组件的 Sheet 包裹（迁移为独立页面后不再需要）

### 迁移策略

分四步，每步可独立验证和合并：

| 步骤 | 内容 | 影响范围 |
|------|------|---------|
| ① 路由骨架 | 安装 Vue Router，创建路由表，ChatShell 包装为 `/chat` 页面，其余用占位组件 | `main.js`, `App.vue`, 新增 `router/` |
| ② 双栏侧边栏 | 实现 IconRail + ContextPanel + ConversationPanel，替换 AppSidebar | 删除 `AppSidebar.vue`，新增 3 个组件 |
| ③ 页面迁移 | Drawer 组件逐一迁移为独立页面（每个 Drawer → View 组件 + 路由） | 每个 Drawer 独立迁移 |
| ④ 交互增强 | 命令面板、键盘快捷键、右键菜单、宽度拖拽、状态持久化 | 新增命令面板组件和 composable |

---

## 9. 文件清单

### 新增文件

```
frontend/src/
├── router/
│   └── index.js                     ← 路由配置
├── stores/
│   └── useSidebarStore.js           ← 侧边栏状态管理
├── layouts/
│   └── AppShell.vue                 ← 侧边栏 + 主内容布局容器
├── features/sidebar/
│   ├── IconRail.vue                 ← 图标轨道
│   ├── ContextPanel.vue             ← 上下文面板容器
│   ├── ConversationPanel.vue        ← 对话面板
│   ├── KnowledgePanel.vue           ← 知识库面板
│   ├── DocumentPanel.vue            ← 文档面板
│   ├── ModelPanel.vue               ← 模型面板
│   ├── GraphPanel.vue               ← 图谱面板
│   ├── EvalPanel.vue                ← 评测面板
│   ├── TeamPanel.vue                ← 团队面板
│   └── SettingsPanel.vue            ← 设置面板
├── features/command/
│   └── CommandPalette.vue           ← 命令面板
├── composables/
│   ├── useCommandPalette.js         ← 命令面板逻辑
│   ├── useKeyboardShortcuts.js      ← 全局快捷键
│   └── usePanelResize.js            ← 面板宽度拖拽
├── views/
│   ├── ChatView.vue                 ← 从 ChatShell 迁移
│   ├── KnowledgeView.vue            ← 从 KnowledgebaseDrawer 迁移
│   ├── KnowledgeDetailView.vue      ← 知识库详情
│   ├── DocumentsView.vue            ← 从 DocumentDrawer 迁移
│   ├── ModelsView.vue               ← 从 ModelManager 迁移
│   ├── GraphView.vue                ← 从 GraphViewer 迁移
│   ├── EvalView.vue                 ← 从 EvalDashboard 迁移
│   ├── TeamView.vue                 ← 从 TeamDrawer 迁移
│   └── SettingsView.vue             ← 从 RagSettingsDrawer 迁移
```

### 删除文件

```
frontend/src/features/conversations/AppSidebar.vue  ← 替换为 sidebar/ 组件
```

### 修改文件

```
frontend/src/App.vue        ← 移除 Drawer 声明，引入 AppShell + Router
frontend/src/main.js         ← 安装 Vue Router
frontend/package.json        ← 添加 vue-router 依赖
```
