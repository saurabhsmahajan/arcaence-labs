import test from "node:test";
import assert from "node:assert/strict";
import { createPaymentAgent } from "../src/payment.mjs";
import { createOrderAgent } from "../src/order.mjs";
import { createShopperAgent } from "../src/shopper.mjs";
import { ORDER } from "../src/exchange.mjs";
import { SHOPPER } from "../src/issuer.mjs";
import { loginToken } from "../test-support/helpers.mjs";

function setup() {
  const payment = createPaymentAgent();
  const order = createOrderAgent({ payment });
  const shopper = createShopperAgent({ order });
  return { payment, order, shopper };
}

test("happy path: Sam buys, and the ledger shows who acted for whom", async () => {
  const { payment, shopper } = setup();
  const result = await shopper.buy(await loginToken(), {
    orderId: "1042",
    amount: 499,
  });
  assert.equal(result.status, "charged");
  assert.equal(payment.ledger.length, 1);
  assert.equal(payment.ledger[0].customer, "customer:sam");
  assert.deepEqual(payment.ledger[0].actors, [ORDER, SHOPPER]);
});

test("a refund request is recorded for a human and no money moves", async () => {
  const { payment, order, shopper } = setup();
  const login = await loginToken();
  await shopper.buy(login, { orderId: "1042", amount: 499 });
  const result = await shopper.askRefund(login, { orderId: "1042" });
  assert.equal(result.status, "pending_human_approval");
  assert.equal(order.refundRequests.length, 1);
  assert.equal(payment.ledger.length, 1);
});

test("buying the same order twice is refused", async () => {
  const { shopper } = setup();
  const login = await loginToken();
  await shopper.buy(login, { orderId: "1042", amount: 499 });
  await assert.rejects(
    shopper.buy(login, { orderId: "1042", amount: 499 }),
    /already charged/,
  );
});

test("a refund request for an order that was never placed is refused", async () => {
  const { shopper } = setup();
  await assert.rejects(
    shopper.askRefund(await loginToken(), { orderId: "1042" }),
    /unknown order/,
  );
});
