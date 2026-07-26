# Settings Page Redesign — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current SettingsPanel menu + RagSettingsDrawer pattern with a full-page sidebar + content settings view, matching webui's SettingsView design.

**Architecture:** When `activeNav === 'settings'`, hide L2Sidebar and ChatShell, show a full-page `SettingsView` with its own 17rem sidebar navigation and content area. The settings store gains field-name mapping to fix the frontend/backend mismatch bug. New UI primitives (`ToggleButton`, `SettingsGroup`, `SettingsRow`) are created as Vue components following the existing shadcn-vue pattern.

**Tech Stack:** Vue 3 (Composition API), Pinia, Tailwind CSS v4, Radix Vue, lucide-vue-next, class-variance-authority

---

### Task 1: Create ToggleButton Component

**Files:**
- Create: `frontend/src/components/ui/toggle-button.vue`

- [ ] **Step 1: Create toggle-button.vue**

Create `frontend/src/components/ui/toggle-button.vue`:

```vue
<script setup>
import { cn } from '@/lib/utils'

const props = defineProps({
  checked: { type: Boolean, default: false },
  disabled: { type: Boolean, default: false },
  label: { type: String, default: '' },
})

const emit = defineEmits(['update:checked'])

function toggle() {
  if (!props.disabled) {
    emit('update:checked', !props.checked)
  }
}
</script>

<template>
  <button
    type="button"
    role="switch"
    :aria-checked="checked"
    :aria-label="label"
    :disabled="disabled"
    @click="toggle"
    :class="cn(
      'relative inline-flex h-[22px] w-[38px] shrink-0 items-center rounded-full p-[2px]',
      'transition-colors duration-200 ease-out focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2',
      checked
        ? 'bg-[#2997FF] shadow-[inset_0_0_0_1px_rgba(0,0,0,0.035)]'
        : 'bg-muted shadow-[inset_0_0_0_1px_rgba(0,0,0,0.035)] hover:bg-muted/80',
      disabled && 'cursor-default opacity-60',
    )"
  >
    <span
      aria-hidden
      :class="cn(
        'h-[18px] w-[18px] rounded-full bg-background shadow-[0_1px_2px_rgba(0,0,0,0.18),0_2px_7px_rgba(0,0,0,0.11)]',
        'transition-transform duration-200 ease-out',
        checked ? 'translate-x-[16px]' : 'translate-x-0',
      )"
    />
    <span class="sr-only">{{ label }}</span>
  </button>
</template>
```

- [ ] **Step 2: Verify the file compiles**

Run: `cd frontend && npx vue-tsc --noEmit --skipLibCheck 2>&1 | head -20` (or just check for syntax errors visually)

Expected: No errors related to `toggle-button.vue`

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/ui/toggle-button.vue
git commit -m "feat: add ToggleButton UI component (iOS-style toggle switch)"
```

---

### Task 2: Create SettingsGroup and SettingsRow Components

**Files:**
- Create: `frontend/src/components/ui/settings-group.vue`
- Create: `frontend/src/components/ui/settings-row.vue`
- Create: `frontend/src/components/ui/settings-section-title.vue`

- [ ] **Step 1: Create settings-group.vue**

Create `frontend/src/components/ui/settings-group.vue`:

```vue
<script setup>
import { cn } from '@/lib/utils'

const props = defineProps({
  class: { type: String, default: '' },
})
</script>

<template>
  <div :class="cn(
    'overflow-hidden rounded-[22px] border border-border/45 bg-card/86',
    'shadow-[0_18px_65px_rgba(15,23,42,0.075)] backdrop-blur-xl',
    'dark:border-white/10 dark:shadow-[0_18px_65px_rgba(0,0,0,0.24)]',
    props.class
  )">
    <div class="divide-y divide-border/45">
      <slot />
    </div>
  </div>
</template>
```

- [ ] **Step 2: Create settings-row.vue**

Create `frontend/src/components/ui/settings-row.vue`:

```vue
<script setup>
const props = defineProps({
  title: { type: String, required: true },
  description: { type: String, default: '' },
})
</script>

<template>
  <div class="flex min-h-[62px] flex-col gap-3 px-4 py-3.5 sm:flex-row sm:items-center sm:justify-between sm:px-5">
    <div class="min-w-0">
      <div class="text-[14px] font-medium leading-5 text-foreground">{{ title }}</div>
      <div v-if="description" class="mt-0.5 max-w-[28rem] text-[12px] leading-5 text-muted-foreground">
        {{ description }}
      </div>
    </div>
    <div class="min-w-0 sm:ml-6 sm:shrink-0">
      <slot />
    </div>
  </div>
</template>
```

- [ ] **Step 3: Create settings-section-title.vue**

Create `frontend/src/components/ui/settings-section-title.vue`:

```vue
<script setup>
const props = defineProps({
  class: { type: String, default: '' },
})
</script>

