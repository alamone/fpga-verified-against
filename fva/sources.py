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

Independent databases (DEV_DATABASES): published by individual developers outside update_all's
built-in list (users add a section to downloader.ini), so a stock install never sees them. Found through MisterZine's
source list and a GitHub search, 2026-09-29; the list is fixed here like the defaults, so a reader
knows exactly what was covered. rmCores is left out on purpose: it rebuilds official cores with
display options, and those cores are already analyzed from their official repos. Where the database
serves a build straight from its source repo (kuzecores), that URL gives repo and commit exactly;
otherwise the developer's own repos are searched for a commit that added a file of the same name.
A build with no public repository behind it is recorded as "source not published".
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
DEV_DATABASES = {  # key: (title, db_url, GitHub accounts whose repos may hold the source)
    "meat": ("MeatCores", "https://raw.githubusercontent.com/meathax/meatcores/db/db.json.zip", ["meathax"]),
    "slop": ("Slop Cores", "https://raw.githubusercontent.com/TheJesusFish/Slop-Core/db/db.json.zip", ["TheJesusFish"]),
    "kuze": ("kuzecores", "https://raw.githubusercontent.com/kuzearcade/kuzecores/db/db.json.zip", ["kuzearcade"]),
    "jlrh": ("jlrh", "https://raw.githubusercontent.com/jlrh/jlrh-misterfpga-db/db/db.json.zip", ["jlrh"]),
    "arcfpga": ("arcfpga", "https://raw.githubusercontent.com/bmo00/arcfpga-mister-db/db/db.json.zip", ["bmo00"]),
    "blahm1d": ("blahm1d", "https://mister.blahm1d.com/db.json.zip", ["blahm1d"]),
}
ALL_DATABASES = {**DATABASES, **{k: v[1] for k, v in DEV_DATABASES.items()}}
WIKI_CORES = "https://raw.githubusercontent.com/wiki/MiSTer-devel/Wiki_MiSTer/Cores.md"
JT_SOURCE = "https://github.com/jotego/jtcores.git"
JT_BIN = "https://github.com/jotego/jtcores_mister.git"


def fetch(url, dest=None):
    headers = dict(UA)
    if url.startswith("https://api.github.com/") and os.environ.get("GITHUB_TOKEN"):
        headers["Authorization"] = "Bearer " + os.environ["GITHUB_TOKEN"]   # read-only; raises the rate limit
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=60) as r:
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


def arcade_builds(db, with_url=False):
    """_Arcade/cores/*.rbf in a database, with tags resolved through its tag dictionary."""
    rev = {v: k for k, v in db.get("tag_dictionary", {}).items()}
    out = {}
    for p, m in db["files"].items():
        if p.lower().startswith("_arcade/cores/") and p.lower().endswith(".rbf"):
            tags = [rev.get(t, t) for t in m.get("tags", [])]
            out[os.path.basename(p)] = (tags, m.get("url") or (db.get("base_files_url") or "") + p) if with_url else tags
    return out


def hist_dir(repo):
    """Bare history clone for owner/name. MiSTer-devel repos keep their plain name (the cache predates
    other owners); everything else is owner__name so two owners' same-named repos cannot collide."""
    owner, name = repo.split("/")
    return os.path.join(HIST, (name if owner == "MiSTer-devel" else f"{owner}__{name}") + ".git")


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


# --- Developer databases ---------------------------------------------------------------------------

_RAW = re.compile(r"^https://raw\.githubusercontent\.com/([^/]+)/([^/]+)/([0-9a-f]{40})/(.+)$")


def _owner_repos(owner):
    repos, page = [], 1
    while True:
        batch = json.loads(fetch(f"https://api.github.com/users/{owner}/repos?per_page=100&page={page}"))
        repos += [r["full_name"] for r in batch if not r["fork"]]
        if len(batch) < 100:
            return repos
        page += 1


