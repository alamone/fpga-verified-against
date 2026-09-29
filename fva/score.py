"""Heuristic hardware-fidelity score, v0 — every point traceable to a quoted line.

The score answers one question: how much EVIDENCE is there that this core was checked against the
real hardware rather than against MAME? It does not penalize using MAME as a reference — only
using it as the thing the core is verified against, or copying it without saying so.

Each rule counts once per comment (or readme sentence); per module a rule contributes
pts x log2(1 + times fired) — diminishing returns. Hardware points and MAME points are kept separate:

  HARDWARE                                         MAME
  +1  hw_specific  schematic page, part number,    -0.5 mame_cited      MAME file/line cited
                   PROM/PAL with board location,   -2   mame_verified   "matches / verified
                   decap / netlist                                       against MAME"
  +2  hw_verified  "verified/tested on the real    -3   mame_transcribed "translated / ported
                   board/PCB/hardware"                                   from MAME source"
  +3  hw_measured  measurement on hardware that    -1   mame_surrogate  MAME's own guess or
                   states a number                                       approximation kept
  +3  mame_diverge departs from MAME for a stated  -1   copied_text     6-word run shared
                   reason ("MAME is wrong here")                         with the driver, in a
                                                                         module that does not
                                                                         declare it

Module fidelity = (hw + 1) / (hw + mame + 2)
Core score      = 100 x line-weighted mean of fidelity over modules that HAVE evidence (the readme
                  counts as one module weighted like 25% of the code). Modules with none are
                  unknown, reported as COVERAGE (share of the core's own code with evidence), not
                  averaged in as 50. CONFIDENCE comes from the total evidence points.
Libraries (CPU/sound cores, the MiSTer framework) are outside the score, as in analyze.py.
"""
import collections
import json
import os
import re
import sys

from . import analyze as A

# The ORIGINAL arcade hardware, unambiguously. "Real hardware" alone is NOT here: in MiSTer circles
# it often means the MiSTer board itself ("tested on real hardware on a CRT"), so it is its own,
# weaker rule (hw_verified_unclear) and never counts as a measurement.
PCBW = (r"\bpcbs?\b|original\s+(?:hardware|hw|pcbs?|board|boards|machine|arcade)|arcade\s+(?:board|pcb|hardware)|"
        r"real\s+(?:pcb|board|arcade)|scheda\s+(?:reale|originale)|\bsilicon\b")
