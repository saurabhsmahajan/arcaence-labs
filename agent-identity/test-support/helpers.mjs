import { issueLoginToken, SHOPPER } from "../src/issuer.mjs";
import {
  exchangeToken,
  makeActorAssertion,
  ORDER,
  PAYMENT,
} from "../src/exchange.mjs";

export const LOGIN = [
  "catalog:read",
  "order:create",
  "order:read",
  "payment:charge",
  "refund:request",
];

export const loginToken = () =>
  issueLoginToken({ customer: "sam", scopes: LOGIN });

export async function orderToken(login, orderId = "1042") {
  return exchangeToken({
    subjectToken: login,
    actor: SHOPPER,
    actorAssertion: await makeActorAssertion(SHOPPER),
    audience: ORDER,
    scopes: ["order:create", "order:read", "refund:request", "payment:charge"],
    orderId,
  });
}

export async function paymentToken(orderTok, scopes = ["payment:charge"]) {
  return exchangeToken({
    subjectToken: orderTok,
    actor: ORDER,
    actorAssertion: await makeActorAssertion(ORDER),
    audience: PAYMENT,
    scopes,
  });
}

export async function freshPaymentToken(orderId = "1042") {
  return paymentToken(await orderToken(await loginToken(), orderId));
}
