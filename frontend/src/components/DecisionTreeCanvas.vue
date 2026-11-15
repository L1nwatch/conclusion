<script setup lang="ts">
import { computed, ref } from 'vue'
import { BaseEdge, Handle, Position, VueFlow, useVueFlow } from '@vue-flow/core'
import type { Edge, EdgeProps, Node as FlowNode, NodeDragEvent } from '@vue-flow/core'
import '@vue-flow/core/dist/style.css'
import '@vue-flow/core/dist/theme-default.css'
import { branch, branchConnector, containsNode, indexTree } from '../decisionTree'
import type { DecisionNode, Point } from '../decisionTree'

const props = defineProps<{
  nodes: DecisionNode[]
  rootId: string
  selectedId: string
  editingId: string
}>()
const emit = defineEmits<{
  select: [id: string]
  edit: [id: string]
  text: [id: string, text: string]
  finish: [id: string, action: 'blur' | 'confirm' | 'cancel']
  command: [id: string, action: string]
  toggle: [id: string]
  arrange: []
  move: [id: string, parentId: string, order: number]
  position: [positions: Map<string, Point>]
}>()

const flow = useVueFlow()
const canvas = ref<HTMLElement>()
const tree = computed(() => indexTree(props.nodes))
const visible = computed(() => branch(tree.value, props.rootId, true))
interface CardData {
  text: string
  collapsed: boolean
  childCount: number
  type: string | null
  canMoveUp: boolean
  canMoveDown: boolean
}
const nodes = computed<FlowNode<CardData>[]>(() => visible.value.map(node => ({
  id: node.id,
  type: 'branch',
  position: { x: node.positionX ?? 0, y: node.positionY ?? 0 },
  data: {
    text: node.text, collapsed: node.collapsed, type: node.type,
    childCount: tree.value.children.get(node.id)?.length ?? 0,
    canMoveUp: node.order > 0,
    canMoveDown: node.parentId !== null &&
      node.order < (tree.value.children.get(node.parentId)?.length ?? 0) - 1,
  },
})))
const edges = computed<Edge[]>(() => visible.value.flatMap(node => node.parentId === null ? [] : [{
  id: node.id,
  source: node.parentId,
  target: node.id,
  type: 'branch',
  style: { stroke: '#81998e', strokeWidth: 1.6 },
}]))

function connectorPath({ source, sourceX, sourceY, targetX, targetY }: EdgeProps) {
  const from = { x: sourceX, y: sourceY }
  const to = { x: targetX, y: targetY }
  const children = tree.value.children.get(source) ?? []
  if (children.length <= 1 || targetX <= sourceX) return branchConnector(from, to)

  let nearest = targetX
  for (const child of children) {
    const x = flow.findNode(child.id)?.computedPosition.x
    if (x !== undefined && x > sourceX) nearest = Math.min(nearest, x)
  }
  return branchConnector(from, to, (sourceX + nearest) / 2)
}

function focusNode(id: string) {
  canvas.value?.querySelector<HTMLButtonElement>(
    `[data-node-id="${CSS.escape(id)}"] button.decision-node-label`,
  )?.focus({ preventScroll: true })
}
defineExpose({ focusNode })

function selectCard(id: string) {
  emit('select', id)
  if (props.editingId !== id) focusNode(id)
}

function focusInput(element: unknown) {
  if (!(element instanceof HTMLTextAreaElement) || element === document.activeElement) return
  requestAnimationFrame(() => {
    if (!canvas.value || !element.isConnected || document.activeElement === element) return
    element.focus({ preventScroll: true })
    element.setSelectionRange(element.value.length, element.value.length)
    const bounds = canvas.value.getBoundingClientRect()
    const card = (element.closest('.decision-node-card') ?? element).getBoundingClientRect()
    const dx = Math.max(0, bounds.left + 16 - card.left) - Math.max(0, card.right - bounds.right + 16)
    const dy = Math.max(0, bounds.top + 60 - card.top) - Math.max(0, card.bottom - bounds.bottom + 52)
    if (dx || dy) {
      const viewport = flow.getViewport()
      void flow.setViewport({ ...viewport, x: viewport.x + dx, y: viewport.y + dy })
    }
  })
}