HWW_UNCLEAR = r"real\s+(?:hardware|hw)|on\s+(?:the\s+)?(?:hardware|hw)\b|\bsu\s+hw\b|\bhw\s+reale|hardware\s+reale"
RULES = [
    # Words are case-insensitive via (?i:...); board locations stay case-sensitive (7U, 11C) and
    # only count next to a chip word, so the full A-Z grid does not match table values; sizes
    # like 4KB / 8KB are not locations.
    ("hw_specific", +0.5, re.compile(
        r"(?i:schematics?\s*(?:page|p\.|sheet|sh\.)?\s*\d|\bsheet\s*\d+|\bSP-\d{3}\b|\bfigure\s*\d+-\d+|"
        r"\b(?:page|sheet)\s*\d+\s*(?:/|of)\s*\d+|"
        r"\b74(?:LS|S|HC|HCT|F|ALS|AS)\d{2,4}\b|\b82S\d{2,3}\b|\b1360\d\d-\d{3,4}\b|jedutil|\bdumped\b|"
        r"decap|die shot|netlist|"
        # a plain statement that schematics were a source or a cross-check
        r"(?:based on|from|according to|per|acc\. to|following|using|against|cross-checked with|and)\s+"
        r"(?:[\w.'/-]+\s+){0,6}?schematics?\b)|"
        r"\b(?:PROM|PAL|GAL|PLA|PLS|ROMs?|RAMs?|latch|LS\d+|74\w+)\s*@?\s*\d{1,2}(?![KMG]B\b)[A-Z]{1,2}\b|"
        r"(?:@|\bat)\s*\d{1,2}(?![KMG]B\b)[A-Z]{1,2}\b|"
        r"\b\d{1,2}(?![KMG]B\b)[A-Z]{1,2}\s+(?:PROM|PAL|GAL|PLA|latch|ROM|RAM)\b")),
    ("hw_measured", +3, re.compile(
        rf"(?:measur|logic analy|oscillo|\bscope\b|misurat)[^\n]{{0,80}}(?:{PCBW})[^\n]{{0,80}}\d|"
        rf"(?:{PCBW})[^\n]{{0,60}}(?:measur|logic analy|oscillo|misurat)[^\n]{{0,60}}\d", re.I)),
    ("hw_verified", +2, re.compile(
        rf"(?:verified|tested|checked|validated|confirmed|compared|verificat|provato|confrontat)[^\n]{{0,50}}"
        rf"(?:against|on|with|contro|su|sul)\s+(?:the\s+|an?\s+)?(?:{PCBW})", re.I)),
    ("hw_verified_unclear", +1, re.compile(
        rf"(?:verified|tested|checked|validated|confirmed|verificat|provato)[^\n]{{0,50}}(?:{HWW_UNCLEAR})", re.I)),
    # Specific forms only. Bare "differ", "bug", "never", "doesn't" near MAME misfired on
    # "0 of 92160 pixels differ" (a MAME MATCH), "MAME trace during bug hunt", "does nothing".
    ("mame_diverge", +3, re.compile(
        r"\bmame(?:'s)?\b[^\n]{0,40}\b(?:is|was|gets? (?:it|this))\s+(?:wrong|incorrect|inaccurate)\b|"
        r"\b(?:wrong|incorrect|inaccurate)\s+in\s+mame\b|\bbug\s+in\s+mame\b|\bmame(?:'s)?\s+bug\b|"
        r"\bunlike\s+mame\b|\bcontrary\s+to\s+mame\b|\bdiffers?\s+from\s+mame\b|\bdiverg\w*\s+from\s+mame\b|"
        r"\bmame\b[^\n]{0,30}\b(?:does\s*n[o']t|doesn't|cannot|can't|never)\s+(?:model|emulate|implement|reproduce|"
        r"compute|execute|arbitrate|handle|support|do)\w*\b|\bmame\s+(?:stubs|ignores|models none)\b|"
        r"(?:schematics?|pcb|hardware|silicon)\s+(?:and|vs\.?)\s+mame\s+disagree|disagree\w*\s+with\s+mame|"
        r"\bmame\s+non\s+\w+|\bsbaglia\b|diversamente\s+da\s+mame", re.I)),
    ("mame_verified", -2, re.compile(
        r"(?:match(?:es|ed|ing)?|verified|tested|checked|bit-exact|pixel-exact|identical|same as|provato|confrontat|"
        r"verificat|uguale)[^\n]{0,50}\bmame\b(?![^\n]{0,20}(?:wrong|bug|incorrect|convention))", re.I)),
    # \b before each verb: "reported in MAME" must not read as "ported from MAME" (jtrastan, v0.2)
    ("mame_transcribed", -3, re.compile(
        r"\b(?:translated|transcribed|trascritt|ported|copied|converted|tradott)\b[^\n]{0,40}\bmame\b|"
        r"\bmame\b[^\n]{0,40}(?:verbatim|1:1|pari pari)|based (?:primarily |mostly )?on (?:the )?mame", re.I)),
    ("mame_surrogate", -1, re.compile(
        r"mame[^\n]{0,60}(?:surrogat|approximat|placeholder|guess|hack|assum)", re.I)),
    ("mame_cited", -0.5, re.compile(r"\bmame\b|\b[a-z0-9_]+\.(?:cpp|ipp)\b(?::\d+)?", re.I)),
]

