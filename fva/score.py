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
        r"\b74(?:LS|S|HC|HCT|F|ALS|AS)\d{2,4}\b|\b82S\d{2,3}\b|\b1360\d\d-\d{3,4}\b|jedutil|"
        # v0.6: "dumped" only next to what gets dumped; alone it fired on "dumped duplicates"
        r"\bdumped\b[^\n]{0,30}\b(?:PROMs?|PALs?|GALs?|PLAs?|MCUs?|ROMs?|chips?|fuses?)\b|"
        r"\b(?:PROMs?|PALs?|GALs?|PLAs?|MCUs?|ROMs?|chips?|fuses?)\b[^\n]{0,30}\bdumped\b|"
        r"decap|die shot|netlist|"
        # a plain statement that schematics were a source or a cross-check
        r"(?:based on|from|according to|per|acc\. to|following|using|against|cross-checked with|and)\s+"
        r"(?:[\w.'/-]+\s+){0,6}?schematics?\b|"
        # v0.9: "This follows the SCHEMATIC, not MAME" (Atari System 2); kept close, since "easier to
        # follow without referring to schematic" (Super Breakout) is not a source statement
        r"\bfollow(?:s|ed)?\s+(?:the\s+)?(?:\w+\s+)?schematics?\b)|"
        r"\b(?:PROM|PAL|GAL|PLA|PLS|ROMs?|RAMs?|latch|LS\d+|74\w+)\s*@?\s*\d{1,2}(?![KMG]B\b)[A-Z]{1,2}\b|"
        r"(?:@|\bat)\s*(?!0X\b)\d{1,2}(?![KMG]B\b)[A-Z]{1,2}\b|"   # not a hex prefix ("@ 0X")
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
        # v0.9: bare "get wrong" too: "the DIP Flip Screen (which both MAME drivers get wrong)" (Fuuki)
        r"\bmame(?:'s)?\b[^\n]{0,40}\b(?:is|was|gets?(?: it| this)?)\s+(?:wrong|incorrect|inaccurate)\b|"
        r"\b(?:wrong|incorrect|inaccurate)\s+in\s+mame\b|\bbug\s+in\s+mame\b|\bmame(?:'s)?\s+bug\b|"
        r"\bunlike\s+mame\b|\bcontrary\s+to\s+mame\b|\bdiffers?\s+from\s+mame\b|\bdiverg\w*\s+from\s+mame\b|"
        r"\bmame\b[^\n]{0,30}\b(?:does\s*n[o']t|doesn't|cannot|can't|never)\s+(?:model|emulate|implement|reproduce|"
        r"compute|execute|arbitrate|handle|support|do)\w*\b|\bmame\s+(?:stubs|ignores|models none)\b|"
        r"(?:schematics?|pcb|hardware|silicon)\s+(?:and|vs\.?)\s+mame\s+disagree|disagree\w*\s+with\s+mame|"
        r"\bmame\s+non\s+\w+|\bsbaglia\b|diversamente\s+da\s+mame|"
        # v0.9: "the SP-320 schematics document something MAME's model does not" (Toobin, Vindicators)
        r"\b(?:schematics?|pcb|hardware|datasheet|documentation)\b[^\n]{0,40}\bmame(?:'s)?(?:\s+model)?\s+does\s*n[o']t\s*(?:[,.;:—-]|$)|"
        # v0.10: "MAME is NOT the oracle for anything bit-timing here" (Irem M72's 8051); "MAME
        # doesn't update these flags, but documentation says it should" (Irem M90/M107's V35)
        r"\bmame\b[^\n]{0,15}\bis\s+not\s+(?:the|an?|our)\s+(?:oracle|reference|source|authority|model)\b|"
        r"\bmame\b[^\n]{0,60}\bbut\s+(?:the\s+)?(?:documentation|datasheet|data\s*sheet|manual|schematics?|"
        r"hardware|pcb)\s+(?:says|shows|states|documents|has)\b",
        re.I | re.M)),
    # v0.6: "we follow MAME" / "MAME's numbers are what we model" name MAME as the reference as
    # plainly as "matches MAME" (Raiden II's COP DMA keeps MAME's fix-up "until that is confirmed on
    # hardware").
    ("mame_verified", -2, re.compile(
        r"(?:match(?:es|ed|ing)?|verified|tested|checked|bit-exact|pixel-exact|identical|same as|provato|confrontat|"
        r"verificat|uguale)[^\n]{0,50}\bmame\b(?![^\n]{0,20}(?:wrong|bug|incorrect|convention))|"
        r"\b(?:we|i|it|this)\s+(?:follows?|mirrors?)\s+mame\b|\bground[- ]truth\b[^\n]{0,10}\bmame\b|"
        r"\bmame(?:'s)?\b[^\n]{0,40}\bare\s+what\s+we\s+(?:model|use|follow)\b", re.I)),
    # \b before each verb: "reported in MAME" must not read as "ported from MAME" (jtrastan, v0.2)
    # v0.6: "From MAME src/mame/...: <parameters>" and "carried over from MAME" say where the values
    # came from as directly as "ported from".
    ("mame_transcribed", -3, re.compile(
        r"\b(?:translated|transcribed|trascritt|ported|copied|converted|tradott)\b[^\n]{0,40}\bmame\b|"
        r"\b(?:carried over|taken|lifted|borrowed)\s+from\s+mame\b|\bfrom\s+mame\s+src/|"
        r"\bmame\b[^\n]{0,40}(?:verbatim|1:1|pari pari)|based (?:primarily |mostly )?on (?:the )?mame|"
        # v0.8: "a fixed-point VHDL port of MAME's Votrax SC-01 core", "Based on the Votrax SC01-A
        # simulation from MAME" (Astrocade, Q*bert) name MAME as the source as plainly as "ported from".
        r"\bport\s+of\s+mame\b|\bbased on\b[^\n]{0,50}\bfrom\s+mame\b", re.I)),
    ("mame_surrogate", -1, re.compile(
        r"mame[^\n]{0,60}(?:surrogat|approximat|placeholder|guess|hack|assum)", re.I)),
    ("mame_cited", -0.5, re.compile(r"\bmame\b|\b[a-z0-9_]+\.(?:cpp|ipp)\b(?::\d+)?", re.I)),
]

