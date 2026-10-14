import { AGENTS } from '../agents'
import type { AgentName } from '../types'
import type { Phase } from './Station'

/**
 * An agent as a plate on the contact sheet.
 *
 * The floor shows five of these at once — the whole cast on one screen, no
 * scrolling. Each gives you only what you need to decide whether to look
 * closer: who, whether they worked, how many tools they reached for, and the
 * first line of what they said. Clicking opens the full station.
 */
export function Plate({ name, phase, said, toolCount, index, onOpen }: {
  name: AgentName
  phase: Phase
  said: string
  toolCount: number
  index: number
  onOpen: (n: AgentName) => void
}) {
  const a = AGENTS[name]
  const idle = phase === 'idle'

  return (
    <button
      className={`plate ${phase}`}
      style={{ ['--hue' as string]: a.hue }}
      onClick={() => !idle && onOpen(name)}
      disabled={idle}
      aria-label={idle ? `${a.label} was not called` : `Open ${a.label}`}
    >
      <span className="p-n">{String(index + 1).padStart(2, '0')}</span>
      <span className="p-name">{a.label}</span>
      <span className="p-role">{a.role}</span>
      <span className="p-rule" />
      {idle ? (
        <span className="p-idle">not called</span>
      ) : (
        <>
          <span className="p-said">{said || '…'}</span>
          <span className="p-foot">
            {toolCount} {toolCount === 1 ? 'tool' : 'tools'}
            <span className="p-more">read →</span>
          </span>
        </>
      )}
    </button>
  )
}
