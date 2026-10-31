import { readFileSync } from "node:fs";

export function loadRegister(
  path = new URL("../AGENT-REGISTER.md", import.meta.url),
) {
  const rows = readFileSync(path, "utf8")
    .split(/\r?\n/)
    .filter((line) => line.startsWith("| spiffe://"));
  const list = (cell) =>
    cell
      .split(",")
      .map((s) => s.trim())
      .filter((s) => s && s !== "-");
  const register = new Map();
  for (const line of rows) {
    const cells = line.split("|").map((c) => c.trim());
    const [, name, owner, purpose, scopes, delegates, approvedBy, reviewDate] =
      cells;
    register.set(name, {
      name,
      owner,
      purpose,
      scopes: list(scopes),
      delegatesTo: list(delegates),
      approvedBy,
      reviewDate,
    });
  }
  return register;
}
