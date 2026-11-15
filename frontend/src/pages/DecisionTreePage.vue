<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, shallowRef } from 'vue'
import { onBeforeRouteLeave, onBeforeRouteUpdate, useRoute } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import type { InputInstance } from 'element-plus'
import { getDecision, saveDecisionTree } from '../api'
import DecisionTreeCanvas from '../components/DecisionTreeCanvas.vue'
import {
  branch, containsNode, fillMissingPositions, indexTree, layoutBranch,
  MIN_NODE_HEIGHT, NODE_TYPES, withPositions,
} from '../decisionTree'
import type { DecisionNode, DecisionRecord, Point } from '../decisionTree'

const route = useRoute()
const decision = shallowRef<DecisionRecord | null>(null)
const draft = shallowRef<DecisionNode[]>([])
const selectedId = ref('')
const dirty = ref(false)
const loading = ref(true)
const saving = ref(false)
const error = ref('')
const textInput = ref<InputInstance>()
const tree = computed(() => indexTree(draft.value))
const selected = computed(() => tree.value.byId.get(selectedId.value))
const blank = computed(() => draft.value.some(node => !node.text.trim()))
const siblings = computed(() => selected.value?.parentId
  ? tree.value.children.get(selected.value.parentId) ?? []
  : [])
const parentOptions = computed(() => {
  const item = selected.value
  if (!item || !decision.value || item.parentId === null) return []
  const excluded = new Set(branch(tree.value, item.id).map(node => node.id))
  return branch(tree.value, decision.value.rootId).filter(node => !excluded.has(node.id))
})

function measure(nodes: DecisionNode[]) {
  const probe = document.createElement('div')
  probe.className = 'decision-node-label decision-node-measure'
  document.body.append(probe)
  const heights = new Map<string, number>()
  try {
    for (const node of nodes) {
      probe.textContent = node.text || '未命名节点'
      heights.set(node.id, Math.max(MIN_NODE_HEIGHT, probe.offsetHeight + 26))
    }
  } finally {
    probe.remove()
  }
  return heights
}

function unpack(record: DecisionRecord): DecisionNode[] {
  return record.nodes.map(({ decisionId: _id, createdAt: _created, updatedAt: _updated, ...node }) => node)
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const record = await getDecision(Number(route.params.id))
    const nodes = unpack(record)
    draft.value = withPositions(nodes, fillMissingPositions(indexTree(nodes), record.rootId, measure(nodes)))
    decision.value = record
    selectedId.value = record.rootId
    dirty.value = false
  } catch (reason) {
    error.value = (reason as Error).message
  } finally {
    loading.value = false
  }
}

async function save() {
  if (!decision.value || blank.value || saving.value || !dirty.value) return
  saving.value = true
  error.value = ''
  try {
    const record = await saveDecisionTree(decision.value.id, decision.value.version, draft.value)
    draft.value = unpack(record)
    decision.value = record
    dirty.value = false
  } catch (reason) {
    error.value = (reason as Error).message
  } finally {
    saving.value = false
  }
}

function leave() {
  if (saving.value) return false
  return !dirty.value || window.confirm('尚有未保存的更改。确定放弃这些更改？')
}

function reload() {
  if (leave()) void load()
}

function beforeUnload(event: BeforeUnloadEvent) {
  if (dirty.value || saving.value) {
    event.preventDefault()
    event.returnValue = ''
  }
}

onBeforeRouteLeave(leave)
onBeforeRouteUpdate(leave)
onMounted(() => {
  void load()
  window.addEventListener('beforeunload', beforeUnload)
})
onUnmounted(() => window.removeEventListener('beforeunload', beforeUnload))

function change(nodes: DecisionNode[]) {
  draft.value = nodes
  dirty.value = true
}

function patchNode(id: string, changes: Partial<DecisionNode>) {
  change(draft.value.map(node => node.id === id ? { ...node, ...changes } : node))
}

async function editText(id: string, select = false) {
  selectedId.value = id
  await nextTick()
  if (select) textInput.value?.select()
  else textInput.value?.focus()
}

function toggle(id: string) {
  const node = tree.value.byId.get(id)
  if (!node) return
  if (!node.collapsed && containsNode(tree.value, id, selectedId.value)) selectedId.value = id
  patchNode(id, { collapsed: !node.collapsed })
}