# A rule does not fire when its comment also matches its veto: a negation of the claim, or a
# context showing the "hardware" is the MiSTer/FPGA itself (SignalTap is Intel's FPGA logic
# analyzer: "MEASURED ON HARDWARE (SignalTap ...)" is a measurement of the core, not the PCB).
_NEG = r"(?:\bnot\b|n't\b|\bnever\b|\byet to\b|\bnon\b|\buntil\b|\bnothing\b|\bnone\b)[^\n]{0,25}"
# v0.6: "UNVALIDATED ON HARDWARE" was read as "...VALIDATED ON HARDWARE" (Raiden II, 2026-09-30).
_UN = r"\bun(?:validated|verified|tested|confirmed|checked|measured)\b"
_FPGA = (r"signaltap|signal\s*tap|\bde10\b|\bmister\b|\bfpga\b|\bcrt\b|\bsimulat|\bverilator\b|"
         r"\bm10k\b|build\s*#|timing closure|\bslack\b|quartus|\bsynthes|"
         # v0.6: the MiSTer's own memory and clocking. "none of this crossing has ever run on real
         # silicon" is about the SDRAM controller on the DE10, not the arcade board.
         r"\bsdram\b|\bddr\d?\b|\bpll\b|clock[- ]domain|\bcrossing\b|"
         # v0.9: "HDMI rotation: done, confirmed on hardware" (Bally Sente), "broke the framework's
         # HDMI path (... confirmed on hardware)" (Psikyo): the MiSTer's video output, not the PCB
         r"\bhdmi\b|\bscaler\b")
# v0.9: a measurement someone wishes for is not one: "A PCB measurement should settle it" (Sand
# Scorpion) scored +3 as a measurement.
_WISH = r"\bmeasurements?\s+(?:should|would|could|will|might|is needed|are needed)\b|\bneeds?\s+(?:an?\s+)?(?:pcb\s+)?measur"
# v0.9: comments that say the thing is NOT from MAME were scoring as citing MAME: "This follows the
# SCHEMATIC, not MAME" (Atari System 2), "original RTL, not translated MAME source", "an RTL
# choice, not from MAME" (Fuuki). Neutral, not a departure either: some only say where a value came
# from. The MiSTer high-score saver's "MAME hiscore.dat" is about saving scores, not emulation.
_NOT_MAME = (r",\s*not\s+(?:from\s+)?mame\b|\bnot\s+(?:from|sourced\s+from|taken\s+from|translated|derived\s+from)\s+"
             r"(?:\w+\s+){0,1}mame\b|\brather\s+than\s+(?:from|against|taken\s+from)\s+mame\b|"
             r"hiscore|hi-score|high\s*score\s+(?:sav|support|data|table)")
