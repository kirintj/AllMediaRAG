# DataPilotAI Frontend WebUI Redesign

**Date**: 2026-07-22
**Status**: Approved
**Scope**: Full frontend rebuild — chat, conversation management, auth, document management, evaluation dashboard

## Goal

Replicate the Nanobot WebUI layout and visual style in DataPilotAI's Vue 3 frontend. Replace Element Plus with Tailwind CSS + shadcn/vue. Keep existing API layer, Pinia stores, and SSE streaming logic unchanged.

## Tech Stack

| Layer | Current | Target |
|-------|---------|--------|
| Framework | Vue 3.5 + Vite 8 | **unchanged** |
| State | Pinia 3 | **unchanged** |
| UI Library | Element Plus 2.14 | **remove**, replace with shadcn/vue |
| Styling | custom CSS + CSS vars | **Tailwind CSS 3** + HSL tokens |
| Markdown | marked 18 | keep |
| HTTP | Axios + fetch (SSE) | **unchanged** |
| Icons | (none) | **lucide-vue-next** |

New dependencies: `tailwindcss`, `@tailwindcss/vite`, `class-variance-authority`, `clsx`, `tailwind-merge`, `lucide-vue-next`

Remove: `element-plus`, `@element-plus/icons-vue`

## Layout Architecture

```
┌──────────────────────────────────────────────┐
│ App.vue                                       │
│ ┌─────────┬──────────────────────────────────┐│
│ │ Sidebar │  Main (flex-1)                   ││
│ │ 272px   │  ┌─────────────────────────────┐ ││
│ │         │  │ ChatHeader (44px)            │ ││
│ │ ┌─────┐ │  ├─────────────────────────────┤ ││
│ │ │Logo │ │  │                             │ ││
│ │ ├─────┤ │  │  ChatViewport               │ ││
│ │ │New  │ │  │  (messages + composer)      │ ││
│ │ │Chat │ │  │                             │ ││
│ │ ├─────┤ │  │  max-width: 792px centered  │ ││
│ │ │Conv │ │  │                             │ ││
│ │ │List │ │  │  ┌─────────────────────┐   │ ││
│ │ ├─────┤ │  │  │ Composer (sticky)    │   │ ││
│ │ │Docs │ │  │  └─────────────────────┘   │ ││
│ │ │Set  │ │  └─────────────────────────────┘ ││
│ │ └─────┘ │                                  ││
│ └─────────┴──────────────────────────────────┘│
└──────────────────────────────────────────────┘
```

- **Sidebar**: 272px wide, collapsible to 56px icon rail on desktop, Sheet overlay on mobile
- **Message area**: max-width 792px centered
- **Composer**: sticky bottom, rounded pill (22px radius), shadow
- **Empty state**: centered hero layout with greeting + centered composer (928px max)

## Design Tokens (HSL)

Aligned with Nanobot's `globals.css`:

```css
:root {
  --background: 0 0% 100%;
  --foreground: 240 3% 12%;
  --primary: 240 4% 16%;
  --secondary: 0 0% 96.1%;
  --muted: 0 0% 96.1%;
  --accent: 0 0% 96.1%;
  --destructive: 0 84.2% 60.2%;
  --border: 0 0% 89.8%;
  --sidebar: 0 0% 98.5%;
  --radius: 0.4375rem;
}

.dark {
  --background: 0 0% 10%;
  --foreground: 240 4% 96%;
  --sidebar: 0 0% 11.5%;
}
```

Font stacks:
- Sans: system-ui, -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Noto Sans, Noto Sans SC, PingFang SC, Hiragino Sans GB, Microsoft YaHei, sans-serif
- Mono: JetBrains Mono, Fira Code, Cascadia Code, Source Code Pro, Menlo, Consolas, monospace

## Component Map

| Nanobot (React) | DataPilotAI (Vue) | Notes |
|---|---|---|
| `Sidebar.tsx` | `AppSidebar.vue` | Logo + new chat + conversation list + settings |
| `ChatList.tsx` | `ConversationList.vue` | Sessions grouped by date, context menu |
| `ThreadShell.tsx` | `ChatShell.vue` | Chat area wrapper |
| `ThreadHeader.tsx` | `ChatHeader.vue` | Sidebar toggle + title + theme toggle |
| `ThreadViewport.tsx` | `ChatViewport.vue` | Scrollable messages + auto-scroll + scroll-to-bottom FAB |
| `MessageBubble.tsx` | `MessageBubble.vue` | User: right-aligned pill. AI: left-aligned prose |
| `ThreadComposer.tsx` | `ChatComposer.vue` | Hero/thread variants, RAG/direct mode toggle in toolbar |
| — | `DocumentDrawer.vue` | shadcn Sheet, upload/list/delete/sync |
| — | `EvalDashboard.vue` | shadcn Dialog + Tabs |
| — | `LoginView.vue` | Centered card login/register |