function addNode(parentId: string, order?: number) {
  if (!decision.value) return
  const id = Array.from(crypto.getRandomValues(new Uint8Array(16)),
    byte => byte.toString(16).padStart(2, '0')).join('')
  const index = order ?? tree.value.children.get(parentId)?.length ?? 0
  const nodes = [
    ...draft.value.map(node => {
      if (node.id === parentId) return { ...node, collapsed: false }
      if (node.parentId === parentId && node.order >= index) return { ...node, order: node.order + 1 }
      return node
    }),
    {
      id, parentId, order: index, text: '新节点', description: null, type: null,
      collapsed: false, positionX: null, positionY: null,
    },
  ]
  change(withPositions(nodes, fillMissingPositions(indexTree(nodes), decision.value.rootId, measure(nodes))))
  void editText(id, true)
}

function moveNode(id: string, parentId: string, order: number) {
  const node = tree.value.byId.get(id)
  const parent = tree.value.byId.get(parentId)
  if (!node?.parentId || !parent || containsNode(tree.value, id, parentId)) return
  if (node.parentId === parentId && node.order === order) return

  const destination = (tree.value.children.get(parentId) ?? []).filter(sibling => sibling.id !== id)
  destination.splice(order, 0, node)
  const orders = new Map(destination.map((sibling, index) => [sibling.id, index]))
  const nodes = draft.value.map(current => {
    const newOrder = orders.get(current.id)
    if (newOrder !== undefined) return { ...current, parentId, order: newOrder }
    if (current.id === parentId) return { ...current, collapsed: false }
    if (current.parentId === node.parentId && current.order > node.order) {
      return { ...current, order: current.order - 1 }
    }
    return current
  })
  const updated = indexTree(nodes)
  const positions = layoutBranch(updated, parentId, measure(branch(updated, parentId)), {
    x: parent.positionX ?? 0, y: parent.positionY ?? 0,
  })
  change(withPositions(nodes, positions))
  selectedId.value = id
}

function changeParent(id: string, parentId: string) {
  moveNode(id, parentId, tree.value.children.get(parentId)?.length ?? 0)
}

