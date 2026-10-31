import test from "node:test";
import assert from "node:assert/strict";
import { audit } from "../src/audit.mjs";
import { computeMetrics } from "../src/metrics.mjs";
import { whoDidThis } from "../src/whodid.mjs";
import { createPaymentAgent } from "../src/payment.mjs";
import { createOrderAgent } from "../src/order.mjs";
import { createShopperAgent } from "../src/shopper.mjs";
import { ORDER } from "../src/exchange.mjs";
import { SHOPPER } from "../src/issuer.mjs";
import { revokeAgent, clearRevocations } from "../src/revocation.mjs";
import {
  loginToken,
  orderToken,
  paymentToken,
} from "../test-support/helpers.mjs";

function setup() {
  const payment = createPaymentAgent();
  const order = createOrderAgent({ payment });
  const shopper = createShopperAgent({ order });
  return { payment, order, shopper };
}

test("metrics for a clean purchase", async () => {
  audit.clear();
  const { shopper } = setup();
  await shopper.buy(await loginToken(), { orderId: "1042", amount: 499 });
  const m = computeMetrics(audit.all());
  assert.equal(m.chainRecordedPct, 100);
  assert.equal(m.wideningIncidents, 0);
  assert.equal(m.deniedPct, 0);
  assert.ok(m.maxTokenLifetimeSeconds <= 300);
});

test("a denied attempt shows up in the denied rate and its reason", async () => {
  audit.clear();
  const login = await loginToken();
  const orderTok = await orderToken(login);
  await assert.rejects(paymentToken(orderTok, ["payment:refund"]));
  const m = computeMetrics(audit.all());
  assert.ok(m.deniedPct > 0);
  assert.equal(m.denialsByReason["scope wider than parent token"], 1);
});

test("time from revoking an agent to its first blocked request is measured", async () => {
  clearRevocations();
  audit.clear();
  const { shopper } = setup();
  const login = await loginToken();
  revokeAgent(ORDER, "drill");
  await assert.rejects(
    shopper.buy(login, { orderId: "1042", amount: 499 }),
    /agent revoked/,
  );
  const m = computeMetrics(audit.all());
  assert.equal(m.revocations[0].agent, ORDER);
  assert.equal(typeof m.revocations[0].msToFirstBlock, "number");
  clearRevocations();
});

test("who-did-this names the customer, the chain and the owners", async () => {
  audit.clear();
  const { shopper } = setup();
  await shopper.buy(await loginToken(), { orderId: "1042", amount: 499 });
  const report = whoDidThis(audit.all(), "1042");
  assert.equal(report.customer, "customer:sam");
  assert.equal(report.amount, 499);
  assert.equal(report.hops.length, 3);
  assert.deepEqual(report.hops.map((h) => h.actor).slice(1), [SHOPPER, ORDER]);
  assert.equal(report.owners.length, 3);
  assert.ok(report.owners.every((o) => o.owner === "Saurabh Mahajan"));
  assert.equal(whoDidThis(audit.all(), "9999"), null);
});
