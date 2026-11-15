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
  const spans = new Map<string, number>()
  const childSpans = new Map<string, number>()
  const height = (id: string) => heights.get(id) ?? MIN_NODE_HEIGHT
  for (let i = ordered.length - 1; i >= 0; i--) {
    const id = ordered[i]!.id
    const children = index.children.get(id) ?? []
    const span = children.reduce((total, child) => total + spans.get(child.id)! + GAP, -GAP)
    childSpans.set(id, Math.max(0, span))
    spans.set(id, Math.max(height(id), span))
  }

  const positions = new Map<string, Point>()
  const pending = [{ id: rootId, x: anchor.x, center: anchor.y + height(rootId) / 2 }]
  while (pending.length) {
    const { id, x, center } = pending.pop()!
    positions.set(id, { x, y: center - height(id) / 2 })
    let top = center - childSpans.get(id)! / 2
    for (const child of index.children.get(id) ?? []) {
      const span = spans.get(child.id)!
      pending.push({ id: child.id, x: x + COLUMN, center: top + span / 2 })
      top += span + GAP
    }
  }
  return positions
}

export function fillMissingPositions(
  index: TreeIndex, rootId: string, heights: Map<string, number>,
): Map<string, Point> {
  const defaults = layoutBranch(index, rootId, heights)
  const ordered = branch(index, rootId)
  if (ordered.every(node => node.positionX === null)) return defaults

  const positions = new Map<string, Point>()
  const occupied: Array<{ x: number; y: number; bottom: number }> = []
  const height = (id: string) => heights.get(id) ?? MIN_NODE_HEIGHT
  function reserve(id: string, point: Point) {
    positions.set(id, point)
    occupied.push({ ...point, bottom: point.y + height(id) })
  }
  for (const node of ordered) {
    if (node.positionX !== null && node.positionY !== null) {
      reserve(node.id, { x: node.positionX, y: node.positionY })
    }
  }
  for (const node of ordered) {
    if (positions.has(node.id)) continue
    const point = { ...defaults.get(node.id)! }
    if (node.parentId !== null) {
      const parent = positions.get(node.parentId)!
      point.x = parent.x + COLUMN
      point.y += parent.y - defaults.get(node.parentId)!.y
    }
    const relevant = occupied.filter(other => Math.abs(point.x - other.x) < NODE_WIDTH + GAP)
      .sort((a, b) => a.y - b.y)
    for (const other of relevant) {
      if (point.y + height(node.id) + GAP > other.y && point.y < other.bottom + GAP) {
        point.y = other.bottom + GAP
      }
    }
    reserve(node.id, point)
  }
  return positions
}

export function withPositions(nodes: DecisionNode[], positions: Map<string, Point>): DecisionNode[] {
  return nodes.map(node => {
    const position = positions.get(node.id)
    return position ? { ...node, positionX: position.x, positionY: position.y } : node
  })
}
