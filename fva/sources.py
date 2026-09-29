"""Which cores exist, where their source is, and which commit each distributed build came from.

The list is taken from the DATABASES users actually install from, not from any GitHub organization:
update_all's three default databases (MiSTer official distribution, JTCORES, Coin-Op Collection).
An organization holds repos that are not distributed (MiSTer-devel's 1943 repo is not; players get
Jotego's), so starting from the org would describe cores nobody runs.

MiSTer official: the distribution's own build script reads the arcade list from the MiSTer wiki
(Cores.md, between arcade_list_start/end), takes each repo's releases/ build and strips an
"Arcade-" prefix. We follow the same path: wiki entry -> repo -> the commit that added the build
file whose name matches the distributed one. A few builds do not match by name (an undated file, a
year typo, an "ikacore_" prefix, a file updated in place); those fall back to the release commit
nearest the distributed date and say so in `match`.

JTCORES: builds come from the jotego/jtcores monorepo, cores/<name>. Builds carry no date and the
publishing commits no source reference, and all builds are republished together, so every JT build
is pinned APPROXIMATELY to the newest jtcores commit on or before the build was published.

Coin-Op Collection: distributed as builds only (a subscriber model); recorded as "source not
published". Their few older public repos are not what users run, so they are not analyzed.
"""
import collections
import concurrent.futures as cf
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import urllib.parse
import urllib.request
import zipfile

from .paths import DBS, HIST, MANIFEST, MRAS

UA = {"User-Agent": "fpga-verified-against"}
DATABASES = {  # update_all defaults (update_all/src/update_all/databases.py)
    "dist": "https://raw.githubusercontent.com/MiSTer-devel/Distribution_MiSTer/main/db.json.zip",
    "jt": "https://raw.githubusercontent.com/jotego/jtcores_mister/main/jtbindb.json.zip",
    "coinop": "https://raw.githubusercontent.com/Coin-OpCollection/Distribution-MiSTerFPGA/db/db.json.zip",
}
WIKI_CORES = "https://raw.githubusercontent.com/wiki/MiSTer-devel/Wiki_MiSTer/Cores.md"
JT_SOURCE = "https://github.com/jotego/jtcores.git"
JT_BIN = "https://github.com/jotego/jtcores_mister.git"


def fetch(url, dest=None):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        data = r.read()
    if dest:
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        open(dest, "wb").write(data)
    return data


def git(*args, **kw):
    return subprocess.run(["git", *args], capture_output=True, text=True, **kw)


def load_db(name):
    z = zipfile.ZipFile(os.path.join(DBS, name + ".zip"))
    return json.loads(z.read(z.namelist()[0]))


def arcade_builds(db):
    """_Arcade/cores/*.rbf in a database, with tags resolved through its tag dictionary."""
    rev = {v: k for k, v in db.get("tag_dictionary", {}).items()}
    out = {}
    for p, m in db["files"].items():
        if p.lower().startswith("_arcade/cores/") and p.lower().endswith(".rbf"):
            out[os.path.basename(p)] = [rev.get(t, t) for t in m.get("tags", [])]
    return out


def clone_history(url, dest, flt="blob:none"):
    """Commits and trees only (no file contents): enough to find which commit added a build."""
    if not os.path.exists(dest):
        p = git("clone", "-q", "--bare", f"--filter={flt}", url, dest, timeout=900)
        if p.returncode:
            raise RuntimeError(f"clone {url}: {p.stderr.strip()[-200:]}")
    return dest


# --- MiSTer official ------------------------------------------------------------------------------

def wiki_arcade_list():
    link = re.compile(r"\[(.*?)\]\((.*?)\)")
    rows, reading = [], False
    for line in fetch(WIKI_CORES).decode("utf-8", "replace").splitlines():
        low = line.lower()
        if "arcade_list_start" in low:
            reading = True
            continue
        if "arcade_list_end" in low:
            reading = False
            continue
        if reading and "https://github.com/mister-devel/" in low:
            cols = line.split("|")
            if len(cols) > 1 and (m := link.search(cols[1])):
                rows.append((m.group(1).strip(), m.group(2).strip()))
    return rows


_PREFIX = re.compile(r"^(Arcade-|Arcade_|ikacore_)", re.I)


