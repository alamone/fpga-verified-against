"""Repository-only cores: public source and a downloadable build, but no database behind them.

No list of these exists, so they are found two ways:
1. GitHub repository searches (QUERIES), fixed here so a reader knows what was searched. A search
   only finds repos that say "arcade" with "mister" or "fpga" in their name, description or topics.
2. data/extra_repos.tsv: repos anyone can add by pull request, for what the search cannot see
   (a repo named "ikacore_CV1k" with the description "the fire was everywhere").

A candidate is included when it has, at its newest commit, HDL files, a MiSTer build (.rbf) and MRA
files committed to the repo. MRA files are how MiSTer arcade cores load games; without them there is
no telling which games a core runs, so nothing to compare with MAME. The build pins the analysis: each build is analyzed at
the commit that last added or changed that file, so the reading describes what people download, not
whatever the repo holds today. Repos with source but no build yet are listed as found and skipped,
with the reason, rather than analyzed at an arbitrary commit.

Not counted again: repos already covered by a database (by name), and copies of them. A copy is a
repo whose first commit is in a covered repo's history; GitHub only marks forks made with its fork
button, and many copies of official cores were pushed as new repos. Also listed rather than analyzed:
a developer's own earlier or working copy of a core that ships in a covered database (superseded:
same games, and the repo's commit authors appear in the covered repo's history), and ports to other
FPGA boards (Analogue Pocket, SoCKit, DE1-SoC, Neptuno, MiST...). Another developer's core for the
same games is an independent implementation and is analyzed.

Needs GITHUB_TOKEN (a read-only token): without it the search limits allow only a few queries.
"""
import collections
import concurrent.futures as cf
import csv
import json
import os
import re
import time
import urllib.parse

from .paths import HIST, REPO
from .sources import clone_history, fetch, git, hist_dir

QUERIES = [
    "arcade mister in:name,description,topics fork:false",
    "arcade fpga in:name,description,topics fork:false",
    "topic:mister-fpga fork:false",
    "topic:misterfpga fork:false",
    "topic:mister fork:false",
]
COVERED_OWNERS = {"mister-devel", "jotego", "coin-opcollection"}
EXTRA = os.path.join(REPO, "data", "extra_repos.tsv")
HDL = re.compile(r"\.(v|sv|vhd|vhdl)$", re.I)
OTHER_BOARD_REPO = re.compile(r"openfpga|sockit|de1-soc|de10-standard|neptuno|analogue|pocket|(^|[^a-z])mist([^e]|$)",
                              re.I)
OTHER_BOARD = re.compile(r"(^|/)(neptuno\w*|mist|sidi\w*|mc2\w*|mcp|pocket|openfpga|de10lite|deca|qmtech|zxuno|"
                         r"uareloaded|chameleon\w*|mimic\w*)(/|$)", re.I)


def api(path):
    return json.loads(fetch("https://api.github.com/" + path))


def search(q):
    """All repos for one query (the API returns at most 1,000; the queries stay under that)."""
    names, page = [], 1
    while page <= 10:
        d = api(f"search/repositories?q={urllib.parse.quote(q)}&per_page=100&page={page}")
        names += [(r["full_name"], r["default_branch"], r["description"] or "") for r in d["items"]]
        if len(d["items"]) < 100:
            break
        page += 1
        time.sleep(2.2)   # search allows 30 requests a minute with a token
    return names


def tree(repo, branch):
    try:
        return [e["path"] for e in api(f"repos/{repo}/git/trees/{urllib.parse.quote(branch)}?recursive=1")["tree"]
                if e["type"] == "blob"]
    except Exception:  # noqa: BLE001  (empty or deleted repo)
        return []


def roots(gd):
    return set(git(f"--git-dir={gd}", "rev-list", "--max-parents=0", "--all").stdout.split())


def _stem(rbf):
    """Build file name without its date (and a same-day respin letter: Rayforce_20260908b.rbf)."""
    return re.sub(r"(_\d{8}[a-z]?)?\.rbf$", "", os.path.basename(rbf), flags=re.I)


