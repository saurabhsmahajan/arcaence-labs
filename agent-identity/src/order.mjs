import { verifyAccess } from "./verify.mjs";
import {
  exchangeToken,
  makeActorAssertion,
  ORDER,
  PAYMENT,
} from "./exchange.mjs";

export function createOrderAgent({ payment }) {
  const orders = new Map();
  const refundRequests = [];

  async function placeOrder(token, { orderId, amount }) {
    await verifyAccess(token, {
      audience: ORDER,
      scope: "order:create",
      orderId,
    });
    const paymentToken = await exchangeToken({
      subjectToken: token,
      actor: ORDER,
      actorAssertion: await makeActorAssertion(ORDER),
      audience: PAYMENT,
      scopes: ["payment:charge"],
    });
    const receipt = await payment.charge(paymentToken, { orderId, amount });
    orders.set(orderId, { orderId, amount, status: "paid" });
    return receipt;
  }

  // Records the request for a human. Never moves money.
  async function requestRefund(token, { orderId }) {
    const claims = await verifyAccess(token, {
      audience: ORDER,
      scope: "refund:request",
      orderId,
    });
    if (!orders.has(orderId)) throw new Error(`unknown order: ${orderId}`);
    refundRequests.push({ orderId, customer: claims.sub });
    return { status: "pending_human_approval", orderId };
  }

  return { placeOrder, requestRefund, orders, refundRequests };
}
