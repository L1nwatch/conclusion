import { describe, expect, it } from 'vitest'
import { branch, branchConnector, indexTree, layoutBranch, restorePositions } from './decisionTree'
import type { DecisionNode } from './decisionTree'

function node(id: string, parentId: string | null, order = 0): DecisionNode {
  return {
    id, parentId, order, text: id, description: null, type: null,
    collapsed: false, positionX: null, positionY: null,
  }
}

describe('decision tree layout', () => {
  it('places ordered siblings left to right by depth and avoids overlap with tall nodes', () => {
    const tree = indexTree([node('b', 'root', 1), node('root', null), node('a', 'root'), node('c', 'a')])
    const positions = layoutBranch(tree, 'root', new Map([['a', 180]]))
    expect(positions.get('a')!.x).toBeGreaterThan(positions.get('root')!.x)
    expect(positions.get('c')!.x).toBeGreaterThan(positions.get('a')!.x)
    expect(positions.get('b')!.y).toBeGreaterThan(positions.get('a')!.y + 180)
  })

  it('preserves completed custom positions on reopen, including collapsed descendants', () => {
    const root = { ...node('root', null), collapsed: true, positionX: 70, positionY: 115 }
    const a = { ...node('a', 'root'), positionX: 420, positionY: 120 }
    const b = { ...node('b', 'root', 1), positionX: 420, positionY: 230 }
    const tree = indexTree([root, a, b])
    expect(branch(tree, 'root', true)).toEqual([root])
    const positions = restorePositions(tree, 'root', new Map())
    expect(positions.get('root')).toEqual({ x: 70, y: 115 })
    expect(positions.get('a')).toEqual({ x: 420, y: 120 })
    expect(positions.get('b')).toEqual({ x: 420, y: 230 })
  })

  it('centers each parent and keeps an uneven set of sibling subtrees apart', () => {
    const tree = indexTree([
      node('root', null), node('a', 'root'), node('b', 'root', 1),
      node('a1', 'a'), node('a2', 'a', 1), node('a3', 'a1'),
      node('b1', 'b'), node('b2', 'b', 1),
    ])
    const heights = new Map([['a1', 160], ['a3', 220], ['b2', 120]])
    const positions = layoutBranch(tree, 'root', heights)
    const center = (id: string) => positions.get(id)!.y + (heights.get(id) ?? 68) / 2
    expect(center('root')).toBe((center('a') + center('b')) / 2)
    expect(center('a')).toBe((center('a1') + center('a2')) / 2)
    expect(center('b')).toBe((center('b1') + center('b2')) / 2)
    expect(center('a1')).toBe(center('a3'))
    const upperBottom = Math.max(...branch(tree, 'a').map(item =>
      positions.get(item.id)!.y + (heights.get(item.id) ?? 68),
    ))
    const lowerTop = Math.min(...branch(tree, 'b').map(item => positions.get(item.id)!.y))
    expect(upperBottom + 24).toBeLessThanOrEqual(lowerTop)
  })

  it('repairs old interleaved columns and lays out new nodes added without coordinates', () => {
    const existing = [
      { ...node('root', null), positionX: 0, positionY: 0 },
      { ...node('a', 'root'), positionX: 298, positionY: 0 },
      { ...node('b', 'root', 1), positionX: 298, positionY: 92 },
      { ...node('b1', 'b'), positionX: 596, positionY: 92 },
      { ...node('a1', 'a'), positionX: 596, positionY: 184 },
    ]
    for (const nodes of [existing, [...existing, node('a2', 'a', 1)]]) {
      const positions = restorePositions(indexTree(nodes), 'root', new Map())
      expect(positions.get('root')).toEqual({ x: 0, y: 0 })
      expect(positions.get('a1')!.y + 68).toBeLessThan(positions.get('b1')!.y)
    }
  })

  it('draws a direct connection or straight segments along one shared junction', () => {
    expect(branchConnector({ x: 0, y: 0 }, { x: 60, y: 0 })).toBe('M 0,0 L 60,0')
    expect(branchConnector({ x: 0, y: 0 }, { x: 60, y: 20 }, 30)).toBe('M 0,0 H 30 V 20 H 60')
    expect(branchConnector({ x: 0, y: 0 }, { x: 60, y: -20 }, 30)).toBe('M 0,0 H 30 V -20 H 60')
  })

  it('lays out deep trees iteratively', () => {
    const nodes = Array.from({ length: 5000 }, (_, i) => node(String(i), i ? String(i - 1) : null))
    const tree = indexTree(nodes)
    expect(layoutBranch(tree, '0', new Map()).size).toBe(nodes.length)
  })
})
