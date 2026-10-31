import { SignJWT } from "jose";
import { randomUUID } from "node:crypto";
import { loadRegister } from "./register.mjs";
import { privateKey } from "./keys.mjs";
import { audit } from "./audit.mjs";

export const ISSUER = "spiffe://storefront.local/issuer";
export const SHOPPER = "spiffe://storefront.local/agents/shopper";
const LOGIN_TTL_SECONDS = 300;

export async function issueLoginToken({
  customer,
  scopes,
  audience = SHOPPER,
  register = loadRegister(),
}) {
  const traceId = randomUUID();
  const base = {
    event: "login_issued",
    traceId,
    customer: `customer:${customer}`,
    audience,
    requestedScopes: scopes,
  };
  const fail = (reason) => {
    audit.record({ ...base, outcome: "deny", reason });
    throw new Error(reason);
  };

  const entry = register.get(audience);
  if (!entry) fail(`audience not in register: ${audience}`);
  const notAllowed = scopes.filter((s) => !entry.scopes.includes(s));
  if (notAllowed.length > 0) {
    fail(`scope not in register for ${audience}: ${notAllowed.join(", ")}`);
  }

  const jti = randomUUID();
  const token = await new SignJWT({ scope: scopes.join(" "), trace: traceId })
    .setProtectedHeader({ alg: "EdDSA" })
    .setIssuer(ISSUER)
    .setSubject(`customer:${customer}`)
    .setAudience(audience)
    .setJti(jti)
    .setIssuedAt()
    .setExpirationTime(`${LOGIN_TTL_SECONDS}s`)
    .sign(privateKey("issuer"));
  audit.record({
    ...base,
    outcome: "allow",
    jti,
    lifetimeSeconds: LOGIN_TTL_SECONDS,
  });
  return token;
}
