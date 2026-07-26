# Full-Page Views for All Pages — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert all drawer/modal/panel pages to full-page views with sidebar navigation, matching the settings page pattern.

**Architecture:** Each L1 nav item (except chat) shows a full-page view with its own sidebar. L2 sidebar is hidden when any full-page view is active. A reusable `PageLayout` component provides the sidebar + content structure. Existing components are stripped of their drawer/modal chrome and wrapped in page layouts.

**Tech Stack:** Vue 3, Pinia, Tailwind CSS v4, Radix Vue, lucide-vue-next

---

### Task 1: Create PageLayout Reusable Component

**Files:**
- Create: `frontend/src/components/layout/PageLayout.vue`

- [ ] **Step 1: Create PageLayout.vue**

```vue
<script setup>
import ScrollArea from '../ui/scroll-area.vue'

const props = defineProps({
  sidebarWidth: { type: String, default: 'w-[272px]' },
})
</script>

<template>
  <div class="flex h-full w-full">
    <div :class="`flex flex-col h-full ${props.sidebarWidth} border-r border-border/45 bg-background flex-shrink-0`">
      <slot name="sidebar" />
    </div>
    <main class="flex-1 min-w-0 overflow-hidden">
      <ScrollArea class="h-full">
        <div class="mx-auto max-w-[920px] px-6 py-6 sm:px-8 sm:py-8">
          <slot />
        </div>
      </ScrollArea>
    </main>
  </div>
</template>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/components/layout/PageLayout.vue
git commit -m "feat: add PageLayout reusable component for full-page views"
```

---

### Task 2: Add activePage to Navigation Store

**Files:**
- Modify: `frontend/src/stores/useNavigationStore.js`

- [ ] **Step 1: Add activePage state**

Add after `activeSettingsSection`:
```js
  /** Active sub-page within current nav section */
  const activePage = ref('')
```

Add setter:
```js
  function setActivePage(page) {
    activePage.value = page
  }
```

Update `setActiveNav` to reset `activePage` when switching nav:
```js
  function setActiveNav(nav) {
    if (activeNav.value === nav) {
      l2Expanded.value = !l2Expanded.value
    } else {
      activeNav.value = nav
      activePage.value = ''
      l2Expanded.value = true
    }
  }
```

Add both to the return object.

- [ ] **Step 2: Commit**

```bash
git add frontend/src/stores/useNavigationStore.js
git commit -m "feat: add activePage state to navigation store"
```

---

### Task 3: Create KbPage (Knowledge Base Full-Page View)

**Files:**
- Create: `frontend/src/features/kb/KbPage.vue`

- [ ] **Step 1: Create KbPage.vue**

This wraps 4 sub-pages: knowledgebases, documents, tag-kb, graph. Each uses the existing component's content but without drawer chrome.

```vue
<script setup>
import { onMounted } from 'vue'
import { useNavigationStore } from '../../stores/useNavigationStore.js'
import { FolderOpen, FileText, Tags, Network, ArrowLeft, LogOut } from 'lucide-vue-next'
import { cn } from '../../lib/utils.js'
import { useAuthStore } from '../../stores/useAuthStore.js'
import PageLayout from '../../components/layout/PageLayout.vue'
import KnowledgebaseContent from './KnowledgebaseContent.vue'
import DocumentContent from '../documents/DocumentContent.vue'
import TagKbContent from '../tag-kb/TagKbContent.vue'
import GraphContent from '../graph/GraphContent.vue'

const navigationStore = useNavigationStore()
const authStore = useAuthStore()

const navItems = [
  { key: 'knowledgebases', label: '知识库管理', icon: FolderOpen },
  { key: 'documents', label: '文档管理', icon: FileText },
  { key: 'tag-kb', label: '标签知识库', icon: Tags },
  { key: 'graph', label: '知识图谱', icon: Network },
]

// Default to first item
onMounted(() => {
  if (!navigationStore.activePage || !navItems.find(i => i.key === navigationStore.activePage)) {
    navigationStore.setActivePage('knowledgebases')
  }
})
</script>

<template>
  <PageLayout>
    <template #sidebar>
      <!-- Back -->
      <div class="px-3 pt-3 pb-1">
        <button
          @click="navigationStore.setActiveNav('chat')"
          class="flex items-center gap-2 w-full px-3 py-2 rounded-[10px] text-sm text-muted-foreground hover:bg-muted/45 transition-colors"
        >
          <ArrowLeft class="h-4 w-4" />
          <span>返回</span>
        </button>
      </div>
      <div class="px-5 pt-2 pb-3">
        <h1 class="text-lg font-semibold text-foreground">知识库</h1>
      </div>
      <nav class="flex-1 overflow-y-auto min-h-0 px-3">
        <div class="flex flex-col gap-0.5">
          <button
            v-for="item in navItems"
            :key="item.key"
            @click="navigationStore.setActivePage(item.key)"
            :class="cn(
              'flex items-center gap-3 w-full px-3 py-2.5 rounded-[10px] text-sm transition-colors',
              navigationStore.activePage === item.key
                ? 'bg-muted/60 text-foreground font-medium'
                : 'text-muted-foreground hover:bg-muted/45 hover:text-foreground',
            )"
          >
            <component :is="item.icon" class="h-4 w-4 flex-shrink-0" />
            <span>{{ item.label }}</span>
          </button>
        </div>
      </nav>
      <div class="flex-shrink-0 px-3 py-3 border-t border-border/45">
        <button
          @click="authStore.logout()"
          class="flex items-center gap-3 w-full px-3 py-2.5 rounded-[10px] text-sm text-destructive hover:bg-destructive/10 transition-colors"
        >
          <LogOut class="h-4 w-4 flex-shrink-0" />
          <span>退出登录</span>
        </button>
      </div>
    </template>

    <KnowledgebaseContent v-if="navigationStore.activePage === 'knowledgebases'" />
    <DocumentContent v-else-if="navigationStore.activePage === 'documents'" />
    <TagKbContent v-else-if="navigationStore.activePage === 'tag-kb'" />
    <GraphContent v-else-if="navigationStore.activePage === 'graph'" />
  </PageLayout>
</template>
```