VETO = {
    "hw_verified": re.compile(rf"{_NEG}(?:verified|tested|checked|validated|confirmed|verificat|provato)|{_UN}|"
                              rf"(?:pcb|hardware)-verified[^\n]{{0,5}}$|\bnot\s+\w*-?verified", re.I),
    "hw_verified_unclear": re.compile(rf"{_NEG}(?:verified|tested|checked|validated|confirmed)|{_UN}|{_FPGA}|"
                                      r"against\s+mame", re.I),
    "hw_measured": re.compile(rf"{_FPGA}|{_NEG}measur|{_UN}|{_WISH}", re.I),
    "mame_cited": re.compile(_NOT_MAME, re.I),
    "mame_verified": re.compile(r"expect[^\n]{0,40}(?:fail|differ)|\bnot\s+\w*-?verified", re.I),
    # v0.10: "full oscillator resolution here ... NOT MAME's 3-or-6-counts approximation" (Irem M72)
    # rejects MAME's approximation rather than keeping it
    "mame_surrogate": re.compile(r"rather than guess|\b(?:not|unlike|instead of|rather than)\s+mame'?s?\b", re.I),
    # v0.6: "MAME ignores it, and so should we" / "MAME ignores them too" AGREE with MAME.
    # v0.10: "this value agrees with MAME, and MAME is not the authority here" (jtharier) hedges, it
    # does not depart
    "mame_diverge": re.compile(r"\bso (?:should|do|does|did) (?:we|i|it|ours?)\b|\bmame\b[^\n]{0,30}\btoo\b|"
                               r"\bagrees?\s+with\s+mame\b", re.I),
    # v0.6: "every equation below is read off SP-316 sheet 3 rather than taken from MAME's main_map"
    # (Blasteroids) is a statement AGAINST copying MAME.
    "mame_transcribed": re.compile(
        r"(?:rather than|instead of|\bnot\b|n't\b|\bnever\b|\bnothing\b)\s+(?:\w+\s+){0,2}?"
        r"(?:taken|ported|copied|translated|transcribed|converted|carried|lifted|borrowed)\b|"
        # v0.8: "This replaced a port of MAME's OLD core" (Seibu SPI's YMF271) is the port going away
        r"\breplac(?:ed|es|ing)\s+(?:\w+\s+){0,2}?port\s+of\b", re.I),
}
# v0.8: a bare "something.cpp" is not necessarily MAME's. LaserdiscGames cites Daphne's lair.cpp and
# ldp1000.cpp, Raiden II its own sim/tb_r2crypt.cpp testbench, Seibu SPI the MiSTer Main's
# user_io.cpp, and Astrocade's ROM tables say "Auto-generated by gen_votrax_roms.cpp" (spot check,
# 2026-09-30): 119 items across 28 cores were scoring as MAME citations. A .cpp citation now counts
# only when the file is not in the core's own repository, is not a testbench or generator by name,
# is not one of the MiSTer Main's files, and the comment does not name another emulator. A comment
# that says "MAME" counts as before, whatever else it cites.
_CPP = re.compile(r"\b[a-z0-9_]+\.(?:cpp|ipp)\b", re.I)
_MAME_WORD = re.compile(r"\bmame\b", re.I)
_OTHER_EMU = re.compile(r"\b(?:daphne|hypseus|singe|main_mister|verilator)\b", re.I)
_OWN_TOOL = re.compile(r"^(?:tb|gen|sim|test)_|_(?:ref|tb|test)\.(?:cpp|ipp)$|^sim_main\.", re.I)
MISTER_MAIN = {"user_io.cpp", "menu.cpp", "mra_loader.cpp", "file_io.cpp", "fpga_io.cpp", "osd.cpp"}