**Not included** (YAGNI): PromptRail, FilePreviewPanel, voice input, Agent activity, slash commands, workspace controls.

## Message Bubble Design

**User messages** (right-aligned pill):
- `ml-auto max-w-[min(85%,36rem)]`
- `rounded-[18px] bg-secondary/70 px-4 py-2`
- 16px font, 1.75 line-height, whitespace-pre-wrap
- Slide-in animation: `fade-in-0 slide-in-from-bottom-1 duration-300`

**Assistant messages** (left-aligned prose):
- `w-full text-[15px]`, CJK-aware line-height (1.8)
- No bubble border — prose flows like a document
- Footer: copy button + elapsed time
- Verification block: collapsible section below answer (confidence, faithfulness, hallucination risk)

## Composer Design

**Hero variant** (empty state):
- Max-width 58rem, centered
- `rounded-[28px]` with `shadow-[0_20px_55px_rgba(15,23,42,0.08)]`
- Textarea min-height 78px

**Thread variant** (in-conversation):
- Max-width 49.5rem, centered
- `rounded-[22px]` with smaller shadow
- Textarea min-height 50px

**Toolbar** (shared):
- Left: attach button (for document upload)
- Center: RAG/Direct mode toggle pill
- Right: send button (dark fill, `bg-foreground text-background`)
- Stop button replaces send during streaming

## File Structure

```
frontend/src/
├── api/                        # KEEP UNCHANGED
│   ├── index.js
│   ├── chat.js
│   ├── auth.js
│   ├── conversations.js
│   ├── documents.js
│   └── eval.js
├── stores/                     # KEEP UNCHANGED
│   ├── useChatStore.js
│   ├── useAuthStore.js
│   ├── useConversationStore.js
│   ├── useDocumentStore.js
│   ├── useEvalStore.js
│   └── useToastStore.js
├── components/
│   └── ui/                     # shadcn/vue primitives (manually added)
│       ├── button.vue
│       ├── input.vue
│       ├── textarea.vue
│       ├── dialog.vue
│       ├── sheet.vue
│       ├── dropdown-menu.vue
│       ├── separator.vue
│       ├── tooltip.vue
│       ├── scroll-area.vue
│       └── tabs.vue
├── features/
│   ├── auth/
│   │   └── LoginView.vue
│   ├── chat/
│   │   ├── ChatShell.vue
│   │   ├── ChatHeader.vue
│   │   ├── ChatViewport.vue
│   │   ├── ChatComposer.vue
│   │   ├── MessageBubble.vue
│   │   └── MarkdownRenderer.vue
│   ├── conversations/
│   │   ├── AppSidebar.vue
│   │   └── ConversationList.vue
│   ├── documents/
│   │   └── DocumentDrawer.vue
│   └── eval/
│       └── EvalDashboard.vue
├── composables/
│   ├── useTheme.ts
│   └── useMarkdown.ts
├── lib/
│   └── utils.ts
├── styles/
│   └── globals.css
├── App.vue
└── main.js
```

## Files to Delete

- `frontend/src/style.css` — replaced by `globals.css`
- `frontend/src/styles/nanobot-tokens.css` — merged into `globals.css`
- `frontend/src/styles/harmony-tokens.css` — unused
- `frontend/src/styles/mobile-scale.css` — handled by Tailwind responsive
- All files under `frontend/src/features/documents/` except `DocumentDrawer.vue` — inline into drawer
- `frontend/src/features/eval/EvalDashboard.vue` — rewrite from scratch

## Implementation Order

1. **Infrastructure**: Tailwind CSS + shadcn/ui primitives + design tokens + `lib/utils.ts`
2. **Layout shell**: `App.vue` + `AppSidebar.vue` + `ChatShell.vue` + `ChatHeader.vue`
3. **Chat core**: `ChatViewport.vue` + `MessageBubble.vue` + `ChatComposer.vue` + `MarkdownRenderer.vue`
4. **Conversation management**: `ConversationList.vue` — wire to existing `useConversationStore`
5. **Auth**: `LoginView.vue` — wire to existing `useAuthStore`
6. **Documents**: `DocumentDrawer.vue` — wire to existing `useDocumentStore`
7. **Evaluation**: `EvalDashboard.vue` — wire to existing `useEvalStore`
8. **Cleanup**: remove Element Plus, delete old CSS files, verify all imports

## Constraints

- No new backend changes required — all existing API endpoints remain unchanged
- SSE streaming (`api/chat.js`) must be preserved as-is
- Dark mode must work (class-based toggle)
- Mobile responsive: sidebar becomes Sheet overlay below 1024px
- CJK typography: line-height 1.8 for Chinese content

## Non-Goals

- No PromptRail / prompt navigation dots
- No voice input
- No file preview side panel
- No slash command palette
- No agent activity / tool-call visualization
- No workspace/project management
