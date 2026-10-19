#!/usr/bin/env python3
"""The Omega Hive registry: hive/registry/hive.json.

One roster that connects every scripted figure already in the bundle to an avatar, an AUTHORED personality, an
on-device voice profile and the lines it can say:

  agents/registry/advisors.json   9 hall advisors
  agents/registry/crews.json      6 crews, 20 roles
  npcs/registry/npcs.json         168 NPC guides (parish and Bay worlds)

Rules, each stated where it is applied:
  - LINES are quoted, never written here. Every line carries the registry path it was read from, and the build
    re-reads that path and refuses a line that is not character-for-character the same. A `read` topic (an advisor
    or crew binding resolved live in the 3D hall) is quoted as the binding's own description from advisors.json.
    The only AUTHORED words on a line are the short `ask` prompts for a crew role's job and stop condition and for an
    NPC's limits line, and each such ask is marked ask_provenance AUTHORED.
  - AVATARS are avatars/ locker configurations. An NPC's cfg is copied from npcs.json. An advisor's or crew role's
    cfg starts from the locker character nearest to what the registry says it wears (most equal sections, ties by
    locker order), takes the NPC variety rule for body sections (sha256('<agent id>:<section>')[:8] mod pool) and
    then puts on exactly what the registry says it wears. Every value must be a locker option id.
  - PERSONALITIES and base VOICE settings are AUTHORED in hive/authored/personalities.json (per advisor, per crew
    role, per NPC role, plus one family trait for trade mentors). Nothing generates them at view time.
  - K-12: the play-safe roster and the held-word list are AUTHORED in the same file and applied here.

Fails closed: a missing field, an unknown option id, a line that does not resolve or does not match, or a count that
is not the source registry's own count stops the build with a named error. `--check` rebuilds in memory and fails if
the committed registry is stale.
"""
import hashlib
import json
import pathlib
import re
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = HERE / 'registry' / 'hive.json'
AUTH_REL = 'hive/authored/personalities.json'


class HiveBuildError(Exception):
    pass


def need(cond, msg):
    if not cond:
        raise HiveBuildError(msg)


_CACHE = {}


def load(rel):
    if rel not in _CACHE:
        p = ROOT / rel
        need(p.exists(), f'missing source registry {rel}')
        _CACHE[rel] = json.loads(p.read_text(encoding='utf-8'))
    return _CACHE[rel]


# "<a>.<b>[3].<c>" or ["dotted.key"] - the same path syntax npcs/ uses, plus a quoted key for binding names
_TOK = re.compile(r'\.?([A-Za-z0-9_\-]+)|\[(\d+)\]|\["([^"]+)"\]')


def resolve(ref):
    need('#' in ref, f'source {ref!r} names no path')
    rel, path = ref.split('#', 1)
    node, pos = load(rel), 0
    while pos < len(path):
        m = _TOK.match(path, pos)
        need(m is not None and m.end() > pos, f'bad source path {ref}')
        key, idx, qkey = m.group(1), m.group(2), m.group(3)
        if idx is not None:
            need(isinstance(node, list) and int(idx) < len(node), f'source path {ref}: no index {idx}')
            node = node[int(idx)]
        else:
            k = qkey if qkey is not None else key
            need(isinstance(node, dict) and k in node, f'source path {ref}: no key {k}')
            node = node[k]
        pos = m.end()
    return node


def quote(ref):
    text = resolve(ref)
    need(isinstance(text, str) and text.strip(), f'{ref} is not a non-empty string')
    return text


ADV_REL = 'agents/registry/advisors.json'
CREW_REL = 'agents/registry/crews.json'
NPC_REL = 'npcs/registry/npcs.json'
AV_REL = 'avatars/registry/avatars.json'

ADV, CREWS, NPCS, AV = load(ADV_REL), load(CREW_REL), load(NPC_REL), load(AV_REL)
AUTH = load(AUTH_REL)
for k in ('provenance', 'voice_rule', 'bounds', 'k12', 'advisors', 'crew_roles', 'npc_roles', 'families'):
    need(k in AUTH, f'{AUTH_REL} has no {k}')

