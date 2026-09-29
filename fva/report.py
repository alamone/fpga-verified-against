"""results/results.json -> results/index.html: one row per core, a meter from MAME (left) to hardware
(right), and every statement behind it linked to its line at the analyzed commit.

Wording is descriptive only: the page reports what each core's own code states, never a judgment.
Below LOW confidence the bar is a colorless outline with no needle ("not enough evidence"); a
closed-source build gets a dashed outline ("source not published") — different states, labelled so.
"""
import html
import json
import os
from urllib.parse import quote

from .paths import RESULTS

LABEL = {  # rule -> (side, title, what it includes)
    "hw_specific": ("hardware", "Cites hardware documentation that MAME's driver does not",
                    "schematic sheet, part number, chip location, dumped PAL, decap — only when MAME's driver for the game does not already give it"),
    "hw_ref_in_mame": ("neutral", "Cites hardware references that MAME's driver also gives",
                       "not counted: copying them from MAME would look the same"),
    "hw_verified": ("hardware", "Says it was checked against the original PCB", "explicitly the original board, PCB or arcade hardware"),
    "hw_measured": ("hardware", "Reports a measurement taken on the original PCB",
                    "states a value; measurements of the MiSTer itself (e.g. SignalTap) do not count"),
    "hw_verified_unclear": ("hardware", "Says it was checked on “real hardware”",
                            "may mean the MiSTer board itself rather than the original PCB, so it counts less"),
    "hw_files": ("hardware", "Ships hardware documentation files", "schematic sheets, schematic PDFs, PAL equations in the core's own folder"),
    "mame_diverge": ("hardware", "Notes where it differs from MAME", "a stated difference implies another reference"),
    "mame_cited": ("mame", "Cites MAME source", "a MAME file, function or line"),
    "mame_verified": ("mame", "Says it matches or was checked against MAME", ""),
    "mame_transcribed": ("mame", "Says it was translated or ported from MAME", ""),
    "mame_surrogate": ("mame", "Keeps a MAME approximation", "where MAME itself notes a guess or stand-in"),
    "copied_text": ("mame", "Shares text with the MAME driver without saying so", "a 6-word run in a comment"),
}
POINTS = {"hw_specific": "+0.5", "hw_ref_in_mame": "0", "hw_verified": "+2", "hw_verified_unclear": "+1",
          "hw_files": "+2", "hw_measured": "+3", "mame_diverge": "+3", "mame_cited": "−0.5",
          "mame_verified": "−2", "mame_transcribed": "−3", "mame_surrogate": "−1", "copied_text": "−1"}
DBNAME = {"dist": "MiSTer official", "jt": "JTCORES", "coinop": "Coin-Op Collection"}
READING = {"mostly hardware": "Mostly hardware", "both": "Both", "mostly MAME": "Mostly MAME",
           "not enough evidence": "Not enough evidence in the code"}

# MAME end blue (its logo). Hardware end amber, not MiSTer's white: every core here is a MiSTer core,
# the right end means the original board, and white would blur into the outlined no-score bars and
# the white needle. Blue/amber stays distinct under red-green color blindness; links are a muted
# blue so they don't read as MAME.
CSS = """:root{--bg:#0f1115;--fg:#e6e6e6;--muted:#9aa0ad;--line:#2a2f3a;--hw:#e8a33d;--mame:#2f6fd6}
body{background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,sans-serif;margin:0 auto;padding:24px 16px;max-width:1100px}
a{color:#b4c2dc} code{font-size:12.5px} .muted{color:var(--muted)} .small{font-size:13px}
.note{border-left:3px solid var(--muted);padding:4px 12px;margin:12px 0}
.meter{position:relative;height:16px;width:150px}
.meter .bar{position:absolute;top:5px;left:0;right:0;height:6px;border-radius:3px;background:linear-gradient(90deg,var(--mame),#777 50%,var(--hw))}
.meter.empty .bar{background:transparent;border:1.5px solid var(--fg);height:10px;top:2px}
.meter.closed .bar{border-style:dashed}
.meter .needle{position:absolute;top:1px;width:3px;height:14px;margin-left:-1.5px;background:#fff;border-radius:2px;box-shadow:0 0 0 2px #0008}
.axis{display:flex;justify-content:space-between;width:150px;font-size:11px;color:var(--muted)}
details{border-left:3px solid var(--line);padding:2px 10px;margin:4px 0} details.hardware{border-color:var(--hw)}
details.mame{border-color:var(--mame)} details.neutral{border-color:#777}
details ul{margin:6px 0;padding-left:18px;max-height:320px;overflow:auto} li{margin:3px 0;overflow-wrap:anywhere}
table{border-collapse:collapse;width:100%} td{padding:4px 8px;border-bottom:1px solid var(--line);vertical-align:top;font-size:14px}
tr.ev td{padding:0 8px 8px 24px} .num{text-align:right}"""


def a(href, text):
    return f'<a href="{html.escape(href)}">{html.escape(text)}</a>'


