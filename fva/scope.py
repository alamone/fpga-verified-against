"""Which HDL files a build is made from: the core's own code is what the build compiles, not every file
in the repository.

Before v0.5 every HDL file under the core's folder was read, so side folders counted as the core
(SNK6502's "Useful Information/Ian Suggestions" notes, abandoned experiments, a second board's
variant), and a JTCORES core that takes its HDL from a sibling core (Paroda uses Riders' and Simpsons'
modules) was read from an almost empty folder.

- MiSTer projects: the core's Quartus project. The .qsf names the HDL files and QIP files; a QIP names
  more, often as [file join $::quartus(qip_path) rtl/x.sv], relative to the QIP itself. A repo with
  several projects (kuzecores' NMK16 builds one per board family) uses the project named like the
  build, else all of them.
- JTCORES: cores/<core>/cfg/files.yaml, by JTFRAME's rules (modules/jtframe/doc/jtframe-files.md): a
  section named after a core takes files from cores/<name>/hdl/, an empty section pulls in that core's
  own files.yaml, a .yaml entry is another list in that core's cfg/. Sections naming a module
  (jtframe, jt680x, jt12...) are shared libraries and stay excluded, as before.

Either way, files a listed file pulls in with Verilog's `include are part of the build too (Druaga's
ioctrl.v includes ioctrl_0/1/2.v; batch-1 structural review, 2026-10-31, found them missing).

Where neither exists the scope falls back to every HDL file under the core's folder and says so, so a
reader knows which reading rests on the narrower rule. Shared-library folders (analyze.LIB_DIRS) are
excluded either way.
"""
import glob
import os
import re

HDL_EXT = (".v", ".sv", ".vhd", ".vhdl")
_INCLUDE = re.compile(r'^\s*`include\s+"([^"]+)"', re.M)
_FRAMEWORK_INCLUDES = {"build_id.v"}   # MiSTer's build date, written by the Quartus flow
# SOURCE_FILE: Quartus takes the language from the extension. NaughtyBoy, Phoenix and Pleiads list
# their whole board that way, so before v0.14 they were read as a T80 and the framework.
_ASSIGN = re.compile(r"set_global_assignment\s+-name\s+(VERILOG_FILE|SYSTEMVERILOG_FILE|VHDL_FILE|SOURCE_FILE|QIP_FILE)"
                     r"\s+(.+)$", re.I)


def _norm(name):
    return re.sub(r"[^a-z0-9]", "", re.sub(r"^(arcade[-_])|(_\d{8}[a-z]?)?(\.rbf|\.qsf)$", "", name.lower()))


def _qsf_paths(value, base, project):
    """The file named by one assignment, as candidate absolute paths."""
    value = value.strip()
    m = re.search(r"qip_path\)\s*\"?([^\]\"]+)", value)
    if m:
        return [os.path.normpath(os.path.join(base, m.group(1).strip()))]
    tokens = [t.strip("\"'{}") for t in value.split()]
    path = next((t for t in reversed(tokens) if "." in t and not t.startswith("-")), None)
    if not path:
        return []
    return [os.path.normpath(os.path.join(project, path)), os.path.normpath(os.path.join(base, path))]


def _case_fold(path, root=None):
    """The file a case-insensitive filesystem would open for `path`, or None. Quartus runs on
    Windows, where rtl/pokey/ finds rtl/Pokey/, so a project can name a file in the wrong case and
    still build; on the Linux runner the exact-case lookup missed it (CrystalCastles, Exerion and
    TaitoSJ, all shared libraries, found by structural batch 3).

    Every path goes through here, not only the ones an exact lookup misses: the name returned is
    the one on disk, so a project that spells one folder two ways (PinballAction's rtl/JT49 and
    rtl/jt49) lists each file once. Windows found both spellings and counted seven files twice.
    Given the project folder as `root`, every name below it is matched against the disk, since on
    Windows rtl/JT49 exists as spelled and would otherwise be kept."""
    head, parts = path, []
    rel = os.path.relpath(path, root) if root else os.pardir
    if not rel.startswith(os.pardir):
        head, parts = root, list(reversed(rel.split(os.sep)))
    while not os.path.isdir(head):
        head, tail = os.path.split(head)
        if not tail:
            return None
        parts.append(tail)
    for part in reversed(parts):
        try:
            match = next((e for e in os.listdir(head) if e.lower() == part.lower()), None)
        except OSError:
            return None
        if match is None:
            return None
        head = os.path.join(head, match)
    return head if os.path.isfile(head) else None


