import { audit } from "./audit.mjs";

const revoked = new Map();

export function revokeAgent(agent, reason) {
  revoked.set(agent, { reason, at: new Date().toISOString() });
  audit.record({ event: "agent_revoked", outcome: "allow", agent, reason });
}

export const isRevoked = (agent) => revoked.has(agent);

export function clearRevocations() {
  revoked.clear();
}