<template>
  <h2 :class="`mb-2 px-1 text-[13px] font-semibold tracking-[-0.01em] text-foreground/85 ${props.class}`">
    <slot />
  </h2>
</template>
```

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/ui/settings-group.vue frontend/src/components/ui/settings-row.vue frontend/src/components/ui/settings-section-title.vue
git commit -m "feat: add SettingsGroup, SettingsRow, SettingsSectionTitle UI components"
```

---

### Task 3: Add Field Name Mapping to Settings Store

**Files:**
- Modify: `frontend/src/stores/useSettingsStore.js`

- [ ] **Step 1: Read the current store**

Read `frontend/src/stores/useSettingsStore.js` to confirm current content.

- [ ] **Step 2: Replace the store with mapping logic**

Replace the entire content of `frontend/src/stores/useSettingsStore.js` with:

```js
import { ref } from 'vue'
import { defineStore } from 'pinia'

/**
 * Maps between frontend form field names and backend RagSettings model names.
 * Frontend uses short names (e.g. "auto_keywords"), backend uses prefixed names (e.g. "enable_auto_keywords").
 */
const TO_BACKEND = {
  auto_keywords: 'enable_auto_keywords',
  auto_questions: 'enable_auto_questions',
  metadata_extraction: 'enable_metadata_extraction',
  toc_extraction: 'enable_toc_extraction',
  keywords_topn: 'auto_keywords_topn',
  questions_topn: 'auto_questions_topn',
  raptor_enabled: 'enable_raptor',
  raptor_method: 'raptor_clustering_method',
  raptor_max_clusters: 'raptor_max_clusters',
  tagging_enabled: 'enable_content_tagging',
  tagging_topn: 'content_tag_topn',
  tagging_tag_kb_ids: 'content_tag_kb_ids',
  graphrag_enabled: 'graphrag_enabled',
  graphrag_method: 'graphrag_method',
  graphrag_entity_resolution: 'graphrag_enable_resolution',
  graphrag_community_detection: 'graphrag_enable_community',
  graphrag_pagerank: 'graphrag_pagerank_enabled',
}

// Reverse map: backend -> frontend
const TO_FRONTEND = Object.fromEntries(
  Object.entries(TO_BACKEND).map(([k, v]) => [v, k])
)

function mapToBackend(form) {
  const result = {}
  for (const [key, value] of Object.entries(form)) {
    const backendKey = TO_BACKEND[key] || key
    result[backendKey] = value
  }
  return result
}

function mapToFrontend(backendData) {
  const result = {}
  for (const [key, value] of Object.entries(backendData)) {
    const frontendKey = TO_FRONTEND[key] || key
    result[frontendKey] = value
  }
  return result
}

export const useSettingsStore = defineStore('settings', () => {
  const settings = ref(null)
  const loading = ref(false)
  const saving = ref(false)

  async function fetchSettings() {
    loading.value = true
    try {
      const { getRagSettings } = await import('../api/settings.js')
      const raw = await getRagSettings()
      settings.value = mapToFrontend(raw)
    } finally {
      loading.value = false
    }
  }

  async function saveSettings(formPayload) {
    saving.value = true
    try {
      const { updateRagSettings } = await import('../api/settings.js')
      const backendPayload = mapToBackend(formPayload)
      const result = await updateRagSettings(backendPayload)
      settings.value = mapToFrontend(result.settings)
      return result
    } finally {
      saving.value = false
    }
  }

  return { settings, loading, saving, fetchSettings, saveSettings }
})
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/stores/useSettingsStore.js
git commit -m "fix: add field name mapping between frontend form and backend RagSettings model"
```

---

### Task 4: Add activeSettingsSection to Navigation Store

**Files:**
- Modify: `frontend/src/stores/useNavigationStore.js`

- [ ] **Step 1: Read the current store**

Read `frontend/src/stores/useNavigationStore.js` to confirm current content.

- [ ] **Step 2: Add activeSettingsSection state**

Add the following after the `mobileSidebarOpen` ref declaration (after line `const mobileSidebarOpen = ref(false)`):

```js
  /** Active settings section: 'overview' | 'doc-parsing' | 'raptor' | 'tagging' | 'graphrag' */
  const activeSettingsSection = ref('overview')
```

Add the setter function before the `return` statement:

```js
  function setActiveSettingsSection(section) {
    activeSettingsSection.value = section
  }
```

