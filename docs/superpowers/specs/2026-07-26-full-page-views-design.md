# Plan: Full-Page Views for All Pages

## Goal
Convert all drawer/modal/panel-based pages to full-page views with sidebar navigation, matching the settings page pattern.

## Current State
- L1 sidebar: chat, kb, team, settings (4 nav items)
- L2 sidebar: shows different panels based on activeNav, opens drawers
- Main content: always ChatShell
- 7 drawer components: DocumentDrawer, KnowledgebaseDrawer, ModelManager, TagKbDrawer, GraphViewer, TeamDrawer, EvalDashboard

## New Architecture

### Navigation Model
- `activeNav` (L1): 'chat' | 'kb' | 'team' | 'settings'
- `activePage` (new): tracks which sub-page is active within each nav section

When `activeNav === 'chat'`: show L2 sidebar + ChatShell (unchanged)
When `activeNav !== 'chat'`: hide L2 sidebar, show full-page view with its own sidebar

### Page Mapping

**KB section** (`activeNav === 'kb'`):
| Sub-page | Content | Current Source |
|----------|---------|----------------|
| knowledgebases | 知识库管理 | KnowledgebaseDrawer |
| documents | 文档管理 | DocumentDrawer |
| tag-kb | 标签知识库 | TagKbDrawer |
| graph | 知识图谱 | GraphViewer |

**Team section** (`activeNav === 'team'`):
| Sub-page | Content | Current Source |
|----------|---------|----------------|
| members | 团队管理 | TeamDrawer |

**Settings section** (`activeNav === 'settings'`):
| Sub-page | Content | Current Source |
|----------|---------|----------------|
| overview/doc-parsing/raptor/tagging/graphrag | RAG 设置 | SettingsView (already done) |
| models | 模型管理 | ModelManager |
| eval | 评测看板 | EvalDashboard |

### Implementation Steps

#### Step 1: Create PageLayout component
A reusable layout wrapper: left sidebar (272px) + right content area (ScrollArea).
Reused by all full-page views.

`frontend/src/components/layout/PageLayout.vue`
- Props: none (uses slots)
- Slots: `sidebar`, `default` (content)
- Layout: `flex h-full w-full` → sidebar (272px, border-r) + main (flex-1, ScrollArea, max-w-[920px])

#### Step 2: Create KbPage
Wraps KnowledgebaseDrawer, DocumentDrawer, TagKbDrawer, GraphViewer in a full-page view.

`frontend/src/features/kb/KbPage.vue`
- Uses PageLayout
- Sidebar: nav items for KB, docs, tag-kb, graph
- Content: conditionally renders the appropriate component (stripped of drawer/modal chrome)

#### Step 3: Create TeamPage
Wraps TeamDrawer in a full-page view.

`frontend/src/features/team/TeamPage.vue`
- Uses PageLayout
- Sidebar: just "团队管理" (single item, could be simplified)
- Content: TeamDrawer content without overlay

#### Step 4: Update SettingsPage
Add models and eval as sub-pages in the settings sidebar.

Update `SettingsSidebar.vue`: add 模型管理 and 评测看板 nav items
Update `SettingsView.vue`: add ModelManager and EvalDashboard as conditional sections

#### Step 5: Strip drawer/modal chrome from components
For each component, create a "content-only" version or refactor the existing component to optionally render without overlay:
- KnowledgebaseDrawer: remove `fixed inset-0` overlay, keep inner content
- DocumentDrawer: already content-only, just wrap in page
- TagKbDrawer: already content-only, just wrap in page
- GraphViewer: remove Teleport/modal, make SVG responsive
- TeamDrawer: remove overlay, keep inner content
- ModelManager: already content-only, just wrap in page
- EvalDashboard: remove Radix Dialog wrapper, keep tab content

#### Step 6: Update App.vue
Replace drawer Sheet components with conditional page rendering:

```vue
<main class="flex-1 flex flex-col min-w-0 overflow-hidden bg-background">
  <SettingsView v-if="navigationStore.activeNav === 'settings'" ... />
  <KbPage v-else-if="navigationStore.activeNav === 'kb'" />
  <TeamPage v-else-if="navigationStore.activeNav === 'team'" />
  <ChatShell v-else @open-docs="..." @open-eval="..." />
</main>
```

Remove all Sheet wrappers and drawer refs (showDocs, showEval, showModels, showTagKb, showGraph, showKb, showTeam).

#### Step 7: Update L1/L2 sidebar behavior
- When activeNav is 'chat': show L2 sidebar (ChatPanel)
- When activeNav is anything else: hide L2 sidebar (page provides its own nav)
- Remove drawer-opening events from L2 sidebar

### Files to Create
- `frontend/src/components/layout/PageLayout.vue`
- `frontend/src/features/kb/KbPage.vue`
- `frontend/src/features/team/TeamPage.vue`

### Files to Modify
- `frontend/src/App.vue` — conditional page rendering, remove drawers
- `frontend/src/features/settings/SettingsSidebar.vue` — add models, eval nav items
- `frontend/src/features/settings/SettingsView.vue` — add models, eval sections
- `frontend/src/features/kb/KnowledgebaseDrawer.vue` — strip overlay
- `frontend/src/features/graph/GraphViewer.vue` — strip modal, make responsive
- `frontend/src/features/team/TeamDrawer.vue` — strip overlay
- `frontend/src/features/eval/EvalDashboard.vue` — strip dialog wrapper
- `frontend/src/stores/useNavigationStore.js` — add activePage state

### Files to Remove (Sheet wrappers in App.vue)
- All `<Sheet v-model="showXxx">` blocks
- All `showXxx` refs
- All `@open-xxx` event handlers from L2Sidebar
