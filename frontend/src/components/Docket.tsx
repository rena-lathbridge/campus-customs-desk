import type { Ticket } from '../types'

/** One ticket, drawn as an index card on the spike. Resolved ones get stamped. */
export function Docket({ ticket, selected, onPick }: {
  ticket: Ticket
  selected: boolean
  onPick: (id: number) => void
}) {
  const tags = [
    ticket.sku, ticket.size && `size ${ticket.size}`,
    ticket.qty != null && `qty ${ticket.qty}`,
    ticket.invoice_id && `inv ${ticket.invoice_id}`,
    ticket.lease_id && `lease ${ticket.lease_id}`,
  ].filter(Boolean) as string[]

  return (
    <button
      className={`docket${selected ? ' on' : ''}${ticket.resolved ? ' done' : ''}`}
      onClick={() => onPick(ticket.id)}
    >
      <div className="no">#{ticket.id} · {ticket.type.replace('_', ' ')}</div>
      <div className="subj">{ticket.subject}</div>
      <div className="who">{ticket.requester}</div>
      {ticket.notes && <div className="ask">“{ticket.notes}”</div>}
      {tags.length > 0 && (
        <div className="tags">{tags.map(t => <span className="tag" key={t}>{t}</span>)}</div>
      )}
      {ticket.resolved && <div className="stamp">SETTLED</div>}
    </button>
  )
}
