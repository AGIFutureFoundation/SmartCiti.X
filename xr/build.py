"""xr/ - the head-mounted hardware this bundle is aimed at, and the one
question that matters more than any feature list: does it take away the
eye protection the room already requires?

This bundle has a WebXR layer with hand tracking, and an open question in
rnd/ that says plainly no headset has ever run it. That question is not
closed by this pack. What this pack does is write down the target list
with the two facts a safety officer asks first - how it attaches to the
head, and whether it is certified eye protection - and cross-reference the
second against the PPE this bundle's own room registry already requires.

THE PROVENANCE PROBLEM, STATED UP FRONT

Not one record here is RECORDED. Every device fact is a vendor claim
relayed into this repository as text; the citations point at vendor pages,
and this environment cannot open them (all three sampled hosts returned
000/ERR). A claim I cannot open is not a claim I have checked, and calling
it RECORDED because it arrived with a URL attached would be exactly the
kind of laundering the rest of this bundle exists to prevent. So every
device is AUTHORED, every one carries the URL it was claimed from, and
every one carries `claim_checked: false`. The day someone opens those
pages, this pack gets a real tier.

WHY THE EYE-PROTECTION FIELD FAILS CLOSED

`eye_protection.standard` is None unless a standard was actually named.
None does NOT mean "no protection" - it means THIS PACK CANNOT SAY, which
for a person deciding what to put on a worker's face is the only safe
reading. A default of "probably fine" here is a policy decision about
somebody's eyesight, and section 23.1 of the spec says a default is a
policy decision. The counts below report the not-established group as its
own number rather than folding it in with either answer.
"""
import hashlib
import json
import pathlib

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
OUT = HERE / 'registry' / 'devices.json'

PACK_VERSION = json.loads(
    (ROOT / 'pack' / 'manifest.json').read_text())['pack_version']

# How the thing gets onto a head. This is a safety question, not a comfort
# one: a mount through a helmet's approved accessory slot is a different
# claim from a strap somebody worked out on site.
ATTACH = {
    'integrated-certified-hardhat':
        'the display is built into a hardhat the vendor certifies as a '
        'hardhat - one product, one certification',
    'integrated-protective-mask':
        'the display is built into a protective mask',
    'vendor-helmet-mount':
        'the vendor sells a named mount for standard helmet accessory slots',
    'vendor-states-compatible':
        'the vendor states helmet mounting is supported, without a single '
        'named mount part in the claim relayed here',
    'integrator-dependent':
        'no vendor mount is named in the claim relayed here; helmet fitting '
        'is left to whoever integrates it, which is the weakest of these',
    'worn-alongside':
        'not mounted to the helmet - worn with existing eyewear and helmet',
}

# The strength of the helmet-attachment claim, kept SEPARATE from the claim
# itself so a reader can sort by how much is actually known.
EVIDENCE_RANK = {
    'integrated-certified-hardhat': 4,
    'integrated-protective-mask': 4,
    'vendor-helmet-mount': 3,
    'vendor-states-compatible': 2,
    'worn-alongside': 2,
    'integrator-dependent': 1,
}

