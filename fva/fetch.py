"""Check out each open-source build's code at its pinned commit, and MAME's drivers for comparison.

Only code and documentation files are checked out (HDL, .md, .txt); the MiSTer framework (sys/)
and the release builds are skipped. Files are listed from the pinned commit first and checked out
by name, because a pattern that matches nothing (a core with no VHDL) makes git refuse the whole
checkout. Paths Windows cannot hold (names ending in a dot, reserved characters) are skipped.
"""
import concurrent.futures as cf
import json
import os
import re

from .paths import MAME_REPO, MANIFEST, PINNED, jt_checkout
from .sources import git, hist_dir

KEEP = re.compile(r"\.(v|sv|vhd|vhdl|md|txt|qsf|qip)$", re.I)   # .qsf/.qip: which files the build compiles
SKIP = re.compile(r"^(sys|releases)/|[<>:\"|?*]|\.(/|$)")


def pin_repo(c):
    """A build whose repo and commit are known exactly (official, independent databases). Only files
    missing from an earlier checkout are fetched, so adding a file type (v0.5's .qsf/.qip) fills in
    existing checkouts without redoing them."""
    out = os.path.join(PINNED, c["db"], c["core"])
    os.makedirs(out, exist_ok=True)
    gd = hist_dir(c["repo"])
    sub = (c.get("subdir") or "").strip("/")
    files = [f for f in git(f"--git-dir={gd}", "ls-tree", "-r", "--name-only", c["build_commit"]).stdout.splitlines()
             if KEEP.search(f) and (not sub or f.startswith(sub + "/"))
             and not SKIP.search(f[len(sub) + 1:] if sub else f)]
    files = [f for f in files if not os.path.exists(os.path.join(out, f))]
    if not files:
        return c["core"], "cached"
    env = dict(os.environ, GIT_INDEX_FILE=os.path.abspath(out + ".index"))
    err = ""
    for i in range(0, len(files), 200):
        p = git(f"--git-dir={gd}", f"--work-tree={out}", "checkout", c["build_commit"], "--", *files[i:i + 200],
                env=env, timeout=900)
        err = err or (p.stderr.strip()[-200:] if p.returncode else "")
    if os.path.exists(out + ".index"):
        os.remove(out + ".index")
    return c["core"], err or f"{len(files)} files"


JT_SPARSE = ("/cores/*/hdl/**", "/cores/*/README.md", "/cores/*/doc/*.md", "/cores/*/doc/*.txt",
             "/cores/*/custom/**", "/cores/*/pal/*.txt", "/README.md", "/cores/*/cfg/*.yaml")


def pin_jtcores(commit):
    """A sparse checkout of jtcores at one commit: each core's hdl/, docs, README, and cfg/*.yaml (which
    files a core is built from, fva/scope.py). One clone (work/pinned/jtcores) holds the objects; each
    commit JT builds are pinned to gets its own worktree, since builds from different releases differ."""
    base = os.path.join(PINNED, "jtcores")
    if not os.path.exists(base):
        git("clone", "-q", "--filter=blob:none", "--no-checkout", "https://github.com/jotego/jtcores.git", base, timeout=900)
    d = jt_checkout(commit)
    if not os.path.exists(d):
        git("-C", base, "fetch", "-q", "origin", commit, timeout=900)
        p = git("-C", base, "worktree", "add", "--detach", "--no-checkout", d, commit, timeout=900)
        if p.returncode:
            raise RuntimeError(p.stderr[-300:])
        git("-C", d, "sparse-checkout", "init", "--no-cone")
    git("-C", d, "sparse-checkout", "set", "--no-cone", *JT_SPARSE)
    p = git("-C", d, "checkout", "-q", commit, timeout=900)
    if p.returncode:
        raise RuntimeError(p.stderr[-300:])
    return d


def mame(ref="master"):
    """MAME's game drivers (src/mame) only; the commit used is recorded in the results."""
    if not os.path.exists(MAME_REPO):
        git("clone", "-q", "--depth", "1", "--filter=blob:none", "--sparse", "-b", ref,
            "https://github.com/mamedev/mame.git", MAME_REPO, timeout=1800)
        git("-C", MAME_REPO, "sparse-checkout", "set", "src/mame")
    return git("-C", MAME_REPO, "rev-parse", "HEAD").stdout.strip()


def run():
    m = json.load(open(MANIFEST, encoding="utf-8"))
    pinned = [c for c in m["cores"] if c["db"] != "jt" and c.get("repo") and c.get("build_commit")]
    with cf.ThreadPoolExecutor(8) as ex:
        res = list(ex.map(pin_repo, pinned))
    bad = [r for r in res if not (r[1] == "cached" or r[1].endswith("files"))]
    for commit in sorted({c["build_commit"] for c in m["cores"] if c["db"] == "jt" and c.get("build_commit")}):
        pin_jtcores(commit)
    sha = mame()
    print(f"pinned {len(res) - len(bad)}/{len(res)} cores (official + independent databases); problems: {bad[:5]}; MAME {sha[:10]}")
    return sha
