"""Provenance evidence for an FPGA core vs the MAME driver for the same games.

Produces, per core, the EVIDENCE (not a verdict): what the core's own HDL shares with the MAME
driver it corresponds to, what it cites from hardware, and what it says about itself. Every item
carries file:line so a reader can check it and disagree.

Signals:
  A. shared text   — 6-word runs in the core's comments that also occur in the MAME driver files
                     (comments carry across languages, so a C++ -> HDL translation keeps them)
  B. rare shared identifiers — names in the core's code that appear in the MAME driver and in
                     few MAME files overall (common words and chip names excluded by that rarity)
  C. MAME handler naming — identifiers ending _w / _r (MAME's read/write-handler convention)
  D. MAME mentions in the core's own code comments
  E. hardware evidence — TTL part numbers, schematic/PAL/sheet references, measurement words,
                     in the core's comments and docs
Known blind spots, reported with the results: ROM file names (MiSTer uses MAME's sets by design),
memory addresses (a faithful core must share them), CPU/sound chip libraries (excluded).
"""
import collections
import json
import os
import re
import sys

from .paths import MAME, WORK
HDL_EXT = (".v", ".sv", ".vhd", ".vhdl")
# Shared libraries and framework, excluded from "the core's own code". Listed in every report.
LIB_DIRS = {"sys", "sim", "jt12", "jt03", "jt6295", "jt5205", "jt51", "jtopl", "jtframe", "t80",
            "fx68k", "tg68k", "ucore", "common", "lib", "modules", "arcadia", "highscore", "sound",
            "releases", "pll", "mister"}
# v0.9: the same framework, copied in as a single file rather than a folder. hiscore.v is the MiSTer
# arcade template's high-score saver ("MAME hiscore.dat support for MiSTer arcade cores"), shipped in
# 85 cores' rtl/ folders; its one MAME mention scored as a citation and its ~800 lines then weighed
# in every one of those cores' averages. The highscore/ folder form was already excluded.
LIB_FILES = {"hiscore.v", "hiscore.sv"}
WORD = re.compile(r"[a-z0-9]+")
IDENT = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]{5,}\b")
GENERIC = set("""clock reset enable address output input signal buffer counter select write
read value always assign module endmodule begin wire logic integer parameter localparam
generate function return default unsigned signed""".split())


def comments(text, ext):
    """(line_no, comment_text) for // and /* */ (Verilog/SV) or -- (VHDL)."""
    out = []
    if ext in (".vhd", ".vhdl"):
        for i, line in enumerate(text.splitlines(), 1):
            if "--" in line:
                out.append((i, line.split("--", 1)[1]))
        return out
    for m in re.finditer(r"//[^\n]*|/\*.*?\*/", text, re.S):
        out.append((text.count("\n", 0, m.start()) + 1, m.group(0).lstrip("/*").rstrip("*/")))
    return out


def strip_comments(text, ext):
    if ext in (".vhd", ".vhdl"):
        return re.sub(r"--[^\n]*", "", text)
    return re.sub(r"//[^\n]*|/\*.*?\*/", "", text, flags=re.S)


def rel_path(f, core_dir):
    """A file's path as shown and linked: relative to the core's folder, or, for a file a JTCORES core
    takes from a sibling core, from the repository's cores/ folder (the report links cores/... as is)."""
    r = os.path.relpath(f, core_dir).replace("\\", "/")
    if r.startswith("../"):
        a = os.path.abspath(f).replace("\\", "/")
        r = "cores/" + a.rsplit("/cores/", 1)[1] if "/cores/" in a else r
    return r


