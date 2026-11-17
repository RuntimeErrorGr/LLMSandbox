import type {
  AgentAction,
  AgentRun,
  AgentRunSummary,
  Catalog,
  Detector,
  ImpactStart,
  ImpactTest,
  StatusCheck,
  ThreatBoard,
} from './types'

type Method = 'GET' | 'POST'

function describeError(detail: unknown, fallback: string): string {
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) return detail.map((item) => item?.msg ?? String(item)).join('; ')
  return fallback
}

async function request<T>(method: Method, url: string, body?: unknown): Promise<T> {
  const response = await fetch(url, {
    method,
    headers: body === undefined ? undefined : { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}))
    throw new Error(describeError(payload.detail, `${response.status} ${response.statusText}`))
  }
  return response.json() as Promise<T>
}

export const api = {
  status: () => request<StatusCheck[]>('GET', '/api/status'),
  catalog: () => request<Catalog>('GET', '/api/catalog'),
  leaderboard: () => request<ThreatBoard[]>('GET', '/api/leaderboard'),
  detector: (name: string) => request<Detector>('GET', `/api/detectors/${encodeURIComponent(name)}`),
  benchmark: (name: string) =>
    request<{ detector: string }>('POST', `/api/detectors/${encodeURIComponent(name)}/benchmark`),
  impactTests: () => request<ImpactTest[]>('GET', '/api/impact'),
  startImpact: (body: ImpactStart) => request<{ id: number }>('POST', '/api/impact', body),
  agentRuns: () => request<AgentRunSummary[]>('GET', '/api/agents/runs'),
  agentRun: (id: number) => request<AgentRun>('GET', `/api/agents/runs/${id}`),
  startAgentRun: (text: string) =>
    request<{ id: number }>('POST', '/api/agents/runs', { request: text }),
  agentAction: (id: number, action: AgentAction) =>
    request<{ id: number }>('POST', `/api/agents/runs/${id}/${action}`),
}
