export function snapshotRegister(register) {
  const out = {};
  for (const [name, entry] of register) {
    out[name] = {
      scopes: [...entry.scopes].sort(),
      delegatesTo: [...entry.delegatesTo].sort(),
    };
  }
  return out;
}

// Compares the register with the snapshot the owner last approved.
export function diffRegister(baseline, current) {
  const findings = [];
  const now = snapshotRegister(current);
  for (const [name, cur] of Object.entries(now)) {
    const base = baseline[name];
    if (!base) {
      findings.push({ type: "agent_added", agent: name });
      continue;
    }
    for (const scope of cur.scopes.filter((s) => !base.scopes.includes(s))) {
      findings.push({ type: "scope_added", agent: name, scope });
    }
    for (const to of cur.delegatesTo.filter(
      (d) => !base.delegatesTo.includes(d),
    )) {
      findings.push({ type: "delegation_added", agent: name, to });
    }
  }
  for (const name of Object.keys(baseline)) {
    if (!now[name]) findings.push({ type: "agent_removed", agent: name });
  }
  return findings;
}

// Scopes in the register that nobody was granted, according to the audit log.
export function unusedScopes(register, events) {
  const used = new Map();
  const mark = (agent, scopes) => {
    const set = used.get(agent) ?? new Set();
    scopes.forEach((s) => set.add(s));
    used.set(agent, set);
  };
  for (const e of events) {
    if (e.outcome !== "allow") continue;
    if (e.event === "login_issued") mark(e.audience, e.requestedScopes);
    if (e.event === "token_exchanged") mark(e.audience, e.grantedScopes);
  }
  const findings = [];
  for (const [agent, entry] of register) {
    for (const scope of entry.scopes) {
      if (!used.get(agent)?.has(scope)) {
        findings.push({ type: "unused_scope", agent, scope });
      }
    }
  }
  return findings;
}

export function overdueReviews(register, today = new Date()) {
  const findings = [];
  for (const [agent, entry] of register) {
    if (new Date(entry.reviewDate) < today) {
      findings.push({
        type: "review_overdue",
        agent,
        reviewDate: entry.reviewDate,
      });
    }
  }
  return findings;
}