def _read_project(path, project, seen):
    out = set()
    if path in seen or not os.path.exists(path):
        return out
    seen.add(path)
    base = os.path.dirname(path)
    for line in open(path, encoding="utf-8", errors="replace"):
        line = line.split("#", 1)[0]
        # MiSTer's project template pulls its file list in with Tcl: "source files.qip"
        s = re.match(r"\s*source\s+\"?([^\s\"]+\.qip)", line, re.I)
        if s:
            inc = os.path.normpath(os.path.join(base, s.group(1)))
            out |= _read_project(_case_fold(inc, project) or inc, project, seen)
            continue
        m = _ASSIGN.search(line)
        if not m:
            continue
        cands = _qsf_paths(m.group(2), base, project)
        if m.group(1).upper() == "QIP_FILE":
            # a .qip is case-folded too: SegaVICZ80 names rtl/tv80/TV80.qip, and the file is tv80.qip
            for c in cands:
                out |= _read_project(_case_fold(c, project) or c, project, seen)
        else:
            hit = next(filter(None, (_case_fold(c, project) for c in cands)), None)
            if hit:
                out.add(hit)
    return out


def quartus_files(core_dir, rbf):
    qsfs = [f for f in os.listdir(core_dir) if f.lower().endswith(".qsf")]
    if not qsfs:
        return None
    want = _norm(rbf or "")
    named = [f for f in qsfs if _norm(f) == want]
    # Quartus 13 copies (X_Q13.qsf) build the same core for the older toolchain
    pick = named or ([q for q in qsfs if not re.search(r"_q13\.qsf$", q, re.I)] or qsfs)
    files = set()
    for q in pick:
        files |= _read_project(os.path.join(core_dir, q), core_dir, set())
    files = {f for f in files if f.lower().endswith(HDL_EXT)}
    return sorted(files) or None


def _yaml_sections(path):
    """cores/<x>/cfg/*.yaml in the small subset JTFRAME uses: top-level sections, each a list of
    {from, get: [files]} groups. Conditions (when/unless) are ignored, so every conditional file counts."""
    sections, key, cur = {}, None, None
    for raw in open(path, encoding="utf-8", errors="replace"):
        line = raw.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        s = line.strip()
        if not raw[0].isspace() and s.endswith(":"):
            key, cur = s[:-1].strip().strip("\"'"), None   # numeric names are quoted: "1943":
            sections[key] = []
            continue
        if key is None:
            continue
        item = s[2:].strip() if s.startswith("- ") else s
        if item.startswith("from:"):
            cur = {"from": item[5:].strip(), "get": []}
            sections[key].append(cur)
        elif item.startswith("get:"):
            if cur is None or s.startswith("- "):
                cur = {"from": "", "get": []}
                sections[key].append(cur)
            rest = item[4:].strip()
            if rest.startswith("["):
                cur["get"] += [x.strip() for x in rest.strip("[]").split(",") if x.strip()]
        elif item.startswith(("when:", "unless:")):
            continue
        elif s.startswith("- "):
            if cur is None:
                cur = {"from": "", "get": []}
                sections[key].append(cur)
            cur["get"].append(item)
    return sections


