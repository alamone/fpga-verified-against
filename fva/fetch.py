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

from .paths import MAME_REPO, MANIFEST, PINNED
from .sources import git, hist_dir

KEEP = re.compile(r"\.(v|sv|vhd|vhdl|md|txt)$", re.I)
SKIP = re.compile(r"^(sys|releases)/|[<>:\"|?*]|\.(/|$)")


def pin_repo(c):
    """A build whose repo and commit are known exactly (official, developer databases)."""
    out = os.path.join(PINNED, c["db"], c["core"])
    if os.path.isdir(out) and any(os.scandir(out)):
        return c["core"], "cached"
    os.makedirs(out, exist_ok=True)
    gd = hist_dir(c["repo"])
    sub = (c.get("subdir") or "").strip("/")
    files = [f for f in git(f"--git-dir={gd}", "ls-tree", "-r", "--name-only", c["build_commit"]).stdout.splitlines()
             if KEEP.search(f) and (not sub or f.startswith(sub + "/"))
             and not SKIP.search(f[len(sub) + 1:] if sub else f)]
    env = dict(os.environ, GIT_INDEX_FILE=os.path.abspath(out + ".index"))
    err = ""
    for i in range(0, len(files), 200):
        p = git(f"--git-dir={gd}", f"--work-tree={out}", "checkout", c["build_commit"], "--", *files[i:i + 200],
                env=env, timeout=900)
        err = err or (p.stderr.strip()[-200:] if p.returncode else "")
    if os.path.exists(out + ".index"):
        os.remove(out + ".index")
    return c["core"], err or f"{len(files)} files"


def pin_jtcores(commit):
    """One sparse checkout of jtcores at the (shared) pinned commit: each core's hdl/, docs, README."""
    d = os.path.join(PINNED, "jtcores")
    if not os.path.exists(d):
        git("clone", "-q", "--filter=blob:none", "--no-checkout", "https://github.com/jotego/jtcores.git", d, timeout=900)
        git("-C", d, "sparse-checkout", "init", "--no-cone")
        git("-C", d, "sparse-checkout", "set", "--no-cone", "/cores/*/hdl/**", "/cores/*/README.md",
            "/cores/*/doc/*.md", "/cores/*/doc/*.txt", "/cores/*/custom/**", "/cores/*/pal/*.txt", "/README.md")
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
    jt_commits = {c["build_commit"] for c in m["cores"] if c["db"] == "jt" and c.get("build_commit")}
    assert len(jt_commits) <= 1, f"JT builds pinned to several commits: {jt_commits}"
    if jt_commits:
        pin_jtcores(jt_commits.pop())
    sha = mame()
    print(f"pinned {len(res) - len(bad)}/{len(res)} cores (official + developer databases); problems: {bad[:5]}; MAME {sha[:10]}")
    return sha