SECTION = {s['id']: s for s in AV['sections']}
OPTS = {s['id']: {o['id']: o for o in s['options']} for s in AV['sections']}
SI = {s['id']: i for i, s in enumerate(AV['sections'])}
# the NPC body-variety rule and proxy tints, read from npcs/ itself so there is one copy of each
VARY = ('build', 'skin', 'hair', 'haircolor', 'eyes', 'facialhair')
PROXY_PARTS = {'torso': 'topcolor', 'legs': 'pantscolor', 'head': 'skin', 'hat': 'headcolor'}
VEST_TINT = {'hi-vis-1': 'hi-vis-yellow', 'hi-vis-2': 'hi-vis-yellow', 'hi-vis-3': 'hi-vis-orange',
             'surveyor': 'hi-vis-orange', 'life-vest': 'hi-vis-orange', 'mesh': 'safety-green',
             'harness': 'charcoal', 'harness-position': 'charcoal', 'harness-ladder': 'charcoal',
             'tool-vest': 'duck-brown', 'fire-resist': 'navy', 'rain-vest': 'hi-vis-yellow'}
FACIAL = ('none', 'none', 'none', 'stubble', 'mustache', 'goatee', 'short-beard', 'full-beard', 'circle-beard')


def h8(s):
    return int(hashlib.sha256(s.encode()).hexdigest()[:8], 16)


def opt_src(sec, oid, field):
    idx = [o['id'] for o in SECTION[sec]['options']].index(oid)
    return f'{AV_REL}#sections[{SI[sec]}].options[{idx}].{field}'


def check_cfg(cfg, who):
    need(set(cfg) == set(OPTS), f'{who}: avatar cfg sections {sorted(set(OPTS) ^ set(cfg))} differ from the locker')
    for k, v in cfg.items():
        need(v in OPTS[k], f'{who}: {k}={v} is not an avatars/ locker option')


def proxy_of(cfg):
    proxy = {}
    for part, sec in PROXY_PARTS.items():
        oid = cfg[sec]
        need('value' in OPTS[sec][oid], f'avatar {sec}={oid} has no colour value')
        proxy[part] = {'hex': OPTS[sec][oid]['value'], 'source': opt_src(sec, oid, 'value')}
    if cfg['headwear'] == 'none':
        proxy['hat'] = None
    tint = VEST_TINT.get(cfg['vest'])
    proxy['vest'] = None if tint is None else {'hex': OPTS['topcolor'][tint]['value'], 'source': opt_src('topcolor', tint, 'value')}
    proxy['hair'] = {'hex': OPTS['haircolor'][cfg['haircolor']]['value'], 'source': opt_src('haircolor', cfg['haircolor'], 'value')}
    bo = OPTS['build'][cfg['build']]
    need('scale' in bo, f'build {cfg["build"]} has no scale')
    return proxy, {'xyz': bo['scale'], 'source': opt_src('build', cfg['build'], 'scale')}


CHARS = AV['characters']
COMPARE = [s for s in OPTS if s not in VARY and s != 'crew']


def nearest_character(cfg_or_wear):
    best, best_n = None, -1
    for c in CHARS:
        n = sum(1 for k in COMPARE if k in cfg_or_wear and c['cfg'].get(k) == cfg_or_wear[k])
        if n > best_n:
            best, best_n = c, n
    return best, best_n


def dressed(agent_id, wear):
    """Advisor / crew role: nearest locker character, NPC variety rule on the body, then the registry's own wear."""
    for k, v in wear.items():
        need(k in OPTS and v in OPTS[k], f'{agent_id}: worn {k}={v} is not a locker option')
    ch, n = nearest_character(wear)
    cfg = dict(ch['cfg'])
    for k in VARY:
        pool = list(FACIAL) if k == 'facialhair' else [o['id'] for o in SECTION[k]['options']]
        cfg[k] = pool[h8(f'{agent_id}:{k}') % len(pool)]
    cfg.update(wear)
    check_cfg(cfg, agent_id)
    return ch, n, cfg


def avatar(agent_id, cfg, ch, n, rule):
    proxy, scale = proxy_of(cfg)
    ci = CHARS.index(ch)
    return {'character': ch['id'], 'character_name': ch['name'], 'character_source': f'{AV_REL}#characters[{ci}].id',
            'shared_sections': n, 'rule': rule, 'cfg': cfg, 'proxy': proxy, 'scale': scale,
            'rig': 'avatars locker cfg -> buildAvatarMesh(cfg) (web/build_3d.py)'}


B = AUTH['bounds']
K12 = AUTH['k12']
HOLD = re.compile(r'\b(' + '|'.join(re.escape(w) for w in K12['hold_words']) + r')\b', re.I)


