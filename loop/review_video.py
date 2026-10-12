#!/usr/bin/env python3
"""
SmartCiti.X : Trade Craft Academy — the 2-minute cycle review video.

Renders exactly 120 seconds from what the loop actually recorded: the cycle
ledger (loop/registry/cycles.json), the latest executed eval gates
(loop/state/evals_latest.json), the latest heartbeat (loop/state/heartbeat.jsonl)
and the course pack (courses/registry/courses.json). Nothing on a card is typed
here; every line is read from those files, so a review cannot report a gate
that did not run.

Footage is the project's own generated clips, kept OUTSIDE the repository
(they are 4-13 MB each and already live on the media CDN). Pass the folder:

    python3 loop/review_video.py --cycle 0 --clips /path/to/clips --out review_c0.mp4

Requires ffmpeg with drawtext. Stdlib only.
"""
import argparse, json, os, pathlib, shutil, subprocess, sys, tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
BOLD = next((f for f in ["/usr/share/fonts/truetype/google-fonts/Poppins-Bold.ttf",
                         "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"] if os.path.exists(f)), None)
REG = next((f for f in ["/usr/share/fonts/truetype/google-fonts/Poppins-Regular.ttf",
                        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"] if os.path.exists(f)), None)
MONO = next((f for f in ["/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf"] if os.path.exists(f)), REG)
INK, PAPER, GREEN, OCHRE = "0x10241c", "0xf1ebdf", "0x1f6b4a", "0xa86a10"
ENC = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "27", "-pix_fmt", "yuv420p", "-r", "30", "-an"]
TOTAL = 120.0

# The footage library: clip id -> what it shows. Only used to pick footage that
# matches a course's trade; captions come from the registries.
FOOTAGE = {
    "welding": ["02b728a5", "fbecfea5"], "electrical": ["1a3619cd", "ecb309f1"],
    "hvac": ["a792c7a1"], "carpentry": ["0562079c", "674c7bc4"], "heavy": ["333b37e0", "456e9db0"],
    "cosmetology": ["2e423e2f", "710df385", "77d1cfdd"], "crew": ["a6cb64bd", "7db6bdeb", "2213746f"],
    "maps": ["8e25662a", "c4cabe6f", "c8676b93", "b3920f62", "96268dae", "f47b4ca0"],
    "boards": ["a7208bb9", "cc3963c0", "c147cf33"],
}


class Cutter:
    def __init__(self, work, clips):
        self.work, self.clips, self.parts, self.n, self.t = work, clips, [], 0, 0.0

    def _tf(self, text):
        self.n += 1
        p = os.path.join(self.work, f"t{self.n}.txt")
        open(p, "w", encoding="utf-8").write(text)
        return p

    def _run(self, args, out, dur):
        r = subprocess.run(["ffmpeg", "-v", "error", "-y"] + args + ENC + [out])
        if r.returncode:
            sys.exit("ffmpeg failed on " + out)
        self.parts.append(out)
        self.t += dur

    def card(self, dur, kicker, title, body="", mono=False):
        out = os.path.join(self.work, f"p{len(self.parts):03d}.mp4")
        face = MONO if mono else REG
        size = 20 if mono else 22
        tsize = max(30, min(50, int(1900 / max(1, len(title)))))
        vf = (f"drawbox=x=80:y=150:w=6:h=110:color={GREEN}:t=fill,"
              f"drawtext=expansion=none:fontfile={BOLD}:textfile={self._tf(kicker)}:x=110:y=110:fontsize=22:fontcolor={GREEN},"
              f"drawtext=expansion=none:fontfile={BOLD}:textfile={self._tf(title)}:x=110:y=150:fontsize={tsize}:fontcolor={INK},"
              f"drawtext=expansion=none:fontfile={face}:textfile={self._tf(body or ' ')}:x=112:y=235:fontsize={size}:line_spacing=8:fontcolor={INK}@0.85,"
              f"drawtext=expansion=none:fontfile={BOLD}:textfile={self._tf('SmartCiti.X  |  Trade Craft Academy  |  powered by AGI Corp  |  loop review')}:x=110:y=684:fontsize=16:fontcolor={INK}@0.55,"
              f"fade=t=in:st=0:d=0.4,fade=t=out:st={dur-0.4}:d=0.4")
        self._run(["-f", "lavfi", "-i", f"color=c={PAPER}:s=1280x720:d={dur}:r=30", "-vf", vf], out, dur)

    def clip(self, dur, cid, label, caption):
        out = os.path.join(self.work, f"p{len(self.parts):03d}.mp4")
        src = os.path.join(self.clips, cid + ".mp4")
        vf = (f"scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,"
              f"drawbox=x=0:y=596:w=1280:h=124:color=black@0.6:t=fill,"
              f"drawtext=expansion=none:fontfile={BOLD}:textfile={self._tf(label)}:x=48:y=614:fontsize=20:fontcolor=0x9fe0bf,"
              f"drawtext=expansion=none:fontfile={REG}:textfile={self._tf(caption)}:x=48:y=648:fontsize=27:fontcolor=white,"
              f"fade=t=in:st=0:d=0.3,fade=t=out:st={dur-0.3}:d=0.3")
        # loop short sources so any duration can be filled
        self._run(["-stream_loop", "-1", "-i", src, "-t", f"{dur:.3f}", "-vf", vf], out, dur)

    def finish(self, out):
        lst = os.path.join(self.work, "list.txt")
        open(lst, "w", encoding="utf-8").write("".join(f"file '{p}'\n" for p in self.parts))
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst,
                        "-c", "copy", "-movflags", "+faststart", out], check=True)
        d = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                           "-of", "csv=p=0", out]).decode().strip())
        return d


