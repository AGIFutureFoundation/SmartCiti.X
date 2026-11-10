// verify.mjs — SmartCiti.X training scenarios: content + viewer-drift check.
// Run: node verify.mjs  (from this directory)
// - Validates every scenarios/*.json: required fields, unique ids, registry
//   strands only, valid tiers, steps reference stations defined in the file.
// - Validates scenarios.json index lists exactly the scenario files.
// - Deep-compares the data embedded in index.html (between the
//   __EMBEDDED_SCENARIOS__ / __END_EMBEDDED__ markers) against the JSON
//   files, so the file://-working viewer can never drift from the files.
// Exit 0 = all checks pass. Exit 1 = any failure. No network, no writes.
import { readFileSync, readdirSync } from "node:fs";

const failures = [];
const check = (ok, msg) => { if (!ok) failures.push(msg); };

const REGISTRY_STRANDS = new Set([
  "coordination", "documentation", "inspection", "layout", "leadership",
  "machines", "materials", "procedure", "safety", "tools", "troubleshooting",
]);
const TIERS = new Set(["fundamentals", "applied", "mastery"]);
const TRADEPATH_ZONES = new Set([
  "electrical", "solar", "hvac", "plumbing", "dental-operatory",
  "sterilization", "dental-reception", "outreach-hub", "operations-office",
  "volunteer-hall",
]);
const REQUIRED = ["id", "title", "audience", "description", "strands", "tiers",
  "stations", "steps", "sources", "deep_links", "halls", "sites", "mode"];

const files = readdirSync(new URL(".", import.meta.url))
  .filter((f) => f.endsWith(".json") && f !== "scenarios.json")
  .sort();
check(files.length === 6, `expected 6 scenario files, got ${files.length}: ${files.join(", ")}`);

const byId = new Map();
for (const f of files) {
  let sc;
  try {
    sc = JSON.parse(readFileSync(new URL(`./${f}`, import.meta.url), "utf8"));
  } catch (e) {
    failures.push(`${f}: invalid JSON (${e.message})`);
    continue;
  }
  for (const r of REQUIRED) check(r in sc, `${f}: missing required field ${r}`);
  if (byId.has(sc.id)) failures.push(`${f}: duplicate scenario id ${sc.id}`);
  byId.set(sc.id, sc);
  check(sc.id === f.replace(/\.json$/, ""), `${f}: id ${sc.id} does not match filename`);
  check(Array.isArray(sc.strands) && sc.strands.length > 0, `${f}: no strands`);
  for (const s of sc.strands ?? []) check(REGISTRY_STRANDS.has(s), `${f}: strand ${s} is not a registry strand`);
  for (const t of sc.tiers ?? []) check(TIERS.has(t), `${f}: tier ${t} is not a valid tier`);
  check(sc.steps?.length === 5, `${f}: expected 5 steps, got ${sc.steps?.length}`);
  const stationIds = new Set((sc.stations ?? []).map((s) => s.id));
  check(stationIds.size === (sc.stations ?? []).length, `${f}: duplicate station ids`);
  for (const step of sc.steps ?? []) {
    check(stationIds.has(step.stationId), `${f}: step references unknown station ${step.stationId}`);
    check(typeof step.action === "string" && step.action.length > 0, `${f}: step missing action`);
    check(typeof step.check === "string" && step.check.length > 0, `${f}: step missing check`);
  }
  const tl = sc.deep_links?.tradepath_zone;
  if (tl !== null && tl !== undefined) {
    const m = /^\/?\?zone=([a-z-]+)/.exec(tl);
    check(m !== null && TRADEPATH_ZONES.has(m[1]), `${f}: tradepath_zone link ${tl} is not a known TradePath zone`);
  }
  check(sc.halls?.mapped_hall === null, `${f}: mapped_hall must be null (no hall mapping verified)`);
  for (const site of ["louisiana", "indiana"]) {
    check(typeof sc.sites?.[site] === "string" && sc.sites[site].includes("no site, city, or address"),
      `${f}: sites.${site} must state no site/city/address named`);
  }
  check(!JSON.stringify(sc).match(/partner|incorporated|funded|customer/i) || JSON.stringify(sc).includes("not a partner"),
    `${f}: unexpected partner/incorporation claim`);
}

// Index lists exactly the scenario files.
const index = JSON.parse(readFileSync(new URL("./scenarios.json", import.meta.url), "utf8"));
const indexIds = (index.scenarios ?? []).map((s) => s.id).sort();
check(JSON.stringify(indexIds) === JSON.stringify([...byId.keys()].sort()),
  `scenarios.json ids [${indexIds}] do not match files [${[...byId.keys()].sort()}]`);
for (const entry of index.scenarios ?? []) {
  check(entry.file === `${entry.id}.json`, `index: file for ${entry.id} should be ${entry.id}.json`);
  check(entry.deepLink === `index.html?scenario=${entry.id}`, `index: deepLink for ${entry.id} is wrong`);
}

// Embedded viewer data matches the JSON files exactly.
const viewer = readFileSync(new URL("./index.html", import.meta.url), "utf8");
const m = /\/\*__EMBEDDED_SCENARIOS__\*\/([\s\S]*?)\/\*__END_EMBEDDED__\*\//.exec(viewer);
check(m !== null, "index.html: embedded-scenarios markers not found");
if (m !== null) {
  let embedded;
  try {
    // Captured text ends with the statement semicolon after the array.
    embedded = JSON.parse(m[1].trim().replace(/;\s*$/, ""));
  } catch (e) {
    failures.push(`index.html: embedded scenarios are not valid JSON (${e.message})`);
  }
  if (embedded) {
    check(Array.isArray(embedded) && embedded.length === byId.size,
      `index.html: embedded ${embedded?.length} scenarios, files have ${byId.size}`);
    for (const sc of embedded ?? []) {
      const file = byId.get(sc.id);
      check(file !== undefined, `index.html: embedded unknown scenario ${sc.id}`);
      if (file) {
        check(JSON.stringify(sc) === JSON.stringify(file),
          `index.html: embedded ${sc.id} differs from ${sc.id}.json`);
      }
    }
  }
}

// Viewer inline JS parses.
const scripts = [...viewer.matchAll(/<script>([\s\S]*?)<\/script>/g)].map((x) => x[1]);
check(scripts.length === 1, `index.html: expected 1 inline script, got ${scripts.length}`);
for (const [i, src] of scripts.entries()) {
  try {
    new (await import("node:vm")).Script(src);
  } catch (e) {
    failures.push(`index.html: inline script ${i} does not parse (${e.message})`);
  }
}
check(viewer.includes('get("scenario")'), "index.html: no ?scenario= deep-link support found");
check(viewer.includes("Demo mode"), "index.html: missing demo-mode banner");
check(viewer.includes("not incorporated"), "index.html: missing proposed/not-incorporated banner");

if (failures.length) {
  console.error("\nFAILURES:");
  for (const f of failures) console.error(" -", f);
  process.exit(1);
}
console.log(`scenarios: ${byId.size} files, index + viewer embedded copy all match.`);
console.log("All checks passed.");
