<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import { getGraphData, searchGraph, getGraphStats } from '../../api/graph.js'
import { Loader2, Search, RotateCcw } from 'lucide-vue-next'

const nodes = ref([])
const edges = ref([])
const stats = ref(null)
const searchQuery = ref('')
const selectedNode = ref(null)
const loading = ref(false)
const error = ref(null)
const dragNode = ref(null)

// Node type colors
const TYPE_COLORS = {
  organization: '#3b82f6',
  person: '#ef4444',
  geo: '#22c55e',
  event: '#f59e0b',
  category: '#8b5cf6',
  unknown: '#6b7280',
}

function initNodes(rawNodes) {
  return rawNodes.map((n, i) => ({
    ...n,
    x: 400 + Math.cos(i * 2.399) * 200,
    y: 300 + Math.sin(i * 2.399) * 200,
    vx: 0,
    vy: 0,
    radius: Math.max(8, Math.min(20, Math.sqrt((n.pagerank || 0.001) * 10000))),
    color: TYPE_COLORS[n.type] || TYPE_COLORS.unknown,
  }))
}

async function loadGraph() {
  loading.value = true
  error.value = null
  try {
    const data = await getGraphData(200)
    nodes.value = initNodes(data.nodes || [])
    edges.value = data.edges || []
    stats.value = await getGraphStats()
  } catch (err) {
    if (err.response?.status === 503) {
      error.value = err.response.data?.detail || '知识图谱未配置，请先启动 Neo4j 并设置 USE_KNOWLEDGE_GRAPH=true'
    } else {
      console.error('Failed to load graph:', err)
      error.value = '图谱加载失败'
    }
  } finally {
    loading.value = false
  }
}

async function handleSearch() {
  if (!searchQuery.value.trim()) {
    await loadGraph()
    return
  }
  loading.value = true
  try {
    const data = await searchGraph(searchQuery.value)
    nodes.value = initNodes(data.nodes || [])
    const nodeIds = new Set(nodes.value.map(n => n.id))
    edges.value = (data.edges || []).filter(e => nodeIds.has(e.source) && nodeIds.has(e.target))
  } catch (err) {
    console.error('Graph search failed:', err)
  } finally {
    loading.value = false
  }
}

function resetSearch() {
  searchQuery.value = ''
  loadGraph()
}

// Simple force simulation
let simulationTimer = null

function startSimulation() {
  if (simulationTimer) clearInterval(simulationTimer)
  const centerForce = 0.01
  const repulsion = 500
  const linkDistance = 100

  simulationTimer = setInterval(() => {
    const ns = nodes.value
    if (!ns.length) return

    // Center gravity
    for (const n of ns) {
      n.vx += (400 - n.x) * centerForce
      n.vy += (300 - n.y) * centerForce
    }

    // Repulsion between nodes
    for (let i = 0; i < ns.length; i++) {
      for (let j = i + 1; j < ns.length; j++) {
        const dx = ns[j].x - ns[i].x
        const dy = ns[j].y - ns[i].y
        const dist = Math.max(Math.sqrt(dx * dx + dy * dy), 1)
        const force = repulsion / (dist * dist)
        const fx = (dx / dist) * force
        const fy = (dy / dist) * force
        ns[i].vx -= fx
        ns[i].vy -= fy
        ns[j].vx += fx
        ns[j].vy += fy
      }
    }

    // Link attraction
    const nodeMap = new Map(ns.map(n => [n.id, n]))
    for (const e of edges.value) {
      const src = nodeMap.get(e.source)
      const tgt = nodeMap.get(e.target)
      if (!src || !tgt) continue
      const dx = tgt.x - src.x
      const dy = tgt.y - src.y
      const dist = Math.max(Math.sqrt(dx * dx + dy * dy), 1)
      const force = (dist - linkDistance) * 0.005
      src.vx += (dx / dist) * force
      src.vy += (dy / dist) * force
      tgt.vx -= (dx / dist) * force
      tgt.vy -= (dy / dist) * force
    }

    // Apply velocity with damping
    for (const n of ns) {
      n.vx *= 0.85
      n.vy *= 0.85
      n.x += n.vx * 0.3
      n.y += n.vy * 0.3
      n.x = Math.max(30, Math.min(770, n.x))
      n.y = Math.max(30, Math.min(570, n.y))
    }
  }, 50)
}

function stopSimulation() {
  if (simulationTimer) {
    clearInterval(simulationTimer)
    simulationTimer = null
  }
}

// Drag support
function onNodeMouseDown(node, event) {
  dragNode.value = node
  event.preventDefault()
}

function onMouseMove(event) {
  if (!dragNode.value) return
  const svg = event.currentTarget
  const rect = svg.getBoundingClientRect()
  dragNode.value.x = event.clientX - rect.left
  dragNode.value.y = event.clientY - rect.top
  dragNode.value.vx = 0
  dragNode.value.vy = 0
}

function onMouseUp() {
  dragNode.value = null
}