def _added_rbfs(repo):
    """basename -> [(commit, date, path)] for every commit that added or changed an .rbf in the repo."""
    gd = clone_history(f"https://github.com/{repo}.git", hist_dir(repo))
    out, cur = collections.defaultdict(list), None
    # --no-renames: jlrh moved builds between folders, and a rename is not an "A" or "M" otherwise
    for line in git(f"--git-dir={gd}", "log", "--all", "--no-renames", "--diff-filter=AM", "--format=@%H %cs",
                    "--name-only").stdout.splitlines():
        if line.startswith("@"):
            cur = line[1:].split()
        elif line.lower().endswith(".rbf"):
            out[os.path.basename(line.strip())].append((cur[0], cur[1], line.strip()))
    return out


def _core_subdir(repo, commit, path, rbf):
    """The folder holding this build's own source. Family repos keep one folder per core
    (jlrh/konami-fpga: cores/mystwarr for ffmystwarr_*.rbf; arcfpga-cores: cores/mystston/releases/…);
    a single-core repo is analyzed whole."""
    if "/releases/" in path:
        return path.split("/releases/")[0]
    stem = re.sub(r"^(ff|jt|arcade-)|(_\d{8})?\.rbf$", "", rbf.lower())
    dirs = git(f"--git-dir={hist_dir(repo)}", "ls-tree", "-d", "--name-only", f"{commit}:cores").stdout.split()
    return f"cores/{stem}" if stem in dirs else ""


def _bstem(name):
    """Build or repo name reduced to the core it names: Arcade-Batsugun.rbf, Batsugun_20260912.rbf and
    Arcade-Batsugun_MiSTer all give "batsugun"; jlrh's "ff" and Jotego's "jt" prefixes go too."""
    n = re.sub(r"(_\d{8})?\.rbf$", "", name.lower())
    n = re.sub(r"^(arcade[-_]|ff|jt|blahm1d_)|(_mister|-fpga)$", "", n)
    return re.sub(r"[^a-z0-9]", "", n)


def map_devdb(key, db):
    title, _, owners = DEV_DATABASES[key]
    db_repo = db.get("db_id", "")
    builds = arcade_builds(db, with_url=True)
    published = dt.datetime.fromtimestamp(db.get("timestamp", 0), dt.timezone.utc).date().isoformat()
    index = None
    out = []
    for rbf, (tags, url) in sorted(builds.items()):
        rec = {"db": key, "channel": "independent database", "core": re.sub(r"(_\d{8})?\.rbf$", "", rbf, flags=re.I),
               "rbf": rbf}
        m = _RAW.match(url)
        if m and f"{m.group(1)}/{m.group(2)}".lower() != db_repo.lower():
            repo, sha, path = f"{m.group(1)}/{m.group(2)}", m.group(3), m.group(4)
            clone_history(f"https://github.com/{repo}.git", hist_dir(repo))
            date = git(f"--git-dir={hist_dir(repo)}", "log", "-1", "--format=%cs", sha).stdout.strip()
            how = "exact: the database serves this build from the source repo at this commit"
        else:
            if index is None:   # the developer's own repos (not forks, not the database itself)
                index, repos = {}, []
                for o in owners:
                    try:
                        repos += [r for r in _owner_repos(o) if r.lower() != db_repo.lower()]
                    except Exception:  # noqa: BLE001  (account gone: every build is then unpublished)
                        pass
                for r in repos:
                    for b, hits in _added_rbfs(r).items():
                        index.setdefault(b, []).extend((r, *h) for h in hits)
            st = _bstem(rbf)
            hits = index.get(rbf, [])
            if hits:   # the same file in the developer's repos; one named after the core wins a tie
                hits = [h for h in hits if _bstem(h[0].split("/")[1]) == st] or hits
                repo, sha, date, path = max([h for h in hits if h[2] <= published] or hits, key=lambda h: h[2])
                how = "exact file"
            else:
                # The database's build is not committed anywhere (Slop Cores ship a rebuilt, dated file;
                # the repo keeps an undated one). One repo naming the same core, pinned like JTCORES:
                # its newest commit on or before the build's date, and marked approximate.
                cands = sorted({h[0] for b, hs in index.items() if _bstem(b) == st for h in hs} |
                               {r for r in repos if _bstem(r.split("/")[1]) == st})
                if len(cands) > 1:
                    # A repo started as a copy of another keeps its builds (s32multi still carries
                    # System 32 builds from before it split off). The one still building this core is
                    # the one with the newest build of it.
                    newest = {r: max((h[2] for b, hs in index.items() if _bstem(b) == st for h in hs if h[0] == r),
                                     default="") for r in cands}
                    top = max(newest.values())
                    if top and list(newest.values()).count(top) == 1:
                        cands = [r for r in cands if newest[r] == top]
                if len(cands) != 1:
                    out.append(dict(rec, status="source not published",
                                    note=f"several candidate repos: {', '.join(cands)}" if cands else ""))
                    continue
                repo, path = cands[0], ""
                m8 = re.search(r"_(\d{4})(\d{2})(\d{2})\.rbf$", rbf)
                bdate = "-".join(m8.groups()) if m8 else published
                line = git(f"--git-dir={hist_dir(repo)}", "log", "-1", "--format=%H %cs", f"--until={bdate} 23:59:59",
                           "HEAD").stdout.split()
                if not line:
                    out.append(dict(rec, status="source not published"))
                    continue
                sha, date = line
                how = f"approximate: this build is not in the source repo; newest commit on or before {bdate}"
        out.append(dict(rec, repo=repo, ref=None, subdir=_core_subdir(repo, sha, path, rbf),
                        build_commit=sha, build_commit_date=date, match=how))
    return out


