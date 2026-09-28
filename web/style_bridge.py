"""HOMEUX wave 4: map a page's own house-dark palette names (--good, --warn, --crit, ...) onto the colours
each of the five switcher styles (design_kit.STYLES) declares, so html[data-style] reaches them.

bridge_css(extra) -> CSS text. With no style chosen nothing applies: the page keeps its own default look.
`extra` maps more page variable names to a style token name ('ok', 'warn', 'crit', 'link', 'ink', 'muted',
'accent', 'plate', 'panel', 'raised', 'line'). Every text colour is asserted >= 4.5 against the style's plate,
panel and raised at import/build time (fails closed, by name)."""
from design_kit import STYLES, contrast

CRIT = {'light': '#B42318', 'dark': '#FF9B8A'}   # error red per style scheme (measured below)
BASE = {'good': 'ok', 'warn': 'warn', 'crit': 'crit', 'steel-ink': 'link'}
TEXT = ('ok', 'warn', 'crit', 'link', 'ink', 'muted')
IDS = [s['id'] for s in STYLES]


def scheme(s):
    t = s['tokens']
    return 'light' if contrast('#000000', t['plate']) > contrast('#FFFFFF', t['plate']) else 'dark'


def palette(s):
    p = dict(s['tokens'])
    p['crit'] = CRIT[scheme(s)]
    p['on-ok'] = max(('#FFFFFF', '#0C1113'), key=lambda c: contrast(c, p['ok']))   # text on an ok-filled badge
    return p


def sel(i):
    return f'html:is([data-style="{i}"],:has(input[name="tc-style"][value="{i}"]:checked))'


def any_sel():
    return ('html:is([data-style],:has(input[name="tc-style"]:is('
            + ','.join(f'[value="{i}"]' for i in IDS) + '):checked))')


for _s in STYLES:
    _p = palette(_s)
    for _k in TEXT:
        for _bg in ('plate', 'panel', 'raised'):
            _r = contrast(_p[_k], _p[_bg])
            if _r < 4.5:
                raise SystemExit(f'style_bridge: {_s["id"]} {_k} {_p[_k]} on {_bg} {_p[_bg]} = {_r:.2f} < 4.5')
    if contrast(_p['on-ok'], _p['ok']) < 4.5:
        raise SystemExit(f'style_bridge: {_s["id"]} on-ok {_p["on-ok"]} on ok {_p["ok"]} < 4.5')


def bridge_css(extra=None):
    m = dict(BASE)
    m.update(extra or {})
    out = ['/* style_bridge: page palette -> 5-style tokens (HOMEUX) */']
    for s in STYLES:
        p = palette(s)
        decl = ';'.join(f'--{name}:{p[tok]}!important' for name, tok in m.items())
        out.append(f'{sel(s["id"])}{{{decl}}}')
    return '\n'.join(out)


if __name__ == '__main__':
    print(bridge_css())
