import test from "node:test";
import assert from "node:assert/strict";
import {
  exchangeToken,
  makeActorAssertion,
  ORDER,
  PAYMENT,
} from "../src/exchange.mjs";
import { createPaymentAgent } from "../src/payment.mjs";
import { SHOPPER } from "../src/issuer.mjs";
import {
  loginToken,
  orderToken,
  paymentToken,
  freshPaymentToken,
} from "../test-support/helpers.mjs";

test("refund relay, layer 1: the issuer will not give the shopper a refund token", async () => {
  const login = await loginToken();
  await assert.rejects(
    exchangeToken({
      subjectToken: login,
      actor: SHOPPER,
      actorAssertion: await makeActorAssertion(SHOPPER),
      audience: ORDER,
      scopes: ["payment:refund"],
      orderId: "1042",
    }),
    /wider than parent/,
  );
});

test("refund relay, layer 2: the issuer will not give the order agent a refund token", async () => {
  const orderTok = await orderToken(await loginToken());
  await assert.rejects(
    paymentToken(orderTok, ["payment:refund"]),
    /wider than parent/,
  );
});

test("refund relay, layer 3: the payment agent refuses even with a valid charge token", async () => {
  const payment = createPaymentAgent();
  await assert.rejects(
    payment.refund(await freshPaymentToken(), { orderId: "1042" }),
    /missing scope: payment:refund/,
  );
});

test("skipped hop: the shopper cannot get a token addressed to the payment agent", async () => {
  await assert.rejects(
    exchangeToken({
      subjectToken: await loginToken(),
      actor: SHOPPER,
      actorAssertion: await makeActorAssertion(SHOPPER),
      audience: PAYMENT,
      scopes: ["payment:charge"],
      orderId: "1042",
    }),
    /may not delegate/,
  );
});

test("backwards hop: the order agent cannot hand authority back to the shopper", async () => {
  const orderTok = await orderToken(await loginToken());
  await assert.rejects(
    exchangeToken({
      subjectToken: orderTok,
      actor: ORDER,
      actorAssertion: await makeActorAssertion(ORDER),
      audience: SHOPPER,
      scopes: ["order:read"],
    }),
    /may not delegate/,
  );
});
