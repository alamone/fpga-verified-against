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

Where neither exists the scope falls back to every HDL file under the core's folder and says so, so a
reader knows which reading rests on the narrower rule. Shared-library folders (analyze.LIB_DIRS) are
excluded either way.
"""
import glob
import os
import re

HDL_EXT = (".v", ".sv", ".vhd", ".vhdl")
_ASSIGN = re.compile(r"set_global_assignment\s+-name\s+(VERILOG_FILE|SYSTEMVERILOG_FILE|VHDL_FILE|QIP_FILE)\s+(.+)$",
                     re.I)


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
            out |= _read_project(os.path.normpath(os.path.join(base, s.group(1))), project, seen)
            continue
        m = _ASSIGN.search(line)
        if not m:
            continue
        cands = _qsf_paths(m.group(2), base, project)
        if m.group(1).upper() == "QIP_FILE":
            for c in cands:
                out |= _read_project(c, project, seen)
        else:
            hit = next((c for c in cands if os.path.exists(c)), None)
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
            key, cur = s[:-1].strip(), None
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


def build_files(c, core_dir):
    """-> (files or None for "every HDL file", how the scope was decided)."""
    if c["db"] == "jt":
        files = jt_files(core_dir)
        return files, ("files.yaml" if files else "all HDL files: no cfg/files.yaml")
    files = quartus_files(core_dir, c.get("rbf"))
    return files, ("Quartus project" if files else "all HDL files: no Quartus project found")
