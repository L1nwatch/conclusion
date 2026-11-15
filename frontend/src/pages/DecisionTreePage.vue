<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, shallowRef } from 'vue'
import { onBeforeRouteLeave, onBeforeRouteUpdate, useRoute } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import { ApiError, getDecision, saveDecisionTree } from '../api'
import DecisionTreeCanvas from '../components/DecisionTreeCanvas.vue'
import {
  branch, containsNode, indexTree, layoutBranch, restorePositions,
  MIN_NODE_HEIGHT, NODE_TYPES, withPositions,
} from '../decisionTree'
import type { DecisionNode, DecisionRecord, Point } from '../decisionTree'

const route = useRoute()
const decision = shallowRef<DecisionRecord | null>(null)
const draft = shallowRef<DecisionNode[]>([])
const canvas = ref<InstanceType<typeof DecisionTreeCanvas>>()
const selectedId = ref('')
const editing = shallowRef<{ id: string; original: string }>()
const detailsId = ref('')
const detailsOpen = ref(false)
const revision = ref(0)
const savedRevision = ref(0)
const dirty = computed(() => revision.value !== savedRevision.value)
const loading = ref(true)
const saving = ref(false)
const loadError = ref('')
const saveError = ref('')
const conflict = ref(false)
let saveTimer: ReturnType<typeof setTimeout> | undefined
let pendingSave: Promise<void> | undefined
const tree = computed(() => indexTree(draft.value))
const details = computed(() => tree.value.byId.get(detailsId.value))
const blank = computed(() => draft.value.some(node => !node.text.trim()))
const saveStatus = computed(() => {
  if (conflict.value) return '保存冲突'
  if (saveError.value) return '自动保存失败'
  if (saving.value) return '正在保存…'
  if (dirty.value) return blank.value ? '正在编辑节点' : '等待自动保存…'
  return '已保存'
})
const parentOptions = computed(() => {
  const item = details.value
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
  clearTimeout(saveTimer)
  loading.value = true
  loadError.value = ''
  try {
    const record = await getDecision(Number(route.params.id))
    const nodes = unpack(record)
    draft.value = withPositions(nodes, restorePositions(indexTree(nodes), record.rootId, measure(nodes)))
    decision.value = record
    selectedId.value = record.rootId
    editing.value = undefined
    revision.value = 0
    savedRevision.value = 0
    saveError.value = ''
    conflict.value = false
  } catch (reason) {
    loadError.value = (reason as Error).message
  } finally {
    loading.value = false
  }
}

function scheduleSave() {
  clearTimeout(saveTimer)
  if (dirty.value && !blank.value && !saving.value && !conflict.value) {
    saveTimer = setTimeout(() => void save(), 650)
  }
}

function save(): Promise<void> | undefined {
  clearTimeout(saveTimer)
  if (pendingSave) return pendingSave
  const record = decision.value
  if (!record || blank.value || !dirty.value || conflict.value) return
  const snapshot = draft.value
  const submitted = revision.value
  saving.value = true
  saveError.value = ''
  pendingSave = saveDecisionTree(record.id, record.version, snapshot).then(updated => {
    decision.value = updated
    savedRevision.value = submitted
  }).catch((reason: Error) => {
    saveError.value = reason.message
    conflict.value = reason instanceof ApiError && reason.status === 409
  }).finally(() => {
    pendingSave = undefined
    saving.value = false
    if (!saveError.value) scheduleSave()
  })
  return pendingSave
}

async function leave() {
  if (editing.value) finishEdit(editing.value.id, 'blur')
  await pendingSave
  while (dirty.value && !saveError.value) {
    const writing = save()
    if (!writing) break
    await writing
  }
  return !dirty.value || window.confirm('尚有未保存的更改。确定放弃这些更改？')
}

function reload() {
  if (saving.value) return
  if (!dirty.value || window.confirm('重新加载会放弃本页尚未保存的更改。继续？')) void load()
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
onUnmounted(() => {
  clearTimeout(saveTimer)
  window.removeEventListener('beforeunload', beforeUnload)
})

function change(nodes: DecisionNode[]) {
  draft.value = nodes
  revision.value++
  scheduleSave()
}

function patchNode(id: string, changes: Partial<DecisionNode>) {
  const current = tree.value.byId.get(id)
  if (!current) return
  const updated = { ...current, ...changes }
  const nodes = draft.value.map(node => node.id === id ? updated : node)
  const heightChanged = changes.text !== undefined &&
    measure([current]).get(id) !== measure([updated]).get(id)
  change(heightChanged ? arrangedNodes(nodes) : nodes)
}

function editText(id: string) {
  const node = tree.value.byId.get(id)
  if (!node || editing.value?.id === id) return
  selectedId.value = id
  editing.value = { id, original: node.text || '新节点' }
}

function updateText(id: string, text: string) {
  if (editing.value?.id === id && tree.value.byId.get(id)?.text !== text) patchNode(id, { text })
}

function finishEdit(id: string, action: 'blur' | 'confirm' | 'cancel') {
  const item = editing.value
  if (item?.id !== id) return
  const current = tree.value.byId.get(id)?.text ?? ''
  const text = action === 'cancel' ? item.original : current.trim() || item.original
  editing.value = undefined
  if (current !== text) patchNode(id, { text })
  if (action !== 'blur') void nextTick(() => canvas.value?.focusNode(id))
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
      id, parentId, order: index, text: '', description: null, type: null,
      collapsed: false, positionX: null, positionY: null,
    },
  ]
  change(arrangedNodes(nodes))
  editText(id)
}

