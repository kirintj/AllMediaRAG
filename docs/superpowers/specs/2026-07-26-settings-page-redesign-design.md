# Settings Page Redesign — Full-Page Settings View

**Date:** 2026-07-26
**Status:** Draft
**Scope:** Replace the current SettingsPanel menu + RagSettingsDrawer pattern with a full-page sidebar + content settings view, matching webui's SettingsView design.

---

## 1. Problem

The current DataPilotAI settings UX is fragmented: `SettingsPanel` (L2 sidebar) is just a menu list of 8 items, each opening a separate right-side Sheet drawer. The actual RAG settings form (`RagSettingsDrawer`) lives in a narrow drawer (400-540px) with no persistent navigation. This is inconsistent with the webui's full-page settings design and wastes screen space.

Additionally, there is a **field name mismatch bug**: the frontend sends field names like `auto_keywords` and `raptor_enabled`, but the backend `RagSettings` Pydantic model expects `enable_auto_keywords` and `enable_raptor`. The save likely silently fails or uses defaults.

## 2. Design

### 2.1 Layout

When the user clicks `settings` in the L1 sidebar, the L2 sidebar is hidden and the main content area is replaced by a full-page `SettingsView`:

```
+-- L1 Sidebar --+-- SettingsView (flex row) --------------------------+
|  [icons]        |                                                     |
|  chat            |  Settings Sidebar    |  <main> content area        |
|  kb              |  (17rem wide)        |  (flex-1, max-w-[920px])    |
|  team            |                      |                             |
|  settings *      |  ◄ Back button       |  Section title (h1)         |
|                  |  "设置" heading       |  SettingsGroup cards        |
|                  |  Nav items list       |  SettingsRow rows           |
|                  |  退出 button          |  Save button                |
+------------------+----------------------+-----------------------------+
```

- L2 sidebar is hidden when `activeNav === 'settings'`
- ChatShell is hidden; SettingsView occupies the main content area
- Settings sidebar: 17rem wide, left border, rounded nav items, logout button at bottom
- Content area: radial gradient background, frosted glass cards

### 2.2 Settings Sections

Five sections with sidebar navigation:

| Nav Item | Icon | Content |
|----------|------|---------|
| **概览** | `LayoutDashboard` | Current RAG config summary cards (clickable to jump to section) |
| **文档解析** | `FileText` | auto_keywords, auto_questions, metadata_extraction, toc_extraction, topn settings |
| **RAPTOR** | `Layers` | raptor_enabled, raptor_method, raptor_max_clusters |
| **内容标签** | `Tag` | tagging_enabled, tagging_topn, tagging_tag_kb_ids |
| **知识图谱** | `Network` | graphrag_enabled, graphrag_method, entity_resolution, community_detection, pagerank |

### 2.3 UI Components (Vue ports of webui patterns)

**Layout primitives** (new, in `components/ui/`):

- `SettingsGroup` — Rounded frosted glass card container:
  - `rounded-[22px] border border-border/45 bg-card/86 backdrop-blur-xl shadow-[0_18px_65px_rgba(15,23,42,0.075)]`
  - Children separated by `divide-y divide-border/45`

- `SettingsRow` — Row inside SettingsGroup:
  - Left: title (14px) + optional description (12px)
  - Right: control area (toggle, input, segmented control)
  - `flex min-h-[62px] flex-col gap-3 px-4 py-3.5 sm:flex-row sm:items-center sm:justify-between`

- `SettingsSectionTitle` — Section heading:
  - `text-[13px] font-semibold tracking-[-0.01em] text-foreground/85`

- `SettingsFooter` — Save button area at bottom of form sections

**Interactive components** (new):

- `ToggleButton` — iOS-style toggle switch (22×38px):
  - ON: `bg-[#2997FF]` with white knob
  - OFF: `bg-muted` with gray knob
  - Smooth transition animation

- `SegmentedControl` — Pill-style radio group:
  - Container: `inline-flex h-8 items-center rounded-full bg-muted p-0.5`
  - Active option: `bg-background text-foreground shadow-sm`
  - Used for RAPTOR method selection, GraphRAG method selection

- `NumberInput` — Numeric input with optional suffix label

**Existing components reused:**
- `Input` (text input)
- `Button` (actions)
- `ScrollArea` (content scrolling)

### 2.4 Visual Details

- Font sizes: section title 13px, row title 14px, description 12px
- Content background: radial gradient `bg-[radial-gradient(circle_at_50%_0%,hsl(var(--muted))_0%,hsl(var(--background))_42%)]`
- Hover effects: nav items `hover:bg-muted/45 transition-colors`
- Active nav item: left accent border + `bg-muted/60`
- Sidebar border: `border-r border-border/45`
- Cards: frosted glass with `backdrop-blur-xl`

