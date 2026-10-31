import { loadRegister } from "./register.mjs";

// Answers: who did this, for whom, through which agents, with what authority?
// Walks back from the charge: payment token -> order token -> login token.
export function whoDidThis(events, orderId, register = loadRegister()) {
  const charge = events.find(
    (e) =>
      e.event === "payment_charge" &&
      e.outcome === "allow" &&
      e.orderId === orderId,
  );
  if (!charge) return null;

  const issued = events.filter(
    (e) =>
      e.outcome === "allow" &&
      (e.event === "login_issued" || e.event === "token_exchanged"),
  );
  const chain = [];
  let current = issued.find((e) => e.jti === charge.jti);
  while (current) {
    chain.unshift(current);
    const parent = current.parentJti;
    current = parent ? issued.find((e) => e.jti === parent) : null;
  }

  const hops = chain.map((e) => ({
    step: e.event,
    actor: e.actor ?? "issuer",
    to: e.audience,
    scopes: e.grantedScopes ?? e.requestedScopes,
    lifetimeSeconds: e.lifetimeSeconds,
  }));
  const agents = [
    ...new Set(
      chain
        .flatMap((e) => [e.actor, e.audience])
        .filter((a) => register.has(a)),
    ),
  ];

  return {
    orderId,
    customer: charge.customer,
    traceId: charge.traceId,
    amount: charge.amount,
    chargedAt: charge.time,
    hops,
    owners: agents.map((a) => ({
      agent: a,
      owner: register.get(a).owner,
      approvedBy: register.get(a).approvedBy,
    })),
  };
}
