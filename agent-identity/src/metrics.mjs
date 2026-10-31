import { findWidening } from "./chaincheck.mjs";

const DECISIONS = [
  "login_issued",
  "token_exchanged",
  "payment_charge",
  "payment_refund",
];
const pct = (n, d) => (d === 0 ? 100 : Math.round((n / d) * 1000) / 10);

export function computeMetrics(events) {
  const decisions = events.filter((e) => DECISIONS.includes(e.event));
  const denied = decisions.filter((e) => e.outcome === "deny");
  const traced = decisions.filter((e) => e.traceId && e.customer);
  const lifetimes = events
    .filter((e) => e.outcome === "allow" && e.lifetimeSeconds)
    .map((e) => e.lifetimeSeconds);

  const denialsByReason = {};
  for (const e of denied) {
    const key = String(e.reason)
      .replace(/spiffe:\/\/\S+\/agents\//g, "")
      .split(": ")[0];
    denialsByReason[key] = (denialsByReason[key] ?? 0) + 1;
  }

  const revocations = events
    .filter((e) => e.event === "agent_revoked")
    .map((r) => {
      const block = events.find(
        (e) =>
          e.outcome === "deny" &&
          String(e.reason).includes("agent revoked") &&
          String(e.reason).includes(r.agent) &&
          e.time >= r.time,
      );
      return {
        agent: r.agent,
        msToFirstBlock: block ? new Date(block.time) - new Date(r.time) : null,
      };
    });

  return {
    decisions: decisions.length,
    chainRecordedPct: pct(traced.length, decisions.length),
    maxTokenLifetimeSeconds: Math.max(0, ...lifetimes),
    wideningIncidents: findWidening(events).length,
    deniedPct: pct(denied.length, decisions.length),
    denialsByReason,
    revocations,
  };
}
