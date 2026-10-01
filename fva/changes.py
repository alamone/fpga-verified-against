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


def summary(old, new):
    O = {_key(r): r for r in old["cores"]}
    N = {_key(r): r for r in new["cores"]}
    lines = []
    for k in sorted(N.keys() - O.keys()):
        r = N[k]
        lines.append(f"+ {r['core']} ({r['db']}): new, {r.get('reading') or r.get('status')}")
    for k in sorted(O.keys() - N.keys()):
        lines.append(f"- {O[k]['core']} ({O[k]['db']}): no longer in its database")
    rebuilt, moved = [], []
    for k in sorted(O.keys() & N.keys()):
        o, n = O[k], N[k]
        if _state(o) == _state(n):
            continue
        build = o.get("build_commit") != n.get("build_commit")
        os_, ns = (o.get("score") or {}).get("score"), (n.get("score") or {}).get("score")
        what = f"{os_} {o.get('reading') or o.get('status')} -> {ns} {n.get('reading') or n.get('status')}"
        (rebuilt if build else moved).append(f"  {n['core']} ({n['db']}): {what}")
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