Add `activeSettingsSection` and `setActiveSettingsSection` to the return object.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/stores/useNavigationStore.js
git commit -m "feat: add activeSettingsSection to navigation store"
```

---

### Task 5: Create SettingsSidebar Component

**Files:**
- Create: `frontend/src/features/settings/SettingsSidebar.vue`

- [ ] **Step 1: Create SettingsSidebar.vue**

Create `frontend/src/features/settings/SettingsSidebar.vue`:

```vue
<script setup>
import { useNavigationStore } from '../../stores/useNavigationStore.js'
import { useAuthStore } from '../../stores/useAuthStore.js'
import { LayoutDashboard, FileText, Layers, Tag, Network, ArrowLeft, LogOut } from 'lucide-vue-next'
import { cn } from '../../lib/utils.js'

const navigationStore = useNavigationStore()
const authStore = useAuthStore()

const navItems = [
  { key: 'overview', label: '概览', icon: LayoutDashboard },
  { key: 'doc-parsing', label: '文档解析', icon: FileText },
  { key: 'raptor', label: 'RAPTOR', icon: Layers },
  { key: 'tagging', label: '内容标签', icon: Tag },
  { key: 'graphrag', label: '知识图谱', icon: Network },
]

function selectSection(key) {
  navigationStore.setActiveSettingsSection(key)
}

function backToChat() {
  navigationStore.setActiveNav('chat')
}
</script>

<template>
  <div class="flex flex-col h-full w-[272px] border-r border-border/45 bg-background flex-shrink-0">
    <!-- Back button -->
    <div class="px-3 pt-3 pb-1">
      <button
        @click="backToChat"
        class="flex items-center gap-2 w-full px-3 py-2 rounded-[10px] text-sm text-muted-foreground hover:bg-muted/45 transition-colors"
      >
        <ArrowLeft class="h-4 w-4" />
        <span>返回</span>
      </button>
    </div>

    <!-- Title -->
    <div class="px-5 pt-2 pb-3">
      <h1 class="text-lg font-semibold text-foreground">设置</h1>
    </div>

    <!-- Nav items -->
    <nav class="flex-1 overflow-y-auto min-h-0 px-3">
      <div class="flex flex-col gap-0.5">
        <button
          v-for="item in navItems"
          :key="item.key"
          @click="selectSection(item.key)"
          :class="cn(
            'flex items-center gap-3 w-full px-3 py-2.5 rounded-[10px] text-sm transition-colors',
            navigationStore.activeSettingsSection === item.key
              ? 'bg-muted/60 text-foreground font-medium'
              : 'text-muted-foreground hover:bg-muted/45 hover:text-foreground',
          )"
        >
          <component :is="item.icon" class="h-4 w-4 flex-shrink-0" />
          <span>{{ item.label }}</span>
        </button>
      </div>
    </nav>

    <!-- Logout -->
    <div class="flex-shrink-0 px-3 py-3 border-t border-border/45">
      <button
        @click="authStore.logout()"
        class="flex items-center gap-3 w-full px-3 py-2.5 rounded-[10px] text-sm text-destructive hover:bg-destructive/10 transition-colors"
      >
        <LogOut class="h-4 w-4 flex-shrink-0" />
        <span>退出登录</span>
      </button>
    </div>
  </div>
</template>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/features/settings/SettingsSidebar.vue
git commit -m "feat: add SettingsSidebar component with section navigation"
```

---

### Task 6: Create SettingsDocParsing Section

**Files:**
- Create: `frontend/src/features/settings/SettingsDocParsing.vue`

- [ ] **Step 1: Create SettingsDocParsing.vue**

Create `frontend/src/features/settings/SettingsDocParsing.vue`:

```vue
<script setup>
import { watch } from 'vue'
import { useSettingsStore } from '../../stores/useSettingsStore.js'
import SettingsGroup from '../../components/ui/settings-group.vue'
import SettingsRow from '../../components/ui/settings-row.vue'
import SettingsSectionTitle from '../../components/ui/settings-section-title.vue'
import ToggleButton from '../../components/ui/toggle-button.vue'
import Input from '../../components/ui/input.vue'

const props = defineProps({
  form: { type: Object, required: true },
})

const emit = defineEmits(['update:form'])

function updateField(key, value) {
  emit('update:form', { ...props.form, [key]: value })
}
</script>