# v0.9: "netlist" means the board's netlist only outside FPGA context. "On this netlist Quartus
# 17.0.2's fitter" (Vindicators), "the same netlist is clean in simulation" (Space Harrier) and
# "segfaults Quartus ... netlist" (NMK16) were scoring as hardware documentation.
_FPGA_RE = re.compile(_FPGA, re.I)
_NETLIST = re.compile(r"netlist", re.I)

_MAME_NAMES = None


def mame_file_names():
    """Every .cpp/.ipp basename in the pinned MAME tree. Some cores ship MAME's own drivers as a
    reference (DECO Cassette's decocass_m.cpp, Champion Baseball's champbas.cpp); citing one of
    those is still citing MAME, so a name MAME has is never treated as the developer's own."""
    global _MAME_NAMES
    if _MAME_NAMES is None:
        import subprocess
        from . import paths
        out = subprocess.run(["git", "-C", paths.MAME_REPO, "ls-tree", "-r", "--name-only", "HEAD"],
                             capture_output=True, text=True, check=True).stdout
        # src/ only: MAME's 3rdparty/ tree (imgui, bgfx ...) is not what a core means by MAME
        _MAME_NAMES = frozenset(p.rsplit("/", 1)[-1].lower() for p in out.splitlines()
                                if p.startswith("src/") and p.endswith((".cpp", ".ipp")))
    return _MAME_NAMES


# v0.10: a .cpp named under the core's own tool folders is the developer's file, wherever else in
# the core it is named bare. Irem M72's V30 says "THIS MODULE IS A TRANSLITERATION OF sim/exec_impl.h
# + sim/loader_impl.h + sim/alu.cpp", then cites `alu.cpp::kDiv` and timed_runner.cpp without the
# folder; those files are not in the repository at the build commit, so v0.8's own-repo check
# missed them, and ten of his own simulator's files scored as MAME citations (operator report of
# Martin Donlon's reply, 2026-10-01).
_TOOL_PATH = re.compile(r"\b(?:sim|sims|tools?|tests?|tb|ver|verif|scripts?|bench|model)/(?:[\w.-]+/)*([a-z0-9_]+\.(?:cpp|ipp))\b",
                        re.I)


def tool_file_names(texts):
    """Every .cpp a core names under one of its tool folders, anywhere in its code or readme."""
    return frozenset(m.group(1).lower() for t in texts for m in _TOOL_PATH.finditer(t))


def cites_mame_file(text, own_names=frozenset()):
    """True when the comment's .cpp citation can be MAME's: see the note above."""
    if _MAME_WORD.search(text):
        return True
    if _OTHER_EMU.search(text):
        return False
    return any(n not in own_names and n not in MISTER_MAIN and not _OWN_TOOL.search(n)
               for n in (m.group(0).lower() for m in _CPP.finditer(text)))


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


# v0.6: the same test for a MEASUREMENT. Raiden II's "Measured on a real PCB: VSync 55.4859 Hz,
# HSync 15.5586 kHz" is MAME's own note in raiden2.cpp, figure for figure; repeating it is not a
# measurement by the developer. A figure with 3+ decimals is specific enough to identify its source;
# if every one in the sentence is in the compared MAME files, the item counts as hw_ref_in_mame.
# Not MHz: a crystal's frequency is a part value every source prints (3.579545 MHz is the NTSC
# colour-burst crystal), so finding it in MAME says nothing; Tropical Angel's "3.579545mhz divided
# by 4 according to measurements by Corrado" is a real measurement of the divider.
MEAS_TOKEN = re.compile(r"(?<![\d.])\d+\.\d{3,}(?![\d.])(?!\s*mhz)", re.I)


def measurements_all_in_mame(text, mame_text):
    toks = MEAS_TOKEN.findall(text)
    return bool(toks and mame_text) and all(
        re.search(rf"(?<![\d.]){re.escape(t)}(?![\d])", mame_text) for t in toks)


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
    """[(token, mame_relpath, line)] — where MAME's driver files give each hardware reference or
    measured figure, so a reader can open the MAME line and compare for themselves."""
    out = []
    for m in [*HW_TOKEN.finditer(text), *MEAS_TOKEN.finditer(text)]:
        t = m.group(0)
        if MEAS_TOKEN.fullmatch(t):
            pat = re.compile(rf"(?<![\d.]){re.escape(t)}(?![\d])")
        elif re.fullmatch(r"\d{1,2}[A-Z]{1,2}", t, re.I):
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


