import test from "node:test";
import assert from "node:assert/strict";
import { jwtVerify } from "jose";
import { issueLoginToken, ISSUER, SHOPPER } from "../src/issuer.mjs";
import { publicKey } from "../src/keys.mjs";

const scopes = ["catalog:read", "order:create", "order:read", "refund:request"];

test("Sam's login token verifies and carries the expected claims", async () => {
  const token = await issueLoginToken({ customer: "sam", scopes });
  const { payload } = await jwtVerify(token, publicKey("issuer"), {
    issuer: ISSUER,
    audience: SHOPPER,
  });
  assert.equal(payload.sub, "customer:sam");
  assert.equal(payload.scope, scopes.join(" "));
  assert.ok(payload.exp - payload.iat <= 300);
  assert.ok(payload.jti);
});

test("a scope that is not in the register is refused", async () => {
  await assert.rejects(
    issueLoginToken({ customer: "sam", scopes: ["payment:refund"] }),
    /not in register/,
  );
});

test("a token checked with the wrong audience is rejected", async () => {
  const token = await issueLoginToken({ customer: "sam", scopes });
  await assert.rejects(
    jwtVerify(token, publicKey("issuer"), {
      issuer: ISSUER,
      audience: "spiffe://storefront.local/agents/payment",
    }),
  );
});
