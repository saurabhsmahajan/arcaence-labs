import test from "node:test";
import assert from "node:assert/strict";
import { createPaymentAgent } from "../src/payment.mjs";
import { ORDER } from "../src/exchange.mjs";
import { SHOPPER } from "../src/issuer.mjs";
import { loginToken, freshPaymentToken } from "../test-support/helpers.mjs";

test("a valid chain token charges the order and the ledger records the chain", async () => {
  const payment = createPaymentAgent();
  const result = await payment.charge(await freshPaymentToken(), {
    orderId: "1042",
    amount: 499,
  });
  assert.equal(result.status, "charged");
  assert.equal(payment.ledger[0].customer, "customer:sam");
  assert.deepEqual(payment.ledger[0].actors, [ORDER, SHOPPER]);
});

test("a replayed token is refused", async () => {
  const payment = createPaymentAgent();
  const token = await freshPaymentToken();
  await payment.charge(token, { orderId: "1042", amount: 499 });
  await assert.rejects(
    payment.charge(token, { orderId: "1042", amount: 499 }),
    /already used/,
  );
});

test("the same order cannot be charged twice, even with a fresh token", async () => {
  const payment = createPaymentAgent();
  await payment.charge(await freshPaymentToken(), {
    orderId: "1042",
    amount: 499,
  });
  await assert.rejects(
    payment.charge(await freshPaymentToken(), { orderId: "1042", amount: 499 }),
    /already charged/,
  );
});

test("an amount above the hard limit is refused by the service", async () => {
  const payment = createPaymentAgent({ maxAmount: 5000 });
  await assert.rejects(
    payment.charge(await freshPaymentToken(), {
      orderId: "1042",
      amount: 6000,
    }),
    /outside limit/,
  );
});

test("a token for one order cannot charge another order", async () => {
  const payment = createPaymentAgent();
  await assert.rejects(
    payment.charge(await freshPaymentToken("1042"), {
      orderId: "2000",
      amount: 499,
    }),
    /not valid for order 2000/,
  );
});

test("the payment agent refuses a refund: no token carries that scope", async () => {
  const payment = createPaymentAgent();
  await assert.rejects(
    payment.refund(await freshPaymentToken(), { orderId: "1042" }),
    /missing scope: payment:refund/,
  );
});

test("Sam's own login token is rejected by the payment agent", async () => {
  const payment = createPaymentAgent();
  await assert.rejects(
    payment.charge(await loginToken(), { orderId: "1042", amount: 499 }),
  );
});
