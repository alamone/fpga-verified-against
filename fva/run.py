"""Analyze every open-source build in the manifest at its pinned commit -> results/results.json.

Each record carries what a reader needs to reproduce it: database, build file, repository, commit
(and how the commit was matched), the MAME files compared and MAME's commit, the rules version.
"""
import collections
import datetime as dt
import json
import os

from . import RULES_VERSION, VERSION
from . import analyze as A
from . import indirect
from . import score as S
from .paths import HIST, MANIFEST, MAME_REPO, PINNED, RESULTS
from .sources import git


def repo_listing(c):
    """Every file in the core's folder at the pinned commit (for shipped schematics / PAL dumps)."""
    if c["db"] == "dist":
        gd = os.path.join(HIST, c["repo"].split("/")[1] + ".git")
        files = git(f"--git-dir={gd}", "ls-tree", "-r", "--name-only", c["build_commit"]).stdout.splitlines()
        sub = (c.get("subdir") or "").strip("/")
        return [f for f in files if (not sub or f.startswith(sub + "/")) and not f.startswith(("sys/", "releases/"))]
    return git("-C", os.path.join(PINNED, "jtcores"), "ls-tree", "-r", "--name-only", c["build_commit"], "--",
               c["subdir"]).stdout.splitlines()


def core_dir(c):
    return os.path.join(PINNED, "dist", c["core"]) if c["db"] == "dist" else os.path.join(PINNED, "jtcores", c["subdir"])


def lean(sc):
    if sc["confidence"] == "insufficient" or sc["score"] is None:
        return "not enough evidence"
    return "mostly MAME" if sc["score"] < 40 else "mostly hardware" if sc["score"] > 60 else "both"


def run():
    m = json.load(open(MANIFEST, encoding="utf-8"))
    mame_sha = git("-C", MAME_REPO, "rev-parse", "HEAD").stdout.strip()
    out = []
    for c in m["cores"]:
        rec = dict(c)
        if c["db"] == "coinop":
            out.append(rec)
            continue
        d = core_dir(c)
        if not (os.path.isdir(d) and any(os.scandir(d))):
            rec["status"] = "source not checked out"
            out.append(rec)
            continue
        ev = A.analyze(c["core"], core_dir=d, sets=c["setnames"])
        sc = S.score_core(c["core"], core_dir=d, ev=ev, repo_files=repo_listing(c))
        rec.update(status="analyzed", mame_drivers=ev["mame_drivers"], mame_files=ev["mame_files_compared"],
                   own_hdl_lines=ev["own_hdl_lines"], excluded_libraries=ev["excluded_library_files"],
                   reading=lean(sc), score=sc)
        out.append(rec)
    group_modules = indirect.attach(out)   # closed-source cores: what the team chose to publish (never scored)
    meta = {"tool_version": VERSION, "rules_version": RULES_VERSION,
            "generated": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
            "manifest_built": m["built"], "databases": m["databases"], "mame_commit": mame_sha,
            "coinop_public_modules": group_modules}
    json.dump({"meta": meta, "cores": out}, open(os.path.join(RESULTS, "results.json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=0)
    print(collections.Counter((r["db"], r.get("reading", r.get("status"))) for r in out))
    return meta