# vendor, product, class, attachment, eye-protection standard (None when
# none was named), how that protection is delivered, fit, claim URL
DEVICES = [
    ('realwear', 'RealWear', 'Navigator 520', 'assisted-reality',
     'worn-alongside', None, None,
     'construction, utilities, oil and gas, remote expert support, inspection',
     'https://vsight.io/industrial-smart-glasses-vsight-compatibility/'),
    ('realwear-hmt1z1', 'RealWear', 'HMT-1Z1', 'assisted-reality',
     'vendor-states-compatible', None, None,
     'industrial response, petrochemical, mining, emergency maintenance',
     'https://vsight.io/industrial-smart-glasses-vsight-compatibility/'),
    ('vuzix-m400', 'Vuzix', 'M400 Smart Glasses', 'monocular-ar',
     'vendor-helmet-mount', None, None,
     'field inspection, public-sector inspection, construction service teams',
     'https://www.vuzix.com/products/m-series-safety-helmet-mounts'),
    ('vuzix-m4000', 'Vuzix', 'M4000 Smart Glasses', 'monocular-ar',
     'vendor-helmet-mount', None, None,
     'remote assistance, procedures, asset inspection',
     'https://www.vuzix.com/products/m-series-safety-helmet-mounts'),
    ('vuzix-blade2', 'Vuzix', 'Blade 2', 'monocular-ar',
     'integrator-dependent', None, None,
     'lighter-duty logistics, field operations, guided workflows',
     'https://www.vuzix.com/products/m-series-safety-helmet-mounts'),
    ('epson-bt45cs', 'Epson', 'Moverio BT-45CS', 'binocular-ar',
     'vendor-states-compatible', 'ANSI Z87.1', 'attachable certified shield',
     'construction supervision, maintenance, training, inspection',
     'https://news.epson.com/news/moverio-bt-45c-45cs-ar-smart-glasses'),
    ('epson-bt45c', 'Epson', 'Moverio BT-45C', 'binocular-ar',
     'vendor-states-compatible', None, None,
     'hands-free remote guidance and jobsite workflows',
     'https://news.epson.com/news/moverio-bt-45c-45cs-ar-smart-glasses'),
    ('rokid-xcraft', 'Rokid', 'X-Craft', 'binocular-ar',
     'vendor-states-compatible', None, None,
     'utilities, energy, rail, aviation, industrial construction',
     'https://displaydaily.com/an-interesting-upgrade-to-an-interesting-ar-headset/'),
    ('iristick-g2', 'Iristick', 'Iristick.G2', 'monocular-ar',
     'vendor-states-compatible', None, None,
     'first-response communications, field service, assisted procedures',
     'https://nsflow.com/blog/best-industrial-grade-augmented-reality-ar-glasses'),
    ('thirdeye-x2', 'ThirdEye', 'X2 MR Glasses', 'binocular-ar',
     'worn-alongside', None, None,
     'EMS, fire and public safety, telemedicine, incident documentation',
     'https://www.thirdeyegen.com/'),
    ('thirdeye-midas', 'ThirdEye', 'MIDAS', 'mask-integrated',
     'integrated-protective-mask', None, None,
     'firefighters, hazmat, defense, zero-visibility emergency response',
     'https://www.thirdeyegen.com/'),
    ('univet-visionar', 'Univet Optics', 'VisionAR', 'monocular-ar',
     'worn-alongside', 'ANSI Z87.1+ and EN166', 'the device itself',
     'construction, manufacturing, industrial safety workflows',
     'https://news.epson.com/news/moverio-bt-45c-45cs-ar-smart-glasses'),
    ('hololens2-ie', 'Microsoft', 'HoloLens 2 Industrial Edition',
     'mr-headset', 'integrator-dependent', None, None,
     'BIM overlays, construction QA/QC, digital-twin visualization',
     'https://www.vuzix.com/products/m-series-safety-helmet-mounts'),
    ('xyz-atom', 'XYZ Reality', 'Atom', 'integrated-hardhat',
     'integrated-certified-hardhat', None, None,
     'high-precision BIM layout, structural verification, installation',
     'https://www.xyzreality.com/atom'),
    ('daqri-helmet', 'DAQRI', 'Smart Helmet', 'integrated-hardhat',
     'integrated-certified-hardhat', None, None,
     'legacy reference for smart-hardhat concepts',
     'https://www.vuzix.com/products/m-series-safety-helmet-mounts'),
]