def _stem(b):
    return re.sub(r"(_\d{8})?\.rbf$", "", _PREFIX.sub("", b), flags=re.I).lower()


def map_official(builds):
    url_re = re.compile(r"github\.com/([^/]+)/([^/#?]+)(?:/tree/([^/]+)(?:/(.*))?)?", re.I)
    entries = wiki_arcade_list()
    repos = {}
    for name, url in entries:
        m = url_re.search(url)
        repos[(m.group(2).removesuffix(".git"), m.group(3), (m.group(4) or "").strip("/"))] = None
    os.makedirs(HIST, exist_ok=True)
    names = sorted({k[0] for k in repos})
    with cf.ThreadPoolExecutor(10) as ex:
        list(ex.map(lambda n: clone_history(f"https://github.com/MiSTer-devel/{n}.git", os.path.join(HIST, n + ".git")),
                    names))
    dist_names = set(builds)
    cores, not_distributed = {}, []
    for name, url in entries:
        m = url_re.search(url)
        repo, branch, sub = m.group(2).removesuffix(".git"), m.group(3), (m.group(4) or "").strip("/")
        gd = os.path.join(HIST, repo + ".git")
        rel = f"{sub}/releases" if sub else "releases"
        log = git(f"--git-dir={gd}", "log", "--diff-filter=AM", "--format=@%H %cs", "--name-only",
                  branch or "HEAD", "--", rel).stdout
        touched, cur = [], None
        for line in log.splitlines():
            if line.startswith("@"):
                cur = line[1:].split()
            elif line.strip().lower().endswith(".rbf"):
                touched.append((os.path.basename(line.strip()), cur[0], cur[1]))
        stems = {_stem(b) for b, _, _ in touched}
        cands = [n for n in dist_names if _stem(n) in stems]
        if len(cands) > 1:  # a repo shipping several cores (the M92 repo also builds M72)
            own = re.sub(r"^(arcade[-_])|(_mister)$", "", repo.lower()).replace("-", "")
            cands = [n for n in cands if _stem(n) in (own, name.lower().replace(" ", ""))] or cands
        if len(cands) != 1:
            not_distributed.append({"wiki_name": name, "url": url})
            continue
        rbf = cands[0]
        dd = re.search(r"_(\d{8})\.rbf$", rbf).group(1)
        ddate = f"{dd[:4]}-{dd[4:6]}-{dd[6:]}"
        same = [t for t in touched if _stem(t[0]) == _stem(rbf)]
        exact = [t for t in same if _PREFIX.sub("", t[0]) == rbf]
        if exact:
            b, sha, date = max(exact, key=lambda t: t[2])
            how = "exact file"
        else:  # allow a week after the distributed date (Irem M92's build was committed a day late)
            lim = (dt.date.fromisoformat(ddate) + dt.timedelta(days=7)).isoformat()
            b, sha, date = max([t for t in same if t[2] <= lim] or same, key=lambda t: t[2])
            how = f"by date: distributed {ddate}, nearest release change {b} on {date}"
        if rbf in cores:  # one core, several wiki entries (Raiden II / Raiden DX)
            cores[rbf]["wiki_name"] += " / " + name
            continue
        cores[rbf] = {"db": "dist", "channel": "default", "core": re.sub(r"_\d{8}\.rbf$", "", rbf), "rbf": rbf,
                      "wiki_name": name, "repo": f"MiSTer-devel/{repo}", "ref": branch, "subdir": sub,
                      "build_commit": sha, "build_commit_date": date, "match": how}
    return list(cores.values()), not_distributed


# --- JTCORES --------------------------------------------------------------------------------------

def map_jtcores(builds):
    src = clone_history(JT_SOURCE, os.path.join(HIST, "jtcores.git"), flt="tree:0")
    binr = clone_history(JT_BIN, os.path.join(HIST, "jtcores_mister.git"))
    commits = sorted(tuple(l.split()) for l in git("-C", src, "log", "--first-parent", "--format=%cs %H",
                                                   "HEAD").stdout.splitlines() if l.strip())
    tree = set()  # core folders at HEAD, from the GitHub API (no trees in a tree:0 clone)
    for e in json.loads(fetch("https://api.github.com/repos/jotego/jtcores/contents/cores")):
        tree.add(e["name"])
    out, unmapped = [], []
    for rbf, tags in sorted(builds.items()):
        core = re.sub(r"^jt|\.rbf$", "", rbf)
        if core not in tree:
            unmapped.append(rbf)
            continue
        pub = git("-C", binr, "log", "-1", "--format=%cs", "HEAD", "--", f"_Arcade/cores/{rbf}").stdout.strip()
        pin = max((c for c in commits if c[0] <= pub), default=None) if pub else None
        out.append({"db": "jt", "channel": "default", "core": rbf[:-4], "rbf": rbf, "repo": "jotego/jtcores",
                    "subdir": f"cores/{core}", "build_published": pub,
                    "build_commit": pin[1] if pin else None, "build_commit_date": pin[0] if pin else None,
                    "match": "approximate: newest jtcores commit on or before the build was published"})
    return out, unmapped


