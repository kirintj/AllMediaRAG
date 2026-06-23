# 文档管理布局重构设计

## 1. 概述

将文档管理模块从右侧 280px 固定侧边栏重构为独立抽屉页面，遵循 HarmonyOS Design 规范（mobile-list 布局），优化信息层级和视觉一致性。

### 1.1 目标
- 视觉对齐 HMOS 设计规范（card/list 布局、语义 token、交互状态层）
- 重新梳理信息层级，突出核心功能
- 提升文档管理的可发现性和操作效率

### 1.2 设计参考
- `references/1.layout/layout-list.md` — mobile-list 布局规范
- `references/3.component/list.md` — list 组件（icon2lines 变体）
- `references/3.component/titlebar.md` — titlebar 组件（secondary 变体）
- `references/3.component/search.md` — search 组件
- `references/3.component/chipstab.md` — chips 筛选组件
- `references/3.component/cardview.md` — cardview 容器组件

---

## 2. 容器架构

### 2.1 形态
- 从固定侧边栏改为**独立抽屉页面**
- 触发入口：ChatView 顶部工具栏「文档管理」图标按钮
- 打开动画：从右侧滑入（300ms ease-out），背景加半透明遮罩
- 关闭方式：关闭按钮 / 点击遮罩 / Esc 键

### 2.2 响应式宽度
| 视口宽度 | 抽屉宽度 | 行为 |
|---------|---------|------|
| ≥1024px | 480px | 左侧保留主内容区可见 |
| 768px~1023px | 400px | 左侧保留主内容区可见 |
| <768px | 100vw | 全屏覆盖 |

---

## 3. 页面骨架

遵循 `layout-list.md` 的页面结构：

```
┌─────────────────────────────────────┐
│  Titlebar (secondary variant)       │ ← 标题 + 副标题摘要 + 关闭按钮
├─────────────────────────────────────┤
│  Stats Header Card                  │ ← 3 列统计（文档块/文档数/总大小）
├─────────────────────────────────────┤
│  Upload Area                        │ ← 拖拽上传区
├─────────────────────────────────────┤
│  Search + Chips Filter              │ ← 搜索框 + 类型筛选
├─────────────────────────────────────┤
│  Document List (scrollable)         │ ← 文档列表（icon2lines 变体）
│    ├── DocumentListItem             │
│    ├── DocumentListItem             │
│    └── ...                          │
├─────────────────────────────────────┤
│  Bottom Action Bar (sticky)         │ ← 加载/同步/清空 按钮
└─────────────────────────────────────┘
```

---

## 4. 组件映射

| 布局块 | 组件 Reference | 变体 | 职责 |
|--------|---------------|------|------|
| Titlebar | `titlebar.md` | `secondary` + 1 action | 标题「文档管理」+ 副标题「X 个文档 · Y 块向量」+ 关闭按钮 |
| Stats Header Card | `cardview.md` + 自定义 | 白色圆角卡片 | 3 列统计数字展示 |
| Upload Area | 页面级自定义 + Element Plus | 拖拽区域 | 文件上传交互 |
| Search Bar | `search.md` | `off/normal` | 搜索输入 + 清除按钮 |
| Chips Tabs | `chipstab.md` | 文件类型筛选 | 全部/PDF/DOCX/MD/图片 |
| Document List Item | `list.md` | `icon2lines` (72px) | 文件图标 + 名称 + 元数据 |
| Divider | `divider.md` | `inset` | 列表项间分割线 |
| Bottom Shell | 页面级自定义 | 固定吸底 | 加载/同步/清空按钮 |

---

## 5. 文档列表项设计

基于 `list.md` 的 `icon2lines` 变体（72px 高度）：

### 5.1 结构
```
┌──────────────────────────────────────────────────┐
│  ┌──────┐                                        │
│  │ PDF  │  技术文档v2.pdf              🗑️    │ ← 72px
│  │ 类型  │  PDF · 24 块 · 2.3 MB                │
│  └──────┘                                        │
│──────────────────────────────────────────────────│ ← inset divider
└──────────────────────────────────────────────────┘
```

### 5.2 内部细节
- **左侧**：文件类型图标（48×48, r=12），背景色按类型区分
- **中间文本组**：文件名（16px Medium, 单行截断）+ 元数据行（14px Regular, `font_secondary`）
- **右侧**：删除按钮（默认隐藏，hover 淡入显示）
- **元数据**：类型标签 chip + 块数 + 文件大小，用 `·` 分隔

