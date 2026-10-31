import { exchangeToken, makeActorAssertion, ORDER } from "./exchange.mjs";
import { SHOPPER } from "./issuer.mjs";

export function createShopperAgent({ order }) {
  async function tokenForOrderAgent(loginToken, scopes, orderId) {
    return exchangeToken({
      subjectToken: loginToken,
      actor: SHOPPER,
      actorAssertion: await makeActorAssertion(SHOPPER),
      audience: ORDER,
      scopes,
      orderId,
    });
  }

  async function buy(loginToken, { orderId, amount }) {
    const token = await tokenForOrderAgent(
      loginToken,
      ["order:create", "payment:charge"],
      orderId,
    );
    return order.placeOrder(token, { orderId, amount });
  }

  async function askRefund(loginToken, { orderId }) {
    const token = await tokenForOrderAgent(
      loginToken,
      ["refund:request"],
      orderId,
    );
    return order.requestRefund(token, { orderId });
  }

  return { buy, askRefund };
}