<template>
  <div class="space-y-4">
    <SettingsSectionTitle>文档解析增强</SettingsSectionTitle>

    <SettingsGroup>
      <SettingsRow title="自动关键词" description="为文档块自动生成关键词，提升检索召回率">
        <ToggleButton
          :checked="form.auto_keywords"
          label="自动关键词"
          @update:checked="updateField('auto_keywords', $event)"
        />
      </SettingsRow>

      <SettingsRow title="自动问题" description="为文档块自动生成可能的提问，用于问题匹配检索">
        <ToggleButton
          :checked="form.auto_questions"
          label="自动问题"
          @update:checked="updateField('auto_questions', $event)"
        />
      </SettingsRow>

      <SettingsRow title="元数据提取" description="自动提取文档的标题、作者、日期等元数据信息">
        <ToggleButton
          :checked="form.metadata_extraction"
          label="元数据提取"
          @update:checked="updateField('metadata_extraction', $event)"
        />
      </SettingsRow>

      <SettingsRow title="TOC 提取" description="自动提取文档的目录结构，用于层级检索">
        <ToggleButton
          :checked="form.toc_extraction"
          label="TOC 提取"
          @update:checked="updateField('toc_extraction', $event)"
        />
      </SettingsRow>
    </SettingsGroup>

    <SettingsGroup>
      <SettingsRow title="Keywords TopN" description="每个文档块生成的关键词数量上限">
        <Input
          type="number"
          :model-value="form.keywords_topn"
          @update:model-value="updateField('keywords_topn', Number($event))"
          min="1"
          max="20"
          class="w-20 h-8 text-right"
        />
      </SettingsRow>

      <SettingsRow title="Questions TopN" description="每个文档块生成的问题数量上限">
        <Input
          type="number"
          :model-value="form.questions_topn"
          @update:model-value="updateField('questions_topn', Number($event))"
          min="1"
          max="20"
          class="w-20 h-8 text-right"
        />
      </SettingsRow>
    </SettingsGroup>
  </div>
</template>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/features/settings/SettingsDocParsing.vue
git commit -m "feat: add SettingsDocParsing section component"
```

---

### Task 7: Create SettingsRaptor Section

**Files:**
- Create: `frontend/src/features/settings/SettingsRaptor.vue`

- [ ] **Step 1: Create SettingsRaptor.vue**

Create `frontend/src/features/settings/SettingsRaptor.vue`:

```vue
<script setup>
import SettingsGroup from '../../components/ui/settings-group.vue'
import SettingsRow from '../../components/ui/settings-row.vue'
import SettingsSectionTitle from '../../components/ui/settings-section-title.vue'
import ToggleButton from '../../components/ui/toggle-button.vue'
import Input from '../../components/ui/input.vue'
import { cn } from '../../lib/utils.js'

const props = defineProps({
  form: { type: Object, required: true },
})

const emit = defineEmits(['update:form'])

function updateField(key, value) {
  emit('update:form', { ...props.form, [key]: value })
}

const methodOptions = [
  { value: 'gmm', label: 'GMM' },
  { value: 'ahc', label: 'AHC' },
]
</script>

<template>
  <div class="space-y-4">
    <SettingsSectionTitle>RAPTOR 递归抽象处理</SettingsSectionTitle>

    <SettingsGroup>
      <SettingsRow title="启用 RAPTOR" description="使用递归聚类算法对文档块进行层级化组织，提升长文档检索效果">
        <ToggleButton
          :checked="form.raptor_enabled"
          label="启用 RAPTOR"
          @update:checked="updateField('raptor_enabled', $event)"
        />
      </SettingsRow>

      <SettingsRow title="聚类方法" description="选择文档块聚类的算法">
        <div class="inline-flex h-8 items-center rounded-full bg-muted p-0.5">
          <button
            v-for="opt in methodOptions"
            :key="opt.value"
            @click="updateField('raptor_method', opt.value)"
            :class="cn(
              'px-3 py-1 text-xs font-medium rounded-full transition-all',
              form.raptor_method === opt.value
                ? 'bg-background text-foreground shadow-sm'
                : 'text-muted-foreground hover:text-foreground',
            )"
          >
            {{ opt.label }}
          </button>
        </div>
      </SettingsRow>

      <SettingsRow title="最大聚类数" description="每个层级的最大聚类数量">
        <Input
          type="number"
          :model-value="form.raptor_max_clusters"
          @update:model-value="updateField('raptor_max_clusters', Number($event))"
          min="2"
          max="100"
          class="w-20 h-8 text-right"
        />
      </SettingsRow>
    </SettingsGroup>
  </div>
</template>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/features/settings/SettingsRaptor.vue
git commit -m "feat: add SettingsRaptor section component"
```

---

### Task 8: Create SettingsTagging Section

**Files:**
- Create: `frontend/src/features/settings/SettingsTagging.vue`

- [ ] **Step 1: Create SettingsTagging.vue**

Create `frontend/src/features/settings/SettingsTagging.vue`:

```vue
<script setup>
import SettingsGroup from '../../components/ui/settings-group.vue'
import SettingsRow from '../../components/ui/settings-row.vue'
import SettingsSectionTitle from '../../components/ui/settings-section-title.vue'
import ToggleButton from '../../components/ui/toggle-button.vue'
import Input from '../../components/ui/input.vue'

const props = defineProps({
  form: { type: Object, required: true },
})

const emit = defineEmits(['update:form'])

function updateField(key, value) {
  emit('update:form', { ...props.form, [key]: value })
}
</script>