# --- MRAs: which ROM sets each build loads ---------------------------------------------------------

def core_sets():
    tag = lambda t, s: (m.group(1).strip() if (m := re.search(rf"<{t}>\s*(.*?)\s*</{t}>", s, re.S | re.I)) else None)
    jobs = []
    for k in ALL_DATABASES:
        db = load_db(k)
        base = db.get("base_files_url") or ""
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
    "zerowing_mister" for two different builds; kuzecores' show "NMK16_Afega" for
    Arcade-NMK16_Afega_20260920.rbf (MiSTer drops the "Arcade-" prefix when it resolves them). Try the
    full name, then without the date, then without the "_mister" suffix or the "Arcade-" prefix."""
    for c in cores:
        full = re.sub(r"\.rbf$", "", c["rbf"], flags=re.I).lower()
        nodate = re.sub(r"_\d{8}$", "", full)
        for cand in (full, nodate, re.sub(r"_mister$", "", nodate), re.sub(r"^arcade-", "", nodate)):
            if (c["db"], cand) in sets:
                hit = sets[(c["db"], cand)]
                break
        else:
            hit = {}
        c["setnames"] = sorted(hit.get("setnames", ()))
        c["titles"] = sorted(hit.get("titles", ()))


def build():
    for k, url in ALL_DATABASES.items():
        fetch(url, os.path.join(DBS, k + ".zip"))
    dbs = {k: arcade_builds(load_db(k)) for k in DATABASES}
    official, not_distributed = map_official(dbs["dist"])
    jt, jt_unmapped = map_jtcores(dbs["jt"])
    closed = [{"db": "coinop", "channel": "default" if not any("coinopcollection" in t for t in tags)
               else "opt-in (" + next(t for t in tags if "coinopcollection" in t).replace("coinopcollection", "") + ")",
               "core": re.sub(r"(_mister)?_\d{8}\.rbf$", "", rbf, flags=re.I), "rbf": rbf, "status": "source not published"}
              for rbf, tags in sorted(dbs["coinop"].items())]
    dev = [c for k in DEV_DATABASES for c in map_devdb(k, load_db(k))]
    attach_sets(official + jt + closed + dev, core_sets())
    manifest = {"built": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
                "databases": DATABASES, "developer_databases": {k: {"title": v[0], "url": v[1]} for k, v in DEV_DATABASES.items()},
                "cores": official + jt + closed + dev,
                "official_listed_not_distributed": not_distributed, "jt_unmapped": jt_unmapped}
    json.dump(manifest, open(MANIFEST, "w", encoding="utf-8"), indent=1, ensure_ascii=False)
    n = collections.Counter(c["db"] for c in manifest["cores"])
    print(f"manifest: {dict(n)} | official listed but not distributed: {len(not_distributed)} | "
          f"JT unmapped: {jt_unmapped} | by-date matches: "
          f"{[c['rbf'] for c in official if c['match'] != 'exact file']}")
    return manifest
