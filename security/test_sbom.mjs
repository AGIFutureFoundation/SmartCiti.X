/**
 * SBOM tests. The bill of materials is a claim about bytes in the tree; every
 * check here holds a claim to the bytes as they are right now.
 */
import assert from 'node:assert/strict';
import { createHash } from 'node:crypto';
import { readFileSync, readdirSync, statSync } from 'node:fs';
import { join, relative } from 'node:path';
import { fileURLToPath } from 'node:url';

const HERE = fileURLToPath(new URL('.', import.meta.url));
const ROOT = join(HERE, '..');
const VENDOR = join(ROOT, 'web', 'vendor');
let n = 0; const ok = (m) => { n++; console.log(`  ok  ${m}`); };
const sha = (buf) => createHash('sha256').update(buf).digest('hex');
const prop = (o, name) => (o.properties ?? []).find((p) => p.name === name)?.value;

const doc = JSON.parse(readFileSync(join(HERE, 'registry', 'sbom.cdx.json'), 'utf8'));

{
  assert.equal(doc.bomFormat, 'CycloneDX');
  assert.equal(doc.specVersion, '1.5');
  assert.equal(doc.metadata.component.type, 'application');
  const manifest = JSON.parse(readFileSync(join(ROOT, 'pack', 'manifest.json'), 'utf8'));
  assert.equal(doc.metadata.component.version, manifest.pack_version, 'the bundle version is the pack version');
  assert.equal(doc.metadata.timestamp, undefined, 'no timestamp: the same tree must build the same document');
  ok('the document parses as CycloneDX 1.5 and describes this bundle at the pack version');
}

{
  const src = readFileSync(join(HERE, 'build_sbom.py'));
  assert.equal(prop(doc.metadata, 'smartcitix:source_stamp'), sha(src).slice(0, 16),
    'the SBOM was built by a different build_sbom.py than the one in the tree — rebuild it');
  ok('the source stamp matches the builder in the tree');
}

const walk = (dir) => readdirSync(dir).flatMap((f) => {
  const p = join(dir, f);
  return statSync(p).isDirectory() ? walk(p) : [p];
});
const vendored = walk(VENDOR).map((p) => 'web/vendor/' + relative(VENDOR, p).split('\\').join('/')).sort();
const listed = doc.components.map((c) => c['bom-ref']).sort();

{
  assert.deepEqual(listed, vendored,
    'the SBOM must list every file under web/vendor/ and nothing else');
  assert.ok(vendored.length >= 2, 'the vendor tree is not empty');
  ok(`the SBOM lists exactly the ${vendored.length} files under web/vendor/ — no more, no fewer`);
}

const SPDX = new Set(['MIT', 'BSD-3-Clause']);
const PURLS = { three: 'pkg:npm/three@0.160.0', 'maplibre-gl': 'pkg:npm/maplibre-gl@4.7.1' };

