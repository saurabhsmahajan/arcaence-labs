import test from "node:test";
import assert from "node:assert/strict";
import { audit } from "../src/audit.mjs";
import { loadRegister } from "../src/register.mjs";
import { issueLoginToken } from "../src/issuer.mjs";
import { PAYMENT } from "../src/exchange.mjs";
import { SHOPPER } from "../src/issuer.mjs";
import { createPaymentAgent } from "../src/payment.mjs";
import { createOrderAgent } from "../src/order.mjs";
import { createShopperAgent } from "../src/shopper.mjs";
import {
  snapshotRegister,
  diffRegister,
  unusedScopes,
  overdueReviews,
} from "../src/review.mjs";

test("an unchanged register shows no drift", () => {
  const register = loadRegister();
  assert.deepEqual(diffRegister(snapshotRegister(register), register), []);
});

test("SIMULATED CREEP: a scope added without re-approval is flagged", () => {
  const approved = snapshotRegister(loadRegister());
  const changed = loadRegister();
  changed.get(PAYMENT).scopes.push("payment:refund");
  assert.deepEqual(diffRegister(approved, changed), [
    { type: "scope_added", agent: PAYMENT, scope: "payment:refund" },
  ]);
});

test("SIMULATED CREEP: a new delegation path is flagged", () => {
  const approved = snapshotRegister(loadRegister());
  const changed = loadRegister();
  changed.get(SHOPPER).delegatesTo.push(PAYMENT);
  assert.deepEqual(diffRegister(approved, changed), [
    { type: "delegation_added", agent: SHOPPER, to: PAYMENT },
  ]);
});

test("scopes that were never granted are reported as unused", async () => {
  audit.clear();
  const payment = createPaymentAgent();
  const order = createOrderAgent({ payment });
  const shopper = createShopperAgent({ order });
  const login = await issueLoginToken({
    customer: "sam",
    scopes: ["order:create", "payment:charge", "refund:request"],
  });
  await shopper.buy(login, { orderId: "1042", amount: 499 });
  await shopper.askRefund(login, { orderId: "1042" });
  const found = unusedScopes(loadRegister(), audit.all())
    .map((f) => `${f.agent.split("/").pop()}:${f.scope}`)
    .sort();
  assert.deepEqual(found, [
    "order:order:read",
    "shopper:catalog:read",
    "shopper:order:read",
  ]);
});

test("reviews are overdue only after their date", () => {
  const register = loadRegister();
  assert.equal(overdueReviews(register, new Date("2026-11-01")).length, 0);
  assert.equal(overdueReviews(register, new Date("2027-02-01")).length, 3);
});
