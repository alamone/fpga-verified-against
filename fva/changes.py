"""What changed between the published results and a fresh run, for the weekly job's commit message.

python -m fva.changes OLD.json NEW.json  -> prints a summary; exit 0 if anything a reader would see
changed, 1 if not, 2 if the new run lost more than a tenth of the cores (a database that failed to
download looks exactly like every core in it being withdrawn; that must fail the job, not publish).
"Changed" means a core was added or removed, or a core's build, status, score or reading moved. Run-to-run metadata (generation time, when the database list was read) does not
count: without that distinction the job would commit every week whether or not a core changed.
"""
import json
import sys


def _key(r):
    return (r["db"], r["core"], r.get("subdir") or "")


def _state(r):
    s = r.get("score") or {}
    return (r.get("status"), r.get("build_commit"), s.get("score"), r.get("reading"))


def _what(o, n):
    """One line on how a core changed, in terms a reader of the results page would use."""
    analyzed = lambda r: r.get("status") == "analyzed"
    if not analyzed(o) and analyzed(n):
        return f"source now published, {n.get('reading')}"
    if analyzed(o) and not analyzed(n):
        return f"{o.get('reading')} -> {n.get('status')}"
    if not o.get("build_commit") and n.get("build_commit") and o.get("rbf") == n.get("rbf"):
        # The same build, now traced to the commit that added it (15 blahm1d cores on 2026-10-19,
        # once the history copies were kept current). Not a new build.
        return f"build now traced to {n.get('repo')} @ {n['build_commit'][:8]}"
    if not analyzed(n):
        # Closed source: no score or reading to compare, so name the builds. Printing the empty
        # score twice ("None source not published -> None source not published", 2026-10-19 log)
        # told a reader nothing.
        return f"{o.get('rbf')} -> {n.get('rbf')}"
    os_, ns = (o.get("score") or {}).get("score"), (n.get("score") or {}).get("score")
    result = (f"unchanged at {ns} {n.get('reading')}" if (os_, o.get("reading")) == (ns, n.get("reading"))
              else f"{os_} {o.get('reading')} -> {ns} {n.get('reading')}")
    return f"{n.get('rbf')}, {result}" if o.get("rbf") != n.get("rbf") else result


def summary(old, new):
    O = {_key(r): r for r in old["cores"]}
    N = {_key(r): r for r in new["cores"]}
    added, removed = sorted(N.keys() - O.keys()), sorted(O.keys() - N.keys())
    # The same core under a changed key is a change, not one core removed and another added. The
    # key carries the source folder, which a core gains when its source is published: jlrh's
    # ffdeadang was logged on 2026-10-19 as both "new" and "no longer in its database".
    by_name = {(O[k]["db"], O[k]["core"]): k for k in removed}
    pairs = {k: by_name.pop((N[k]["db"], N[k]["core"])) for k in added
             if (N[k]["db"], N[k]["core"]) in by_name}
    lines = []
    for k in added:
        if k not in pairs:
            r = N[k]
            lines.append(f"+ {r['core']} ({r['db']}): new, {r.get('reading') or r.get('status')}")
    for k in removed:
        if k in by_name.values():
            lines.append(f"- {O[k]['core']} ({O[k]['db']}): no longer in its database")
    rebuilt, moved = [], []
    for o, n in [(O[k], N[k]) for k in sorted(O.keys() & N.keys())] + \
                [(O[ok], N[nk]) for nk, ok in sorted(pairs.items())]:
        if _state(o) == _state(n) and _key(o) == _key(n):
            continue
        build = o.get("rbf") != n.get("rbf") or bool(
            o.get("build_commit") and o.get("build_commit") != n.get("build_commit"))
        (rebuilt if build else moved).append(f"  {n['core']} ({n['db']}): {_what(o, n)}")
    if rebuilt:
        lines.append("New builds:")
        lines += rebuilt
    if moved:
        lines.append("Same build, different result:")
        lines += moved
    return lines


if __name__ == "__main__":
    old = json.load(open(sys.argv[1], encoding="utf-8"))
    new = json.load(open(sys.argv[2], encoding="utf-8"))
    if len(new["cores"]) < 0.9 * len(old["cores"]):
        print(f"refusing: {len(new['cores'])} cores against {len(old['cores'])} last time; "
              "check the database downloads")
        sys.exit(2)
    out = summary(old, new)
    print("\n".join(out) if out else "no changes")
    sys.exit(0 if out else 1)