function shortcut(event: KeyboardEvent, id: string, editing = false) {
  if (event.isComposing || event.keyCode === 229 || event.metaKey || event.ctrlKey || event.altKey || event.shiftKey) return
  const key = event.key
  if (key === 'Tab') {
    event.preventDefault()
    emit('command', id, 'child')
  } else if (key === 'Enter') {
    event.preventDefault()
    if (editing) emit('finish', id, 'confirm')
    else if (id !== props.rootId) emit('command', id, 'sibling')
    else emit('edit', id)
  } else if (key === 'Escape') {
    event.preventDefault()
    event.stopPropagation()
    if (editing) emit('finish', id, 'cancel')
    else {
      emit('select', '')
      canvas.value?.focus({ preventScroll: true })
    }
  } else if (!editing && key === 'F2') {
    event.preventDefault()
    emit('edit', id)
  } else if (!editing && (key === 'Delete' || key === 'Backspace') && id !== props.rootId) {
    event.preventDefault()
    emit('command', id, 'delete')
  }
}

function updateText(event: Event, id: string) {
  if (event instanceof InputEvent && event.isComposing) return
  emit('text', id, (event.target as HTMLTextAreaElement).value)
}

function openNodeMenu(event: MouseEvent) {
  const button = (event.currentTarget as HTMLElement).querySelector<HTMLButtonElement>('.node-menu')
  button?.focus({ preventScroll: true })
  button?.click()
}

function pointOf(node: DecisionNode): Point {
  return { x: node.positionX ?? 0, y: node.positionY ?? 0 }
}

let moving: { origin: Point; nodes: DecisionNode[] } | null = null
function startPositionDrag({ node }: NodeDragEvent) {
  const descendants = branch(tree.value, node.id)
  if (descendants.length) moving = { origin: pointOf(descendants[0]!), nodes: descendants }
}

function translatedPositions(point: Point) {
  const positions = new Map<string, Point>()
  if (!moving) return positions
  const dx = point.x - moving.origin.x
  const dy = point.y - moving.origin.y
  for (const item of moving.nodes) {
    const start = pointOf(item)
    positions.set(item.id, { x: start.x + dx, y: start.y + dy })
  }
  return positions
}

function previewPosition({ node }: NodeDragEvent) {
  for (const [id, position] of translatedPositions(node.position)) {
    if (id !== node.id && flow.findNode(id)) flow.updateNode(id, { position })
  }
}

function finishPosition({ node }: NodeDragEvent) {
  const positions = translatedPositions(node.position)
  moving = null
  if (positions.size) emit('position', positions)
}

type DropLocation = 'before' | 'child' | 'after'
const movingId = ref('')
const drop = ref<{ target: string; location: DropLocation } | null>(null)

function startBranchDrag(event: DragEvent, id: string) {
  if (!event.dataTransfer) {
    event.preventDefault()
    return
  }
  movingId.value = id
  const card = (event.currentTarget as HTMLElement).closest('.decision-node-card')
  if (card) event.dataTransfer.setDragImage(card, 18, 22)
  event.dataTransfer.effectAllowed = 'move'
  event.dataTransfer.setData('text/plain', id)
}

function endBranchDrag() {
  movingId.value = ''
  drop.value = null
}

