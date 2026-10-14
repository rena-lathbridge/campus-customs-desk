/** Every call the board makes to the Problem 7 backend. */

import type { AgentEvent, Approval, BossDecision, Cash, RunResult, Ticket } from './types'

export const API = 'http://localhost:8000'

async function json<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    headers: { 'content-type': 'application/json' },
    ...init,
  })
  if (!res.ok) {
    let detail = res.statusText
    try { detail = (await res.json()).detail ?? detail } catch { /* keep statusText */ }
    throw new Error(detail)
  }
  return res.json() as Promise<T>
}

export const api = {
  health: () => json<{ ok: boolean; model: string; shop_date: string }>('/api/health'),

  tickets: () => json<{ tickets: Ticket[]; open: number; resolved: number; shop_date: string }>(
    '/api/tickets'),

  ticket: (id: number) => json<Ticket & { last_run?: { run_id: string;
    decision: BossDecision } | null }>(`/api/tickets/${id}`),

  runTicket: (id: number) => json<RunResult>(`/api/tickets/${id}/run`, {
    method: 'POST', body: JSON.stringify({ instruction: '' }),
  }),

  events: (since: number) => json<{ events: AgentEvent[]; latest_seq: number }>(
    `/api/events?since=${since}`),

  approvals: () => json<{ approvals: Approval[] }>('/api/approvals'),

  approve: (id: number, approved_by: string) =>
    json<{ ok: boolean; cash: Cash; ticket: Ticket; payment: Record<string, unknown> }>(
      `/api/approvals/${id}/approve`,
      { method: 'POST', body: JSON.stringify({ approved_by }) }),

  decline: (id: number, declined_by: string, reason = '') =>
    json<{ ok: boolean; approval: Approval }>(`/api/approvals/${id}/decline`, {
      method: 'POST', body: JSON.stringify({ declined_by, reason }),
    }),

  cash: () => json<Cash>('/api/cash'),

  reset: () => json<{ reset: boolean; cash: Cash; tickets: Ticket[] }>('/api/reset', {
    method: 'POST',
  }),
}