# Procurement flags this pack raises ITSELF, against the list as relayed.
# These are recollection, not lookup - the hosts are unreachable from here -
# so each says how sure it is and that it must be checked before anyone
# spends money. Silence would be worse: both devices below are presented in
# the relayed list as live options with no note attached.
FLAGS = {
    'daqri-helmet': {
        'flag': 'the vendor is believed to have ceased operations in 2019 '
                'and the product to be unavailable new',
        'confidence': 'high, from general knowledge; not verified here '
                      'because no vendor host is reachable from this build',
        'consequence': 'treat as a historical reference design only. A '
                       'procurement shortlist that carries it as an option '
                       'is carrying a dead line item.',
    },
    'hololens2-ie': {
        'flag': 'production is believed to have ended in 2024 with security '
                'support announced only to the end of 2027',
        'confidence': 'moderate, from general knowledge; not verified here',
        'consequence': 'viable for a pilot or a training-room fixture, '
                       'questionable as the basis of a multi-year fleet. '
                       'Confirm the support date with the vendor before '
                       'committing.',
    },
}

# ---------------------------------------------------------------------------
# what the rooms already require - read, never retyped

fin = json.loads((ROOT / 'surfaces' / 'registry' / 'finishes.json').read_text())


def walk_rooms(o):
    if isinstance(o, dict):
        if 'ppe' in o and not isinstance(o.get('ppe'), dict):
            yield o
        else:
            for v in o.values():
                yield from walk_rooms(v)


rooms = list(walk_rooms(fin))
assert rooms, 'xr: no rooms with a ppe list came out of surfaces/'


def rooms_requiring(*items):
    want = set(items)
    return [r for r in rooms if want & set(r.get('ppe') or [])]


EYE_ITEMS = ('safety glasses', 'face shield', 'arc-flash face shield',
             'welding hood')
HEAD_ITEMS = ('hard hat', 'chinstrap helmet')

eye_rooms = rooms_requiring(*EYE_ITEMS)
head_rooms = rooms_requiring(*HEAD_ITEMS)
both_rooms = [r for r in eye_rooms if set(HEAD_ITEMS) & set(r.get('ppe') or [])]

# ---------------------------------------------------------------------------

devices = {}
for (did, vendor, product, klass, attach, std, how, fit, url) in DEVICES:
    if attach not in ATTACH:
        raise KeyError('xr: %s: unknown attachment %r (known: %r)'
                       % (did, attach, sorted(ATTACH)))
    if (std is None) != (how is None):
        raise ValueError('xr: %s: a named standard and the way it is '
                         'delivered travel together, or neither does' % did)
    devices[did] = {
        'vendor': vendor,
        'product': product,
        'class': klass,
        'head_attachment': attach,
        'head_attachment_means': ATTACH[attach],
        'head_attachment_evidence': EVIDENCE_RANK[attach],
        'eye_protection': {
            'standard': std,
            'delivered_by': how,
            # the whole point of the pack, said per device
            'replaces_room_eye_ppe': bool(std is not None),
            'note': ('states a standard, so it can be evaluated as the '
                     'room\'s eye protection - by a safety officer, against '
                     'the specific room, not by this file'
                     if std else
                     'NO eye-protection standard is named in the claim '
                     'relayed here. This pack therefore records that it does '
                     'NOT replace the eye protection a room requires, and '
                     'that a worker needs certified eyewear as well. That is '
                     'the fail-closed reading, not a finding about the '
                     'product.'),
        },
        'best_fit': fit,
        'claim_source': url,
        'claim_checked': False,
        'provenance': 'AUTHORED',
    }
    if did in FLAGS:
        devices[did]['procurement_flag'] = FLAGS[did]

_std = [d for d in devices.values() if d['eye_protection']['standard']]
_nostd = [d for d in devices.values() if not d['eye_protection']['standard']]
_own = [d for d in _std if d['eye_protection']['delivered_by'] == 'the device itself']

stamp = hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest()[:16]