def clamp(x, lo, hi):
    return round(min(hi, max(lo, x)), 3)


def voice_of(agent_id, base, jitter):
    for k in ('pitch', 'rate'):
        need(isinstance(base.get(k), (int, float)), f'{agent_id}: AUTHORED voice has no {k}')
    off = (h8(f'{agent_id}:voice') % 9 - 4) * 0.01 if jitter else 0.0
    return {'pitch': clamp(base['pitch'] + off, *B['pitch']), 'rate': clamp(base['rate'] + off, *B['rate']),
            'volume': B['volume'], 'lang': 'en', 'engine': 'speechSynthesis', 'on_device_only': True,
            'offset': round(off, 3), 'provenance': 'AUTHORED base' + (' + DERIVED offset' if jitter else '')}


def personality_of(agent_id, p, family=None):
    for k in ('traits', 'style'):
        need(k in p and p[k], f'{agent_id}: AUTHORED personality has no {k}')
    need(len(p['traits']) == 3, f'{agent_id}: a personality has exactly three traits')
    traits = list(p['traits'])
    if family:
        need(family in AUTH['families'], f'{agent_id}: trade family {family} has no AUTHORED trait')
        traits.append(AUTH['families'][family])
    return {'traits': traits, 'style': p['style'], 'tone': 'plain', 'provenance': 'AUTHORED'}


def line(lid, ref, kind, ask=None, ask_src=None, ask_authored=False, text_ref=None):
    text = quote(ref)
    out = {'id': lid, 'kind': kind, 'text': text, 'source': ref, 'k12': not HOLD.search(text)}
    if text_ref:
        out['via'] = text_ref
        need(quote(text_ref) == text, f'line {lid}: {text_ref} does not quote {ref} verbatim')
    if ask is not None:
        out['ask'] = ask
        out['ask_provenance'] = 'AUTHORED' if ask_authored else 'REGISTRY'
        if ask_src:
            need(quote(ask_src) == ask, f'line {lid}: ask does not match {ask_src}')
            out['ask_source'] = ask_src
    return out


ASK_JOB = 'What is your job here?'
ASK_STOPS = 'What do you stop the work for?'
ASK_LIMITS = 'Does any of this certify me?'


def topic_lines(base, topics, prefix):
    out = []
    for i, t in enumerate(topics):
        for k in ('id', 'ask', 'kind'):
            need(k in t, f'{prefix}.topics[{i}] has no {k}')
        if t['kind'] == 'say':
            out.append(line(t['id'], f'{base}.topics[{i}].say', 'say', t['ask'], f'{base}.topics[{i}].ask'))
        elif t['kind'] == 'read':
            need(t['bind'] in ADV['bindings'], f'{prefix}.topics[{i}] reads unknown binding {t["bind"]}')
            ln = line(t['id'], f'{ADV_REL}#bindings["{t["bind"]}"]', 'read', t['ask'], f'{base}.topics[{i}].ask')
            ln['bind'] = t['bind']
            out.append(ln)
        else:
            raise HiveBuildError(f'{prefix}.topics[{i}] has unknown kind {t["kind"]}')
    return out


