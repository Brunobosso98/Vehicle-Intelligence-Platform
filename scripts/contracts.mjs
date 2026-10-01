import { execFileSync } from "node:child_process";
import { readFileSync, writeFileSync } from "node:fs";
import openapiTS, { astToString } from "openapi-typescript";
import prettier from "prettier";
const raw = execFileSync(
  "apps/api/.venv/bin/python",
  ["scripts/export_openapi.py"],
  { encoding: "utf8" },
);
const schema = JSON.parse(raw);
const openapi = await prettier.format(JSON.stringify(schema), {
  parser: "json",
});
const types = await prettier.format(astToString(await openapiTS(schema)), {
  parser: "typescript",
});
for (const [path, value] of [
  ["packages/contracts/schemas/openapi.json", openapi],
  ["packages/contracts/generated/api.ts", types],
]) {
  if (process.argv.includes("--check")) {
    if (readFileSync(path, "utf8") !== value)
      throw new Error(`Generated contract drift: ${path}. Run make contracts.`);
  } else writeFileSync(path, value);
}