# A rule does not fire when its comment also matches its veto: a negation of the claim, or a
# context showing the "hardware" is the MiSTer/FPGA itself (SignalTap is Intel's FPGA logic
# analyzer: "MEASURED ON HARDWARE (SignalTap ...)" is a measurement of the core, not the PCB).
_NEG = r"(?:\bnot\b|n't\b|\bnever\b|\byet to\b|\bnon\b)[^\n]{0,25}"
_FPGA = (r"signaltap|signal\s*tap|\bde10\b|\bmister\b|\bfpga\b|\bcrt\b|\bsimulat|\bverilator\b|"
         r"\bm10k\b|build\s*#|timing closure|\bslack\b|quartus|\bsynthes")
VETO = {
    "hw_verified": re.compile(rf"{_NEG}(?:verified|tested|checked|validated|confirmed|verificat|provato)|"
                              rf"(?:pcb|hardware)-verified[^\n]{{0,5}}$|\bnot\s+\w*-?verified", re.I),
    "hw_verified_unclear": re.compile(rf"{_NEG}(?:verified|tested|checked|validated|confirmed)|{_FPGA}|"
                                      r"against\s+mame", re.I),
    "hw_measured": re.compile(_FPGA, re.I),
    "mame_verified": re.compile(r"expect[^\n]{0,40}(?:fail|differ)|\bnot\s+\w*-?verified", re.I),
    "mame_surrogate": re.compile(r"rather than guess", re.I),
}
HW_RULES = {"hw_specific", "hw_measured", "hw_verified", "hw_verified_unclear", "mame_diverge", "hw_files"}

# Hardware documentation shipped in the core's own folder: schematic captures, PAL/GAL equation
# dumps, schematic PDFs. The comment rules cannot see these (jtcores keeps 870 files under sch/).
HW_FILE = re.compile(r"\.(?:kicad_sch|sch|jed|pld)$|/(?:sch|schematics?|pals?)/[^/]+$|schem[^/]*\.pdf$", re.I)


# Not evidence about THIS arcade board: files inside bundled libraries (jt12's lab/arduino.kicad_sch
# turns up in a dozen cores), bench "lab" folders, and MiSTer accessory boards under hardware/
# (IGS PGM's PGMPassThru / PGMPicoProg). Inside a sch/ folder only documents count, not KiCad
# project settings.
HW_FILE_SKIP_DIRS = set(A.LIB_DIRS) | {"lab", "hardware"}
HW_DOC_EXT = re.compile(r"\.(?:pdf|kicad_sch|sch|jed|pld|eqn|txt|png|jpe?g|gif)$", re.I)


def hw_file_ok(path):
    parts = [p.lower() for p in path.split("/")[:-1]]
    return not any(p in HW_FILE_SKIP_DIRS for p in parts) and bool(HW_DOC_EXT.search(path))


# A hardware reference proves nothing about hardware if MAME's driver for the game already says
# the same thing (operator, 2026-09-28: Arabian cites "SP-237 sheet 8B", and so does arabian.cpp).
# Each part number, sheet, schematic package and board location in the comment is looked up in
# the MAME files compared for this core; if ALL are there, the item becomes hw_ref_in_mame (0 pts,
# shown as neutral). Only references MAME does not carry count (+0.5): the developer likely had the
# documentation itself. A statement with no concrete reference ("based on the schematics") stays.
HW_TOKEN = re.compile(r"\b(?:74(?:LS|S|HC|HCT|F|ALS|AS)\d{2,4}|82S\d{2,3}|SP-\d{3}|1360\d\d-\d{3,4})\b|"
                      r"\bsheet\s*\d+|(?<![\w.$])\d{1,2}(?![KMG]B\b)[A-Z]{1,2}\b", re.I)


def refs_all_in_mame(text, mame_text):
    toks = [m.group(0) for m in HW_TOKEN.finditer(text)]
    if not toks or not mame_text:
        return False
    for t in toks:
        if re.fullmatch(r"\d{1,2}[A-Z]{1,2}", t, re.I):   # board location
            # Any case, with a non-alphanumeric on each side: MAME writes locations lower-case
            # inside ROM names ("dk3c.5l", "136002-125.d7"), which is exactly where a core could
            # take them from; the guard keeps hex like "0x2a" from counting.
            if not re.search(rf"(?<![A-Za-z0-9]){re.escape(t)}(?![A-Za-z0-9])", mame_text, re.I):
                return False
        elif not re.search(re.escape(re.sub(r"\s+", " ", t)).replace(r"\ ", r"\s*"), mame_text, re.I):
            return False
    return True


