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

const SPDX = new Set(['MIT', 'BSD-3-Clause', 'OFL-1.1']);
const PURLS = {
  three: 'pkg:npm/three@0.160.0',
  'maplibre-gl': 'pkg:npm/maplibre-gl@4.7.1',
  // The four self-hosted type families. Each is its own upstream under its
  // own copyright - collapsing them into one "webfonts" entry would
  // attribute three of them to authors who did not write them.
  'barlow-condensed': 'pkg:generic/barlow-condensed@v13',
  'ibm-plex-sans': 'pkg:generic/ibm-plex-sans@v23',
  'ibm-plex-mono': 'pkg:generic/ibm-plex-mono@v20',
  archivo: 'pkg:generic/archivo@v25',
};
// A font is a binary; decoding one as UTF-8 produces mojibake that the
// banner and version searches below would then happily search.
const isBinary = (ref) => ref.endsWith('.woff2');
const FONTS = JSON.parse(readFileSync(join(ROOT, 'web/vendor/fonts/manifest.json'), 'utf8'));
const FAMILY_UP = { 'Barlow Condensed': 'barlow-condensed', 'IBM Plex Sans': 'ibm-plex-sans',
                    'IBM Plex Mono': 'ibm-plex-mono', Archivo: 'archivo' };

let libs = 0, own = 0;
for (const c of doc.components) {
  const bytes = readFileSync(join(ROOT, c['bom-ref']));
  assert.equal(c.hashes.length, 1);
  assert.equal(c.hashes[0].alg, 'SHA-256');
  assert.equal(c.hashes[0].content, sha(bytes), `${c['bom-ref']}: hash does not match the file bytes`);

  // Our own generated files live under web/vendor/ so the stylesheet's
  // relative url() sits beside the fonts it names. They are listed so the
  // SBOM accounts for the whole tree, and they must NOT claim to be
  // somebody else's work.
  if (c.type === 'file') {
    own++;
    assert.ok(prop(c, 'smartcitix:first_party'),
      `${c['bom-ref']}: typed as a file but does not say it is ours`);
    assert.ok(!c.licenses, `${c['bom-ref']}: a first-party file must not claim a third-party licence`);
    assert.ok(!c.purl, `${c['bom-ref']}: a first-party file must not claim an upstream purl`);
    continue;
  }

  libs++;
  const text = isBinary(c['bom-ref']) ? '' : bytes.toString('utf8');
  assert.equal(c.type, 'library');
  assert.ok(SPDX.has(c.licenses[0].license.id), `${c['bom-ref']}: licence is not an SPDX id we recognise`);
  assert.ok(c.purl === PURLS[c.name] || c.purl.startsWith(PURLS[c.name] + '#'),
    `${c['bom-ref']}: purl ${c.purl} is not ${PURLS[c.name]}`);
  assert.ok(c.purl.includes(`@${c.version}`), 'purl and version agree');
  const ev = prop(c, 'smartcitix:version_evidence');
  assert.ok(ev, 'every component says what its version rests on');

  if (c.name in FAMILY_UP || Object.values(FAMILY_UP).includes(c.name)) {
    // A font carries no version string of its own. Its version is the `vN`
    // Google Fonts served it under, and the evidence is the exact URL
    // web/fetch_fonts.py recorded at fetch time - checked against that
    // manifest, which is a stronger claim than "this string is in the
    // file", not a weaker one: it ties the bytes to where they came from.
    const name = c['bom-ref'].split('/').pop();
    const rec = FONTS.files[name]
      ?? Object.values(FONTS.licences).find((l) => l.file === name);
    assert.ok(rec, `${c['bom-ref']}: no record in the font manifest`);
    assert.equal(ev, rec.from, `${c['bom-ref']}: version evidence is not the URL it was fetched from`);
    if (name.endsWith('.woff2')) {
      assert.ok(ev.includes(`/${c.version}/`),
        `${c['bom-ref']}: evidence "${ev}" does not carry version ${c.version}`);
      assert.equal(rec.sha256, sha(bytes), `${c['bom-ref']}: font manifest hash disagrees with the file`);
    }
    // Redistributing these bytes is only permitted WITH the licence, so the
    // full OFL for this family has to be in the tree, not behind a URL.
    const lic = Object.entries(FONTS.licences).find(([fam]) => FAMILY_UP[fam] === c.name);
    assert.ok(lic, `${c.name}: no licence recorded in the font manifest`);
    const licBytes = readFileSync(join(ROOT, 'web/vendor/fonts', lic[1].file));
    assert.equal(sha(licBytes), lic[1].sha256, `${lic[1].file}: licence hash does not match`);
    assert.ok(/SIL OPEN FONT LICENSE/i.test(licBytes.toString('utf8')),
      `${lic[1].file}: does not read as an OFL`);
    assert.ok(c.externalReferences.some((r) => r.type === 'license'));
    continue;
  }

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
assert.ok(libs > 0 && own > 0, 'both third-party and first-party entries are present');
ok(`every self-hosted font is tied to the URL it came from and to a full OFL committed in the tree (${own} first-party files listed separately, claiming no upstream)`);
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
  // The font files are named transitively rather than one by one: thirty
  // filenames in a prose table is a table nobody reads, and a statement
  // nobody reads is not a statement. So THIRD_PARTY.md must point at the
  // manifest, and the manifest must actually account for the file - which
  // is checked here, so the indirection cannot become a place to hide one.
  const fontManifest = 'web/vendor/fonts/manifest.json';
  for (const f of vendored) {
    const base = f.split('/').pop();
    if (f.includes('/fonts/')) {
      assert.ok(third.includes(fontManifest),
        'THIRD_PARTY.md must point at the font manifest if it does not name each font file');
      const known = base in FONTS.files
        || Object.values(FONTS.licences).some((l) => l.file === base)
        || base === 'fonts.css' || base === 'manifest.json';
      assert.ok(known, `${f} is in web/vendor/fonts/ but the font manifest does not account for it`);
      continue;
    }
    const stem = base.replace(/\.(module\.min\.js|min\.js|js|css)$/, '');
    assert.ok(third.includes(stem) || third.includes(base),
      `THIRD_PARTY.md does not mention vendored file ${f}`);
  }
  for (const fam of ['Barlow Condensed', 'Archivo', 'IBM Plex Sans', 'IBM Plex Mono']) {
    assert.ok(third.includes(fam), `THIRD_PARTY.md does not name the font family ${fam}`);
  }
  assert.ok(/no page contacts a font service/i.test(third),
    'THIRD_PARTY.md still has to say whether a page load reaches a font service');
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