<template>
  <div class="space-y-4">
    <SettingsSectionTitle>内容标签标注</SettingsSectionTitle>

    <SettingsGroup>
      <SettingsRow title="启用标签标注" description="自动为文档块生成语义标签，用于标签路由和过滤检索">
        <ToggleButton
          :checked="form.tagging_enabled"
          label="启用标签标注"
          @update:checked="updateField('tagging_enabled', $event)"
        />
      </SettingsRow>

      <SettingsRow title="TopN" description="每个文档块生成的标签数量上限">
        <Input
          type="number"
          :model-value="form.tagging_topn"
          @update:model-value="updateField('tagging_topn', Number($event))"
          min="1"
          max="20"
          class="w-20 h-8 text-right"
        />
      </SettingsRow>

      <SettingsRow title="Tag KB IDs" description="用于标签检索的知识库 ID 列表，以逗号分隔">
        <Input
          type="text"
          :model-value="form.tagging_tag_kb_ids"
          @update:model-value="updateField('tagging_tag_kb_ids', $event)"
          placeholder="kb1, kb2"
          class="w-48 h-8"
        />
      </SettingsRow>
    </SettingsGroup>
  </div>
</template>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/features/settings/SettingsTagging.vue
git commit -m "feat: add SettingsTagging section component"
```

---

### Task 9: Create SettingsGraphRAG Section

**Files:**
- Create: `frontend/src/features/settings/SettingsGraphRAG.vue`

- [ ] **Step 1: Create SettingsGraphRAG.vue**

Create `frontend/src/features/settings/SettingsGraphRAG.vue`:

```vue
<script setup>
import SettingsGroup from '../../components/ui/settings-group.vue'
import SettingsRow from '../../components/ui/settings-row.vue'
import SettingsSectionTitle from '../../components/ui/settings-section-title.vue'
import ToggleButton from '../../components/ui/toggle-button.vue'
import { cn } from '../../lib/utils.js'

const props = defineProps({
  form: { type: Object, required: true },
})

const emit = defineEmits(['update:form'])

function updateField(key, value) {
  emit('update:form', { ...props.form, [key]: value })
}

const methodOptions = [
  { value: 'general', label: 'General' },
  { value: 'light', label: 'Light' },
  { value: 'ner', label: 'NER' },
]
</script>

<template>
  <div class="space-y-4">
    <SettingsSectionTitle>知识图谱 (GraphRAG)</SettingsSectionTitle>

    <SettingsGroup>
      <SettingsRow title="启用知识图谱" description="基于实体-关系图谱进行检索，适用于复杂关联性问题">
        <ToggleButton
          :checked="form.graphrag_enabled"
          label="启用知识图谱"
          @update:checked="updateField('graphrag_enabled', $event)"
        />
      </SettingsRow>

      <SettingsRow title="图谱构建方法" description="选择知识图谱的构建策略">
        <div class="inline-flex h-8 items-center rounded-full bg-muted p-0.5">
          <button
            v-for="opt in methodOptions"
            :key="opt.value"
            @click="updateField('graphrag_method', opt.value)"
            :class="cn(
              'px-3 py-1 text-xs font-medium rounded-full transition-all',
              form.graphrag_method === opt.value
                ? 'bg-background text-foreground shadow-sm'
                : 'text-muted-foreground hover:text-foreground',
            )"
          >
            {{ opt.label }}
          </button>
        </div>
      </SettingsRow>
    </SettingsGroup>

    <SettingsGroup>
      <SettingsRow title="实体消歧" description="自动合并指代同一实体的不同表述（如 'OpenAI' 和 'open ai'）">
        <ToggleButton
          :checked="form.graphrag_entity_resolution"
          label="实体消歧"
          @update:checked="updateField('graphrag_entity_resolution', $event)"
        />
      </SettingsRow>

      <SettingsRow title="社区检测" description="将关联紧密的实体聚类为社区，生成摘要用于全局检索">
        <ToggleButton
          :checked="form.graphrag_community_detection"
          label="社区检测"
          @update:checked="updateField('graphrag_community_detection', $event)"
        />
      </SettingsRow>

      <SettingsRow title="PageRank" description="使用 PageRank 算法对实体进行重要性排序，影响检索权重">
        <ToggleButton
          :checked="form.graphrag_pagerank"
          label="PageRank"
          @update:checked="updateField('graphrag_pagerank', $event)"
        />
      </SettingsRow>
    </SettingsGroup>
  </div>
</template>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/features/settings/SettingsGraphRAG.vue
git commit -m "feat: add SettingsGraphRAG section component"
```

---

### Task 10: Create SettingsOverview Section

**Files:**
- Create: `frontend/src/features/settings/SettingsOverview.vue`

- [ ] **Step 1: Create SettingsOverview.vue**

Create `frontend/src/features/settings/SettingsOverview.vue`:

```vue
<script setup>
import { useNavigationStore } from '../../stores/useNavigationStore.js'
import { FileText, Layers, Tag, Network, ChevronRight } from 'lucide-vue-next'
import SettingsGroup from '../../components/ui/settings-group.vue'
import SettingsSectionTitle from '../../components/ui/settings-section-title.vue'

