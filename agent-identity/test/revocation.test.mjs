import test from "node:test";
import assert from "node:assert/strict";
import { audit } from "../src/audit.mjs";
import { createPaymentAgent } from "../src/payment.mjs";
import { createOrderAgent } from "../src/order.mjs";
import { createShopperAgent } from "../src/shopper.mjs";
import { ORDER, PAYMENT } from "../src/exchange.mjs";
import { SHOPPER } from "../src/issuer.mjs";
import { revokeAgent, clearRevocations } from "../src/revocation.mjs";
import { loginToken, freshPaymentToken } from "../test-support/helpers.mjs";

function setup() {
  const payment = createPaymentAgent();
  const order = createOrderAgent({ payment });
  const shopper = createShopperAgent({ order });
  return { payment, order, shopper };
}

test("revoking the order agent kills a token it already holds", async () => {
  clearRevocations();
  const { payment } = setup();
  const token = await freshPaymentToken();
  revokeAgent(ORDER, "incident drill");
  await assert.rejects(
    payment.charge(token, { orderId: "1042", amount: 499 }),
    /agent revoked/,
  );
  clearRevocations();
});

test("a revoked agent cannot get new tokens", async () => {
  clearRevocations();
  const { shopper } = setup();
  const login = await loginToken();
  revokeAgent(SHOPPER, "incident drill");
  await assert.rejects(
    shopper.buy(login, { orderId: "1042", amount: 499 }),
    /agent revoked/,
  );
  clearRevocations();
});

test("a revoked payment agent refuses every charge", async () => {
  clearRevocations();
  const { payment } = setup();
  const token = await freshPaymentToken();
  revokeAgent(PAYMENT, "incident drill");
  await assert.rejects(
    payment.charge(token, { orderId: "1042", amount: 499 }),
    /agent revoked/,
  );
  clearRevocations();
});

test("a revocation is written to the audit log with its reason", async () => {
  clearRevocations();
  audit.clear();
  revokeAgent(ORDER, "incident drill");
  const events = audit.all().filter((e) => e.event === "agent_revoked");
  assert.equal(events.length, 1);
  assert.equal(events[0].agent, ORDER);
  assert.equal(events[0].reason, "incident drill");
  clearRevocations();
});
