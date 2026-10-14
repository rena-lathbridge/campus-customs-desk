import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { api } from './api'
import { AGENTS, ORDER, isAgent } from './agents'
import { ApprovalForm } from './components/ApprovalForm'
import { Docket } from './components/Docket'
import { Plate } from './components/Plate'
import { Station, type Phase } from './components/Station'
import { Till } from './components/Till'
import { Wire } from './components/Wire'
import type { AgentEvent, AgentName, Approval, BossDecision, Cash, Ticket } from './types'

type View = 'team' | 'decision' | 'reply' | 'risks'
import './theme.css'

interface Seen { phase: Phase; said: string; tools: string[]; blocked: string[] }

/** Fold the event stream into per-agent state: who is working, who has spoken. */
function readStations(events: AgentEvent[], running: boolean): Record<AgentName, Seen> {
  const base = {} as Record<AgentName, Seen>
  ORDER.forEach(n => { base[n] = { phase: 'idle', said: '', tools: [], blocked: [] } })

  for (const e of events) {
    const who = isAgent(e.agent) ? e.agent : null
    if (!who) continue
    const s = base[who]
    if (e.kind === 'agent_started' || e.kind === 'run_started') {
      if (s.phase !== 'spoke') s.phase = 'live'
    } else if (e.kind === 'agent_replied' || e.kind === 'decision') {
      s.phase = 'spoke'
      if (e.summary) s.said = e.summary
    } else if (e.kind === 'tool_call') {
      if (s.phase === 'idle') s.phase = 'live'
      const blocked = (e.detail as { blocked?: boolean })?.blocked
      const list = blocked ? s.blocked : s.tools
      if (!list.includes(e.tool)) list.push(e.tool)
    }
  }
  if (!running) ORDER.forEach(n => { if (base[n].phase === 'live') base[n].phase = 'spoke' })
  return base
}

