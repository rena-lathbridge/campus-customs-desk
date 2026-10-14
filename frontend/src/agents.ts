/**
 * Each agent's visual identity.
 *
 * The five agents are deliberately NOT interchangeable coloured chips. Each one
 * gets its own way of rendering what it says, because the five produce
 * genuinely different kinds of output. A stock count and a drafted apology
 * should not look alike.
 *
 * The hues are tonal rather than bright — oxblood, olive, sage, slate, clay,
 * all desaturated to within a few steps of grey. They appear only as a single
 * hairline rule beside each station. The real differentiation is typographic.
 */

import type { AgentName } from './types'

export type Voice = 'decree' | 'count' | 'ledger' | 'calendar' | 'letter'

export interface AgentStyle {
  name: AgentName
  label: string
  role: string
  hue: string          // accent colour
  glow: string         // translucent version for halos
  mark: string         // CSS-drawn glyph (text, never an image asset)
  voice: Voice         // how this agent's words are rendered
}

export const AGENTS: Record<AgentName, AgentStyle> = {
  boss: {
    name: 'boss', label: 'Boss', role: 'decides & closes',
    hue: '#8c2f2a', glow: 'rgba(140,47,42,.07)', mark: '—', voice: 'decree',
  },
  inventory: {
    name: 'inventory', label: 'Inventory', role: 'the shelf',
    hue: '#6e6552', glow: 'rgba(110,101,82,.07)', mark: '—', voice: 'count',
  },
  accounting: {
    name: 'accounting', label: 'Accounting', role: 'the money',
    hue: '#4d5a4f', glow: 'rgba(77,90,79,.07)', mark: '—', voice: 'ledger',
  },
  facilities: {
    name: 'facilities', label: 'Facilities', role: 'the premises',
    hue: '#4e5a69', glow: 'rgba(78,90,105,.07)', mark: '—', voice: 'calendar',
  },
  customer_service: {
    name: 'customer_service', label: 'Customer Service', role: 'the words',
    hue: '#7d5c55', glow: 'rgba(125,92,85,.07)', mark: '—', voice: 'letter',
  },
}

export const ORDER: AgentName[] = [
  'boss', 'inventory', 'accounting', 'facilities', 'customer_service',
]

export const isAgent = (s: string): s is AgentName => s in AGENTS