const props = defineProps({
  form: { type: Object, default: () => ({}) },
})

const navigationStore = useNavigationStore()

const sections = [
  {
    key: 'doc-parsing',
    label: '文档解析增强',
    icon: FileText,
    getStatus: (f) => {
      const enabled = [f.auto_keywords, f.auto_questions, f.metadata_extraction, f.toc_extraction].filter(Boolean).length
      return `${enabled}/4 项已启用`
    },
  },
  {
    key: 'raptor',
    label: 'RAPTOR',
    icon: Layers,
    getStatus: (f) => f.raptor_enabled ? `已启用 · ${f.raptor_method?.toUpperCase()}` : '未启用',
  },
  {
    key: 'tagging',
    label: '内容标签',
    icon: Tag,
    getStatus: (f) => f.tagging_enabled ? `已启用 · TopN ${f.tagging_topn}` : '未启用',
  },
  {
    key: 'graphrag',
    label: '知识图谱',
    icon: Network,
    getStatus: (f) => f.graphrag_enabled ? `已启用 · ${f.graphrag_method}` : '未启用',
  },
]

function goToSection(key) {
  navigationStore.setActiveSettingsSection(key)
}
</script>

<template>
  <div class="space-y-4">
    <SettingsSectionTitle>RAG 配置概览</SettingsSectionTitle>

    <SettingsGroup>
      <button
        v-for="section in sections"
        :key="section.key"
        @click="goToSection(section.key)"
        class="flex items-center gap-4 w-full px-4 py-3.5 sm:px-5 min-h-[62px] text-left hover:bg-muted/45 transition-colors"
      >
        <component :is="section.icon" class="h-5 w-5 text-muted-foreground flex-shrink-0" />
        <div class="flex-1 min-w-0">
          <div class="text-[14px] font-medium text-foreground">{{ section.label }}</div>
          <div class="text-[12px] text-muted-foreground mt-0.5">
            {{ section.getStatus(form) }}
          </div>
        </div>
        <ChevronRight class="h-4 w-4 text-muted-foreground flex-shrink-0" />
      </button>
    </SettingsGroup>
  </div>
</template>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/features/settings/SettingsOverview.vue
git commit -m "feat: add SettingsOverview section with config summary cards"
```

---

### Task 11: Create Main SettingsView Container

**Files:**
- Create: `frontend/src/features/settings/SettingsView.vue`

- [ ] **Step 1: Create SettingsView.vue**

Create `frontend/src/features/settings/SettingsView.vue`:

```vue
<script setup>
import { ref, watch, onMounted } from 'vue'
import { useSettingsStore } from '../../stores/useSettingsStore.js'
import { useNavigationStore } from '../../stores/useNavigationStore.js'
import { useToastStore } from '../../stores/useToastStore.js'
import { Loader2, Save } from 'lucide-vue-next'
import Button from '../../components/ui/button.vue'
import ScrollArea from '../../components/ui/scroll-area.vue'
import SettingsSidebar from './SettingsSidebar.vue'
import SettingsOverview from './SettingsOverview.vue'
import SettingsDocParsing from './SettingsDocParsing.vue'
import SettingsRaptor from './SettingsRaptor.vue'
import SettingsTagging from './SettingsTagging.vue'
import SettingsGraphRAG from './SettingsGraphRAG.vue'

const settingsStore = useSettingsStore()
const navigationStore = useNavigationStore()
const toast = useToastStore()

const form = ref({
  auto_keywords: false,
  auto_questions: false,
  metadata_extraction: false,
  toc_extraction: false,
  keywords_topn: 5,
  questions_topn: 5,
  raptor_enabled: false,
  raptor_method: 'gmm',
  raptor_max_clusters: 10,
  tagging_enabled: false,
  tagging_topn: 5,
  tagging_tag_kb_ids: '',
  graphrag_enabled: false,
  graphrag_method: 'general',
  graphrag_entity_resolution: false,
  graphrag_community_detection: false,
  graphrag_pagerank: false,
})

