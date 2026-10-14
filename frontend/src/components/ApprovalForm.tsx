import { useState } from 'react'
import type { Approval } from '../types'

const money = (n: number) =>
  `$${n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`

/**
 * The thing that makes the human the one who spends. The team can only ever
 * park a payment here; nothing moves until a name is typed and approve is hit.
 */
export function ApprovalForm({ approval, busy, onApprove, onDecline }: {
  approval: Approval
  busy: boolean
  onApprove: (id: number, who: string) => void
  onDecline: (id: number, who: string) => void
}) {
  const [who, setWho] = useState('')
  const ready = who.trim().length > 1 && !busy

  if (approval.status !== 'awaiting_approval') {
    return (
      <div className="approve">
        <div className="ahead">
          {approval.status === 'approved' ? 'Paid' :
           approval.status === 'declined' ? 'Declined' : 'Refused'}
        </div>
        <div className="awhat">{approval.what}</div>
        <div className="amt">{money(approval.amount)}</div>
        <div className="sigline">
          {approval.decided_by ? `signed — ${approval.decided_by}` : 'no signature'}
        </div>
      </div>
    )
  }

  return (
    <div className="approve">
      <div className="ahead">Awaiting a human</div>
      <div className="awhat">{approval.what}</div>
      <div className="amt">{money(approval.amount)}</div>
      <div className="note">
        The team prepared this but cannot pay it. Paying {approval.kind}
        {approval.ref_id != null ? ` #${approval.ref_id}` : ''} from {approval.account}.
      </div>
      <input
        value={who}
        onChange={e => setWho(e.target.value)}
        placeholder="Type your name to sign"
        onKeyDown={e => { if (e.key === 'Enter' && ready) onApprove(approval.id, who.trim()) }}
      />
      <div className="row">
        <button className="ok" disabled={!ready}
          onClick={() => onApprove(approval.id, who.trim())}>
          {busy ? 'Paying…' : 'Approve & pay'}
        </button>
        <button className="no" disabled={busy}
          onClick={() => onDecline(approval.id, who.trim() || 'unsigned')}>
          Decline
        </button>
      </div>
      <div className="sigline">authorised by ________________</div>
    </div>
  )
}