export default function App() {
  const [tickets, setTickets] = useState<Ticket[]>([])
  const [picked, setPicked] = useState<number | null>(null)
  const [cash, setCash] = useState<Cash | null>(null)
  const [events, setEvents] = useState<AgentEvent[]>([])
  const [approvals, setApprovals] = useState<Approval[]>([])
  const [decision, setDecision] = useState<BossDecision | null>(null)
  const [running, setRunning] = useState(false)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')
  const [shopDate, setShopDate] = useState('')
  const [dropped, setDropped] = useState<number | null>(null)
  //: Which view of the selected ticket is open, and which agent inside it.
  //: Everything about a ticket lives behind a click — nothing is one long scroll.
  const [view, setView] = useState<View>('team')
  const [openAgent, setOpenAgent] = useState<AgentName | null>(null)
  const seq = useRef(0)

  const refresh = useCallback(async () => {
    const [t, c, a] = await Promise.all([api.tickets(), api.cash(), api.approvals()])
    setTickets(t.tickets); setShopDate(t.shop_date); setCash(c); setApprovals(a.approvals)
  }, [])

  useEffect(() => { refresh().catch(e => setErr(String(e.message ?? e))) }, [refresh])

  // Picking a ticket loads whatever the team last decided about it, so the
  // "what each agent did" summary survives a page reload.
  useEffect(() => {
    setView('team'); setOpenAgent(null)
    if (picked == null) { setDecision(null); return }
    let alive = true
    api.ticket(picked)
      .then(t => { if (alive) setDecision(t.last_run?.decision ?? null) })
      .catch(() => { if (alive) setDecision(null) })
    return () => { alive = false }
  }, [picked])

  // Poll the wire fast while a run is in flight, slowly when idle.
  useEffect(() => {
    let alive = true
    const tick = async () => {
      try {
        const { events: fresh, latest_seq } = await api.events(seq.current)
        if (!alive) return
        if (fresh.length) { seq.current = latest_seq; setEvents(p => [...p, ...fresh]) }
      } catch { /* backend asleep; try again next tick */ }
    }
    const id = setInterval(tick, running ? 700 : 3000)
    tick()
    return () => { alive = false; clearInterval(id) }
  }, [running])

  const run = async () => {
    if (picked == null) return
    setRunning(true); setErr('')
    try {
      const res = await api.runTicket(picked)
      setDecision(res.decision)
      await refresh()
    } catch (e) { setErr(String((e as Error).message)) }
    finally { setRunning(false) }
  }

  const approve = async (id: number, who: string) => {
    setBusy(true); setErr('')
    const before = cash?.checking_balance ?? 0
    try {
      const res = await api.approve(id, who)
      setCash(res.cash)
      setDropped(before - (res.cash.checking_balance ?? before))
      setTimeout(() => setDropped(null), 4200)
      await refresh()
    } catch (e) { setErr(String((e as Error).message)) }
    finally { setBusy(false) }
  }

  const decline = async (id: number, who: string) => {
    setBusy(true)
    try { await api.decline(id, who); await refresh() }
    catch (e) { setErr(String((e as Error).message)) }
    finally { setBusy(false) }
  }

  const reset = async () => {
    setBusy(true)
    try {
      await api.reset()
      setEvents([]); seq.current = 0; setDecision(null); setDropped(null); setErr('')
      await refresh()
    } catch (e) { setErr(String((e as Error).message)) }
    finally { setBusy(false) }
  }

  const ticketEvents = useMemo(
    () => events.filter(e => picked == null || e.ticket_id == null || e.ticket_id === picked),
    [events, picked])
  const stations = useMemo(() => readStations(ticketEvents, running), [ticketEvents, running])
  const current = tickets.find(t => t.id === picked) ?? null
  const pending = approvals.filter(a => a.ticket_id === picked)
  const resolvedCount = tickets.filter(t => t.resolved).length

  return (
    <div className="desk">
      <div className="topbar">
        <div className="brand">Campus <em>Customs</em><small>the desk · back office</small></div>
        <div className="spacer" />
        <div className="stat">shop date <b>{shopDate || '—'}</b></div>
        <div className="stat">tickets <b>{resolvedCount}/{tickets.length}</b> settled</div>
        <button className="btn ghost" onClick={reset} disabled={busy || running}>Reset day</button>
        <button className="btn pink" onClick={run} disabled={picked == null || running || busy}>
          {running ? 'Team working…' : picked == null ? 'Pick a ticket' : `Run team on #${picked}`}
        </button>
      </div>

      <div className="floor">
        <div className="col left">
          <h3 className="hdr">The spike</h3>
          {tickets.map(t => (
            <Docket key={t.id} ticket={t} selected={t.id === picked} onPick={setPicked} />
          ))}
        </div>

        <div className="col">
          <h3 className="hdr">The floor</h3>
          {err && <div className="banner">{err}</div>}
          {picked == null ? (
            <div className="empty"><span className="big">✦</span>
              Nobody's working yet. Pull a ticket off the spike to put the team on it.</div>
          ) : (
            <>
              {current && (
                <header className="opener">
                  <div className="opener-no">{current.id}</div>
                  <div className="opener-body">
                    <div className="kicker">{current.type.replace('_', ' ')}</div>
                    <h2 className="opener-title">{current.subject}</h2>
                    <div className="opener-who">{current.requester}</div>
                    {current.resolved && <div className="opener-mark">Settled</div>}
                  </div>
                </header>
              )}

              <nav className="views">
                {([['team', 'The team'], ['decision', 'The decision'],
                   ['reply', 'The reply'], ['risks', 'Risks']] as [View, string][])
                  .map(([v, label]) => (
                    <button key={v} className={view === v ? 'on' : ''}
                      onClick={() => { setView(v); setOpenAgent(null) }}
                      disabled={v !== 'team' && !decision}>
                      {label}
                    </button>
                  ))}
              </nav>

              {view === 'team' && (openAgent
                ? <Station name={openAgent} phase={stations[openAgent].phase}
                    said={stations[openAgent].said} tools={stations[openAgent].tools}
                    blocked={stations[openAgent].blocked}
                    onClose={() => setOpenAgent(null)} />
                : <div className="sheet">
                    {ORDER.map((n, i) => (
                      <Plate key={n} name={n} index={i} phase={stations[n].phase}
                        said={stations[n].said}
                        toolCount={stations[n].tools.length + stations[n].blocked.length}
                        onOpen={setOpenAgent} />
                    ))}
                  </div>
              )}

              {view === 'decision' && decision && (
                <div className="panel">
                  <p className="say decree">{decision.decision}</p>
                  <h4 className="panel-h">What each agent contributed</h4>
                  {decision.steps.length === 0 && (
                    <div className="sline"><span>The Boss settled this one without
                      delegating.</span></div>
                  )}
                  {decision.steps.map((s, i) => {
                    const a = isAgent(s.agent) ? AGENTS[s.agent] : null
                    return (
                      <div className="sline" key={i}>
                        <span className="pill" style={{ color: a?.hue ?? 'var(--muted)' }}>
                          {a?.label ?? s.agent}</span>
                        <span>{s.learned || s.asked}</span>
                      </div>
                    )
                  })}
                  {decision.rationale && (
                    <>
                      <h4 className="panel-h">Why</h4>
                      <p className="panel-p">{decision.rationale}</p>
                    </>
                  )}
                </div>
              )}

              {view === 'reply' && decision && (
                <figure className="pull">
                  <blockquote>{decision.reply_to_requester}</blockquote>
                  <figcaption>sent to {current?.requester}</figcaption>
                </figure>
              )}

              {view === 'risks' && decision && (
                <div className="panel">
                  <h4 className="panel-h">What this still costs</h4>
                  {decision.risks.length === 0 && (
                    <div className="sline"><span>None recorded.</span></div>
                  )}
                  {decision.risks.map((r, i) => (
                    <div className="sline" key={i}>
                      <span className="pill" style={{ color: 'var(--accent)' }}>
                        {String(i + 1).padStart(2, '0')}</span>
                      <span>{r}</span>
                    </div>
                  ))}
                  {decision.unresolved && (
                    <>
                      <h4 className="panel-h">Left open</h4>
                      <p className="panel-p">{decision.unresolved}</p>
                    </>
                  )}
                </div>
              )}
            </>
          )}
        </div>

        <div className="col right">
          <h3 className="hdr">The till</h3>
          <Till cash={cash} dropped={dropped} />
          {current && pending.length === 0 && current.resolved && (
            <div className="empty" style={{ padding: '26px 10px' }}>
              #{current.id} is settled. Nothing to approve.</div>
          )}
          {pending.map(a => (
            <ApprovalForm key={a.id} approval={a} busy={busy}
              onApprove={approve} onDecline={decline} />
          ))}
        </div>
      </div>

      <Wire events={events} live={running} />
    </div>
  )
}