watch(() => settingsStore.settings, (val) => {
  if (val) {
    form.value = {
      auto_keywords: val.auto_keywords ?? false,
      auto_questions: val.auto_questions ?? false,
      metadata_extraction: val.metadata_extraction ?? false,
      toc_extraction: val.toc_extraction ?? false,
      keywords_topn: val.keywords_topn ?? 5,
      questions_topn: val.questions_topn ?? 5,
      raptor_enabled: val.raptor_enabled ?? false,
      raptor_method: val.raptor_method ?? 'gmm',
      raptor_max_clusters: val.raptor_max_clusters ?? 10,
      tagging_enabled: val.tagging_enabled ?? false,
      tagging_topn: val.tagging_topn ?? 5,
      tagging_tag_kb_ids: Array.isArray(val.tagging_tag_kb_ids)
        ? val.tagging_tag_kb_ids.join(', ')
        : (val.tagging_tag_kb_ids ?? ''),
      graphrag_enabled: val.graphrag_enabled ?? false,
      graphrag_method: val.graphrag_method ?? 'general',
      graphrag_entity_resolution: val.graphrag_entity_resolution ?? false,
      graphrag_community_detection: val.graphrag_community_detection ?? false,
      graphrag_pagerank: val.graphrag_pagerank ?? false,
    }
  }
}, { immediate: true })

async function handleSave() {
  try {
    const payload = {
      ...form.value,
      tagging_tag_kb_ids: form.value.tagging_tag_kb_ids
        ? form.value.tagging_tag_kb_ids.split(',').map(s => s.trim()).filter(Boolean)
        : [],
    }
    await settingsStore.saveSettings(payload)
    toast.success('配置已保存')
  } catch (err) {
    toast.error('保存失败: ' + (err.response?.data?.detail || err.message))
  }
}

onMounted(() => {
  settingsStore.fetchSettings()
})
</script>

<template>
  <div class="flex h-full w-full">
    <!-- Settings sidebar -->
    <SettingsSidebar class="hidden lg:flex" />

    <!-- Content area -->
    <main class="flex-1 min-w-0 overflow-hidden">
      <ScrollArea class="h-full">
        <div class="mx-auto max-w-[920px] px-6 py-6 sm:px-8 sm:py-8">
          <!-- Loading state -->
          <div v-if="settingsStore.loading" class="flex items-center justify-center gap-2 py-16 text-muted-foreground">
            <Loader2 class="h-5 w-5 animate-spin" />
            <span class="text-sm">加载配置中...</span>
          </div>

          <template v-else>
            <!-- Section content -->
            <SettingsOverview
              v-if="navigationStore.activeSettingsSection === 'overview'"
              :form="form"
            />
            <SettingsDocParsing
              v-else-if="navigationStore.activeSettingsSection === 'doc-parsing'"
              :form="form"
              @update:form="form = $event"
            />
            <SettingsRaptor
              v-else-if="navigationStore.activeSettingsSection === 'raptor'"
              :form="form"
              @update:form="form = $event"
            />
            <SettingsTagging
              v-else-if="navigationStore.activeSettingsSection === 'tagging'"
              :form="form"
              @update:form="form = $event"
            />
            <SettingsGraphRAG
              v-else-if="navigationStore.activeSettingsSection === 'graphrag'"
              :form="form"
              @update:form="form = $event"
            />

            <!-- Save button (not on overview) -->
            <div v-if="navigationStore.activeSettingsSection !== 'overview'" class="mt-6 flex flex-col items-center gap-2">
              <Button
                :disabled="settingsStore.saving"
                @click="handleSave"
                class="w-full max-w-xs"
              >
                <Loader2 v-if="settingsStore.saving" class="h-4 w-4 animate-spin mr-2" />
                <Save v-else class="h-4 w-4 mr-2" />
                保存配置
              </Button>
              <p class="text-[11px] text-muted-foreground">部分配置修改后需要重启服务才能生效</p>
            </div>
          </template>
        </div>
      </ScrollArea>
    </main>
  </div>
</template>
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/features/settings/SettingsView.vue
git commit -m "feat: add SettingsView main container with sidebar + content layout"
```

---

### Task 12: Integrate SettingsView into App.vue

**Files:**
- Modify: `frontend/src/App.vue`

- [ ] **Step 1: Read the current App.vue**

Read `frontend/src/App.vue` to confirm current content matches what we expect.

- [ ] **Step 2: Add SettingsView import**

In the `<script setup>` section, add the import after the existing imports:

```js
import SettingsView from './features/settings/SettingsView.vue'
```

- [ ] **Step 3: Conditionally hide L2Sidebar and ChatShell when settings is active**

Replace the template section. The key changes are:

1. Wrap `L2Sidebar` with `v-if="navigationStore.activeNav !== 'settings'"`
2. In the `<main>` section, conditionally show `ChatShell` or `SettingsView`:

Replace the `<div class="flex h-full w-full">` block with:

```vue
    <div class="flex h-full w-full">
      <!-- L1: Icon sidebar (always visible on desktop) -->
      <L1Sidebar class="hidden lg:flex" @logout="handleLogout" />

      <!-- L2: Content panel (hidden when settings is active) -->
      <L2Sidebar
        v-if="navigationStore.activeNav !== 'settings'"
        class="hidden lg:block"
        :width="navigationStore.l2Width"
        :expanded="navigationStore.l2Expanded"
        @update:width="navigationStore.setL2Width($event)"
        @open-docs="showDocs = true"
        @open-eval="showEval = true"
        @open-models="showModels = true"
        @open-tag-kb="showTagKb = true"
        @open-settings="showRagSettings = true"
        @open-graph="showGraph = true"
        @open-kb="showKb = true"
        @open-team="showTeam = true"
        @logout="handleLogout"
      />

      <!-- Main content -->
      <main class="flex-1 flex flex-col min-w-0 overflow-hidden bg-background">
        <SettingsView v-if="navigationStore.activeNav === 'settings'" />
        <ChatShell
          v-else
          @open-docs="showDocs = true"
          @open-eval="showEval = true"
        />
      </main>
    </div>
