import { AGENTS } from '../agents'
import type { AgentName } from '../types'

export type Phase = 'idle' | 'live' | 'spoke'

/**
 * One agent's station. The body renders in that agent's own voice — a decree,
 * a count, a ledger line, a calendar note, or a letter — because the five
 * produce different kinds of output and should not all look like chat bubbles.
 *
 * The voice also sets the station's *shape*, not just its type. A decree runs
 * full width as a statement; the three data voices sit in a two-column rail;
 * a letter is inset and narrow. That is what keeps the floor from reading as
 * five identical rows stacked down the page.
 */
export function Station({ name, phase, said, tools, blocked, onClose }: {
  name: AgentName
  phase: Phase
  said: string
  tools: string[]
  blocked: string[]
  onClose?: () => void
}) {
  const a = AGENTS[name]
  const led = phase === 'live' ? 'working' : phase === 'spoke' ? 'reported' : 'idle'

  return (
    <div
      className={`station v-${a.voice} ${phase}`}
      style={{ ['--hue' as string]: a.hue, ['--glow' as string]: a.glow }}
    >
      <div className="srow">
        <div className="rail">
          <div className="sname">{a.label}</div>
          <div className="srole">{a.role}</div>
        </div>
        <div className="led">{led}</div>
        {onClose && (
          <button className="s-back" onClick={onClose}>← all five</button>
        )}
      </div>

      {phase === 'live' && !said && (
        <div className="dots"><i /><i /><i /></div>
      )}

      {said && <div className={`say ${a.voice}`}>{said}</div>}

      {(tools.length > 0 || blocked.length > 0) && (
        <div className="tools">
          {tools.map((t, i) => <span className="tool" key={`${t}${i}`}>{t}</span>)}
          {blocked.map((t, i) => (
            <span className="tool blocked" key={`b${t}${i}`} title="agents may not spend">
              {t}
            </span>
          ))}
        </div>
      )}
    </div>
  )
}
