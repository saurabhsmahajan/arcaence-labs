import { mkdirSync, rmSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { audit } from "../src/audit.mjs";
import { issueLoginToken, SHOPPER } from "../src/issuer.mjs";
import {
  exchangeToken,
  makeActorAssertion,
  ORDER,
  PAYMENT,
} from "../src/exchange.mjs";
import { createPaymentAgent } from "../src/payment.mjs";
import { createOrderAgent } from "../src/order.mjs";
import { createShopperAgent } from "../src/shopper.mjs";
import { revokeAgent } from "../src/revocation.mjs";
import { computeMetrics } from "../src/metrics.mjs";
import { whoDidThis } from "../src/whodid.mjs";

audit.clear();
const payment = createPaymentAgent();
const order = createOrderAgent({ payment });
const shopper = createShopperAgent({ order });

async function attempt(label, fn) {
  try {
    await fn();
    console.log(`!! ${label}: SUCCEEDED (unexpected)`);
  } catch (err) {
    console.log(`refused  ${label}: ${err.message}`);
  }
}

const login = await issueLoginToken({
  customer: "sam",
  scopes: ["order:create", "payment:charge", "refund:request"],
});

console.log("--- normal activity");
console.log(await shopper.buy(login, { orderId: "1042", amount: 499 }));
console.log(await shopper.askRefund(login, { orderId: "1042" }));
console.log(await shopper.buy(login, { orderId: "1043", amount: 120 }));

console.log("--- attacks");
await attempt("shopper asks for a refund token", async () =>
  exchangeToken({
    subjectToken: login,
    actor: SHOPPER,
    actorAssertion: await makeActorAssertion(SHOPPER),
    audience: ORDER,
    scopes: ["payment:refund"],
    orderId: "1042",
  }),
);
await attempt("shopper skips the order agent", async () =>
  exchangeToken({
    subjectToken: login,
    actor: SHOPPER,
    actorAssertion: await makeActorAssertion(SHOPPER),
    audience: PAYMENT,
    scopes: ["payment:charge"],
    orderId: "1042",
  }),
);
await attempt("same order bought twice", () =>
  shopper.buy(login, { orderId: "1042", amount: 499 }),
);

console.log("--- revocation drill");
revokeAgent(ORDER, "incident drill");
await attempt("purchase after the order agent is revoked", () =>
  shopper.buy(login, { orderId: "1044", amount: 80 }),
);

console.log("--- metrics (lab data, synthetic)");
console.log(JSON.stringify(computeMetrics(audit.all()), null, 2));

console.log("--- who did this? order 1042");
console.log(JSON.stringify(whoDidThis(audit.all(), "1042"), null, 2));

const dir = new URL("../evidence/", import.meta.url);
mkdirSync(dir, { recursive: true });
const file = fileURLToPath(new URL("audit-demo.jsonl", dir));
rmSync(file, { force: true });
audit.saveTo(file);
console.log(
  `--- audit log saved: evidence/audit-demo.jsonl (${audit.all().length} events)`,
);