for (const c of doc.components) {
  const bytes = readFileSync(join(ROOT, c['bom-ref']));
  const text = bytes.toString('utf8');
  assert.equal(c.type, 'library');
  assert.equal(c.hashes.length, 1);
  assert.equal(c.hashes[0].alg, 'SHA-256');
  assert.equal(c.hashes[0].content, sha(bytes), `${c['bom-ref']}: hash does not match the file bytes`);
  assert.ok(SPDX.has(c.licenses[0].license.id), `${c['bom-ref']}: licence is not an SPDX id we recognise`);
  assert.ok(c.purl === PURLS[c.name] || c.purl.startsWith(PURLS[c.name] + '#'),
    `${c['bom-ref']}: purl ${c.purl} is not ${PURLS[c.name]}`);
  assert.ok(c.purl.includes(`@${c.version}`), 'purl and version agree');
  const ev = prop(c, 'smartcitix:version_evidence');
  assert.ok(ev, 'every component says what its version rests on');
  if (/^no version string/.test(ev)) {
    assert.ok(!text.includes(c.version), `${c['bom-ref']}: claims no version string but contains one`);
  } else {
    assert.ok(text.includes(ev), `${c['bom-ref']}: version evidence "${ev}" is not in the file`);
    const digits = c.name === 'three' ? c.version.split('.')[1] : c.version;
    assert.ok(ev.includes(digits), `${c['bom-ref']}: evidence "${ev}" does not carry version ${c.version}`);
  }
  const banner = c.evidence.copyright[0]?.text;
  const lic = prop(c, 'smartcitix:licence_evidence');
  if (banner) {
    assert.ok(text.startsWith(banner) || text.includes(banner), `${c['bom-ref']}: banner is not in the file`);
    assert.ok(/license/i.test(banner), 'the banner actually speaks of a licence');
    assert.ok(banner.includes(c.licenses[0].license.id) || /3-Clause BSD/.test(banner),
      `${c['bom-ref']}: the banner does not name the licence the SBOM claims`);
  } else {
    assert.ok(/^no licence banner in this file/.test(lic),
      `${c['bom-ref']}: no banner recorded and no statement of what the licence rests on`);
    assert.ok(!/@license|SPDX-License-Identifier/.test(text.slice(0, 2000)),
      `${c['bom-ref']}: the file does carry a banner the SBOM failed to record`);
  }
  assert.ok(c.externalReferences.some((r) => r.type === 'vcs') && c.externalReferences.some((r) => r.type === 'license'));
}
ok('every hash matches the file bytes right now, every licence is an SPDX id, every purl is upstream\'s');
ok('every version claim is backed by a version string found verbatim in a vendored file');
ok('every licence claim is backed by the banner in the file — or says plainly that the file has none');

{
  const ml = doc.components.filter((c) => c.name === 'maplibre-gl');
  assert.ok(ml.length >= 1);
  for (const c of ml) {
    assert.match(prop(c, 'smartcitix:licence_text'), /not vendored and not fetched/,
      'the BSD text is a URL we cannot fetch at build; the SBOM must not pretend to carry it');
  }
  ok('no licence text is invented: MapLibre\'s full text is named by URL and stated as not vendored');
}

{
  const third = readFileSync(join(ROOT, 'THIRD_PARTY.md'), 'utf8');
  for (const f of vendored) {
    const stem = f.split('/').pop().replace(/\.(module\.min\.js|min\.js|js|css)$/, '');
    assert.ok(third.includes(stem) || third.includes(f.split('/').pop()),
      `THIRD_PARTY.md does not mention vendored file ${f}`);
  }
  for (const [name, ver] of [['Three.js', '0.160.0'], ['MapLibre GL JS', '4.7.1']]) {
    assert.ok(third.includes(`${name} ${ver}`), `THIRD_PARTY.md and the SBOM disagree on ${name} ${ver}`);
  }
  assert.ok(third.includes('sbom.cdx.json'), 'THIRD_PARTY.md points at the SBOM');
  ok('THIRD_PARTY.md, the human-readable statement of the same facts, names every vendored file and version');
}

{
  const sec = readFileSync(join(ROOT, 'SECURITY.md'), 'utf8');
  const row = sec.split('\n').find((l) => /SBOM generation/.test(l));
  assert.ok(row && /built and tested/.test(row) && /sbom\.cdx\.json/.test(row), 'SECURITY.md says the SBOM is built');
  const scan = sec.split('\n').find((l) => /container scanning/.test(l));
  assert.ok(scan && /open/.test(scan) && /maintainer/.test(scan),
    'SECURITY.md must keep CI scanning open — no workflow was changed here');
  assert.match(prop(doc.metadata, 'smartcitix:ci_scanning'), /not configured/);
  ok('SECURITY.md and the SBOM agree: SBOM built, CI scanning still open pending a maintainer-approved workflow');
}

{
  const sec = readFileSync(join(ROOT, 'SECURITY.md'), 'utf8');
  const m = sec.match(/(\d+) in `test_sbom\.mjs`/);
  assert.ok(m, 'SECURITY.md states this suite\'s check count');
  assert.equal(Number(m[1]), n + 1, `SECURITY.md says ${m[1]} sbom checks; this run has ${n + 1}`);
  ok('SECURITY.md states this suite\'s check count and it is the count that ran');
}

console.log(`\n${n} checks passed.`);