HONESTY = {
    'status': 'AUTHORED: every device fact here is a vendor claim relayed '
              'into this repository as text. Not one was opened and read by '
              'this build - the three vendor hosts sampled all returned '
              '000/ERR from this environment - so not one is RECORDED, and '
              'each carries the URL it was claimed from and claim_checked '
              'false.',
    'not_a_recommendation': 'This is a target list, not a shortlist. The '
                            'ordering in the source material was somebody '
                            'else\'s recommendation and is not reproduced '
                            'as a ranking here. Nothing in this bundle has '
                            'been run on any of these devices.',
    'no_headset_has_run_this': 'The WebXR layer in web/build_3d.py has hand '
                               'tracking and four declared gestures whose '
                               'joint distances are AUTHORED and unverified '
                               'on hardware. rnd/ carries that as an open '
                               'question. This pack names hardware; it does '
                               'not close that question and must not be '
                               'read as closing it.',
    'eye_protection_fails_closed': 'A null standard means this pack cannot '
                                   'say, not that the device is unprotected '
                                   'and not that it is fine. %d of %d '
                                   'devices name no eye-protection standard '
                                   'in the claim relayed here, and every one '
                                   'of those is recorded as NOT replacing '
                                   'the eye protection a room requires.'
                                   % (len(_nostd), len(devices)),
    'the_rooms_are_the_constraint': 'This is not a procurement abstraction. '
                                    'Of the %d rooms this bundle describes, '
                                    '%d require eye protection and %d '
                                    'require both eye and head protection. '
                                    'In those %d rooms a head-mounted '
                                    'display is something worn IN ADDITION '
                                    'to certified eyewear unless it is '
                                    'certified itself - and by this list, %d '
                                    'device is certified in its own right.'
                                    % (len(rooms), len(eye_rooms),
                                       len(both_rooms), len(both_rooms),
                                       len(_own)),
    'mounting_does_not_transfer_certification': 'A helmet\'s rating belongs '
                                                'to the helmet as tested. '
                                                'Hanging a powered device '
                                                'off it is a modification '
                                                'until the helmet maker says '
                                                'otherwise. This pack records '
                                                'how strong each attachment '
                                                'claim is (1 integrator-'
                                                'dependent to 4 integrated) '
                                                'and never treats a mount as '
                                                'inheriting a rating.',
}

payload = {
    'pack': 'xr',
    'product': 'head-mounted hardware targets for the walkable layer, with '
               'the eye- and head-protection question each one raises '
               'cross-referenced against the PPE this bundle\'s rooms '
               'already require',
    'pack_version': PACK_VERSION,
    'source_stamp': stamp,
    'honesty': HONESTY,
    'counts': {
        'devices': len(devices),
        'vendors': len({d['vendor'] for d in devices.values()}),
        'eye_protection_standard_named': len(_std),
        'eye_protection_by_the_device_itself': len(_own),
        'eye_protection_not_established': len(_nostd),
        'procurement_flags': len(FLAGS),
        'by_class': {k: sum(1 for d in devices.values() if d['class'] == k)
                     for k in sorted({d['class'] for d in devices.values()})},
        'by_attachment': {k: sum(1 for d in devices.values()
                                 if d['head_attachment'] == k)
                          for k in sorted(ATTACH)},
        'rooms_total': len(rooms),
        'rooms_requiring_eye_protection': len(eye_rooms),
        'rooms_requiring_head_protection': len(head_rooms),
        'rooms_requiring_both': len(both_rooms),
    },
    'attachment_kinds': ATTACH,
    'eye_ppe_items_counted': list(EYE_ITEMS),
    'head_ppe_items_counted': list(HEAD_ITEMS),
    'devices': devices,
}

assert 'AI-SYNTHESIZED' not in json.dumps(payload).upper(), \
    'xr: that word belongs to orbis/'
assert all(not d['claim_checked'] for d in devices.values()), \
    'xr: nothing here has been checked; a true claim_checked needs a build ' \
    'that actually opened the page'

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text(json.dumps(payload, indent=1, sort_keys=True) + '\n')
print('xr: %d devices from %d vendors; %d name an eye-protection standard '
      '(%d in the device itself), %d do not; %d procurement flags. Rooms: '
      '%d of %d require eye protection, %d require eye AND head protection.'
      % (len(devices), payload['counts']['vendors'], len(_std), len(_own),
         len(_nostd), len(FLAGS), len(eye_rooms), len(rooms),
         len(both_rooms)))