### 2.5 Data Flow

```
Page load → useSettingsStore.fetchSettings() → GET /api/settings/rag
                                              ↓
                                    store.settings (Pinia state)
                                              ↓
                              Section components watch → local form ref
                                              ↓
                              User edits → saveSettings() → PUT /api/settings/rag
                                              ↓
                                    Writes to .env (requires restart)
```

### 2.6 Field Name Mapping (Bug Fix)

The store will map frontend form field names to backend `RagSettings` model names on save, and reverse-map on load:

| Frontend Form | Backend Model |
|---------------|---------------|
| `auto_keywords` | `enable_auto_keywords` |
| `auto_questions` | `enable_auto_questions` |
| `metadata_extraction` | `enable_metadata_extraction` |
| `toc_extraction` | `enable_toc_extraction` |
| `keywords_topn` | `auto_keywords_topn` |
| `questions_topn` | `auto_questions_topn` |
| `raptor_enabled` | `enable_raptor` |
| `raptor_method` | `raptor_clustering_method` |
| `raptor_max_clusters` | `raptor_max_clusters` |
| `tagging_enabled` | `enable_content_tagging` |
| `tagging_topn` | `content_tag_topn` |
| `tagging_tag_kb_ids` | `content_tag_kb_ids` |
| `graphrag_enabled` | `graphrag_enabled` |
| `graphrag_method` | `graphrag_method` |
| `entity_resolution` | `graphrag_enable_resolution` |
| `community_detection` | `graphrag_enable_community` |
| `pagerank` | `graphrag_pagerank_enabled` |

### 2.7 Component Structure

```
SettingsView.vue              ← Main container (sidebar + content)
├── SettingsSidebar.vue       ← Left navigation sidebar
├── SettingsOverview.vue      ← Overview page (summary cards)
├── SettingsDocParsing.vue    ← Document parsing settings
├── SettingsRaptor.vue        ← RAPTOR settings
├── SettingsTagging.vue       ← Content tagging settings
└── SettingsGraphRAG.vue      ← Knowledge graph settings
```

All files under `frontend/src/features/settings/`.

### 2.8 App.vue Changes

- When `navigationStore.activeNav === 'settings'`: hide L2 sidebar and ChatShell, show SettingsView
- Remove `showRagSettings` ref and `RagSettingsDrawer` component
- Keep other SettingsPanel menu items (documents, knowledgebase, models, etc.) as they are — they remain as drawer-based features accessible from the settings overview page or L1 sidebar shortcuts

---

## 3. Files to Create

| File | Purpose |
|------|---------|
| `frontend/src/features/settings/SettingsView.vue` | Main settings container |
| `frontend/src/features/settings/SettingsSidebar.vue` | Settings navigation sidebar |
| `frontend/src/features/settings/SettingsOverview.vue` | Overview page |
| `frontend/src/features/settings/SettingsDocParsing.vue` | Document parsing section |
| `frontend/src/features/settings/SettingsRaptor.vue` | RAPTOR section |
| `frontend/src/features/settings/SettingsTagging.vue` | Content tagging section |
| `frontend/src/features/settings/SettingsGraphRAG.vue` | GraphRAG section |
| `frontend/src/components/ui/settings-group.vue` | SettingsGroup card component |
| `frontend/src/components/ui/settings-row.vue` | SettingsRow component |
| `frontend/src/components/ui/toggle-button.vue` | iOS-style toggle |
| `frontend/src/components/ui/segmented-control.vue` | Pill-style radio group |

## 4. Files to Modify

| File | Change |
|------|--------|
| `frontend/src/App.vue` | Add conditional rendering for SettingsView, hide L2 when settings active |
| `frontend/src/features/navigation/panels/SettingsPanel.vue` | Simplify or remove (settings no longer opens drawers) |
| `frontend/src/stores/useSettingsStore.js` | Add field name mapping between frontend and backend |
| `frontend/src/stores/useNavigationStore.js` | Add `activeSettingsSection` state |

## 5. Files to Remove

| File | Reason |
|------|--------|
| `frontend/src/features/settings/RagSettingsDrawer.vue` | Replaced by SettingsView sections |

## 6. Out of Scope

- Adding new settings sections beyond existing RAG settings
- Backend API changes (the `/api/settings/rag` endpoints remain as-is)
- Vue Router integration
- i18n translations (use Chinese labels directly for now)
- Dark mode testing (existing theme system handles this)