def own_hdl(core_dir, only=None):
    """The core's own HDL. `only`: the files the build compiles (fva/scope.py); None reads every HDL
    file under the folder. Shared-library folders are excluded either way and counted."""
    files, excluded = [], collections.Counter()
    if only is not None:
        for f in only:
            parts = [p.lower() for p in rel_path(f, core_dir).split("/")[:-1]]
            lib = next((p for p in parts if p in LIB_DIRS), None) or _lib_file(f)
            if lib:
                excluded[lib] += 1
            else:
                files.append(f)
        return files, excluded
    for dp, dn, fn in os.walk(core_dir):
        rel = os.path.relpath(dp, core_dir).replace("\\", "/")
        parts = [p.lower() for p in rel.split("/") if p != "."]
        if ".git" in parts:
            continue
        for f in fn:
            if not f.lower().endswith(HDL_EXT):
                continue
            lib = next((p for p in parts if p in LIB_DIRS), None) or _lib_file(f)
            if lib:
                excluded[lib] += 1
            else:
                files.append(os.path.join(dp, f))
    return files, excluded


def _lib_file(path):
    name = os.path.basename(path).lower()
    return name if name in LIB_FILES else None


# Cores without .mra loader files (older cores load ROMs another way): set named by hand, and the
# report says so.
MANUAL_SETS = {"1943_MiSTer": {"1943"}}


def setnames(core_dir):
    names = set(MANUAL_SETS.get(os.path.basename(core_dir), ()))
    for dp, _, fn in os.walk(core_dir):
        for f in fn:
            if f.lower().endswith(".mra"):
                t = open(os.path.join(dp, f), encoding="utf-8", errors="replace").read()
                names.update(re.findall(r"<setname>\s*([a-z0-9_]+)\s*</setname>", t))
    return names


_game_index = None


def game_index():
    """setname -> driver .cpp, from GAME/CONS/SYST macros across src/mame."""
    global _game_index
    if _game_index is None:
        _game_index = {}
        pat = re.compile(r"^\s*GAMEL?\s*\(\s*[^,]+,\s*([a-z0-9_]+)\s*,", re.M)
        for dp, _, fn in os.walk(MAME):
            for f in fn:
                if f.endswith(".cpp"):
                    p = os.path.join(dp, f)
                    for s in pat.findall(open(p, encoding="utf-8", errors="replace").read()):
                        _game_index.setdefault(s, p)
    return _game_index


def driver_files(drivers):
    """The driver .cpp plus local headers it includes and their .cpp siblings (video, devices)."""
    seen, todo = set(), list(drivers)
    while todo:
        p = todo.pop()
        if p in seen or not os.path.exists(p):
            continue
        seen.add(p)
        if len(seen) > 40:
            break
        t = open(p, encoding="utf-8", errors="replace").read()
        for inc in re.findall(r'#include\s+"([^"]+\.h)"', t):
            cand = [os.path.join(os.path.dirname(p), inc), os.path.join(MAME, inc)]
            for c in cand:
                if os.path.exists(c):
                    todo.append(c)
                    cpp = c[:-2] + ".cpp"
                    if os.path.exists(cpp):
                        todo.append(cpp)
                    break
    return sorted(seen)


_ident_df = None


def ident_df():
    """Identifier -> number of MAME files containing it (rarity)."""
    global _ident_df
    if _ident_df is None:
        cache = os.path.join(WORK, "mame_ident_df.json")
        if os.path.exists(cache):
            _ident_df = json.load(open(cache))
        else:
            df = collections.Counter()
            for dp, _, fn in os.walk(MAME):
                for f in fn:
                    if f.endswith((".cpp", ".h")):
                        t = open(os.path.join(dp, f), encoding="utf-8", errors="replace").read()
                        df.update({w.lower() for w in IDENT.findall(t)})
            _ident_df = dict(df)
            json.dump(_ident_df, open(cache, "w"))
    return _ident_df


def shingles(words, n=6):
    return {" ".join(words[i:i + n]) for i in range(len(words) - n + 1)}