async function deleteBranch(node: DecisionNode) {
  if (node.parentId === null) return
  const removed = new Set(branch(tree.value, node.id).map(child => child.id))
  try {
    await ElMessageBox.confirm(
      `删除所选节点？共将删除 ${removed.size} 个节点。`, '删除分支',
      { type: 'warning', confirmButtonText: '删除分支', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  selectedId.value = node.parentId
  change(draft.value.filter(item => !removed.has(item.id)).map(item =>
    item.parentId === node.parentId && item.order > node.order
      ? { ...item, order: item.order - 1 }
      : item,
  ))
}

function arrange() {
  if (!decision.value) return
  change(withPositions(draft.value, layoutBranch(tree.value, decision.value.rootId, measure(draft.value))))
}

function position(positions: Map<string, Point>) {
  change(withPositions(draft.value, positions))
}
</script>

<template>
  <main class="decision-editor">
    <RouterLink :to="{ name: 'decision-trees' }" class="back-link">← 决策列表</RouterLink>
    <el-skeleton v-if="loading" :rows="6" animated />
    <template v-else>
      <header v-if="decision" class="editor-header">
        <div class="editor-title">
          <h1>{{ decision.title }}</h1>
          <p v-if="decision.description">{{ decision.description }}</p>
          <span class="trees-status" :class="decision.status.toLowerCase()">{{ decision.status }}</span>
        </div>
        <div class="editor-actions">
          <span aria-live="polite">{{ dirty ? '有未保存的更改' : '已保存' }} · v{{ decision.version }}</span>
          <el-button :disabled="saving" @click="reload">重新加载</el-button>
          <el-button type="primary" :loading="saving" :disabled="!dirty || blank" @click="save">保存决策树</el-button>
        </div>
      </header>
      <el-alert v-if="error" :title="error" type="error" show-icon :closable="false" />
      <el-button v-if="!decision" @click="load">重试</el-button>
      <div v-if="decision" class="editor-workspace">
        <DecisionTreeCanvas
          :nodes="draft" :root-id="decision.rootId" :selected-id="selectedId" :disabled="saving"
          @select="selectedId = $event" @edit="editText" @toggle="toggle" @arrange="arrange"
          @move="moveNode" @position="position"
        />
        <aside v-if="selected" class="node-inspector" aria-labelledby="node-inspector-title">
          <h2 id="node-inspector-title">编辑节点</h2>
          <el-form label-position="top" :disabled="saving" @submit.prevent>
            <el-form-item label="节点文字" :error="!selected.text.trim() ? '请输入节点文字' : ''">
              <el-input
                ref="textInput" type="textarea" :rows="3" maxlength="4000" :model-value="selected.text"
                @update:model-value="patchNode(selected.id, { text: $event })"
              />
            </el-form-item>
            <el-form-item label="备注">
              <el-input
                type="textarea" :rows="2" maxlength="10000" :model-value="selected.description ?? ''"
                @update:model-value="patchNode(selected.id, { description: $event || null })"
              />
            </el-form-item>
            <el-form-item label="类型">
              <el-select
                clearable placeholder="可选" :model-value="selected.type ?? ''"
                @change="patchNode(selected.id, { type: $event || null })"
              >
                <el-option v-for="name in NODE_TYPES" :key="name" :value="name" />
              </el-select>
            </el-form-item>
            <div class="inspector-group">
              <el-button @click="addNode(selected.id)">添加子节点</el-button>
              <el-button v-if="selected.parentId" @click="addNode(selected.parentId, selected.order + 1)">添加同级</el-button>
            </div>
            <template v-if="selected.parentId">
              <el-form-item label="父节点" class="parent-select">
                <el-select
                  filterable :model-value="selected.parentId"
                  @change="changeParent(selected.id, $event)"
                >
                  <el-option v-for="node in parentOptions" :key="node.id" :value="node.id" :label="node.text.slice(0, 100)" />
                </el-select>
              </el-form-item>
              <div class="inspector-group">
                <el-button
                  :disabled="selected.order === 0"
                  @click="moveNode(selected.id, selected.parentId, selected.order - 1)"
                >上移</el-button>
                <el-button
                  :disabled="selected.order >= siblings.length - 1"
                  @click="moveNode(selected.id, selected.parentId, selected.order + 1)"
                >下移</el-button>
                <el-button type="danger" text @click="deleteBranch(selected)">删除分支</el-button>
              </div>
            </template>
          </el-form>
        </aside>
      </div>
    </template>
  </main>
</template>

<style scoped>
.decision-editor { width: min(1520px, calc(100% - 48px)); margin: 0 auto; padding: 24px 0 56px; }
.editor-header { display: flex; justify-content: space-between; align-items: end; gap: 16px; margin: 14px 0 16px; }
.editor-title { min-width: 0; overflow-wrap: anywhere; }
.editor-title h1 { margin: 0 0 7px; font: 500 clamp(1.65rem, 4vw, 2.75rem)/1.16 Georgia, 'Songti SC', serif; }
.editor-title p { white-space: pre-wrap; margin: 8px 0; color: #50675b; }
.editor-actions { display: flex; flex-wrap: wrap; align-items: center; justify-content: flex-end; gap: 8px; }
.editor-actions span { color: #53675c; font-size: .78rem; white-space: nowrap; }
.editor-actions .el-button + .el-button, .inspector-group .el-button + .el-button { margin-left: 0; }
.editor-workspace { display: grid; grid-template-columns: minmax(0, 1fr) minmax(230px, 280px); gap: 12px; margin-top: 12px; }
.node-inspector { min-width: 0; align-self: start; padding: 16px; border: 1px solid var(--line); border-radius: 12px; background: var(--paper); }
.node-inspector h2 { font-size: 1rem; margin: 0 0 16px; }
.inspector-group { display: flex; gap: 6px; flex-wrap: wrap; }
.parent-select { border-top: 1px solid var(--line); padding-top: 14px; margin-top: 14px; }
@media (max-width: 760px) {
  .decision-editor { width: calc(100% - 24px); }
  .editor-header { align-items: start; flex-direction: column; }
  .editor-actions { justify-content: start; }
  .editor-workspace { grid-template-columns: minmax(0, 1fr); }
}
</style>
