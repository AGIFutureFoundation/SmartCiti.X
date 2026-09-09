/*!
 * SmartCiti.X : Trade Craft Academy — module registry consumer library
 * (ACP-10, 111-hall pack). ESM, zero dependencies, Node + browser.
 *
 * The pack ships a skeleton — 111 halls, their 100-level ladders, the skill
 * graph and a shared library — and this library generates the 11,000,000
 * module IDs from it. Nothing enumerates 11 million rows: not the pack, not
 * this library, not the Academy. A hall is resolved by rule, a lesson is
 * resolved by rule, and a variant is resolved by rule.
 */

const CORE_RE = /^u(\d{3})\.l(\d{3})\.s(\d{3})\.(vr_sim|guided_drill|quiz_reading)\.(support|core|stretch)$/;
const LIB_RE = /^(mach|tool|ifc|ppe)(\d{4})$/;

export const SHAPE = Object.freeze({
  halls: 111, levels: 100, slots: 110, variants: 9,
  lessonsPerHall: 11_000, coreModules: 10_989_000,
  sharedLibrary: 11_000, total: 11_000_000,
});

const MODALITIES = ['vr_sim', 'guided_drill', 'quiz_reading'];
const BANDS = ['support', 'core', 'stretch'];
const BAND_OFFSET = { support: -5, core: 0, stretch: 5 };
const BAND_CEILING = { support: 5, core: 3, stretch: 1 };
const STRANDS = ['safety', 'layout', 'materials', 'tools', 'machines', 'procedure',
  'inspection', 'documentation', 'coordination', 'troubleshooting', 'leadership'];
const TIERS = ['fundamentals', 'applied', 'mastery'];
const FORMS = ['principles', 'setup', 'execution', 'verification', 'faults', 'handoff',
  'standards', 'field case', 'drill', 'measurement', 'planning'];
const TRACKS = ['Orientation', 'Pre-Apprentice', 'Apprentice I', 'Apprentice II',
  'Apprentice III', 'Journey', 'Journey Advanced', 'Specialist', 'Master', 'Instructor'];

const isNode = typeof process !== 'undefined' && process.versions?.node;

