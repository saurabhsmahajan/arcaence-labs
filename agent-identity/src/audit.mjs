import { randomUUID } from "node:crypto";
import { appendFileSync } from "node:fs";
import { decodeJwt } from "jose";

const events = [];

export const audit = {
  record(event) {
    const entry = {
      id: randomUUID(),
      time: new Date().toISOString(),
      ...event,
    };
    events.push(entry);
    return entry;
  },
  all: () => [...events],
  byTrace: (traceId) => events.filter((e) => e.traceId === traceId),
  clear: () => {
    events.length = 0;
  },
  saveTo(path) {
    for (const e of events) appendFileSync(path, JSON.stringify(e) + "\n");
  },
};

// Reads a token WITHOUT trusting it. Used only to label log entries.
export function peek(token) {
  try {
    return decodeJwt(token);
  } catch {
    return {};
  }
}
