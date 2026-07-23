# ALLRAG Frontend WebUI Redesign — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace Element Plus with Tailwind CSS + shadcn/vue, replicate Nanobot WebUI layout in ALLRAG's Vue 3 frontend.

**Architecture:** Keep all api/ and stores/ files unchanged. Rewrite all .vue components and styles. shadcn/vue components added manually (no CLI).

**Tech Stack:** Vue 3.5, Vite 8, Tailwind CSS 3, shadcn/vue (Radix Vue), lucide-vue-next, Pinia 3

---

### Task 1: Infrastructure — Tailwind + shadcn/vue + Design Tokens

**Files:**
- Modify: `frontend/package.json`
- Modify: `frontend/vite.config.js`
- Modify: `frontend/src/main.js`
- Create: `frontend/src/styles/globals.css`
- Create: `frontend/src/lib/utils.ts`
- Create: `frontend/src/composables/useTheme.ts`
- Delete: `frontend/src/style.css`, `frontend/src/styles/nanobot-tokens.css`, `frontend/src/styles/harmony-tokens.css`, `frontend/src/styles/mobile-scale.css`

Steps:
- [ ] Install dependencies: tailwindcss, @tailwindcss/vite, radix-vue, class-variance-authority, clsx, tailwind-merge, lucide-vue-next
- [ ] Remove element-plus from package.json
- [ ] Update vite.config.js to add tailwindcss plugin
- [ ] Create globals.css with HSL tokens (from Nanobot)
- [ ] Create lib/utils.ts with cn() helper
- [ ] Create composables/useTheme.ts
- [ ] Update main.js: remove ElementPlus, import globals.css
- [ ] Delete old CSS files
- [ ] Verify dev server starts

### Task 2: shadcn/vue UI Primitives

**Files:**
- Create: `frontend/src/components/ui/button.vue`
- Create: `frontend/src/components/ui/input.vue`
- Create: `frontend/src/components/ui/textarea.vue`
- Create: `frontend/src/components/ui/dialog.vue`
- Create: `frontend/src/components/ui/sheet.vue`
- Create: `frontend/src/components/ui/separator.vue`
- Create: `frontend/src/components/ui/tooltip.vue`
- Create: `frontend/src/components/ui/tabs.vue`
- Create: `frontend/src/components/ui/scroll-area.vue`
- Create: `frontend/src/components/ui/dropdown-menu.vue`

Steps:
- [ ] Create each shadcn/vue primitive using Radix Vue + CVA
- [ ] Verify imports resolve

### Task 3: Layout Shell — App.vue + AppSidebar + ChatShell + ChatHeader

**Files:**
- Rewrite: `frontend/src/App.vue`
- Create: `frontend/src/features/conversations/AppSidebar.vue`
- Create: `frontend/src/features/conversations/ConversationList.vue`
- Create: `frontend/src/features/chat/ChatShell.vue`
- Create: `frontend/src/features/chat/ChatHeader.vue`

Steps:
- [ ] Rewrite App.vue with new layout (sidebar 272px + main flex-1)
- [ ] Create AppSidebar (logo, new chat, conversation list slot, settings)
- [ ] Create ConversationList (grouped by date, load/delete context menu)
- [ ] Create ChatShell (wrapper for header + viewport)
- [ ] Create ChatHeader (sidebar toggle, title, theme toggle)
- [ ] Verify layout renders in dev server

### Task 4: Chat Core — ChatViewport + MessageBubble + ChatComposer + MarkdownRenderer

**Files:**
- Create: `frontend/src/features/chat/ChatViewport.vue`
- Create: `frontend/src/features/chat/MessageBubble.vue`
- Create: `frontend/src/features/chat/ChatComposer.vue`
- Create: `frontend/src/features/chat/MarkdownRenderer.vue`

Steps:
- [ ] Create MarkdownRenderer (marked + highlight.js + DOMPurify)
- [ ] Create MessageBubble (user: right pill, assistant: left prose)
- [ ] Create ChatViewport (scrollable, auto-scroll, scroll-to-bottom FAB)
- [ ] Create ChatComposer (hero/thread variants, RAG/direct toggle, send/stop)
- [ ] Wire to useChatStore — verify SSE streaming works end-to-end

### Task 5: Auth — LoginView

**Files:**
- Rewrite: `frontend/src/features/auth/LoginView.vue`

Steps:
- [ ] Rewrite as centered card with shadcn Tabs (login/register)
- [ ] Wire to useAuthStore

### Task 6: Documents — DocumentDrawer

**Files:**
- Rewrite: `frontend/src/features/documents/DocumentDrawer.vue`
- Delete: DocumentList.vue, DocumentListItem.vue, UploadArea.vue, StatsHeaderCard.vue, BatchUploadProgress.vue

Steps:
- [ ] Rewrite as shadcn Sheet with inline upload/list/delete/sync
- [ ] Wire to useDocumentStore
- [ ] Delete unused component files

### Task 7: Evaluation — EvalDashboard

**Files:**
- Rewrite: `frontend/src/features/eval/EvalDashboard.vue`

Steps:
- [ ] Rewrite as shadcn Dialog + Tabs (reports table + metrics)
- [ ] Wire to useEvalStore

### Task 8: Cleanup

Steps:
- [ ] Delete old ChatView.vue, ChatSidebar.vue, ChatMessage.vue
- [ ] Remove @element-plus/icons-vue if present
- [ ] Verify full app works: login, chat (RAG + direct), documents, eval
- [ ] Commit
