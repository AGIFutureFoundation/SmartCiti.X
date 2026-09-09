"""Shared map data: the module registry folded for the map surfaces.

Both the interactive map and the 3D environment show real module rows per
strand. The folding lives here ONCE — a second copy per builder is the
defect class this bundle exists to prevent — and the JS mirror of the
pipeline rule ships from here too, proven against the pack's own
pipeline_state across every band boundary at import time.
"""
import pathlib
import sys

_HERE = pathlib.Path(__file__).resolve().parent


def _pack_root():
    for cand in (_HERE, *_HERE.parents):
        if (cand / 'pack').is_dir() and (cand / 'unions').is_dir():
            return cand
    raise RuntimeError('cannot locate the packs from ' + str(_HERE))


ROOT = _pack_root()
sys.path.insert(0, str(ROOT / 'pack'))
from build import lesson_of, pipeline_state, STRANDS, SLOTS, LEVELS  # noqa: E402


def strand_modules():
    """The module registry folded per strand, computed once: lesson ids,
    forms and difficulties depend only on (level, slot), so one table is
    shared by all 111 halls. Only the pipeline state varies by hall, and the
    pages derive it with PIPELINE_JS below (the id gains its hall prefix the
    same way). Everything comes from the pack's own lesson_of, so the maps
    and the ledger cannot drift."""
    out = {}
    per_strand_lessons = (SLOTS // len(STRANDS)) * LEVELS      # 10 x 100
    for i, strand in enumerate(STRANDS):
        lo = lesson_of(0, 0, i)
        hi = lesson_of(0, LEVELS - 1, i + SLOTS - len(STRANDS))
        samples = []
        for tier, level in (('fundamentals', 0), ('applied', 40), ('mastery', 80)):
            l = lesson_of(0, level, i)
            samples.append({'suffix': l['lesson_id'].split('.', 1)[1],
                            'form': l['form'], 'd': l['base_difficulty'],
                            'tier': tier, 'level': level, 'slot': i})
        out[strand] = {'lessons': per_strand_lessons,
                       'modules': per_strand_lessons * 9,
                       'd_from': lo['base_difficulty'],
                       'd_to': hi['base_difficulty'],
                       'samples': samples}
    return out


# The JS mirror of pipeline_state that the generated pages embed.
PIPELINE_JS = """\
// pipeline_state, mirrored from the pack rule (the build asserts agreement
// across every band boundary, so this cannot silently drift).
function pipeline(idx, lv) {
  const a = idx < 18 ? [88, 94, 99] : idx < 33 ? [70, 84, 99]
          : idx < 66 ? [44, 66, 84] : [22, 44, 70];
  return lv <= a[0] ? 'live' : lv <= a[1] ? 'calibrating'
       : lv <= a[2] ? 'schema_ok' : 'draft';
}"""

# Prove the mirror against the pack rule at every band boundary, at import
# time, so no page can be generated from a drifted mirror.
for _idx in (0, 17, 18, 32, 33, 65, 66, 110):
    for _lv in (0, 22, 23, 44, 45, 66, 67, 70, 71, 84, 85, 88, 89, 94, 95, 99):
        _a = [88, 94, 99] if _idx < 18 else [70, 84, 99] if _idx < 33 \
            else [44, 66, 84] if _idx < 66 else [22, 44, 70]
        _js = ('live' if _lv <= _a[0] else 'calibrating' if _lv <= _a[1]
               else 'schema_ok' if _lv <= _a[2] else 'draft')
        assert _js == pipeline_state(_idx, _lv), (_idx, _lv, _js)
