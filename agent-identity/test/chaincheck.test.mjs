import test from "node:test";
import assert from "node:assert/strict";
import { audit } from "../src/audit.mjs";
import { findWidening } from "../src/chaincheck.mjs";
import { createPaymentAgent } from "../src/payment.mjs";
import { createOrderAgent } from "../src/order.mjs";
import { createShopperAgent } from "../src/shopper.mjs";
import { loginToken } from "../test-support/helpers.mjs";

const login = (jti, scopes) => ({
  event: "login_issued",
  outcome: "allow",
  traceId: "t1",
  jti,
  requestedScopes: scopes,
});
const hop = (jti, parentJti, grantedScopes, orderId) => ({
  event: "token_exchanged",
  outcome: "allow",
  traceId: "t1",
  actor: "agent-a",
  audience: "agent-b",
  jti,
  parentJti,
  grantedScopes,
  orderId,
});

test("a normal purchase and a refund request show no widening", async () => {
  audit.clear();
  const payment = createPaymentAgent();
  const order = createOrderAgent({ payment });
  const shopper = createShopperAgent({ order });
  const token = await loginToken();
  await shopper.buy(token, { orderId: "1042", amount: 499 });
  await shopper.askRefund(token, { orderId: "1042" });
  assert.deepEqual(findWidening(audit.all()), []);
});

test("SIMULATED LEAK: a hop that grants more than its parent is flagged", () => {
  const events = [
    login("j0", ["order:read"]),
    hop("j1", "j0", ["order:read", "payment:refund"], "1042"),
  ];
  const found = findWidening(events);
  assert.equal(found.length, 1);
  assert.equal(found[0].type, "scope_wider_than_parent");
  assert.deepEqual(found[0].scopes, ["payment:refund"]);
});

test("SIMULATED LEAK: a token with no known parent is flagged", () => {
  const found = findWidening([
    hop("j1", "never-issued", ["order:read"], "1042"),
  ]);
  assert.equal(found.length, 1);
  assert.equal(found[0].type, "unknown_parent");
});

test("SIMULATED LEAK: dropping the order restriction is flagged", () => {
  const events = [
    login("j0", ["order:read"]),
    hop("j1", "j0", ["order:read"], "1042"),
    hop("j2", "j1", ["order:read"], undefined),
  ];
  const found = findWidening(events);
  assert.equal(found.length, 1);
  assert.equal(found[0].type, "order_restriction_dropped");
});
