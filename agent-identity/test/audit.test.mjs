import test from "node:test";
import assert from "node:assert/strict";
import { decodeJwt } from "jose";
import { audit } from "../src/audit.mjs";
import { createPaymentAgent } from "../src/payment.mjs";
import { createOrderAgent } from "../src/order.mjs";
import { createShopperAgent } from "../src/shopper.mjs";
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

test("one trace id ties the whole purchase together, in order", async () => {
  audit.clear();
  const { payment, shopper } = setup();
  await shopper.buy(await loginToken(), { orderId: "1042", amount: 499 });
  const trail = audit
    .byTrace(payment.ledger[0].traceId)
    .map((e) => `${e.event}:${e.outcome}`);
  assert.deepEqual(trail, [
    "login_issued:allow",
    "token_exchanged:allow",
    "token_exchanged:allow",
    "payment_charge:allow",
  ]);
});

test("a refused refund exchange is logged under the same trace", async () => {
  audit.clear();
  const login = await loginToken();
  const traceId = decodeJwt(login).trace;
  const orderTok = await orderToken(login);
  await assert.rejects(paymentToken(orderTok, ["payment:refund"]));
  const denied = audit.byTrace(traceId).filter((e) => e.outcome === "deny");
  assert.equal(denied.length, 1);
  assert.match(denied[0].reason, /wider than parent/);
});

test("a refused refund at the payment agent is logged too", async () => {
  audit.clear();
  const { payment } = setup();
  const login = await loginToken();
  const traceId = decodeJwt(login).trace;
  const payTok = await paymentToken(await orderToken(login));
  await assert.rejects(payment.refund(payTok, { orderId: "1042" }));
  const denied = audit
    .byTrace(traceId)
    .filter((e) => e.event === "payment_refund");
  assert.equal(denied.length, 1);
  assert.equal(denied[0].outcome, "deny");
});
