import { useEffect, useRef } from 'react'
import type { AgentEvent } from '../types'

/** The paper wire along the bottom: every event, newest at the end. */
export function Wire({ events, live }: { events: AgentEvent[]; live: boolean }) {
  const end = useRef<HTMLDivElement>(null)
  useEffect(() => { end.current?.scrollIntoView({ behavior: 'smooth' }) }, [events.length])

  return (
    <div className="wire">
      <div className="wh">
        <i className={`pip${live ? ' on' : ''}`} />
        <span>the wire · {events.length} events</span>
      </div>
      <div className="feed">
        {events.length === 0 && (
          <div style={{ color: 'var(--faint)' }}>quiet. pick a ticket and run the team.</div>
        )}
        {events.map(e => (
          <div className="ln" key={e.seq}>
            <span className="t">{e.at.slice(11, 19)}</span>
            <span className={`k ${e.kind}`}>{e.kind}</span>
            <span className="m">
              {e.agent ? `${e.agent} — ` : ''}{e.tool ? `${e.tool} · ` : ''}{e.summary}
            </span>
          </div>
        ))}
        <div ref={end} />
      </div>
    </div>
  )
}