// Build a node lookup map for edges
function nodeById(id) {
  return nodes.value.find(n => n.id === id)
}

onMounted(() => {
  loadGraph().then(() => startSimulation())
})

onUnmounted(() => {
  stopSimulation()
})
</script>

<template>
  <div class="flex flex-col h-full">
    <!-- Header -->
    <div class="flex items-center justify-between p-4 border-b border-border">
      <div class="flex items-center gap-2">
        <span class="text-lg">&#x1F578;&#xFE0F;</span>
        <h2 class="text-lg font-semibold text-foreground">知识图谱</h2>
        <span v-if="stats" class="text-xs text-muted-foreground">
          {{ stats.entity_count }} 实体 · {{ stats.relation_count }} 关系 · {{ stats.community_count }} 社区
        </span>
      </div>
    </div>

    <!-- Search -->
    <div class="flex gap-2 px-4 py-2 border-b border-border">
      <input
        v-model="searchQuery"
        @keyup.enter="handleSearch"
        placeholder="搜索实体..."
        class="flex-1 px-3 py-1.5 border border-input rounded-md text-sm bg-background shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
      />
      <button
        class="px-3 py-1.5 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:bg-primary/90 transition-colors flex items-center gap-1.5"
        @click="handleSearch"
      >
        <Search class="h-3.5 w-3.5" />
        搜索
      </button>
      <button
        class="px-3 py-1.5 border border-input rounded-md text-sm text-foreground hover:bg-accent transition-colors flex items-center gap-1.5"
        @click="resetSearch"
      >
        <RotateCcw class="h-3.5 w-3.5" />
        重置
      </button>
    </div>

    <!-- Error state -->
    <div v-if="error" class="flex-1 flex items-center justify-center p-8">
      <div class="text-center space-y-3">
        <div class="text-4xl opacity-50">&#x1F578;&#xFE0F;</div>
        <p class="text-sm text-muted-foreground max-w-sm">{{ error }}</p>
        <button
          class="px-4 py-1.5 bg-primary text-primary-foreground rounded-md text-sm font-medium hover:bg-primary/90 transition-colors"
          @click="loadGraph"
        >
          重试
        </button>
      </div>
    </div>

    <!-- Graph -->
    <div v-else class="flex-1 relative overflow-hidden">
      <svg
        class="w-full h-full"
        @mousemove="onMouseMove"
        @mouseup="onMouseUp"
      >
        <!-- Edges -->
        <line
          v-for="edge in edges"
          :key="`e-${edge.source}-${edge.target}`"
          :x1="nodeById(edge.source)?.x || 0"
          :y1="nodeById(edge.source)?.y || 0"
          :x2="nodeById(edge.target)?.x || 0"
          :y2="nodeById(edge.target)?.y || 0"
          stroke="#d1d5db"
          :stroke-width="Math.max(1, (edge.weight || 1) / 2)"
          opacity="0.6"
        />
        <!-- Nodes -->
        <g
          v-for="node in nodes"
          :key="node.id"
          :transform="`translate(${node.x}, ${node.y})`"
          @mousedown="onNodeMouseDown(node, $event)"
          @click="selectedNode = node"
          class="cursor-pointer"
        >
          <circle
            :r="node.radius"
            :fill="node.color"
            opacity="0.85"
            :stroke="selectedNode?.id === node.id ? '#000' : 'none'"
            stroke-width="2"
          />
          <text
            dy="0.35em"
            text-anchor="middle"
            :font-size="Math.max(8, node.radius * 0.8)"
            fill="white"
            class="pointer-events-none select-none"
          >
            {{ (node.name || '').slice(0, 4) }}
          </text>
        </g>
      </svg>

      <!-- Loading overlay -->
      <div v-if="loading" class="absolute inset-0 flex items-center justify-center bg-white/50 dark:bg-black/50">
        <Loader2 class="h-6 w-6 animate-spin text-primary" />
      </div>
    </div>

    <!-- Legend -->
    <div class="flex gap-3 px-4 py-2 border-t border-border text-xs text-muted-foreground">
      <span v-for="(color, type) in TYPE_COLORS" :key="type" class="flex items-center gap-1">
        <span class="w-3 h-3 rounded-full inline-block" :style="{ backgroundColor: color }"></span>
        {{ type }}
      </span>
    </div>

    <!-- Selected node detail -->
    <div v-if="selectedNode" class="px-4 py-3 border-t border-border bg-muted text-sm">
      <div class="flex items-center gap-2 mb-1">
        <span class="w-3 h-3 rounded-full inline-block" :style="{ backgroundColor: selectedNode.color }"></span>
        <span class="font-medium text-foreground">{{ selectedNode.name }}</span>
        <span class="text-xs text-muted-foreground">{{ selectedNode.type }}</span>
      </div>
      <p class="text-muted-foreground text-xs">{{ selectedNode.description }}</p>
      <p class="text-xs text-muted-foreground mt-1">PageRank: {{ selectedNode.pagerank?.toFixed(4) }}</p>
    </div>
  </div>
</template>