# --- MRAs: which ROM sets each build loads ---------------------------------------------------------

def core_sets():
    tag = lambda t, s: (m.group(1).strip() if (m := re.search(rf"<{t}>\s*(.*?)\s*</{t}>", s, re.S | re.I)) else None)
    jobs = []
    for k in DATABASES:
        db = load_db(k)
        base = db["base_files_url"]
        for p, m in db["files"].items():
            if p.startswith("_Arcade/") and p.lower().endswith(".mra"):
                jobs.append((k, p, m.get("url") or base + urllib.parse.quote(p)))

    def get(job):
        k, p, url = job
        dest = os.path.join(MRAS, k, hashlib.sha1(p.encode()).hexdigest()[:16] + ".mra")
        if not os.path.exists(dest):
            fetch(url, dest)
        return k, open(dest, encoding="utf-8", errors="replace").read()

    by = collections.defaultdict(lambda: {"setnames": set(), "titles": set()})
    with cf.ThreadPoolExecutor(16) as ex:
        for k, s in ex.map(get, jobs):
            rbf, setn, name = tag("rbf", s), tag("setname", s), tag("name", s)
            if rbf:
                if setn:
                    by[(k, rbf.lower())]["setnames"].add(setn.lower())
                if name:
                    by[(k, rbf.lower())]["titles"].add(name)
    return by


def attach_sets(cores, sets):
    """MRAs name the core they load in their <rbf> tag, not always as the build file is named:
    Coin-Op's show "blkheart" for blkheart_mister_20260909.rbf, "zerowing_20240404" (dated) and
    "zerowing_mister" for two different builds. Try the full name, then without the date, then
    without the "_mister" suffix."""
    for c in cores:
        full = re.sub(r"\.rbf$", "", c["rbf"], flags=re.I).lower()
        nodate = re.sub(r"_\d{8}$", "", full)
        for cand in (full, nodate, re.sub(r"_mister$", "", nodate)):
            if (c["db"], cand) in sets:
                hit = sets[(c["db"], cand)]
                break
        else:
            hit = {}
        c["setnames"] = sorted(hit.get("setnames", ()))
        c["titles"] = sorted(hit.get("titles", ()))


def build():
    for k, url in DATABASES.items():
        fetch(url, os.path.join(DBS, k + ".zip"))
    dbs = {k: arcade_builds(load_db(k)) for k in DATABASES}
    official, not_distributed = map_official(dbs["dist"])
    jt, jt_unmapped = map_jtcores(dbs["jt"])
    closed = [{"db": "coinop", "channel": "default" if not any("coinopcollection" in t for t in tags)
               else "opt-in (" + next(t for t in tags if "coinopcollection" in t).replace("coinopcollection", "") + ")",
               "core": re.sub(r"(_mister)?_\d{8}\.rbf$", "", rbf, flags=re.I), "rbf": rbf, "status": "source not published"}
              for rbf, tags in sorted(dbs["coinop"].items())]
    attach_sets(official + jt + closed, core_sets())
    manifest = {"built": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                "databases": DATABASES, "cores": official + jt + closed,
                "official_listed_not_distributed": not_distributed, "jt_unmapped": jt_unmapped}
    json.dump(manifest, open(MANIFEST, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    n = collections.Counter(c["db"] for c in manifest["cores"])
    print(f"manifest: {dict(n)} | official listed but not distributed: {len(not_distributed)} | "
          f"JT unmapped: {jt_unmapped} | by-date matches: "
          f"{[c['rbf'] for c in official if c['match'] != 'exact file']}")
    return manifest
