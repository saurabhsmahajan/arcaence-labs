import { writeFileSync } from "node:fs";
import { loadRegister } from "../src/register.mjs";
import { snapshotRegister } from "../src/review.mjs";

const snapshot = snapshotRegister(loadRegister());
writeFileSync(
  new URL("../register-approved.json", import.meta.url),
  JSON.stringify(snapshot, null, 2) + "\n",
);
console.log("approved register snapshot written");
