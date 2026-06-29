import type { CreateSessionResponse } from './types';

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