def build():
    agents = []
    # ---- advisors
    for aid, a in ADV['advisors'].items():
        for k in ('name', 'role', 'glyph', 'crew', 'greeting', 'topics', 'stands_in'):
            need(k in a, f'advisor {aid} has no {k}')
        need(aid in AUTH['advisors'], f'advisor {aid} has no AUTHORED personality')
        base = f'{ADV_REL}#advisors.{aid}'
        hid = f'advisor:{aid}'
        ch, n, cfg = dressed(hid, a['crew'])
        lines = [line('greeting', f'{base}.greeting', 'greeting')] + topic_lines(base, a['topics'], f'advisor {aid}')
        agents.append({'id': hid, 'kind': 'advisor', 'name': a['name'], 'name_source': f'{base}.name',
                       'role': a['role'], 'glyph': a['glyph'], 'where': {'hall_station': a['stands_in']},
                       'avatar': avatar(hid, cfg, ch, n, 'nearest locker character to the registry crew wear, body by the NPC variety rule, then the registry wear'),
                       'personality': personality_of(hid, AUTH['advisors'][aid]),
                       'voice': voice_of(hid, AUTH['advisors'][aid]['voice'], False),
                       'k12': aid in K12['advisors'], 'lines': lines})
    # ---- crew roles
    for cid, c in CREWS['crews'].items():
        for rid, r in c['roles'].items():
            for k in ('name', 'job', 'stops', 'glyph', 'wears', 'greeting', 'topics', 'key', 'standing'):
                need(k in r, f'crew role {cid}:{rid} has no {k}')
            need(r['key'] == f'{cid}:{rid}', f'crew role {cid}:{rid} has key {r["key"]}')
            need(r['key'] in AUTH['crew_roles'], f'crew role {r["key"]} has no AUTHORED personality')
            base = f'{CREW_REL}#crews.{cid}.roles.{rid}'
            hid = f'crew:{r["key"]}'
            ch, n, cfg = dressed(hid, r['wears'])
            lines = ([line('greeting', f'{base}.greeting', 'greeting'),
                      line('job', f'{base}.job', 'job', ASK_JOB, None, True),
                      line('stops', f'{base}.stops', 'stops', ASK_STOPS, None, True)]
                     + topic_lines(base, r['topics'], f'crew role {r["key"]}'))
            agents.append({'id': hid, 'kind': 'crew-role', 'name': r['name'], 'name_source': f'{base}.name',
                           'role': r['job'], 'glyph': r['glyph'], 'crew': cid, 'crew_name': c['name'],
                           'standing': r['standing'], 'where': {'seat': c['seat'], 'muster': c['muster']},
                           'avatar': avatar(hid, cfg, ch, n, 'nearest locker character to the registry crew wear, body by the NPC variety rule, then the registry wear'),
                           'personality': personality_of(hid, AUTH['crew_roles'][r['key']]),
                           'voice': voice_of(hid, AUTH['crew_roles'][r['key']]['voice'], False),
                           'k12': r['key'] in K12['crew_roles'], 'lines': lines})
    # ---- NPC guides
    for i, x in enumerate(NPCS['npcs']):
        for k in ('id', 'role', 'name', 'parish', 'appearance', 'knowledge', 'not_certification', 'home'):
            need(k in x, f'npc #{i} has no {k}')
        need(x['role'] in AUTH['npc_roles'], f'npc role {x["role"]} has no AUTHORED personality')
        base = f'{NPC_REL}#npcs[{i}]'
        hid = f'npc:{x["id"]}'
        cfg = dict(x['appearance']['cfg'])
        check_cfg(cfg, hid)
        ch, n = nearest_character(cfg)
        lines = []
        for j, kn in enumerate(x['knowledge']):
            need('text' in kn and 'source' in kn, f'npc {x["id"]} knowledge[{j}] has no text/source')
            lines.append(line(f'k{j}', kn['source'], 'knowledge', text_ref=f'{base}.knowledge[{j}].text'))
        nc = x['not_certification']
        lines.append(line('limits', nc['source'], 'limits', ASK_LIMITS, None, True, text_ref=f'{base}.not_certification.text'))
        fam = x.get('family') if x['role'] == 'mentor' else None
        agents.append({'id': hid, 'kind': 'npc', 'name': x['name'], 'name_source': f'{base}.name', 'role': x['role'],
                       'glyph': ch['glyph'], 'parish': x['parish'], 'family': x.get('family'),
                       'where': {'place': x['home']['place'], 'guide_to': x.get('guide_to')},
                       'avatar': avatar(hid, cfg, ch, n, 'cfg copied from npcs.json; character is the nearest locker character to it'),
                       'personality': personality_of(hid, AUTH['npc_roles'][x['role']], fam),
                       'voice': voice_of(hid, AUTH['npc_roles'][x['role']]['voice'], True),
                       'k12': x['role'] in K12['npc_roles'], 'lines': lines})

    ids = [a['id'] for a in agents]
    need(len(ids) == len(set(ids)), 'duplicate agent id')
    n_adv, n_role = len(ADV['advisors']), sum(len(c['roles']) for c in CREWS['crews'].values())
    need(n_adv == ADV['counts']['advisors'], f'advisors.json counts {ADV["counts"]["advisors"]}, holds {n_adv}')
    need(n_role == CREWS['counts']['roles'], f'crews.json counts {CREWS["counts"]["roles"]} roles, holds {n_role}')
    need(len(NPCS['npcs']) == NPCS['counts']['npcs'], 'npcs.json count drift')
    for a in agents:
        need(a['lines'], f'{a["id"]} has no line to say')
    lines = [ln for a in agents for ln in a['lines']]
    counts = {
        'agents': len(agents), 'advisors': n_adv, 'crews': len(CREWS['crews']), 'crew_roles': n_role, 'npcs': len(NPCS['npcs']),
        'lines': len(lines), 'say': sum(1 for ln in lines if ln['kind'] == 'say'), 'read': sum(1 for ln in lines if ln['kind'] == 'read'),
        'greeting': sum(1 for ln in lines if ln['kind'] == 'greeting'), 'knowledge': sum(1 for ln in lines if ln['kind'] == 'knowledge'),
        'job_stops_limits': sum(1 for ln in lines if ln['kind'] in ('job', 'stops', 'limits')),
        'characters_used': len({a['avatar']['character'] for a in agents}),
        'k12_agents': sum(1 for a in agents if a['k12']), 'k12_lines_held': sum(1 for a in agents if a['k12'] for ln in a['lines'] if not ln['k12']),
        'personalities': len(agents), 'voices': len(agents), 'models': 0,
    }
    stamp_src = (pathlib.Path(__file__).read_bytes() + (ROOT / AUTH_REL).read_bytes()
                 + ''.join(load(r).get('source_stamp', '') for r in (ADV_REL, CREW_REL, NPC_REL, AV_REL)).encode())
    return {
        'pack': 'smartcitix-trade-craft-academy-hive',
        'product': 'SmartCiti.X : Trade Craft Academy (powered by AGI Corp)',
        'name': 'Omega Hive',
        'schema': 'hive/1',
        'source_stamp': hashlib.sha256(stamp_src).hexdigest()[:16],
        'sources': {'advisors': ADV_REL, 'crews': CREW_REL, 'npcs': NPC_REL, 'avatars': AV_REL, 'personalities': AUTH_REL},
        'source_stamps': {r: load(r)['source_stamp'] for r in (ADV_REL, CREW_REL, NPC_REL, AV_REL)},
        'honesty': {
            'scripted': 'Every agent in the Omega Hive is SCRIPTED: each line it says is quoted verbatim from the registry path printed beside it. Nothing is generated, at build time or at view time.',
            'no_model': 'No AI model runs behind any agent, and no network is reached. The council picks lines by counting shared words between a question and the quoted lines - a fixed rule that gives the same answer every time - and says so when nothing matches.',
            'voice': "Voice is the device's own speech synthesis (the browser's speechSynthesis, on-device voices only). It speaks only when you press a speak button, never on its own, and a mute switch silences it. No audio is recorded or sent anywhere.",
            'personality': 'Personalities and voice settings are AUTHORED by hand for this roster; they change how a quoted line is delivered, never what it says.',
            'not_a_person': 'No agent represents a real worker, teacher, ranger, pilot, union officer or public figure; names are the source registries’ own AUTHORED names.',
            'play': 'Talking to an agent is play: it certifies nothing, unlocks nothing and enters no completion record. Lessons stay unverified general practice.',
        },
        'personality_provenance': AUTH['provenance'],
        'voice_rule': AUTH['voice_rule'],
        'bounds': B,
        'k12': {'rule': K12['rule'], 'advisors': K12['advisors'], 'npc_roles': K12['npc_roles'], 'crew_roles': K12['crew_roles'],
                'hold_words': K12['hold_words']},
        'asks_authored': [ASK_JOB, ASK_STOPS, ASK_LIMITS],
        'counts': counts,
        'agents': agents,
    }


def main():
    try:
        reg = build()
    except (HiveBuildError, KeyError) as e:
        print(f'hive/build.py: FAIL {type(e).__name__}: {e}', file=sys.stderr)
        sys.exit(1)
    text = json.dumps(reg, indent=1, ensure_ascii=False) + '\n'
    if '--check' in sys.argv:
        if not OUT.exists() or OUT.read_text(encoding='utf-8') != text:
            print('hive/build.py --check: FAIL hive/registry/hive.json is stale; run python3 hive/build.py', file=sys.stderr)
            sys.exit(1)
        print(f'hive/build.py --check: up to date (stamp {reg["source_stamp"]})')
        return
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(text, encoding='utf-8')
    c = reg['counts']
    print(f'hive: {c["agents"]} agents ({c["advisors"]} advisors, {c["crew_roles"]} crew roles, {c["npcs"]} NPCs), '
          f'{c["lines"]} quoted lines, {c["characters_used"]} locker characters, k12 {c["k12_agents"]}, stamp {reg["source_stamp"]}')


if __name__ == '__main__':
    main()