function command(id: string, action: string) {
  const node = tree.value.byId.get(id)
  if (!node) return
  if (editing.value && action !== 'edit') finishEdit(editing.value.id, 'blur')
  selectedId.value = id
  if (action === 'child') addNode(id)
  else if (action === 'sibling' && node.parentId) addNode(node.parentId, node.order + 1)
  else if (action === 'edit') editText(id)
  else if (action === 'properties') {
    detailsId.value = id
    detailsOpen.value = true
  } else if (action === 'delete') void deleteBranch(node)
  else if ((action === 'up' || action === 'down') && node.parentId) {
    moveNode(id, node.parentId, node.order + (action === 'up' ? -1 : 1))
  }
}

function arrangedNodes(nodes: DecisionNode[]) {
  if (!decision.value) return nodes
  const index = indexTree(nodes)
  const root = index.byId.get(decision.value.rootId)!
  return withPositions(nodes, layoutBranch(index, root.id, measure(nodes), {
    x: root.positionX ?? 0, y: root.positionY ?? 0,
  }))
}

function moveNode(id: string, parentId: string, order: number) {
  const node = tree.value.byId.get(id)
  const parent = tree.value.byId.get(parentId)
  if (!node?.parentId || !parent || containsNode(tree.value, id, parentId)) return
  if (node.parentId === parentId && node.order === order) return

  const destination = (tree.value.children.get(parentId) ?? []).filter(sibling => sibling.id !== id)
  if (order < 0 || order > destination.length) return
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
  change(arrangedNodes(nodes))
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
  const nodes = draft.value.filter(item => !removed.has(item.id)).map(item =>
    item.parentId === node.parentId && item.order > node.order
      ? { ...item, order: item.order - 1 }
      : item,
  )
  change(arrangedNodes(nodes))
}

function arrange() {
  change(arrangedNodes(draft.value))
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
          <span role="status">{{ saveStatus }} · v{{ decision.version }}</span>
          <el-button :disabled="saving" @click="reload">重新加载</el-button>
          <el-button v-if="saveError && !conflict" type="primary" :disabled="blank" @click="save">重试保存</el-button>
        </div>
      </header>
      <el-alert v-if="loadError || saveError" :title="loadError || saveError" type="error" show-icon :closable="false" />
      <el-button v-if="!decision" @click="load">重试</el-button>
      <div v-if="decision" class="editor-workspace">
        <DecisionTreeCanvas
          ref="canvas" :nodes="draft" :root-id="decision.rootId" :selected-id="selectedId" :editing-id="editing?.id ?? ''"
          @select="selectedId = $event" @edit="editText" @text="updateText" @finish="finishEdit"
          @command="command" @toggle="toggle" @arrange="arrange"
          @move="moveNode" @position="position"
        />
        <el-dialog v-model="detailsOpen" title="节点属性" width="min(440px, calc(100vw - 32px))">
          <el-form v-if="details" label-position="top" @submit.prevent>
            <el-form-item label="备注">
              <el-input
                type="textarea" :rows="3" maxlength="10000" :model-value="details.description ?? ''"
                @update:model-value="patchNode(details.id, { description: $event || null })"
              />
            </el-form-item>
            <el-form-item label="类型">
              <el-select
                clearable placeholder="可选" :model-value="details.type ?? ''"
                @change="patchNode(details.id, { type: $event || null })"
              >
                <el-option v-for="name in NODE_TYPES" :key="name" :value="name" />
              </el-select>
            </el-form-item>
            <el-form-item v-if="details.parentId" label="父节点">
              <el-select
                filterable :model-value="details.parentId"
                @change="changeParent(details.id, $event)"
              >
                <el-option v-for="node in parentOptions" :key="node.id" :value="node.id" :label="node.text.slice(0, 100)" />
              </el-select>
            </el-form-item>
          </el-form>
          <template #footer><el-button type="primary" @click="detailsOpen = false">完成</el-button></template>
        </el-dialog>
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
.editor-actions .el-button + .el-button { margin-left: 0; }
.editor-workspace { margin-top: 12px; }
@media (max-width: 760px) {
  .decision-editor { width: calc(100% - 24px); }
  .editor-header { align-items: start; flex-direction: column; }
  .editor-actions { justify-content: start; }
}
</style>