```

- [ ] **Step 4: Remove the RagSettingsDrawer Sheet**

Remove these lines from the template:

```vue
    <!-- RAG settings drawer -->
    <Sheet v-model="showRagSettings" side="right" class="w-[400px] sm:w-[540px]">
      <RagSettingsDrawer />
    </Sheet>
```

Remove the `showRagSettings` ref declaration:

```js
const showRagSettings = ref(false)
```

Remove the `RagSettingsDrawer` import:

```js
import RagSettingsDrawer from './features/settings/RagSettingsDrawer.vue'
```

Also remove all `@open-settings="showRagSettings = true"` event handlers from `L2Sidebar` and the mobile `Sheet` wrapper's `L2Sidebar` (the settings drawer is no longer opened this way — settings is now accessed via L1 sidebar nav).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/App.vue
git commit -m "feat: integrate SettingsView, hide L2 sidebar when settings active, remove RagSettingsDrawer"
```

---

### Task 13: Update SettingsPanel for New Behavior

**Files:**
- Modify: `frontend/src/features/navigation/panels/SettingsPanel.vue`

- [ ] **Step 1: Read the current SettingsPanel.vue**

Read `frontend/src/features/navigation/panels/SettingsPanel.vue` to confirm current content.

- [ ] **Step 2: Remove the "RAG 设置" entry and its emit**

The `SettingsPanel` is still used by the L2 sidebar for other menu items (文档管理, 知识库管理, etc.), but the "RAG 设置" entry is no longer needed since settings is now a full-page view. Remove the "RAG 设置" entry from `settingsEntries`:

```js
const settingsEntries = [
  { label: '文档管理', icon: FileText, handler: () => emit('open-docs') },
  { label: '知识库管理', icon: FolderOpen, handler: () => emit('open-kb') },
  { label: '模型管理', icon: Cpu, handler: () => emit('open-models') },
  { label: '标签知识库', icon: Tags, handler: () => emit('open-tag-kb') },
  // RAG 设置 removed — now accessed via L1 sidebar as full-page SettingsView
  { label: '知识图谱', icon: Network, handler: () => emit('open-graph') },
  { label: '团队管理', icon: Users, handler: () => emit('open-team') },
  { label: '评测看板', icon: BarChart3, handler: () => emit('open-eval') },
]
```

Remove `'open-settings'` from the `defineEmits` array.

Remove the `Settings` import from `lucide-vue-next` since it's no longer used.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/features/navigation/panels/SettingsPanel.vue
git commit -m "refactor: remove RAG settings entry from SettingsPanel (now full-page)"
```

---

### Task 14: Remove RagSettingsDrawer

**Files:**
- Delete: `frontend/src/features/settings/RagSettingsDrawer.vue`

- [ ] **Step 1: Verify no remaining references**

Run: `grep -r "RagSettingsDrawer" frontend/src/`

Expected: No results (all references were removed in Task 12).

- [ ] **Step 2: Delete the file**

```bash
rm frontend/src/features/settings/RagSettingsDrawer.vue
```

- [ ] **Step 3: Commit**

```bash
git add -A frontend/src/features/settings/RagSettingsDrawer.vue
git commit -m "chore: remove RagSettingsDrawer (replaced by SettingsView)"
```

---

### Task 15: Final Verification

- [ ] **Step 1: Check all imports resolve**

Run: `cd frontend && npx vue-tsc --noEmit --skipLibCheck 2>&1 | head -30`

Expected: No import errors.

- [ ] **Step 2: Start dev server and verify**

Run: `cd frontend && npm run dev`

Open the browser, click the settings icon in L1 sidebar. Expected:
- L2 sidebar disappears
- Full-page settings view appears with left sidebar navigation
- Clicking nav items switches between sections
- Toggles, segmented controls, and inputs work
- Save button sends correct field names to backend
- Overview page shows config summary with clickable rows

- [ ] **Step 3: Final commit with all remaining changes**

```bash
git add -A
git commit -m "feat: complete settings page redesign — full-page sidebar + content layout"
```
