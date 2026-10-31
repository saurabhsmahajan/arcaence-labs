import { readFileSync } from "node:fs";
import { createPrivateKey, createPublicKey } from "node:crypto";

const dir = new URL("../keys/", import.meta.url);

export const privateKey = (name) =>
  createPrivateKey(readFileSync(new URL(`${name}.private.pem`, dir)));

export const publicKey = (name) =>
  createPublicKey(readFileSync(new URL(`${name}.public.pem`, dir)));