def meter(pos, closed=False):
    cls = "meter" + (" empty" if pos is None else "") + (" closed" if closed else "")
    needle = "" if pos is None else f'<div class="needle" style="left:{pos:.0f}%"></div>'
    return f'<div class="{cls}"><div class="bar"></div>{needle}</div>'


def coinop_note(meta):
    """Coin-Op's public components, listed once for the group and attached to no core."""
    g = meta.get("coinop_public_modules")
    if not g:
        return ""
    base = f"https://github.com/{g['repo']}/tree/{g['commit']}"
    mods = ", ".join(a(f"{base}/{quote(m['path'])}", m["module"]) for m in g["modules"])
    return ("<p class='muted small'>Coin-Op Collection also publishes open-source components (" + mods +
            ", each with datasheets and a test bench). Which of its closed cores use them is not published, so they "
            "are not attached to any core above.</p>")


def build():
    data = json.load(open(os.path.join(RESULTS, "results.json"), encoding="utf-8"))
    meta, res = data["meta"], data["cores"]
    mame_blob = f"https://github.com/mamedev/mame/blob/{meta['mame_commit']}/src/mame"

    def mame_link(rel, line=None):
        return a(f"{mame_blob}/{quote(rel)}" + (f"#L{line}" if line else ""), rel + (f":{line}" if line else ""))

    def permalink(r, at):
        path, _, line = at.partition(":")
        if r["db"] == "jt":
            base = f"https://github.com/jotego/jtcores/blob/{r['build_commit']}"
            full = path if path.startswith("cores/") else f"{r['subdir']}/{path}"
        else:
            base = f"https://github.com/{r['repo']}/blob/{r['build_commit']}"
            full = path
        plain = "?plain=1" if path.lower().endswith(".md") else ""   # line anchors need the source view
        return f"{base}/{quote(full)}{plain}" + (f"#L{line}" if line.isdigit() else "")

    def published(r):
        """Closed cores: what the team chose to publish. Facts and links only, neutral styling, and
        the one-sidedness stated beside it (see fva/indirect.py)."""
        ind = r.get("indirect")
        if not ind:
            return ""
        docs_base = f"https://github.com/{ind['docs_repo']}/blob/{ind['docs_commit']}"
        lis = []
        for d in ind["platform_docs"]:
            folder = a(docs_base.replace('/blob/', '/tree/') + '/' + quote(d['folder']), d['folder'])
            files = (f"{len(d['files'])} schematic/layout/manual file(s) in {folder}" if d["files"]
                     else "written overview; no schematic files of its own")
            lis.append(f"<li>Platform write-up {a(docs_base + '/' + quote(d['doc']), d['doc'])} (names "
                       f"“{html.escape(d['matched_title'])}”) — {files}</li>")
        return ('<details class="neutral"><summary>Published by the team — '
                f'{len(lis)} item(s), not evidence of how this core was verified</summary>'
                '<p class="muted small">Chosen and published by the developers. It shows what they decided to share, '
                'not how this core was built or checked. Anything pointing to MAME would not be visible here, so this '
                'list is one-sided by design; it places no needle and is not counted anywhere.</p>'
                f'<ul>{"".join(lis)}</ul></details>')

    rows = []
    for r in sorted(res, key=lambda r: ({"dist": 0, "jt": 1}.get(r["db"], 2), r["core"].lower())):
        titles = html.escape(", ".join(r.get("titles", [])[:3]) + (" …" if len(r.get("titles", [])) > 3 else ""))
        if r.get("status") != "analyzed":
            state = "Source not published" if r["db"] == "coinop" else r.get("status", "")
            pub = published(r)
            src = a("https://github.com/Coin-OpCollection/Distribution-MiSTerFPGA", "distribution (builds only)") \
                if r["db"] == "coinop" else ""
            rows.append(f'<tr><td><b>{html.escape(r["core"])}</b><br><span class="muted small">{titles}<br>{src}</span></td>'
                        f'<td>{DBNAME[r["db"]]}<br><span class="muted small">{html.escape(r.get("channel", ""))}</span></td>'
                        f'<td>{meter(None, closed=True)}</td><td>{state}</td><td></td><td></td></tr>'
                        + (f'<tr class="ev"><td colspan="6">{pub}</td></tr>' if pub else ""))
            continue
        sc = r["score"]
        pos = None if r["reading"] == "not enough evidence" else sc["score"]
        groups = []
        for rule in LABEL:
            its = [i for i in sc["items"] if i["rule"] == rule]
            if not its:
                continue
            side, title, _ = LABEL[rule]

            def mame_note(i):
                refs = i.get("mame_refs") or []
                if not refs:
                    return ""
                lead = "shares text with" if i["rule"] == "copied_text" else "also in MAME:"
                return f' <span class="muted">— {lead} ' + ", ".join(
                    (f"<b>{html.escape(t)}</b> " if i["rule"] != "copied_text" else "") + mame_link(rel, ln)
                    for t, rel, ln in refs) + "</span>"
            lis = "".join(f'<li>{a(permalink(r, i["at"]), i["at"])} '
                          f'{html.escape(i["text"] if i["text"] != i["at"] else "")}{mame_note(i)}</li>' for i in its[:300])
            more = f'<li class="muted">… {len(its) - 300} more</li>' if len(its) > 300 else ""
            groups.append(f'<details class="{side}"><summary>{title} — {len(its)}</summary><ul>{lis}{more}</ul></details>')
        if r["db"] == "jt":
            src = a("https://github.com/jotego/jtcores", "jotego/jtcores") + " @ " + a(
                f"https://github.com/jotego/jtcores/tree/{r['build_commit']}/{r['subdir']}", r["build_commit"][:8] + " (approx.)")
        else:
            tree = f"https://github.com/{r['repo']}/tree/{r['build_commit']}" + (f"/{r['subdir']}" if r.get("subdir") else "")
            src = a(f"https://github.com/{r['repo']}", r["repo"]) + " @ " + a(tree, r["build_commit"][:8])
            if r.get("match", "exact file") != "exact file":
                src += f' <span title="{html.escape(r["match"])}">(matched by date)</span>'
        drv = r.get("mame_drivers") or []
        extra = len(r.get("mame_files") or []) - len(drv)
        mame = ("MAME compared: " + ", ".join(mame_link(d) for d in drv) +
                (f" + {extra} related file(s)" if extra > 0 else "")) if drv else "MAME driver: not found"
        rows.append(f'<tr><td><b>{html.escape(r["core"])}</b><br><span class="muted small">{titles}<br>{src}<br>{mame}</span></td>'
                    f'<td>{DBNAME[r["db"]]}</td><td>{meter(pos)}</td><td>{READING[r["reading"]]}</td>'
                    f'<td class="num">{sc["confidence"]}</td><td class="num">{sc["coverage"]}%</td></tr>'
                    f'<tr class="ev"><td colspan="6">{"".join(groups) or "<span class=muted>no statements</span>"}</td></tr>')

    legend = "".join(f'<tr><td>{t}</td><td class="num">{POINTS[k]}</td>'
                     f'<td>{ {"hardware": "hardware", "mame": "MAME"}.get(s, "neither") }</td><td class="muted">{n}</td></tr>'
                     for k, (s, t, n) in LABEL.items())
    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>FPGA Verified Against</title><style>{CSS}</style></head><body>
