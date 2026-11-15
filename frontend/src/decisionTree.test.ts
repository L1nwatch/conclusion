import { describe, expect, it } from 'vitest'
import { branch, fillMissingPositions, indexTree, layoutBranch } from './decisionTree'
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

  it('preserves manually placed nodes when adding missing or collapsed descendants', () => {
    const root = { ...node('root', null), collapsed: true, positionX: 70, positionY: 115 }
    const a = { ...node('a', 'root'), positionX: 368, positionY: 115 }
    const tree = indexTree([root, a, node('b', 'root', 1)])
    expect(branch(tree, 'root', true)).toEqual([root])
    const positions = fillMissingPositions(tree, 'root', new Map())
    expect(positions.get('root')).toEqual({ x: 70, y: 115 })
    expect(positions.get('a')).toEqual({ x: 368, y: 115 })
    expect(positions.get('b')!.y).toBeGreaterThan(115 + 68)
  })

  it('lays out deep trees iteratively', () => {
    const nodes = Array.from({ length: 5000 }, (_, i) => node(String(i), i ? String(i - 1) : null))
    const tree = indexTree(nodes)
    expect(layoutBranch(tree, '0', new Map()).size).toBe(nodes.length)
  })
})
