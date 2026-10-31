import { generateKeyPairSync } from "node:crypto";
import { mkdirSync, writeFileSync, existsSync } from "node:fs";

const names = ["issuer", "shopper", "order", "payment"];
mkdirSync("keys", { recursive: true });

for (const name of names) {
  const priv = `keys/${name}.private.pem`;
  const pub = `keys/${name}.public.pem`;
  if (existsSync(priv)) {
    console.log(`skip ${name} (already exists)`);
    continue;
  }
  const { publicKey, privateKey } = generateKeyPairSync("ed25519");
  writeFileSync(priv, privateKey.export({ type: "pkcs8", format: "pem" }));
  writeFileSync(pub, publicKey.export({ type: "spki", format: "pem" }));
  console.log(`created ${name}`);
}