### 5.3 类型色彩语义 Token

| 文件类型 | 图标背景 | 文字色 | Token 映射 |
|---------|---------|--------|-----------|
| PDF | `rgba(232,64,38,0.1)` | `#E84026` | `--harmony-warning` 系列 |
| DOCX/DOC | `rgba(10,89,247,0.1)` | `#0A59F7` | `--harmony-brand` |
| MD/TXT | `rgba(0,0,0,0.06)` | `#606266` | `--harmony-font-secondary` |
| 图片 | `rgba(100,187,92,0.1)` | `#64BB5C` | `--harmony-confirm` |

---

## 6. 信息层级

优先级从高到低：

1. **标题栏** — 页面身份 + 摘要数据（文档数/向量块数）
2. **上传区** — 最常用操作，置顶就近
3. **搜索 + 筛选** — 快速定位文档
4. **文档列表** — 核心内容，占据主要滚动空间
5. **底部操作栏** — 低频操作（加载/同步/清空）

---

## 7. 交互行为

### 7.1 搜索与筛选
- 搜索框实时过滤（debounce 300ms），匹配文件名
- Chips 筛选切换时立即过滤列表（单选，点击已选中的取消筛选）
- 搜索 + 筛选条件取交集
- 筛选结果为空时显示空状态插图 + 提示文案

### 7.2 列表项状态
- **默认态**：白色背景
- **Hover**：`background: var(--harmony-interactive-hover)`，删除按钮淡入
- **Pressed**：`background: var(--harmony-interactive-pressed)`
- **删除确认**：`ElMessageBox.confirm` 对话框

### 7.3 底部操作栏
```
[ 📥 加载本地文档 ]  [ 🔄 增量同步 ]  [ 🗑️ 清空 ]
   主按钮(品牌色)      次按钮(描边)    警告按钮
```

### 7.4 键盘交互
- `Esc`：关闭抽屉
- 搜索框聚焦时 `Esc`：清除搜索内容

---

## 8. 状态处理

### 8.1 空状态
- 无文档：居中插图 + 「暂无已导入的文档」+ 引导文案
- 搜索无结果：搜索图标 + 「未找到匹配的文件」+ 清除按钮
- 筛选无结果：筛选图标 + 「没有 X 类型的文档」+ 清除筛选

### 8.2 加载状态
- 初次打开：列表区 skeleton 骨架屏（3 行占位）
- 加载/同步中：按钮 spinner + 禁用，底部进度文本
- 批量上传：上传区内嵌 BatchUploadProgress

### 8.3 错误处理
- 上传失败：Toast 提示文件名 + 原因，不中断其他文件
- 删除失败：Toast 错误提示
- 网络异常：列表区错误状态 + 重试按钮
- 加载/同步失败：按钮恢复 + Toast 提示

---

## 9. 组件拆分

```
features/documents/
  ├── DocumentDrawer.vue       ← 抽屉容器（titlebar + 布局）
  ├── StatsHeaderCard.vue      ← 统计卡片区域
  ├── UploadArea.vue           ← 上传区域
  ├── DocumentList.vue         ← 文档列表（搜索 + 筛选 + 列表）
  ├── DocumentListItem.vue     ← 单个文档列表项
  ├── BatchUploadProgress.vue  ← 批量上传进度（保留）
  └── DocumentPanel.vue        ← 废弃
```

---

## 10. App.vue 变更

- 移除右侧 `<el-aside width="280px">` 固定栏
- 新增 `<DocumentDrawer v-model="showDocs" />`
- ChatView 工具栏新增文档管理入口按钮

---

## 11. 数据流

```
DocumentDrawer.vue
  ├── useDocumentStore()
  │   ├── documents / documentDetails / stats
  │   └── Actions: fetch* / remove* / sync*
  ├── uploadDocument() / uploadBatch()
  ├── loadAllDocuments()
  └── syncDocuments()
```

---

## 12. Token 对齐

- 间距：`--harmony-padding-level*` / `--harmony-corner-radius-level*`
- 字体：`--harmony-font-size-*` / `--harmony-font-weight-*`
- 颜色：`--harmony-font-*` / `--harmony-comp-*` / `--harmony-interactive-*`
- 禁止硬编码十六进制颜色值

---

## 13. 性能考虑

- 文档数 > 50 时启用虚拟滚动
- 搜索输入 debounce 300ms
- 抽屉打开时才加载数据（懒加载）
- 关闭时清理搜索状态