def wrap(s, n=64):
    words, lines, cur = str(s).split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 > n:
            lines.append(cur); cur = w
        else:
            cur = (cur + " " + w).strip()
    if cur:
        lines.append(cur)
    return lines


def footage_for(course):
    t = (course.get("trade", "") + " " + course.get("title", "")).lower()
    for key, words in [("welding", ["weld"]), ("electrical", ["electric"]), ("hvac", ["hvac"]),
                       ("carpentry", ["carpent", "framing"]), ("heavy", ["heavy", "equipment"]),
                       ("cosmetology", ["hair", "nail", "esthet", "cosmet"]), ("electrical", ["robot", "cobot", "mechatron"]),
                       ("crew", ["leader"]), ("carpentry", ["plumb"])]:
        if any(w in t for w in words):
            return FOOTAGE[key]
    return FOOTAGE["crew"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cycle", type=int, required=True)
    ap.add_argument("--clips", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--next", default="", help="one line naming the next checkpoint")
    a = ap.parse_args()

    ledger = json.load(open(ROOT / "loop/registry/cycles.json", encoding="utf-8"))
    cyc = next((c for c in ledger["cycles"] if c["n"] == a.cycle), None)
    if cyc is None:
        sys.exit(f"cycle {a.cycle} is not in the ledger; add it first (node loop/cycle.mjs add)")
    ev_path, hb_path = ROOT / "loop/state/evals_latest.json", ROOT / "loop/state/heartbeat.jsonl"
    if not ev_path.is_file():
        sys.exit("loop/state/evals_latest.json is missing: run `node loop/evals.mjs` first")
    if not hb_path.is_file():
        sys.exit("loop/state/heartbeat.jsonl is missing: run `node loop/heartbeat.mjs` first")
    ev = json.load(open(ev_path, encoding="utf-8"))
    hb_lines = hb_path.read_text(encoding="utf-8").strip().splitlines()
    # Bind the review to the SELECTED cycle: the gates it recorded, and the last
    # heartbeat taken before it ended (not whatever ran most recently).
    beats = [json.loads(l) for l in hb_lines if l.strip()]
    ended = str(cyc.get("ended") or "")
    before = [b for b in beats if str(b.get("ts", "")) <= ended] if ended else beats
    hb = (before or beats or [{"ok": cyc.get("heartbeat_ok", False), "checks": []}])[-1]
    courses = json.load(open(ROOT / "courses/registry/courses.json", encoding="utf-8"))["courses"]

    work = tempfile.mkdtemp(prefix="review_")
    try:
        render(a, ledger, cyc, ev, hb, courses, work)
    finally:
        shutil.rmtree(work, ignore_errors=True)


def render(a, ledger, cyc, ev, hb, courses, work):
    c = Cutter(work, a.clips)
    gates = cyc.get("gates") or ev["gates"]
    passed = sum(g["status"] == "pass" for g in gates)
    planned = ledger["loop"].get("cycles_planned", "?")

    c.card(6, f"CYCLE {cyc['n']} OF {planned}  /  2:00 REVIEW", f"Sprint {cyc.get('sprint','')}",
           "\n".join(wrap(f"{cyc.get('started','')[:16].replace('T',' ')} UTC to {str(cyc.get('ended',''))[:16].replace('T',' ')} UTC. "
                          f"{passed} of {len(gates)} gates passing, {cyc.get('checks_total','?')} checks.", 60)))
    # what shipped
    shipped = cyc.get("shipped", [])
    c.card(10, "01  WHAT SHIPPED THIS CYCLE", f"{len(shipped)} items",
           "\n".join(("- " + "\n  ".join(wrap(s, 84)[:2])) for s in shipped[:6]))
    # wired / featured courses on footage
    wired = [(co, m) for co in courses for m in co["modules"] if m.get("wired")]
    feature = wired[:3] or [(co, co["modules"][0]) for co in courses[:3]]
    for co, m in feature:
        stages = m.get("stages") or []
        floor = next((s.get("text", "") for s in stages if s.get("stage") == "floor"), "")
        c.clip(8, footage_for(co)[0], f"{co['code']}  |  {m['title'][:60]}",
               (wrap(floor or co["title"], 78) or [co["title"]])[0])
    # gate board
    board = "\n".join(f"{g['id']}  {g['status'].upper():6}  {g['name'][:34]:34}  {str(g.get('detail',''))[:30]}" for g in gates)
    c.card(12, "02  EVAL GATES, EXECUTED", f"{passed} / {len(gates)} pass", board, mono=True)
    # heartbeat
    hbt = "\n".join(f"{'ok  ' if k.get('ok') else 'WARN'}  {k['name'][:28]:28}  {str(k.get('detail',''))[:40]}" for k in hb.get("checks", [])[:8])
    c.card(9, "03  HEARTBEAT", "alive" if hb.get("ok") else "attention", hbt, mono=True)
    # agents
    ag = "\n".join(f"{x['name'][:20]:20}  {x.get('result','')[:58]}" for x in cyc.get("agents", [])[:7])
    c.card(10, "04  TEAM AGENTS ON THIS CYCLE", f"{len(cyc.get('agents', []))} agents", ag, mono=True)
    # course coverage montage
    coverage = [co for co in courses if co["code"] not in {f[0]['code'] for f in feature}]
    tail_cards = 6 + 6  # next + status
    remaining = TOTAL - c.t - tail_cards
    per = max(4.0, remaining / max(1, min(len(coverage), 8)))
    i = 0
    while TOTAL - c.t - tail_cards > 0.05 and i < len(coverage):
        co = coverage[i]
        dur = min(per, TOTAL - c.t - tail_cards)
        if dur < 2:
            break
        halls = ", ".join(co.get("halls", [])) or "outside the 111-hall roster"
        c.clip(dur, footage_for(co)[i % len(footage_for(co))], f"{co['code']}  |  {co['trade'].upper()}  |  {co['status'].upper()}",
               f"{co['title'][:52]}  ->  {halls}"[:80])
        i += 1
    gap = TOTAL - c.t - tail_cards
    if gap > 0.05:
        c.clip(gap, FOOTAGE["maps"][a.cycle % len(FOOTAGE["maps"])], "THE CITY IS THE CLASSROOM", "Bay Area training city and four Louisiana parishes")
    c.card(6, "NEXT", "Next checkpoint", "\n".join(wrap(a.next or "See the cycle ledger.", 60)))
    c.card(6, "STATUS, PLAINLY", "Built and in test. Not yet deployed.",
           "Courses are planned drafts. No accreditation, endorsement\nor partner is claimed. Efficacy is not yet measured.")
    d = c.finish(a.out)
    print(f"{a.out}: {d:.3f} s, {os.path.getsize(a.out)//1024} KB")
    if abs(d - TOTAL) > 0.5:
        sys.exit(f"duration {d:.3f} s is not 120 +/- 0.5 s")


if __name__ == "__main__":
    main()