Note: This references `KnowledgebaseContent`, `DocumentContent`, `TagKbContent`, `GraphContent` — these are content-only wrappers we'll create in Tasks 4-7.

- [ ] **Step 2: Commit (after Tasks 4-7 create the content components)**

---

### Task 4: Create KnowledgebaseContent (strip drawer chrome)

**Files:**
- Create: `frontend/src/features/kb/KnowledgebaseContent.vue`

- [ ] **Step 1: Read KnowledgebaseDrawer.vue and extract content**

Read `frontend/src/features/kb/KnowledgebaseDrawer.vue`. Create `KnowledgebaseContent.vue` with the same logic but:
- Remove the outer `fixed inset-0 z-50` overlay div
- Remove the backdrop click handler
- Remove the `open`/`close` props/events
- Remove the close X button
- Remove the `w-[480px]` width constraint
- Keep all the KB management logic (create form, list, expand, upload, delete)

The content should render as a plain `<div class="space-y-4">` without any overlay.

- [ ] **Step 2: Commit**

```bash
git add frontend/src/features/kb/KnowledgebaseContent.vue
git commit -m "feat: add KnowledgebaseContent (drawer content without overlay)"
```

---

### Task 5: Create DocumentContent

**Files:**
- Create: `frontend/src/features/documents/DocumentContent.vue`

- [ ] **Step 1: Read DocumentDrawer.vue and extract content**

Read `frontend/src/features/documents/DocumentDrawer.vue`. Create `DocumentContent.vue` with the same logic. DocumentDrawer is already an embedded panel (no overlay), so this is mainly a copy with the same content, ensuring it works as a standalone page component.

- [ ] **Step 2: Commit**

```bash
git add frontend/src/features/documents/DocumentContent.vue
git commit -m "feat: add DocumentContent (standalone page version)"
```

---

### Task 6: Create TagKbContent

**Files:**
- Create: `frontend/src/features/tag-kb/TagKbContent.vue`

- [ ] **Step 1: Read TagKbDrawer.vue and extract content**

Read `frontend/src/features/tag-kb/TagKbDrawer.vue`. Create `TagKbContent.vue` with the same logic. TagKbDrawer is already an embedded panel (no overlay), so copy the content.

- [ ] **Step 2: Commit**

```bash
git add frontend/src/features/tag-kb/TagKbContent.vue
git commit -m "feat: add TagKbContent (standalone page version)"
```

---

### Task 7: Create GraphContent

**Files:**
- Create: `frontend/src/features/graph/GraphContent.vue`

- [ ] **Step 1: Read GraphViewer.vue and extract content**

Read `frontend/src/features/graph/GraphViewer.vue`. Create `GraphContent.vue` with:
- Remove the `<Teleport to="body">` wrapper
- Remove the `fixed inset-0 z-50` modal overlay
- Remove the `open`/`close` props/events
- Remove the backdrop and close button
- Make the SVG canvas responsive: use `viewBox` and let it fill the available width
- Update the simulation boundary constraints to be dynamic (use container width instead of hardcoded 800)
- Keep all the force simulation logic, node rendering, search, and detail panel

- [ ] **Step 2: Commit**

```bash
git add frontend/src/features/graph/GraphContent.vue
git commit -m "feat: add GraphContent (graph viewer without modal, responsive SVG)"
```

---

### Task 8: Create TeamPage

**Files:**
- Create: `frontend/src/features/team/TeamPage.vue`

- [ ] **Step 1: Read TeamDrawer.vue and create TeamPage**

Read `frontend/src/features/team/TeamDrawer.vue`. Create `TeamPage.vue` that:
- Uses `PageLayout` with a simple sidebar (just "团队管理" heading + back button + logout)
- Content: TeamDrawer's inner content without the `fixed inset-0` overlay
- Remove `open`/`close` props/events
- Remove backdrop and close button

Since team only has one sub-page, the sidebar can be minimal (no nav items needed, just the heading).

- [ ] **Step 2: Commit**