function destination(event: DragEvent, id: string) {
  const from = tree.value.byId.get(movingId.value)
  const target = tree.value.byId.get(id)
  if (!from || !target || containsNode(tree.value, from.id, id)) return
  const box = (event.currentTarget as HTMLElement).getBoundingClientRect()
  const ratio = (event.clientY - box.top) / box.height
  const location: DropLocation = target.parentId === null || (ratio >= .27 && ratio <= .73)
    ? 'child'
    : ratio < .27 ? 'before' : 'after'
  const parentId = location === 'child' ? id : target.parentId!
  const siblings = (tree.value.children.get(parentId) ?? []).filter(node => node.id !== from.id)
  const order = location === 'child' ? siblings.length
    : siblings.findIndex(node => node.id === id) + Number(location === 'after')
  return { target: id, location, parentId, order }
}

function dragOver(event: DragEvent, id: string) {
  const target = destination(event, id)
  drop.value = target ?? null
  if (!target || !event.dataTransfer) return
  event.preventDefault()
  event.dataTransfer.dropEffect = 'move'
}

function dragLeave(event: DragEvent, id: string) {
  const card = event.currentTarget as HTMLElement
  if (drop.value?.target === id && !(event.relatedTarget instanceof Node && card.contains(event.relatedTarget))) drop.value = null
}

function dropBranch(event: DragEvent, id: string) {
  event.preventDefault()
  const target = destination(event, id)
  if (target) emit('move', movingId.value, target.parentId, target.order)
  endBranchDrag()
}
</script>

<template>
  <div ref="canvas" class="tree-canvas" tabindex="-1">
    <div class="canvas-toolbar" aria-label="画布工具">
      <div class="canvas-zoom" role="group" aria-label="缩放">
        <button type="button" aria-label="缩小" title="缩小" @click="flow.zoomOut()">−</button>
        <button type="button" aria-label="放大" title="放大" @click="flow.zoomIn()">+</button>
      </div>
      <button type="button" @click="flow.fitView({ padding: .13, maxZoom: 1 })">适应画布</button>
      <button type="button" @click="emit('arrange')">自动布局</button>
    </div>
    <VueFlow
      :id="flow.id" :nodes="nodes" :edges="edges"
      :nodes-connectable="false" :nodes-focusable="false"
      :elements-selectable="false" :delete-key-code="null"
      :zoom-on-double-click="false" :min-zoom=".03" :max-zoom="2.5"
      :node-drag-threshold="4" :fit-view-on-init="true"
      :fit-view-on-init-options="{ padding: .13, maxZoom: 1 }"
      @node-drag-start="startPositionDrag" @node-drag="previewPosition" @node-drag-stop="finishPosition"
      @pane-click="emit('select', '')"
    >
      <template #edge-branch="edge">
        <BaseEdge :id="edge.id" :path="connectorPath(edge)" :style="edge.style" />
      </template>
      <template #node-branch="{ id, data }">
        <article
          class="decision-node-card"
          :class="[
            data.type?.toLowerCase(),
            { root: id === rootId, selected: id === selectedId, editing: id === editingId, moving: id === movingId },
            drop?.target === id ? 'drop-' + drop.location : '',
          ]"
          :data-node-id="id"
          @dragover="dragOver($event, id)" @dragleave="dragLeave($event, id)" @drop="dropBranch($event, id)"
          @click="selectCard(id)" @dblclick.stop="emit('edit', id)"
          @contextmenu.prevent.stop="openNodeMenu"
        >
          <Handle v-if="id !== rootId" type="target" :position="Position.Left" :connectable="false" />
          <div v-if="id === editingId" class="node-inline-edit nodrag nowheel" @dblclick.stop>
            <span class="decision-node-label" aria-hidden="true">{{ data.text + '\u200b' }}</span>
            <textarea
              :ref="focusInput" class="decision-node-label"
              aria-label="节点文字" placeholder="输入节点文字" maxlength="4000" rows="1"
              :value="data.text"
              @input="updateText($event, id)" @compositionend="updateText($event, id)"
              @keydown="shortcut($event, id, true)" @blur="emit('finish', id, 'blur')"
            />
          </div>
          <button
            v-else class="decision-node-label" type="button"
            :aria-pressed="id === selectedId" aria-keyshortcuts="Tab Enter F2"
            title="双击编辑节点" @focus="emit('select', id)" @keydown="shortcut($event, id)"
          >{{ data.text || '未命名节点' }}</button>
          <button
            v-if="id !== rootId" class="branch-grip nodrag" type="button"
            draggable="true" aria-label="拖拽分支"
            title="拖到节点中间可成为子节点，拖到上沿或下沿可调整同级顺序"
            @dragstart="startBranchDrag($event, id)" @dragend="endBranchDrag" @dblclick.stop
          >⠿</button>
          <button
            v-if="data.childCount" class="branch-fold nodrag" type="button"
            :aria-label="data.collapsed ? '展开分支' : '折叠分支'"
            :aria-expanded="!data.collapsed"
            :title="data.collapsed ? '展开分支' : '折叠分支'"
            @click.stop="emit('toggle', id)" @dblclick.stop
          >{{ data.collapsed ? '+' : '−' }}</button>
          <el-dropdown
            class="node-actions nodrag" trigger="click" placement="right-start"
            @command="emit('command', id, $event)"
          >
            <button
              class="node-menu" type="button" aria-label="节点操作" title="节点操作"
              @click.stop="emit('select', id)" @dblclick.stop
            >⋯</button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="child">添加子节点 <kbd>Tab</kbd></el-dropdown-item>
                <el-dropdown-item v-if="id !== rootId" command="sibling">添加同级 <kbd>Enter</kbd></el-dropdown-item>
                <el-dropdown-item command="edit">编辑文字 <kbd>F2</kbd></el-dropdown-item>
                <el-dropdown-item command="properties">节点属性</el-dropdown-item>
                <template v-if="id !== rootId">
                  <el-dropdown-item command="up" :disabled="!data.canMoveUp" divided>上移</el-dropdown-item>
                  <el-dropdown-item command="down" :disabled="!data.canMoveDown">下移</el-dropdown-item>
                  <el-dropdown-item command="delete" divided>删除分支</el-dropdown-item>
                </template>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
          <Handle type="source" :position="Position.Right" :connectable="false" />
        </article>
      </template>
    </VueFlow>
    <div class="canvas-hint">
      <template v-if="editingId">
        <kbd>Enter</kbd> 完成 · <kbd>Shift + Enter</kbd> 换行 · <kbd>Esc</kbd> 取消
      </template>
      <template v-else>
        双击编辑 · 选中后按 <kbd>Tab</kbd> 新增子节点、<kbd>Enter</kbd> 新增同级
      </template>
    </div>
  </div>
