import { verifyAccess, actorChain } from "./verify.mjs";
import { PAYMENT } from "./exchange.mjs";
import { audit, peek } from "./audit.mjs";

export function createPaymentAgent({ maxAmount = 5000 } = {}) {
  const charged = new Set();
  const usedTokens = new Set();
  const ledger = [];

  async function chargeCore(token, { orderId, amount }) {
    const claims = await verifyAccess(token, {
      audience: PAYMENT,
      scope: "payment:charge",
      orderId,
    });
    if (usedTokens.has(claims.jti)) throw new Error("token already used");
    if (!Number.isFinite(amount) || amount <= 0 || amount > maxAmount) {
      throw new Error(`amount outside limit: ${amount}`);
    }
    if (charged.has(orderId))
      throw new Error(`order already charged: ${orderId}`);
    usedTokens.add(claims.jti);
    charged.add(orderId);
    ledger.push({
      type: "charge",
      orderId,
      amount,
      customer: claims.sub,
      traceId: claims.trace,
      actors: actorChain(claims),
    });
    return { status: "charged", orderId, amount };
  }

  async function refundCore(token, { orderId }) {
    await verifyAccess(token, {
      audience: PAYMENT,
      scope: "payment:refund",
      orderId,
    });
    throw new Error("refunds need human approval");
  }

  async function decide(action, token, details, run) {
    const seen = peek(token);
    const base = {
      event: `payment_${action}`,
      service: PAYMENT,
      traceId: seen.trace,
      customer: seen.sub,
      jti: seen.jti,
      orderId: details.orderId,
    };
    try {
      const result = await run();
      audit.record({ ...base, outcome: "allow", amount: details.amount });
      return result;
    } catch (err) {
      audit.record({ ...base, outcome: "deny", reason: err.message });
      throw err;
    }
  }

  const charge = (token, details) =>
    decide("charge", token, details, () => chargeCore(token, details));
  const refund = (token, details) =>
    decide("refund", token, details, () => refundCore(token, details));

  return { charge, refund, ledger };
}