def jt_files(core_dir):
    root = os.path.dirname(os.path.dirname(core_dir))   # jtcores checkout: cores/<core>
    start = os.path.join(core_dir, "cfg", "files.yaml")
    if not os.path.exists(start):
        return None
    out, seen = set(), set()

    def walk(yaml_path):
        if yaml_path in seen or not os.path.exists(yaml_path):
            return
        seen.add(yaml_path)
        for key, groups in _yaml_sections(yaml_path).items():
            cdir = os.path.join(root, "cores", key)
            if not os.path.isdir(cdir):
                continue   # a module (jtframe, jt680x, jt12...): shared library, excluded
            if not groups:
                walk(os.path.join(cdir, "cfg", "files.yaml"))
            for g in groups:
                for f in g["get"]:
                    f = f.strip("\"'")
                    if f.endswith(".yaml"):
                        walk(os.path.join(cdir, "cfg", f))
                    else:   # names may be wildcards: shouse lists "*.v"
                        for p in glob.glob(os.path.join(cdir, "hdl", g["from"], f)):
                            out.add(os.path.normpath(p))
    walk(start)
    files = sorted(f for f in out if f.lower().endswith(HDL_EXT))
    return files or None


def with_includes(files, core_dir):
    """Add every file the list pulls in with `include, followed recursively. A name resolves against
    the including file's folder, then the core's folder, then the one file of that name anywhere
    under the core's folder; anything else (a JTFRAME macro file, an unresolvable name) is skipped."""
    out, todo = set(files), list(files)
    index = None
    while todo:
        f = todo.pop()
        if not f.lower().endswith((".v", ".sv", ".vh", ".svh")):
            continue
        try:
            text = open(f, encoding="utf-8", errors="replace").read()
        except OSError:
            continue
        for name in _INCLUDE.findall(text):
            if os.path.basename(name).lower() in _FRAMEWORK_INCLUDES:
                continue
            cands = [os.path.normpath(os.path.join(os.path.dirname(f), name)),
                     os.path.normpath(os.path.join(core_dir, name))]
            hit = next((c for c in cands if os.path.isfile(c)), None)
            if hit is None:
                if index is None:
                    index = {}
                    for dp, _, fn in os.walk(core_dir):
                        for x in fn:
                            index.setdefault(x.lower(), []).append(os.path.join(dp, x))
                # isfile: a JT checkout is sparse, so a symlink can point at a folder it left out
                found = [x for x in index.get(os.path.basename(name).lower(), []) if os.path.isfile(x)]
                hit = os.path.normpath(found[0]) if len(found) == 1 else None
            if hit and hit not in out:
                out.add(hit)
                todo.append(hit)
    return sorted(out)


def build_files(c, core_dir):
    """-> (files or None for "every HDL file", how the scope was decided)."""
    if c["db"] == "jt":
        files = jt_files(core_dir)
        how = "files.yaml" if files else "all HDL files: no cfg/files.yaml"
    else:
        files = quartus_files(core_dir, c.get("rbf"))
        how = "Quartus project" if files else "all HDL files: no Quartus project found"
    return (with_includes(files, core_dir) if files else files), how


def jt_generated(core_dir):
    """Files cfg/files.yaml lists that are not in the repository because JTFRAME writes them at build
    time from a cfg/*.yaml (toki's jttoki_video_mmr.v comes from cfg/mmr.yaml), as
    {listed name: the yaml it is generated from}. A reviewer is pointed at the yaml instead."""
    start = os.path.join(core_dir, "cfg", "files.yaml")
    if not os.path.exists(start):
        return {}
    out = {}
    for key, groups in _yaml_sections(start).items():
        cdir = os.path.join(os.path.dirname(os.path.dirname(core_dir)), "cores", key)
        for g in groups:
            for f in g["get"]:
                f = f.strip("\"'")
                if f.endswith(".yaml") or glob.glob(os.path.join(cdir, "hdl", g["from"], f)):
                    continue
                m = re.search(r"_(mmr)\.s?v$", f)
                src = os.path.join(cdir, "cfg", f"{m.group(1)}.yaml") if m else None
                if src and os.path.exists(src):
                    out[f] = os.path.normpath(src)
    return out
