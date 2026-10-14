import type { Cash } from '../types'

const money = (n: number | null | undefined) =>
  n == null ? '—' : `$${n.toLocaleString('en-US', { minimumFractionDigits: 2,
    maximumFractionDigits: 2 })}`

/**
 * The till. The headline number is the checking balance; underneath, a meter
 * shows how little of it is actually free once rent and unpaid bills are taken
 * out — the distinction the whole shop turns on.
 */
export function Till({ cash, dropped }: { cash: Cash | null; dropped: number | null }) {
  if (!cash) return <div className="till"><div className="cap">Checking</div>
    <div className="amount">—</div></div>

  const bal = cash.checking_balance ?? 0
  const free = Math.max(0, cash.available_after_all_commitments)
  // Scale against everything the balance has to cover, so the three segments
  // stay in proportion instead of one clamping to a solid bar.
  const span = Math.max(cash.rent_total + cash.open_invoices_total + free, 0.01)
  const pct = (n: number) => (n / span) * 100
  const rentPct = pct(cash.rent_total)
  const billPct = pct(cash.open_invoices_total)
  const freePct = pct(free)
  const allClear = cash.rent_total === 0 && cash.open_invoices_total === 0

  return (
    <div className="till">
      <div className="cap">Checking · {cash.as_of}</div>
      <div className={`amount${dropped ? ' drop' : ''}`}>{money(bal)}</div>
      {dropped ? <div className="delta">−{money(dropped)} just paid</div> : null}

      <div className="meter">
        <span style={{ width: `${rentPct}%`, background: 'var(--sky)' }} />
        <span style={{ width: `${billPct}%`, background: 'var(--amber)' }} />
        <span style={{ width: `${freePct}%`, background: 'var(--mint)' }} />
      </div>
      <div className="legend">
        <span><i style={{ background: 'var(--sky)' }} />rent</span>
        <span><i style={{ background: 'var(--amber)' }} />bills</span>
        <span><i style={{ background: 'var(--mint)' }} />free</span>
      </div>

      <div className="bars">
        <div className="bar"><span>rent due</span><b>{money(cash.rent_total)}</b></div>
        <div className="bar"><span>unpaid bills</span><b>{money(cash.open_invoices_total)}</b></div>
        <div className="bar"><span>{allClear ? 'nothing owed · all free' : 'actually free'}</span>
          <b style={{ color: 'var(--mint)' }}>
            {money(cash.available_after_all_commitments)}</b></div>
      </div>

      {cash.payments.length > 0 && (
        <div className="receipt">
          <div className="rrow rhead"><span>paid</span><span>approved by</span></div>
          {cash.payments.slice(0, 5).map(p => (
            <div className="rrow" key={p.id}>
              <span>{p.kind} #{p.ref_id ?? '—'} · {money(p.amount)}</span>
              <span>{p.approved_by}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