def find(covered_repos):
    """-> (candidates to analyze [(repo, branch, [rbf paths at HEAD], note)], skipped [(repo, reason)])."""
    found = {}
    for q in QUERIES:
        for name, branch, desc in search(q):
            found.setdefault(name, (branch, "search"))
        time.sleep(2.2)
    if os.path.exists(EXTRA):
        for row in csv.reader(open(EXTRA, encoding="utf-8"), delimiter="\t"):
            if row and not row[0].startswith("#") and "/" in row[0]:
                repo = row[0].strip().removeprefix("https://github.com/").strip("/")
                try:
                    found[repo] = (api(f"repos/{repo}")["default_branch"], "extra_repos.tsv")
                except Exception:  # noqa: BLE001
                    found[repo] = (None, "extra_repos.tsv")
    covered = {r.lower() for r in covered_repos}
    skipped, todo = [], []
    for repo, (branch, via) in sorted(found.items()):
        if repo.split("/")[0].lower() in COVERED_OWNERS or repo.lower() in covered:
            continue
        if branch is None:
            skipped.append((repo, via, "repository not found"))
        else:
            todo.append((repo, branch, via))
    with cf.ThreadPoolExecutor(8) as ex:
        trees = dict(zip([t[0] for t in todo], ex.map(lambda t: tree(t[0], t[1]), todo)))

    # First commits of every covered repo (not of other candidates), to recognize copies pushed as
    # new repos.
    covered_roots = {}
    for r in list(covered_repos) + ["jotego/jtcores"]:
        gd = os.path.join(HIST, "jtcores.git") if r == "jotego/jtcores" else hist_dir(r)
        if os.path.isdir(gd):
            for sha in roots(gd):
                covered_roots[sha] = r
    out = []
    for repo, branch, via in todo:
        paths = trees[repo]
        rbfs = [p for p in paths if p.lower().endswith(".rbf") and not OTHER_BOARD.search(p)]
        # a repo building for several boards: keep the builds in a MiSTer folder
        rbfs = [p for p in rbfs if re.search(r"(^|/)mister(/|$)", p, re.I)] or rbfs
        # where a repo has a releases/ folder, that is what it distributes; builds elsewhere are
        # experiments (Gauntlet_FPGA keeps SVGA test builds under MiSTer/doc/svga/)
        rbfs = [p for p in rbfs if re.search(r"(^|/)releases/", p, re.I)] or rbfs
        arcade = any(p.lower().endswith(".mra") for p in paths)
        if OTHER_BOARD_REPO.search(repo):   # owner too: neptuno-fpga/Arcade-SEGA_SYSTEM_1
            skipped.append((repo, via, "a port for another FPGA board"))
        elif not any(HDL.search(p) for p in paths):
            # builds and MRAs without the design: an arcade core whose source is not published;
            # anything else (MRA packs, scripts, artwork) is not a core and only counted
            is_db = any(p.lower().endswith("db.json.zip") for p in paths) or re.search(r"[-_]db$", repo, re.I)
            skipped.append((repo, via, "not an arcade core (a download database)" if is_db else
                            "builds only: no HDL in the repository" if rbfs and arcade else
                            "not an arcade core (no HDL)"))
        elif not rbfs and via == "extra_repos.tsv":   # listed as an arcade core: say what is missing first
            skipped.append((repo, via, "source only: no MiSTer build committed yet"))
        elif not arcade:
            skipped.append((repo, via, "not an arcade core (no MRA files)"))
        elif not rbfs:
            skipped.append((repo, via, "source only: no MiSTer build committed yet"))
        else:
            out.append((repo, branch, rbfs, via))
    kept = []
    for repo, branch, rbfs, via in out:
        gd = clone_history(f"https://github.com/{repo}.git", hist_dir(repo))
        copy = next((covered_roots[s] for s in roots(gd) if s in covered_roots), None)
        if copy:
            skipped.append((repo, via, f"copy of a covered repository ({copy})"))
        else:
            kept.append((repo, branch, rbfs, via))
    return kept, skipped