def classify(text, mame_text=None, own_names=frozenset()):
    fired = []
    for name, pts, pat in RULES:
        if pat.search(text) and not (name in VETO and VETO[name].search(text)):
            if name == "mame_cited" and any(f[0].startswith("mame_") for f in fired):
                continue  # a stronger MAME rule already covers this comment
            if name == "mame_cited" and not cites_mame_file(text, own_names):
                continue
            if name == "hw_specific" and _FPGA_RE.search(text) and not pat.search(_NETLIST.sub(" ", text)):
                continue  # the only hardware word was a Quartus or simulation netlist
            fired.append((name, pts))
    if mame_text and any(f[0] == "hw_specific" for f in fired) and refs_all_in_mame(text, mame_text):
        fired = [("hw_ref_in_mame", 0) if f[0] == "hw_specific" else f for f in fired]
    if mame_text and any(f[0] == "hw_measured" for f in fired) and measurements_all_in_mame(text, mame_text):
        fired = [("hw_ref_in_mame", 0) if f[0] == "hw_measured" else f for f in fired]
    # one neutral item per sentence, even when a reference and a measurement both came from MAME
    seen, out = set(), []
    for f in fired:
        if f[0] not in seen:
            seen.add(f[0])
            out.append(f)
    return out


_DECOR = re.compile(r"^[\W_]*$")
_TABLE_ROW = re.compile(r"\S {3,}\S.* {3,}\S|\|[^|]*\|[^|]*\|")
_SENT_END = re.compile(r"(?<=[.!?])\s+(?=\S)")
_ABBREV = re.compile(r"(?:\b(?:e\.g|i\.e|vs|etc|approx|fig|no|ver|cf)\.|\b[A-Z]\.)$", re.I)


def sentences(text, ext):
    """(line_no, sentence) for the comments in an HDL file, read the way a person reads them.

    v0.6. The rules used to see one comment LINE at a time, so a sentence wrapped across lines lost
    its second half: Raiden II's "Until that is confirmed on hardware we / follow MAME" scored as
    hardware verification. Consecutive whole-line comments now form a block (a trailing comment
    after code stays on its own: those annotate one line each); a blank or purely decorative
    comment line (====, ----) ends a paragraph; paragraphs are split into sentences. The line
    reported is the one the sentence starts on.
    """
    lines = text.splitlines()
    blocks = []                                   # each: [(line_no, text)]
    prev = None
    if ext in (".vhd", ".vhdl"):
        for i, ln in enumerate(lines, 1):
            if "--" not in ln:
                prev = None
                continue
            code, com = ln.split("--", 1)
            whole = not code.strip()
            if whole and prev == i - 1 and blocks:
                blocks[-1].append((i, com))
            else:
                blocks.append([(i, com)])
            prev = i if whole else None
    else:
        for m in re.finditer(r"//[^\n]*|/\*.*?\*/", text, re.S):
            start = text.count("\n", 0, m.start()) + 1
            line_start = text.rfind("\n", 0, m.start()) + 1
            whole = not text[line_start:m.start()].strip()
            if m.group(0).startswith("/*"):
                body = m.group(0)[2:-2]
                blocks.append([(start + k, l.strip().lstrip("*")) for k, l in enumerate(body.split("\n"))])
                prev = None
                continue
            com = m.group(0)[2:].lstrip("/")
            if whole and prev == start - 1 and blocks:
                blocks[-1].append((start, com))
            else:
                blocks.append([(start, com)])
            prev = start if whole else None
    out = []
    for blk in blocks:
        para = []
        for ln, t in blk + [(None, "")]:
            t = t.strip()
            if ln is None or not t or _DECOR.match(t):
                if para:
                    out.extend(_split(para))
                para = []
                continue
            # A table row (columns aligned with runs of spaces, or | separators) is read on its
            # own: joining rows put words from different rows side by side (Raiden II's
            # SDRAM-fetch benchmark table in Raiden2.sv read as one 300-character sentence).
            if _TABLE_ROW.search(t):
                if para:
                    out.extend(_split(para))
                para = []
                out.append((ln, t))
                continue
            para.append((ln, t))
    return out