def mame_locations(text, mame_files):
    """[(token, mame_relpath, line)] — where MAME's driver files give each hardware reference, so a
    reader can open the MAME line and compare for themselves."""
    out = []
    for m in HW_TOKEN.finditer(text):
        t = m.group(0)
        if re.fullmatch(r"\d{1,2}[A-Z]{1,2}", t, re.I):
            pat = re.compile(rf"(?<![A-Za-z0-9]){re.escape(t)}(?![A-Za-z0-9])", re.I)
        else:
            pat = re.compile(re.escape(re.sub(r"\s+", " ", t)).replace(r"\ ", r"\s*"), re.I)
        for rel, body in mame_files.items():
            hit = pat.search(body)
            if hit:
                out.append((t, rel, body.count("\n", 0, hit.start()) + 1))
                break
    return out


_shingle_cache = {}


def mame_shingle_line(comment, rel, body):
    """Line in a MAME file where a comment's shared 6-word run occurs (copied_text evidence)."""
    if rel not in _shingle_cache:
        words = [(w, body.count("\n", 0, m.start()) + 1) for m in A.WORD.finditer(body.lower()) for w in [m.group(0)]]
        idx = {}
        for i in range(len(words) - 5):
            idx.setdefault(" ".join(w for w, _ in words[i:i + 6]), words[i][1])
        _shingle_cache[rel] = idx
    ws = A.WORD.findall(comment.lower())
    for i in range(len(ws) - 5):
        ln = _shingle_cache[rel].get(" ".join(ws[i:i + 6]))
        if ln:
            return ln
    return None


PTS = {name: pts for name, pts, _ in RULES}
PTS["hw_ref_in_mame"] = 0
PTS["copied_text"] = -1
PTS["hw_files"] = +2


def weigh(counts):
    """Diminishing returns: each rule contributes pts * log2(1 + times it fired) per module, so the
    tenth routine citation adds far less than the first and one strong item is not drowned out."""
    import math
    hw = sum(PTS[r] * math.log2(1 + n) for r, n in counts.items() if r in HW_RULES)
    mame = sum(-PTS[r] * math.log2(1 + n) for r, n in counts.items() if r not in HW_RULES)
    return hw, mame


def classify(text, mame_text=None):
    fired = []
    for name, pts, pat in RULES:
        if pat.search(text) and not (name in VETO and VETO[name].search(text)):
            if name == "mame_cited" and any(f[0].startswith("mame_") for f in fired):
                continue  # a stronger MAME rule already covers this comment
            fired.append((name, pts))
    if mame_text and any(f[0] == "hw_specific" for f in fired) and refs_all_in_mame(text, mame_text):
        fired = [("hw_ref_in_mame", 0) if f[0] == "hw_specific" else f for f in fired]
    return fired