</template>

<style>
.decision-node-label {
  display: block;
  width: 174px;
  padding: 0;
  border: 0;
  background: transparent;
  font-family: inherit;
  font-size: 15px;
  font-weight: 600;
  line-height: 22px;
  text-align: start;
  overflow-wrap: anywhere;
  white-space: pre-wrap;
}
.decision-node-measure {
  position: absolute;
  visibility: hidden;
  pointer-events: none;
  top: 0;
  left: 0;
}
.el-dropdown-menu kbd { margin-inline-start: 12px; color: #60766b; font-size: .75em; }
</style>

<style scoped>
.tree-canvas {
  position: relative;
  min-width: 0;
  min-height: 520px;
  height: min(72vh, 850px);
  border: 1px solid #c9d5cc;
  border-radius: 12px;
  overflow: hidden;
  background: #edf2ee;
}
.canvas-toolbar {
  display: flex;
  gap: 6px;
  position: absolute;
  z-index: 5;
  top: 12px;
  left: 12px;
}
.canvas-toolbar > button, .canvas-zoom {
  border: 1px solid #b8c8bd;
  border-radius: 6px;
  background: #fff;
}
.canvas-toolbar button {
  padding: 0 9px;
  min-height: 34px;
  color: #25493b;
  font-size: .78rem;
  cursor: pointer;
}
.canvas-toolbar button:disabled { opacity: .55; cursor: default; }
.canvas-zoom button { background: none; border: none; min-width: 30px; font-size: 1rem; }
.canvas-zoom button + button { border-left: 1px solid #d7e0da; }
.canvas-hint {
  position: absolute;
  z-index: 4;
  bottom: 8px;
  left: 10px;
  right: 10px;
  color: #355749;
  background: #f8fbf8ed;
  width: fit-content;
  max-width: calc(100% - 20px);
  padding: 6px 8px;
  border-radius: 5px;
  font-size: .73rem;
  pointer-events: none;
}
.decision-node-card {
  position: relative;
  display: flex;
  align-items: center;
  width: 226px;
  min-height: 68px;
  padding: 12px 34px 12px 14px;
  color: #193b2e;
  background: #fff;
  border: 1px solid #96afa1;
  border-left: 3px solid #81a892;
  border-radius: 8px;
  box-shadow: 0 2px 7px #23453716;
  user-select: none;
}
.decision-node-card.root { background: #174435; border-color: #174435; color: white; }
.decision-node-card.condition { border-left-color: #a67d2d; }
.decision-node-card.action { border-left-color: #557cb2; }
.decision-node-card.outcome { border-left-color: #7b63a4; }
.decision-node-card.note { border-left-color: #799390; }
.decision-node-card.selected { outline: 3px solid #428a69; outline-offset: 2px; }
.decision-node-card.editing { outline: 3px solid #15805c; outline-offset: 2px; }
.decision-node-card.moving { opacity: .7; }
.decision-node-card.drop-child { outline: 3px solid #0b754b; background: #d7f4e6; color: #142f22; }
.decision-node-card.drop-before::before, .decision-node-card.drop-after::before {
  position: absolute;
  content: '';
  height: 4px;
  background: #0b754b;
  left: 0;
  right: 0;
  border-radius: 4px;
}
.decision-node-card.drop-before::before { top: -7px; }
.decision-node-card.drop-after::before { bottom: -7px; }
.decision-node-card .decision-node-label { color: inherit; cursor: grab; }
.decision-node-card .decision-node-label:active { cursor: grabbing; }
.node-inline-edit {
  display: grid;
  background: #effaf2;
  box-shadow: 0 0 0 4px #effaf2, 0 0 0 5px #62a982;
  border-radius: 3px;
  color: #153b2a;
}
.node-inline-edit > * { grid-area: 1 / 1; }
.node-inline-edit span { visibility: hidden; }
.decision-node-card .node-inline-edit textarea {
  display: block;
  resize: none;
  overflow: hidden;
  outline: none;
  cursor: text;
  caret-color: #124a36;
  user-select: text;
}
.node-inline-edit textarea::placeholder { color: #507364; }
.branch-grip, .branch-fold {
  position: absolute;
  right: 5px;
  width: 24px;
  height: 24px;
  padding: 0;
  border: 0;
  border-radius: 4px;
  background: transparent;
  color: inherit;
  font-size: 1rem;
  line-height: 1;
  cursor: pointer;
}
.branch-grip { top: 2px; height: 19px; cursor: grab; }
.branch-fold { bottom: 2px; height: 19px; }
.branch-grip:hover, .branch-fold:hover { background: #87a39544; }
.node-actions { position: absolute; right: 5px; top: 23px; }
.root .node-actions { top: 5px; }
.node-menu {
  width: 24px;
  height: 20px;
  padding: 0;
  border: 0;
  border-radius: 4px;
  background: transparent;
  color: inherit;
  font-size: 1rem;
  line-height: 1;
  cursor: pointer;
}
.node-menu:hover, .node-menu:focus-visible { background: #87a39544; }
.decision-node-card.root .node-actions { color: white; }
.decision-node-card :deep(.vue-flow__handle) { opacity: 0; pointer-events: none; }
@media (max-width: 760px) { .tree-canvas { height: 62vh; min-height: 370px; } }
</style>