<h1>FPGA cores: verified against hardware or MAME?</h1>
<p>Every arcade core in update_all's three default databases, analyzed at the commit its distributed build came from.
Each meter summarizes the core's <b>own</b> code comments, readme and shipped documentation files: statements
pointing to MAME on the left, to the original hardware on the right. Expand a row to see every statement, linked
to its line at that commit; items that point at MAME link to the matching line in MAME
(commit {a("https://github.com/mamedev/mame/tree/" + meta["mame_commit"], meta["mame_commit"][:10])}).</p>
<p class="note"><b>Taken at face value.</b> These are the developers' own statements, not independently checked.
A core may be verified more, or less, than its comments say. Open source makes a false claim easy to expose, which is
why developers' own words are a reasonable starting point. This method reads source code, so closed-source cores
cannot be assessed <i>this way</i> and are shown separately; black-box testing against the original hardware or MAME
would still be possible, but is far more work and is not done here.</p>
<p class="muted small">Rules {meta["rules_version"]} · tool {meta["tool_version"]} · generated {meta["generated"]} ·
shared CPU/sound libraries and the MiSTer framework are excluded · below "low" confidence the bar is an outline with
no needle · readings: under 40 mostly MAME, over 60 mostly hardware, otherwise both.</p>
<table><tr><td><b>Core</b></td><td><b>Database</b></td><td><div class="axis"><span>MAME</span><span>Hardware</span></div></td>
<td><b>Reading</b></td><td class="num"><b>Confidence</b></td><td class="num"><b>Coverage</b></td></tr>{"".join(rows)}</table>
{coinop_note(meta)}
<h2>How the needle is placed</h2>
<p>Each comment (or readme sentence) is classified by the rules below. Within a module a rule adds its points ×
log2(1 + times it fired), so repetition counts for less than variety. A module's position is (hardware points + 1) /
(all points + 2), from MAME at 0 to hardware at 100. A core's needle is the size-weighted average over modules that
contain statements; the readme and the shipped documentation files each count like a quarter of the code. Modules
with no statements are left out and reported as coverage. See RULES.md for the reasoning behind each rule.</p>
<table><tr><td><b>Statement</b></td><td class="num"><b>Points</b></td><td><b>Side</b></td><td><b>Includes</b></td></tr>{legend}</table>
<p class="muted">Not counted: ROM file names (MiSTer uses MAME's ROM sets by design) and memory addresses (a correct
core must share them with any correct emulator). Quoted comments remain under their authors' licenses; this analysis
is published under CC BY 4.0.</p>
</body></html>"""
    out = os.path.join(RESULTS, "index.html")
    open(out, "w", encoding="utf-8").write(page)
    print(out, os.path.getsize(out) // 1024, "KB")