# v0.7: standard license notices are not "text shared with MAME". Breakout's GPL header matched
# the GPL header in MAME's nl_breakout.cpp line for line and scored as eight copied comments
# (operator spot check, 2026-09-30). Rather than a keyword filter, which would also drop a real
# comment that mentions a license, the canonical wording of the common notices is shingled and
# those runs are removed from MAME's side of the comparison.
LICENSE_NOTICES = """
This program is free software; you can redistribute it and/or modify it under the terms of the
GNU General Public License as published by the Free Software Foundation; either version 2 of the
License, or (at your option) any later version. This program is distributed in the hope that it
will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details. You should
have received a copy of the GNU General Public License along with this program; if not, write to
the Free Software Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
59 Temple Place, Suite 330, Boston, MA 02111-1307 USA.
This program is free software: you can redistribute it and/or modify it under the terms of the
GNU General Public License as published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version. You should have received a copy of the GNU General
Public License along with this program. If not, see <http://www.gnu.org/licenses/>.
This library is free software; you can redistribute it and/or modify it under the terms of the GNU
Lesser General Public License as published by the Free Software Foundation; either version 2.1 of
the License, or (at your option) any later version. This library is distributed in the hope that
it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
FITNESS FOR A PARTICULAR PURPOSE. See the GNU Lesser General Public License for more details. You
should have received a copy of the GNU Lesser General Public License along with this library.
Redistribution and use in source and binary forms, with or without modification, are permitted
provided that the following conditions are met: Redistributions of source code must retain the
above copyright notice, this list of conditions and the following disclaimer. Redistributions in
binary form must reproduce the above copyright notice, this list of conditions and the following
disclaimer in the documentation and/or other materials provided with the distribution. Neither the
name of the copyright holder nor the names of its contributors may be used to endorse or promote
products derived from this software without specific prior written permission. THIS SOFTWARE IS
PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES,
INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A
PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT
NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR
BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT
LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
Permission is hereby granted, free of charge, to any person obtaining a copy of this software and
associated documentation files (the "Software"), to deal in the Software without restriction,
including without limitation the rights to use, copy, modify, merge, publish, distribute,
sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions: The above copyright notice and this
permission notice shall be included in all copies or substantial portions of the Software.
THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT
NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT.
Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except
in compliance with the License. You may obtain a copy of the License at
http://www.apache.org/licenses/LICENSE-2.0 Unless required by applicable law or agreed to in
writing, software distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the specific
language governing permissions and limitations under the License.
"""
# v0.10: MAME's input-port and DIP-switch definitions (PORT_DIPNAME, PORT_DIPSETTING ...) copied into
# a comment, as Irem M62's input_mapper.vhd does for 13 lines. DIP settings are the game's operator
# documentation, which any correct core shares, like ROM names; copying them says nothing about
# what the logic was checked against.
INPUT_PORT_DEF = re.compile(r"\bPORT_(?:DIP\w*|SERVICE\w*|START|BIT|INCLUDE|MODIFY|CONFNAME|CONFSETTING)\b|"
                            r"\bDEF_STR\s*\(")
LICENSE_SHINGLES = shingles(re.compile(r"[a-z0-9]+").findall(LICENSE_NOTICES.lower()))


HW = [
    ("TTL part number", re.compile(r"\b74(?:LS|S|HC|HCT|F|ALS|AS)?\d{2,4}\b", re.I)),
    ("schematic / sheet", re.compile(r"schematic|\bsheet\s*\d|\bsch\b", re.I)),
    ("PAL/GAL/PROM logic", re.compile(r"\b(?:PAL|GAL|PLD)\d*\b|equation", re.I)),
    ("board location", re.compile(r"\b(?:IC|U)\s?\d{1,3}[A-Z]?\b|\b\d{1,2}[A-H]\b(?=[^a-z])")),
    ("measured on hardware", re.compile(r"measur|logic analy|oscillo|scope|captur|real (?:hw|hardware|pcb|board)|on the pcb|from the pcb", re.I)),
    ("decap / die", re.compile(r"decap|die shot|netlist", re.I)),
]


