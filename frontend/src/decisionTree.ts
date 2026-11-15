export const DECISION_STATUSES = ['Draft', 'Thinking', 'Decided'] as const
export const NODE_TYPES = ['Topic', 'Condition', 'Action', 'Outcome', 'Note'] as const

export type DecisionStatus = typeof DECISION_STATUSES[number]
export type DecisionNodeType = typeof NODE_TYPES[number]
export type Point = { x: number; y: number }

export interface DecisionDetails {
  title: string
  description: string | null
  status: DecisionStatus
}

export interface DecisionSummary extends DecisionDetails {
  id: number
  version: number
  createdAt: string
  updatedAt: string
}

export interface DecisionNode {
  id: string
  parentId: string | null
  text: string
  description: string | null
  type: DecisionNodeType | null
  order: number
  positionX: number | null
  positionY: number | null
  collapsed: boolean
}

export interface DecisionRecord extends DecisionSummary {
  rootId: string
  nodes: Array<DecisionNode & { decisionId: number; createdAt: string; updatedAt: string }>
}

export function indexTree(nodes: DecisionNode[]) {
  const byId = new Map(nodes.map(node => [node.id, node]))
  const children = new Map<string, DecisionNode[]>()
  for (const node of nodes) {
    if (node.parentId === null) continue
    const siblings = children.get(node.parentId) ?? []
    siblings.push(node)
    children.set(node.parentId, siblings)
  }
  for (const siblings of children.values()) siblings.sort((a, b) => a.order - b.order)
  return { byId, children }
}

type TreeIndex = ReturnType<typeof indexTree>

export function branch(index: TreeIndex, rootId: string, visibleOnly = false): DecisionNode[] {
  const result: DecisionNode[] = []
  const root = index.byId.get(rootId)
  if (!root) return result
  const pending = [root]
  while (pending.length) {
    const node = pending.pop()!
    result.push(node)
    if (visibleOnly && node.collapsed) continue
    const children = index.children.get(node.id) ?? []
    for (let i = children.length - 1; i >= 0; i--) pending.push(children[i]!)
  }
  return result
}

export function containsNode(index: TreeIndex, rootId: string, nodeId: string): boolean {
  let current = index.byId.get(nodeId)
  while (current) {
    if (current.id === rootId) return true
    current = current.parentId === null ? undefined : index.byId.get(current.parentId)
  }
  return false
}

export const NODE_WIDTH = 226
const COLUMN = NODE_WIDTH + 72
const GAP = 24
export const MIN_NODE_HEIGHT = 68

export function layoutBranch(
  index: TreeIndex, rootId: string, heights: Map<string, number>, anchor: Point = { x: 0, y: 0 },
): Map<string, Point> {
  const ordered = branch(index, rootId)
  const spans = new Map<string, { above: number; below: number; childOffsets: number[] }>()
  const height = (id: string) => heights.get(id) ?? MIN_NODE_HEIGHT
  for (let i = ordered.length - 1; i >= 0; i--) {
    const id = ordered[i]!.id
    const children = index.children.get(id) ?? []
    let bottom = -GAP
    const centers = children.map(child => {
      const span = spans.get(child.id)!
      const center = bottom + GAP + span.above
      bottom = center + span.below
      return center
    })
    const midpoint = centers.length ? (centers[0]! + centers[centers.length - 1]!) / 2 : 0
    const halfHeight = height(id) / 2
    spans.set(id, {
      above: Math.max(halfHeight, midpoint),
      below: Math.max(halfHeight, bottom - midpoint),
      childOffsets: centers.map(center => center - midpoint),
    })
  }

  const positions = new Map<string, Point>()
  const pending = [{ id: rootId, x: anchor.x, center: anchor.y + height(rootId) / 2 }]
  while (pending.length) {
    const { id, x, center } = pending.pop()!
    positions.set(id, { x, y: center - height(id) / 2 })
    const offsets = spans.get(id)!.childOffsets
    const children = index.children.get(id) ?? []
    children.forEach((child, i) => {
      pending.push({ id: child.id, x: x + COLUMN, center: center + offsets[i]! })
    })
  }
  return positions
}

export function branchConnector(source: Point, target: Point, junctionX?: number): string {
  if (junctionX === undefined || source.y === target.y) {
    return `M ${source.x},${source.y} L ${target.x},${target.y}`
  }
  return `M ${source.x},${source.y} H ${junctionX} V ${target.y} H ${target.x}`
}

export function restorePositions(
  index: TreeIndex, rootId: string, heights: Map<string, number>,
): Map<string, Point> {
  const ordered = branch(index, rootId)
  const root = index.byId.get(rootId)!
  const anchor = { x: root.positionX ?? 0, y: root.positionY ?? 0 }
  if (ordered.some(node => node.positionX === null || node.positionY === null)) {
    return layoutBranch(index, rootId, heights, anchor)
  }
  // Older column layouts could place a new child below a different branch.
  // Custom column positions created by dragging are kept when reopening a tree.
  const inColumns = ordered.every(node => node.parentId === null ||
    Math.abs(node.positionX! - index.byId.get(node.parentId)!.positionX! - COLUMN) < 0.5)
  if (inColumns && branchesInterleave(index, ordered, heights)) {
    return layoutBranch(index, rootId, heights, anchor)
  }
  return new Map(ordered.map(node => [node.id, { x: node.positionX!, y: node.positionY! }]))
}

function branchesInterleave(index: TreeIndex, ordered: DecisionNode[], heights: Map<string, number>) {
  const bounds = new Map<string, { top: number; bottom: number }>()
  for (let i = ordered.length - 1; i >= 0; i--) {
    const node = ordered[i]!
    let top = node.positionY!
    let bottom = top + (heights.get(node.id) ?? MIN_NODE_HEIGHT)
    let previousBottom = -Infinity
    for (const child of index.children.get(node.id) ?? []) {
      const childBounds = bounds.get(child.id)!
      if (childBounds.top < previousBottom - 0.5) return true
      previousBottom = childBounds.bottom
      top = Math.min(top, childBounds.top)
      bottom = Math.max(bottom, childBounds.bottom)
    }
    bounds.set(node.id, { top, bottom })
  }
  return false
}

export function withPositions(nodes: DecisionNode[], positions: Map<string, Point>): DecisionNode[] {
  return nodes.map(node => {
    const position = positions.get(node.id)
    return position ? { ...node, positionX: position.x, positionY: position.y } : node
  })
}