def builds(repo, branch, rbfs, via):
    """One record per core the repo ships: the newest build of each name, pinned to the commit that
    last added or changed it."""
    gd = hist_dir(repo)
    by_stem = collections.defaultdict(list)
    for p in rbfs:
        by_stem[_stem(p).lower()].append(p)
    recs = []
    owner = repo.split("/")[0]
    for stem, paths in sorted(by_stem.items()):
        path = max(paths, key=lambda p: (re.search(r"_(\d{8})\.rbf$", p) or [None, ""])[1] + p)
        line = git(f"--git-dir={gd}", "log", "-1", "--no-renames", "--format=%H %cs", branch, "--", path).stdout.split()
        if not line:
            continue
        sha, date = line
        sub = path.split("/releases/")[0] if "/releases/" in path else ""
        if sub.split("/")[-1].lower() == "sys":   # a build parked inside the MiSTer framework folder
            sub = ""
        recs.append({"db": "repo", "channel": "repository only", "core": f"{_stem(path)} ({owner})",
                     "rbf": os.path.basename(path), "repo": repo, "ref": branch, "subdir": sub,
                     "build_commit": sha, "build_commit_date": date, "found_via": via,
                     "match": "exact file: the newest build committed to the repository"})
    return recs


_GENERIC_AUTHORS = {"github", "noreply@github.com", "web-flow"}


def _authors(gd):
    """Commit author names and emails, lowercased (the bare clones carry every commit)."""
    out = set(git(f"--git-dir={gd}", "log", "--all", "--format=%an%n%ae").stdout.lower().splitlines())
    return {a.strip() for a in out if a.strip()} - _GENERIC_AUTHORS


def superseded(rec, covered_cores, _cache={}):
    """The same developer's earlier or working copy of a core that ships in a covered database: the
    original repos of cores that moved into MiSTer-devel (2018-20), and personal build repos. Build
    dates cannot decide this, since official cores are rebuilt for framework updates; authorship can.
    A different developer's core for the same games is an independent implementation and stays."""
    sets = set(rec["setnames"])
    if not sets:
        return None
    mine = _authors(hist_dir(rec["repo"]))
    for c in sorted(covered_cores, key=lambda c: -len(sets & set(c.get("setnames", ())))):
        if not sets & set(c.get("setnames", ())) or not c.get("repo"):
            continue
        gd = os.path.join(HIST, "jtcores.git") if c["db"] == "jt" else hist_dir(c["repo"])
        if gd not in _cache:
            _cache[gd] = _authors(gd) if os.path.isdir(gd) else set()
        if mine & _cache[gd]:
            return f"superseded: the same developer's core ships as {c['core']} ({c['db']})"
    return None


def mra_sets(rec, single):
    """Game titles and ROM sets from the MRA files in the repo at the pinned commit. A repo shipping
    one core gets all its MRAs; with several, an MRA goes to the build its <rbf> tag names."""
    gd = hist_dir(rec["repo"])
    # MRAs at the build's commit, else at the newest (2019 cores got their MRAs after the last build)
    for at in (rec["build_commit"], rec.get("ref") or "HEAD"):
        mras = [p for p in git(f"--git-dir={gd}", "ls-tree", "-r", "--name-only", at).stdout.splitlines()
                if p.lower().endswith(".mra")]
        if mras:
            break
    tag = lambda t, s: (m.group(1).strip() if (m := re.search(rf"<{t}>\s*(.*?)\s*</{t}>", s, re.S | re.I)) else None)
    sets, titles = set(), set()
    mine = _stem(rec["rbf"]).lower()
    for p in mras:
        s = git(f"--git-dir={gd}", "show", f"{at}:{p}").stdout
        rbf = (tag("rbf", s) or "").lower()
        if not single and rbf and rbf not in (mine, re.sub(r"^arcade-", "", mine)) and not mine.endswith(rbf):
            continue
        if tag("setname", s):
            sets.add(tag("setname", s).lower())
        elif m := re.search(r'<rom[^>]*\bzip="([^"|]+?)(?:\.zip)?["|]', s, re.I):
            sets.add(os.path.basename(m.group(1)).lower())   # MRAs from 2019 name the set only by its zip
        if tag("name", s):
            titles.add(tag("name", s))
    rec["setnames"], rec["titles"] = sorted(sets), sorted(titles)