```bash
git add frontend/src/features/team/TeamPage.vue
git commit -m "feat: add TeamPage (full-page team management)"
```

---

### Task 9: Update SettingsView to Include Models and Eval

**Files:**
- Modify: `frontend/src/features/settings/SettingsSidebar.vue`
- Modify: `frontend/src/features/settings/SettingsView.vue`

- [ ] **Step 1: Read ModelManager.vue and EvalDashboard.vue**

Read both files to understand their content structure.

- [ ] **Step 2: Create ModelContent and EvalContent**

Create `frontend/src/features/model-manager/ModelContent.vue` — ModelManager content without Sheet wrapper (it's already an embedded panel, so mainly a copy).

Create `frontend/src/features/eval/EvalContent.vue` — EvalDashboard content without the Radix Dialog wrapper. Remove `DialogRoot`, `DialogPortal`, `DialogOverlay`, `DialogContent`, `DialogClose`. Remove `modelValue` prop. Keep the tab content, tables, metrics, and auto-polling logic.

- [ ] **Step 3: Update SettingsSidebar.vue**

Add two new nav items:
```js
  { key: 'models', label: '模型管理', icon: Cpu },
  { key: 'eval', label: '评测看板', icon: BarChart3 },
```

Import `Cpu` and `BarChart3` from lucide.

- [ ] **Step 4: Update SettingsView.vue**

Add imports for `ModelContent` and `EvalContent`. Add conditional rendering:
```vue
<ModelContent v-else-if="navigationStore.activeSettingsSection === 'models'" />
<EvalContent v-else-if="navigationStore.activeSettingsSection === 'eval'" />
```

- [ ] **Step 5: Commit**

```bash
git add -A
git commit -m "feat: add models and eval as settings sub-pages"
```

---

### Task 10: Update App.vue — Replace Drawers with Page Rendering

**Files:**
- Modify: `frontend/src/App.vue`

- [ ] **Step 1: Read current App.vue**

- [ ] **Step 2: Add new page imports**

```js
import KbPage from './features/kb/KbPage.vue'
import TeamPage from './features/team/TeamPage.vue'
```

- [ ] **Step 3: Replace main content rendering**

```vue
<main class="flex-1 flex flex-col min-w-0 overflow-hidden bg-background">
  <SettingsView
    v-if="navigationStore.activeNav === 'settings'"
    @open-models="navigationStore.setActiveSettingsSection('models')"
    @open-eval="navigationStore.setActiveSettingsSection('eval')"
  />
  <KbPage v-else-if="navigationStore.activeNav === 'kb'" />
  <TeamPage v-else-if="navigationStore.activeNav === 'team'" />
  <ChatShell v-else />
</main>
```

- [ ] **Step 4: Hide L2 sidebar for all non-chat nav items**

```vue
<L2Sidebar
  v-if="navigationStore.activeNav === 'chat'"
  ...
/>
```

- [ ] **Step 5: Remove all Sheet/drawer wrappers and refs**

Remove:
- All `<Sheet v-model="showXxx">` blocks (docs, models, tag-kb, graph, kb, team)
- `<EvalDashboard v-model="showEval" />`
- All `showXxx` refs
- All imports of removed drawer components
- All `@open-xxx` event handlers from L2Sidebar

Keep only: mobile sidebar Sheet, toast container.

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "feat: replace all drawers with full-page views, update App.vue routing"
```

---

### Task 11: Update L2 Sidebar to Remove Drawer Events

**Files:**
- Modify: `frontend/src/features/navigation/L2Sidebar.vue`

- [ ] **Step 1: Read L2Sidebar.vue**

- [ ] **Step 2: Remove all drawer-opening events**

The L2 sidebar should no longer emit `open-docs`, `open-eval`, `open-models`, `open-tag-kb`, `open-settings`, `open-graph`, `open-kb`, `open-team`. These are replaced by L1 nav switching.

The L2 sidebar only shows when `activeNav === 'chat'` (ChatPanel). Other nav items show full-page views.

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "refactor: remove drawer events from L2 sidebar"
```

---

### Task 12: Final Cleanup and Verification

- [ ] **Step 1: Verify all new files exist**

Check for:
- `frontend/src/components/layout/PageLayout.vue`
- `frontend/src/features/kb/KbPage.vue`
- `frontend/src/features/kb/KnowledgebaseContent.vue`
- `frontend/src/features/documents/DocumentContent.vue`
- `frontend/src/features/tag-kb/TagKbContent.vue`
- `frontend/src/features/graph/GraphContent.vue`
- `frontend/src/features/team/TeamPage.vue`
- `frontend/src/features/model-manager/ModelContent.vue`
- `frontend/src/features/eval/EvalContent.vue`

- [ ] **Step 2: Verify no remaining Sheet/drawer refs in App.vue**

`grep -n "Sheet\|showDocs\|showEval\|showModels\|showTagKb\|showGraph\|showKb\|showTeam" frontend/src/App.vue` should return nothing (except mobile sidebar Sheet).

- [ ] **Step 3: Commit final cleanup**

```bash
git add -A
git commit -m "chore: final cleanup for full-page views migration"
```
