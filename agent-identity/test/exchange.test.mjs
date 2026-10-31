import test from "node:test";
import assert from "node:assert/strict";
import { SignJWT, jwtVerify } from "jose";
import { issueLoginToken, ISSUER, SHOPPER } from "../src/issuer.mjs";
import {
  exchangeToken,
  makeActorAssertion,
  ORDER,
  PAYMENT,
} from "../src/exchange.mjs";
import { privateKey, publicKey } from "../src/keys.mjs";

const LOGIN = [
  "catalog:read",
  "order:create",
  "order:read",
  "payment:charge",
  "refund:request",
];

async function toOrder() {
  const login = await issueLoginToken({ customer: "sam", scopes: LOGIN });
  return exchangeToken({
    subjectToken: login,
    actor: SHOPPER,
    actorAssertion: await makeActorAssertion(SHOPPER),
    audience: ORDER,
    scopes: ["order:create", "order:read", "refund:request", "payment:charge"],
    orderId: "1042",
  });
}

async function toPayment(orderToken, scopes = ["payment:charge"]) {
  return exchangeToken({
    subjectToken: orderToken,
    actor: ORDER,
    actorAssertion: await makeActorAssertion(ORDER),
    audience: PAYMENT,
    scopes,
  });
}

const claims = (token, audience) =>
  jwtVerify(token, publicKey("issuer"), { issuer: ISSUER, audience }).then(
    (r) => r.payload,
  );

test("shopper to order: scope narrows, order is fixed, shopper is recorded", async () => {
  const c = await claims(await toOrder(), ORDER);
  assert.equal(c.sub, "customer:sam");
  assert.ok(!c.scope.split(" ").includes("catalog:read"));
  assert.equal(c.order_id, "1042");
  assert.equal(c.act.sub, SHOPPER);
});

test("order to payment: narrower again, chain recorded, never outlives parent", async () => {
  const orderToken = await toOrder();
  const parent = await claims(orderToken, ORDER);
  const c = await claims(await toPayment(orderToken), PAYMENT);
  assert.equal(c.scope, "payment:charge");
  assert.equal(c.order_id, "1042");
  assert.equal(c.act.sub, ORDER);
  assert.equal(c.act.act.sub, SHOPPER);
  assert.ok(c.exp <= parent.exp);
});

test("asking for a wider scope than the parent token is refused", async () => {
  const orderToken = await toOrder();
  await assert.rejects(
    toPayment(orderToken, ["payment:refund"]),
    /wider than parent/,
  );
  await assert.rejects(
    toPayment(orderToken, ["catalog:read"]),
    /wider than parent/,
  );
});

test("an agent cannot use a token that was issued to another agent", async () => {
  const login = await issueLoginToken({ customer: "sam", scopes: LOGIN });
  await assert.rejects(toPayment(login));
});

test("changing the order id down the chain is refused", async () => {
  const orderToken = await toOrder();
  await assert.rejects(
    exchangeToken({
      subjectToken: orderToken,
      actor: ORDER,
      actorAssertion: await makeActorAssertion(ORDER),
      audience: PAYMENT,
      scopes: ["payment:charge"],
      orderId: "9999",
    }),
    /order_id differs/,
  );
});

test("an agent cannot pretend to be another agent", async () => {
  const login = await issueLoginToken({ customer: "sam", scopes: LOGIN });
  const forged = await new SignJWT({})
    .setProtectedHeader({ alg: "EdDSA" })
    .setIssuer(SHOPPER)
    .setSubject(SHOPPER)
    .setAudience(ISSUER)
    .setIssuedAt()
    .setExpirationTime("60s")
    .sign(privateKey("payment"));
  await assert.rejects(
    exchangeToken({
      subjectToken: login,
      actor: SHOPPER,
      actorAssertion: forged,
      audience: ORDER,
      scopes: ["order:read"],
      orderId: "1042",
    }),
  );
});
