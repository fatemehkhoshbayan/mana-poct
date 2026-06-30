import type { CreateSessionResponse } from './types';

/**
 * Create a new QC session on the backend.
 *
 * `POST /api/sessions` — the response contains the `session_id` used for all
 * subsequent SSE message calls, the initial FSM state, and the greeting text.
 *
 * @param tenantId - Tenant identifier sent in the `X-Tenant-ID` header. Defaults to `'demo'`.
 * @returns The session creation response including `session_id`, initial FSM state, and greeting.
 * @throws If the server responds with a non-2xx status.
 */
export async function createSession(tenantId = 'demo'): Promise<CreateSessionResponse> {
  const res = await fetch('/api/sessions', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Tenant-ID': tenantId,
    },
    body: JSON.stringify({}),
  });
  if (!res.ok) throw new Error(`Failed to create session: ${res.statusText}`);
  return res.json() as Promise<CreateSessionResponse>;
}
