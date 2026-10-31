import { readFileSync } from "node:fs";
import { loadRegister } from "../src/register.mjs";
import { diffRegister, overdueReviews } from "../src/review.mjs";

const baseline = JSON.parse(
  readFileSync(new URL("../register-approved.json", import.meta.url), "utf8"),
);
const register = loadRegister();
const findings = [
  ...diffRegister(baseline, register),
  ...overdueReviews(register),
];
console.log(findings.length ? findings : "no findings");
process.exitCode = findings.length ? 1 : 0;