_MD_BREAK = re.compile(r"^(?:[-*+]\s|\d+[.)]\s|#|>|```|~~~)")


def readme_sentences(body):
    """(line_no, sentence) for a readme, read the way sentences() reads comments.

    v0.9. Readmes used to be split at every line break, so a sentence wrapped across lines lost
    its second half: Tempest's "Use the supplied Tempest MRA with the matching MAME / Tempest Rev 3
    ROM set" scored as verified against MAME, and the ROM-set filter only saw the second line. Lines
    now join into paragraphs; a blank line, a list item, a heading, a quote or a code fence starts a
    new one, and a table row is read on its own, as in comments.
    """
    out, para = [], []
    for ln, t in list(enumerate(body.splitlines(), 1)) + [(None, "")]:
        # README.txt files in the MiSTer template are written as "-- " comment lines
        t = re.sub(r"^(?:--|//)(?=\s|$)", "", t.strip()).strip()
        if ln is None or not t or _DECOR.match(t) or _MD_BREAK.match(t) or _TABLE_ROW.search(t):
            if para:
                out.extend(_split(para))
            para = []
            if ln is None or not t or _DECOR.match(t):
                continue
            if _TABLE_ROW.search(t):
                out.append((ln, t))
                continue
            heading = t.startswith("#")
            t = re.sub(r"^(?:[-*+]\s+|\d+[.)]\s+|#+\s*|>\s*|```\w*|~~~\w*)", "", t).strip()
            if not t:
                continue
            if heading:                      # a heading is never the start of the next paragraph
                out.extend(_split([(ln, t)]))
                continue
        para.append((ln, t))
    return out


def _split(para):
    joined, starts = "", []
    for ln, t in para:
        starts.append((len(joined), ln))
        joined += t + " "

    def line_at(pos):
        return max((ln for off, ln in starts if off <= pos), default=para[0][0])

    out, pos = [], 0
    for m in _SENT_END.finditer(joined):
        if _ABBREV.search(joined[pos:m.start()]):
            continue
        seg = joined[pos:m.start()].strip()
        if seg:
            out.append((line_at(pos), seg))
        pos = m.end()
    seg = joined[pos:].strip()
    if seg:
        out.append((line_at(pos), seg))
    return out


def score_core(name, core_dir=None, ev=None, repo_files=(), only=None):
    assert core_dir and ev is not None, "core_dir and evidence are required"
    files, _ = A.own_hdl(core_dir, only)
    # file names in the core's own repository: citing one of those is citing the developer's tool
    own_names = frozenset(f.rsplit("/", 1)[-1].lower() for f in repo_files
                          if f.lower().endswith((".cpp", ".ipp")))
    texts = [open(f, encoding="utf-8", errors="replace").read() for f in files]
    for d in ("README.md", "readme.md", "README.txt"):
        if os.path.exists(os.path.join(core_dir, d)):
            texts.append(open(os.path.join(core_dir, d), encoding="utf-8", errors="replace").read())
    own_names = (own_names | tool_file_names(texts)) - mame_file_names()
    mame_files = {f: open(os.path.join(A.MAME, f), encoding="utf-8", errors="replace").read()
                  for f in ev.get("mame_files_compared", []) if os.path.exists(os.path.join(A.MAME, f))}
    mame_text = "\n".join(mame_files.values())
    copied = collections.Counter(x["at"].split(":")[0] for x in ev["A_shared_text"])
    modules, items = [], []
    for f in files:
        ext = os.path.splitext(f)[1].lower()
        text = open(f, encoding="utf-8", errors="replace").read()
        rel = A.rel_path(f, core_dir)
        counts = collections.Counter()
        declared = False
        for line, c in sentences(text, ext):
            for rule, pts in classify(c, mame_text, own_names):
                counts[rule] += 1
                declared |= rule == "mame_transcribed"
                it = {"module": rel, "at": f"{rel}:{line}", "rule": rule, "points": pts, "text": c.strip()[:240]}
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
            for line, sent in readme_sentences(body):
                # v0.9: "MRA" as a word too ("Use the supplied Tempest MRA with the matching MAME")
                if re.search(r"keyboard|keys|\.zip|romset|rom set|\.mra|\bmra\b", sent, re.I):
                    continue
                for rule, pts in classify(sent, mame_text, own_names):
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