def analyze(name, core_dir=None, sets=None, only=None):
    """core_dir / sets default to the calibration layout (cores/<name>, sets read from its MRAs);
    the full run passes a pinned checkout, the sets from the distributed MRAs and the build's files."""
    assert core_dir, "core_dir is required"
    files, excluded = own_hdl(core_dir, only)
    sets = set(sets) if sets is not None else setnames(core_dir)
    gi = game_index()
    drivers = sorted({gi[s] for s in sets if s in gi})
    dfiles = driver_files(drivers)
    mame_text = {p: open(p, encoding="utf-8", errors="replace").read() for p in dfiles}
    mame_sh = {}
    for p, t in mame_text.items():
        for s in shingles(WORD.findall(t.lower())):
            mame_sh.setdefault(s, p)
    mame_idents = {w.lower() for t in mame_text.values() for w in IDENT.findall(t)}
    df = ident_df()

    shared_text, ids, handlers, mame_mentions, hw = [], collections.defaultdict(list), [], [], collections.defaultdict(list)
    n_comment_words = n_lines = 0
    for f in files:
        ext = os.path.splitext(f)[1].lower()
        text = open(f, encoding="utf-8", errors="replace").read()
        rel = rel_path(f, core_dir)
        n_lines += text.count("\n")
        for line, c in comments(text, ext):
            words = WORD.findall(c.lower())
            n_comment_words += len(words)
            hits = [s for s in shingles(words) if s in mame_sh and s not in LICENSE_SHINGLES]
            if hits and not INPUT_PORT_DEF.search(c):
                shared_text.append({"at": f"{rel}:{line}", "comment": c.strip()[:200],
                                    "mame": os.path.relpath(mame_sh[hits[0]], MAME).replace("\\", "/"),
                                    "runs": len(hits)})
            if re.search(r"\bmame\b|\.cpp\b", c, re.I):
                mame_mentions.append({"at": f"{rel}:{line}", "comment": c.strip()[:200]})
            for label, pat in HW:
                if pat.search(c):
                    hw[label].append({"at": f"{rel}:{line}", "comment": c.strip()[:160]})
        code = strip_comments(text, ext)
        for w in set(IDENT.findall(code)):
            lw = w.lower()
            if lw in GENERIC:
                continue
            if lw in mame_idents and df.get(lw, 0) <= 5:
                ids[lw].append(rel)
            if re.search(r"[a-z0-9]_[wr]$", lw) and lw in mame_idents:
                handlers.append({"ident": w, "at": rel})
    docs = []
    for dp, _, fn in os.walk(core_dir):
        if ".git" in dp:
            continue
        for f in fn:
            if f.lower().endswith((".md", ".txt")) and "releases" not in dp:
                docs.append(os.path.join(dp, f))
    doc_hw = collections.defaultdict(list)
    for d in docs:
        rel = os.path.relpath(d, core_dir).replace("\\", "/")
        for i, line in enumerate(open(d, encoding="utf-8", errors="replace"), 1):
            for label, pat in HW:
                if label in ("board location",):
                    continue
                if pat.search(line):
                    doc_hw[label].append({"at": f"{rel}:{i}", "text": line.strip()[:160]})
    return {
        "core": name,
        "own_hdl_files": len(files), "own_hdl_lines": n_lines, "comment_words": n_comment_words,
        "excluded_library_files": dict(excluded),
        "setnames": sorted(sets),
        "setnames_manual": os.path.basename(core_dir) in MANUAL_SETS,
        "mame_drivers": [os.path.relpath(p, MAME).replace("\\", "/") for p in drivers],
        "mame_files_compared": [os.path.relpath(p, MAME).replace("\\", "/") for p in dfiles],
        "A_shared_text": shared_text,
        "B_rare_shared_identifiers": {k: sorted(set(v)) for k, v in sorted(ids.items())},
        "C_mame_handler_names": handlers,
        "D_mame_mentions_in_code": mame_mentions,
        "E_hardware_evidence_code": {k: v for k, v in hw.items()},
        "E_hardware_evidence_docs": {k: v for k, v in doc_hw.items()},
    }


