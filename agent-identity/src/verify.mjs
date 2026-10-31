import { jwtVerify } from "jose";
import { ISSUER } from "./issuer.mjs";
import { publicKey } from "./keys.mjs";
import { isRevoked } from "./revocation.mjs";

// Flattens the nested act claim into a list, newest actor first.
export function actorChain(claims) {
  const out = [];
  let a = claims.act;
  while (a) {
    out.push(a.sub);
    a = a.act;
  }
  return out;
}

// Every service runs this on every token it receives.
export async function verifyAccess(token, { audience, scope, orderId }) {
  const { payload } = await jwtVerify(token, publicKey("issuer"), {
    issuer: ISSUER,
    audience,
  });
  const revoked = [audience, ...actorChain(payload)].find(isRevoked);
  if (revoked) throw new Error(`agent revoked: ${revoked}`);
  if (!payload.scope.split(" ").includes(scope)) {
    throw new Error(`missing scope: ${scope}`);
  }
  if (orderId && payload.order_id !== orderId) {
    throw new Error(`token is not valid for order ${orderId}`);
  }
  return payload;
}
