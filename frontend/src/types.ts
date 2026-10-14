/** Shapes the backend returns. Mirrors backend/models.py and the route payloads. */

export type AgentName =
  | 'boss' | 'inventory' | 'accounting' | 'facilities' | 'customer_service'

export interface Ticket {
  id: number
  type: string
  requester: string
  subject: string
  sku: string | null
  size: string | null
  qty: number | null
  lease_id: number | null
  invoice_id: number | null
  status: string
  notes: string | null
  created_at: string
  open: boolean
  resolved: boolean
  approvals?: Approval[]
}

export interface Fact {
  table: string
  field_name: string
  value: string
  means: string
}

export interface MoneyImpact {
  kind: 'invoice' | 'rent' | 'none'
  ref_id: number | null
  account: string
  what: string
  amount: number
  leaves_available: number | null
  affordable: boolean
  needs_human_approval: boolean
}

export interface SpecialistReply {
  answer: string
  facts: Fact[]
  actions_taken: string[]
  money: MoneyImpact | null
  blocked_by: string
  unknown: string
  consulted: string[]
}

export interface TeamStep {
  agent: string
  asked: string
  learned: string
}

export interface BossDecision {
  ticket_id: number | null
  decision: string
  reply_to_requester: string
  rationale: string
  steps: TeamStep[]
  facts: Fact[]
  money: MoneyImpact | null
  needs_human_approval: boolean
  risks: string[]
  unresolved: string
}

export type EventKind =
  | 'run_started' | 'agent_started' | 'agent_replied' | 'tool_call'
  | 'decision' | 'approval' | 'reset' | 'error'

export interface AgentEvent {
  seq: number
  at: string
  run_id: string
  ticket_id: number | null
  kind: EventKind
  agent: string
  tool: string
  summary: string
  detail: Record<string, unknown>
}

export interface Approval {
  id: number
  run_id: string
  ticket_id: number | null
  kind: string
  ref_id: number | null
  amount: number
  account: string
  what: string
  created_at: string
  status: 'awaiting_approval' | 'approved' | 'declined' | 'failed'
  decided_by: string
  decided_at: string
}

export interface Cash {
  as_of: string
  checking_balance: number | null
  accounts: { name: string; balance: number; date: string }[]
  rent_total: number
  open_invoices_total: number
  total_committed: number
  available_after_all_commitments: number
  payments: {
    id: number; kind: string; ref_id: number | null; amount: number
    account: string; paid_at: string; approved_by: string
  }[]
}

export interface RunResult {
  run_id: string
  ticket_id: number
  decision: BossDecision
  awaiting_approval: Approval | null
  ticket: Ticket
  events_through: number
}
