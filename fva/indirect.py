"""Indirect evidence for cores whose source is not published (Coin-Op Collection).

Two public sources from the same group stand in, one step removed from the cores themselves:

1. Development-Documentation: platform reverse-engineering write-ups (Toaplan 2 / Raizing, Technos
   16-bit, Midway Y/Z-Unit) with schematics, PCB layouts and board photos. A write-up is attached to
   a core when the write-up names one of the games the core loads (titles from the MRAs).
2. Development-Modules: open-source components the group built (6502, 65C02, 68705, SN76489,
   AY-3-8910), each with datasheets and a test bench. Listed ONCE, for the group, never per core:
   matching components to cores by the chips in MAME's driver proved unreliable (a ROM checksum
   containing "468705" matched Mystic Warriors; nmk16.cpp covers many boards, only some with a
   68705), and even a correct match would not show that the closed core uses the module.

This material is ONE-SIDED BY CONSTRUCTION (operator, 2026-09-28). For open-source cores every
statement is visible, including the MAME citations nobody chose to show; for closed cores only what
the team chose to publish is visible, and anything pointing at MAME stays private. So it is shown
as facts only (documents, files, components, with links), never classified into hardware/MAME
statements, never colored as hardware evidence, never placing a needle, and never counted in any
total. The page states the gap next to it.
"""
import os
import re

from .paths import WORK
from .sources import git

ORG = "Coin-OpCollection"
DOCS = ("Development-Documentation", "main")
MODULES = ("Development-Modules", "develop")
DOC_FILE = re.compile(r"\.(?:kicad_sch|kicad_pcb|pdf)$", re.I)
# module folder -> MAME device names that show the chip is on the board
MODULE_CHIPS = {
    "x6502": r"\bm6502\b|\bM6502\b",
    "x65c02": r"65c02|R65C02|W65C02",
    "x68705": r"68705",
    "x76489": r"sn76489|SN76489",
    "x8910": r"ay8910|AY8910|ym2149|YM2149",
}


def checkout(repo, branch):
    d = os.path.join(WORK, "indirect", repo)
    if not os.path.exists(d):
        git("clone", "-q", "--filter=blob:none", "--no-checkout", "-b", branch, f"https://github.com/{ORG}/{repo}.git", d,
            timeout=900)
        git("-C", d, "sparse-checkout", "init", "--no-cone")
        git("-C", d, "sparse-checkout", "set", "--no-cone", "*.md", "*.txt", "*.v", "*.qip")
        git("-C", d, "checkout", "-q", branch)
    sha = git("-C", d, "rev-parse", "HEAD").stdout.strip()
    files = git("-C", d, "ls-tree", "-r", "--name-only", "HEAD").stdout.splitlines()
    return d, sha, files


def norm(t):
    return re.sub(r"[^a-z0-9]+", " ", re.sub(r"\(.*?\)", "", t.lower())).strip()


def platform_docs():
    d, sha, files = checkout(*DOCS)
    docs = []
    mds = [f for f in files if f.endswith(".md") and f.count("/") >= 2 and "raw_schematics" not in f]
    doc_folders = {m.rsplit("/", 1)[0] for m in mds}
    for md in mds:
        text = open(os.path.join(d, md), encoding="utf-8", errors="replace").read()
        # game titles: bold captions in the board galleries, plus parentheses in headings
        # ("# RA9704 (Armed Police Batrider) PCB Reference ...")
        raw = re.findall(r"<b>\s*(.*?)\s*</b>", text) + re.findall(r"^#.*?\(([^)]+)\)", text, re.M)
        titles = [norm(t) for t in raw if len(norm(t)) > 3]
        folder = md.rsplit("/", 1)[0]
        # A write-up's OWN files: its folder, minus subfolders that have their own write-up. The
        # Raizing overview must not claim the 25 files that document Batrider's RA9704 board, or
        # Battle Garegga would appear to come with schematics of a board that is not its own.
        deeper = [f2 for f2 in doc_folders if f2 != folder and f2.startswith(folder + "/")]
        own = [f for f in files if f.startswith(folder + "/") and DOC_FILE.search(f)
               and not any(f.startswith(x + "/") for x in deeper)]
        docs.append({"doc": md, "folder": folder, "titles": titles, "files": own})
    return sha, docs


def modules():
    d, sha, files = checkout(*MODULES)
    out = []
    for name, chip_re in MODULE_CHIPS.items():
        base = next((f.rsplit("/", 1)[0] for f in files if f.endswith(f"/{name}/README.md")), None)
        if not base:
            continue
        readme = open(os.path.join(d, base, "README.md"), encoding="utf-8", errors="replace").read()
        first = next((l.strip() for l in readme.splitlines()
                      if l.strip() and not l.strip().startswith(("#", "<", "!", "|", "-", "*", "["))), "")
        out.append({"module": name, "path": base, "chip_re": chip_re, "summary": first[:240],
                    "datasheets": [f for f in files if f.startswith(base + "/doc/") and f.lower().endswith(".pdf")],
                    "testbench": [f for f in files if f.startswith(base + "/sim/")],
                    "testbench_log": next((f for f in files if f.startswith(base + "/doc/readme/tb_")), None)})
    return sha, out


def attach(results):
    """Add an `indirect` block to every closed-source record."""
    doc_sha, docs = platform_docs()
    mod_sha, mods = modules()
    for r in results:
        if r.get("db") != "coinop":
            continue
        titles = [norm(t) for t in r.get("titles", [])]
        hit_docs = []
        for doc in docs:
            match = next((t for t in doc["titles"] if any(ct.startswith(t) or t in ct for ct in titles)), None)
            if match:
                # board-specific material (e.g. RA9704 for Batrider) only when the board folder names the game
                hit_docs.append(dict(doc, matched_title=match))
        if hit_docs:
            r["indirect"] = {"docs_repo": f"{ORG}/{DOCS[0]}", "docs_commit": doc_sha, "platform_docs": hit_docs}
    # Components are listed once for the group, never attached per core (see module docstring).
    return {"repo": f"{ORG}/{MODULES[0]}", "commit": mod_sha,
            "modules": [{k: m[k] for k in ("module", "path", "summary", "datasheets", "testbench", "testbench_log")}
                        for m in mods]}