def score_core(name, core_dir=None, ev=None, repo_files=()):
    assert core_dir and ev is not None, "core_dir and evidence are required"
    files, _ = A.own_hdl(core_dir)
    mame_files = {f: open(os.path.join(A.MAME, f), encoding="utf-8", errors="replace").read()
                  for f in ev.get("mame_files_compared", []) if os.path.exists(os.path.join(A.MAME, f))}
    mame_text = "\n".join(mame_files.values())
    copied = collections.Counter(x["at"].split(":")[0] for x in ev["A_shared_text"])
    modules, items = [], []
    for f in files:
        ext = os.path.splitext(f)[1].lower()
        text = open(f, encoding="utf-8", errors="replace").read()
        rel = os.path.relpath(f, core_dir).replace("\\", "/")
        counts = collections.Counter()
        declared = False
        for line, c in A.comments(text, ext):
            for rule, pts in classify(c, mame_text):
                counts[rule] += 1
                declared |= rule == "mame_transcribed"
                it = {"module": rel, "at": f"{rel}:{line}", "rule": rule, "points": pts, "text": c.strip()[:160]}
                if rule == "hw_ref_in_mame":
                    it["mame_refs"] = mame_locations(c, mame_files)
                items.append(it)
        if copied[rel] and not declared:
            counts["copied_text"] += copied[rel]
            for x in ev["A_shared_text"]:
                if x["at"].split(":")[0] != rel:
                    continue
                body = mame_files.get(x["mame"], "")
                ln = mame_shingle_line(x["comment"], x["mame"], body) if body else None
                items.append({"module": rel, "at": x["at"], "rule": "copied_text", "points": -1,
                              "text": x["comment"][:160], "mame_refs": [("shared text", x["mame"], ln)]})
        hw, mame = weigh(counts)
        lines = max(text.count("\n"), 1)
        modules.append({"module": rel, "lines": lines, "hw": hw, "mame": mame,
                        "fidelity": (hw + 1) / (hw + mame + 2)})
    # readme / docs as one pseudo-module
    counts = collections.Counter()
    for d in ("README.md", "readme.md", "README.txt"):
        p = os.path.join(core_dir, d)
        if os.path.exists(p):
            body = open(p, encoding="utf-8", errors="replace").read()
            pos = 0
            for sent in re.split(r"(?<=[.!?])\s+|\n+", body):
                start = body.find(sent, pos)
                if start >= 0:
                    pos = start + len(sent)
                line = body.count("\n", 0, max(start, 0)) + 1
                if re.search(r"keyboard|keys|\.zip|romset|rom set|\.mra", sent, re.I):
                    continue
                for rule, pts in classify(sent, mame_text):
                    counts[rule] += 1
                    it = {"module": d, "at": f"{d}:{line}", "rule": rule, "points": pts, "text": sent.strip()[:160]}
                    if rule == "hw_ref_in_mame":
                        it["mame_refs"] = mame_locations(sent, mame_files)
                    items.append(it)
            break
    hw, mame = weigh(counts)
    code_lines = sum(m["lines"] for m in modules) or 1
    hwf = [f for f in repo_files if HW_FILE.search(f) and hw_file_ok(f)]
    if hwf:
        for f in hwf:
            items.append({"module": "repository files", "at": f, "rule": "hw_files", "points": 2, "text": f})
        fh, fm = weigh(collections.Counter({"hw_files": len(hwf)}))
        modules.append({"module": "repository files", "lines": code_lines * 0.25, "hw": fh, "mame": fm,
                        "fidelity": (fh + 1) / (fh + fm + 2)})
    modules.append({"module": "README", "lines": code_lines * 0.25, "hw": hw, "mame": mame,
                    "fidelity": (hw + 1) / (hw + mame + 2)})
    # A module with no evidence either way is UNKNOWN, not 50/50: it is left out of the mean (which
    # would otherwise drag every core toward 50) and shows up as lower coverage instead.
    scored = [m for m in modules if m["hw"] + m["mame"] > 0]
    total = sum(m["lines"] for m in scored)
    score = 100 * sum(m["fidelity"] * m["lines"] for m in scored) / total if total else None
    code = [m for m in modules if m["module"] != "README"]
    coverage = (sum(m["lines"] for m in code if m in scored) / (sum(m["lines"] for m in code) or 1))
    evidence = sum(m["hw"] + m["mame"] for m in modules)
    conf = "insufficient" if evidence < 5 else "low" if evidence < 20 else "medium" if evidence < 60 else "high"
    by_rule = collections.Counter()
    for it in items:
        by_rule[it["rule"]] += 1
    return {"core": name, "score": None if score is None else round(score), "confidence": conf,
            "coverage": round(100 * coverage), "evidence_points": round(evidence, 1),
            "rule_counts": dict(by_rule), "modules": modules, "items": items}