async function readJSON(base, rel) {
  const isUrl = base instanceof URL || (typeof base === 'string' && /^[a-z]+:\/\//i.test(base));
  if (isNode && (!isUrl || String(base).startsWith('file:'))) {
    const { readFile } = await import('node:fs/promises');
    if (isUrl) {
      const { fileURLToPath } = await import('node:url');
      return JSON.parse(await readFile(fileURLToPath(new URL(rel, String(base).replace(/\/?$/, '/'))), 'utf8'));
    }
    const { join } = await import('node:path');
    return JSON.parse(await readFile(join(base, rel), 'utf8'));
  }
  const res = await fetch(`${String(base).replace(/\/$/, '')}/${rel}`);
  if (!res.ok) throw new Error(`registry: cannot read ${rel} (${res.status})`);
  return res.json();
}

export const tierOf = (level) => TIERS[Math.min(2, Math.floor(level / 34))];
export const trackOf = (level) => TRACKS[Math.floor(level / 10)];

/** The build front, as a pure function — the same rule the builder applies. */
export function pipelineState(hallIdx, level) {
  if (hallIdx < 18) return level <= 88 ? 'live' : level <= 94 ? 'calibrating' : 'schema_ok';
  if (hallIdx < 33) return level <= 70 ? 'live' : level <= 84 ? 'calibrating' : 'schema_ok';
  if (hallIdx < 66) return level <= 44 ? 'live' : level <= 66 ? 'calibrating'
    : level <= 84 ? 'schema_ok' : 'draft';
  return level <= 22 ? 'live' : level <= 44 ? 'calibrating'
    : level <= 70 ? 'schema_ok' : 'draft';
}

/** Variant states narrow the parent: an uncalibrated stretch band stays back. */
export function variantState(parentState, band) {
  if (parentState === 'live' && band === 'stretch') return 'live';
  if (parentState === 'calibrating' && band === 'stretch') return 'schema_ok';
  return parentState;
}

/**
 * The module ID space is a bijection with [0, 11,000,000).
 *
 * This is what makes uniqueness provable rather than sampled: index() and
 * fromIndex() are inverses over the whole population, so a verifier can walk
 * every index once and confirm the count and the absence of collisions without
 * ever materialising 11 million strings.
 */
export function index(hallIdx, level, slot, modality, band) {
  const m = MODALITIES.indexOf(modality), b = BANDS.indexOf(band);
  if (m < 0 || b < 0) return -1;
  return ((hallIdx * SHAPE.levels + level) * SHAPE.slots + slot) * SHAPE.variants + m * 3 + b;
}

export function fromIndex(i) {
  if (i < 0 || i >= SHAPE.total) return null;
  if (i >= SHAPE.coreModules) {
    const k = i - SHAPE.coreModules;
    const KINDS = [['mach', 4400], ['tool', 4400], ['ifc', 1100], ['ppe', 1100]];
    let off = k;
    for (const [prefix, n] of KINDS) {
      if (off < n) return { kind: 'library', item_id: `${prefix}${String(off).padStart(4, '0')}` };
      off -= n;
    }
    return null;
  }
  const v = i % SHAPE.variants, rest = (i - v) / SHAPE.variants;
  const slot = rest % SHAPE.slots, r2 = (rest - slot) / SHAPE.slots;
  const level = r2 % SHAPE.levels, hallIdx = (r2 - level) / SHAPE.levels;
  return { kind: 'core', hallIdx, level, slot,
           modality: MODALITIES[Math.floor(v / 3)], band: BANDS[v % 3] };
}

export async function openRegistry(base = './registry') {
  const [halls, skills, library, variants] = await Promise.all([
    readJSON(base, 'halls.json'), readJSON(base, 'skills.json'),
    readJSON(base, 'library.json'), readJSON(base, 'variants.json'),
  ]);
  const byIndex = new Map(halls.halls.map((h) => [h.index, h]));
  const bySlug = new Map(halls.halls.map((h) => [h.slug, h]));
  const skillById = new Map(skills.skills.map((s) => [s.skill_id, s]));
  const libIds = new Set(library.items.map((i) => i.item_id));

  /** One generated lesson — the rule the builder uses, mirrored. */
  function lesson(hallIdx, level, slot) {
    const h = byIndex.get(hallIdx);
    if (!h || level < 0 || level >= SHAPE.levels || slot < 0 || slot >= SHAPE.slots) return null;
    const strand = STRANDS[slot % 11], tier = tierOf(level);
    return {
      lesson_id: `u${String(hallIdx).padStart(3, '0')}.l${String(level).padStart(3, '0')}.s${String(slot).padStart(3, '0')}`,
      union: h.slug, union_name: h.name, level, slot,
      track: trackOf(level), tier,
      skill_id: `${h.slug}.${strand}.${tier}`,
      form: FORMS[(slot + level) % 11],
      base_difficulty: +(14 + (level * SHAPE.slots + slot) / (SHAPE.lessonsPerHall - 1) * 78).toFixed(1),
      state: pipelineState(hallIdx, level),
      level_test: slot === SHAPE.slots - 1,
      final_exam: slot === SHAPE.slots - 1 && level % 10 === 9,
    };
  }

  function resolve(moduleId) {
    const lib = LIB_RE.exec(moduleId);
    if (lib) return libIds.has(moduleId)
      ? { kind: 'library', item_id: moduleId, shared: true, state: (+lib[2] % 5) ? 'live' : 'calibrating' }
      : null;
    const m = CORE_RE.exec(moduleId);
    if (!m) return null;
    const [, hs, ls, ss, modality, band] = m;
    const les = lesson(+hs, +ls, +ss);
    if (!les) return null;
    return {
      ...les, module_id: moduleId, kind: 'core', modality, band,
      difficulty: +(les.base_difficulty + BAND_OFFSET[band]).toFixed(1),
      scaffold_ceiling: BAND_CEILING[band],
      state: variantState(les.state, band),
    };
  }

  return {
    shape: SHAPE, halls: halls.halls, skills: skills.skills,
    hall: (k) => (typeof k === 'number' ? byIndex.get(k) : bySlug.get(k)) ?? null,
    skill: (id) => skillById.get(id) ?? null,
    lesson, resolve, index, fromIndex,
    moduleIdAt(i) {
      const d = fromIndex(i);
      if (!d) return null;
      if (d.kind === 'library') return d.item_id;
      return `u${String(d.hallIdx).padStart(3, '0')}.l${String(d.level).padStart(3, '0')}`
        + `.s${String(d.slot).padStart(3, '0')}.${d.modality}.${d.band}`;
    },
    /** Candidates for a dial setpoint, without scanning the space. */
    selectForDial({ union, theta, setpoint, tolerance = 4, limit = 40 }) {
      const h = bySlug.get(union); if (!h) return [];
      const out = [];
      for (let lv = 0; lv < SHAPE.levels && out.length < limit; lv++) {
        if (pipelineState(h.index, lv) !== 'live') continue;
        for (let s = 0; s < SHAPE.slots && out.length < limit; s++) {
          const les = lesson(h.index, lv, s);
          for (const band of BANDS) {
            const d = les.base_difficulty + BAND_OFFSET[band];
            if (Math.abs(d - setpoint) <= tolerance) {
              out.push({ module_id: `${les.lesson_id}.vr_sim.${band}`, difficulty: +d.toFixed(1),
                         skill_id: les.skill_id, state: variantState(les.state, band) });
              break;
            }
          }
        }
      }
      return out;
    },
  };
}
