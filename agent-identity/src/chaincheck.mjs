// Reads the audit log and reports any hop that carries more than its parent.
export function findWidening(events) {
  const granted = new Map();
  const problems = [];

  for (const e of events) {
    if (e.outcome !== "allow") continue;

    if (e.event === "login_issued") {
      granted.set(e.jti, { scopes: e.requestedScopes, orderId: undefined });
      continue;
    }
    if (e.event !== "token_exchanged") continue;

    const found = {
      traceId: e.traceId,
      jti: e.jti,
      actor: e.actor,
      audience: e.audience,
    };
    const parent = granted.get(e.parentJti);

    if (!parent) {
      problems.push({ type: "unknown_parent", ...found });
    } else {
      const wider = e.grantedScopes.filter((s) => !parent.scopes.includes(s));
      if (wider.length > 0) {
        problems.push({
          type: "scope_wider_than_parent",
          scopes: wider,
          ...found,
        });
      }
      if (parent.orderId && e.orderId && parent.orderId !== e.orderId) {
        problems.push({ type: "order_changed", ...found });
      }
      if (parent.orderId && !e.orderId) {
        problems.push({ type: "order_restriction_dropped", ...found });
      }
    }
    granted.set(e.jti, { scopes: e.grantedScopes, orderId: e.orderId });
  }
  return problems;
}
