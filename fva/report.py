"""results/results.json -> results/index.html: one row per core, a meter from MAME (left) to hardware
(right), and every statement behind it linked to its line at the analyzed commit.

Wording is descriptive only: the page reports what each core's own code states, never a judgment.
Below LOW confidence the bar is a colorless outline with no needle ("not enough evidence"); a
closed-source build gets a dashed outline ("source not published") — different states, labelled so.
"""
import html
import json
import os
import re
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
DEFAULT_DBS = {"dist": "MiSTer official", "jt": "JTCORES", "coinop": "Coin-Op Collection"}
DEV_DBS = {"meat": "MeatCores", "slop": "Slop Cores", "kuze": "kuzecores", "jlrh": "jlrh", "arcfpga": "arcfpga",
           "blahm1d": "blahm1d"}   # added to update_all by hand; see fva/sources.py DEV_DATABASES
DBNAME = {**DEFAULT_DBS, **DEV_DBS}
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
tr.main td{border-bottom:0} tr.ev td{padding:0 8px 8px 24px} .num{text-align:right}
thead td{font-weight:600;border-bottom:1px solid var(--muted)}
details.evidence{border:0;padding:0;margin:0} details.evidence>summary{color:var(--muted);font-size:13px;cursor:pointer}
details.evidence>summary .hw{color:var(--hw)} details.evidence>summary .mm{color:var(--mame)}
tbody.core{scroll-margin-top:130px} tbody.core:target td{background:#161a22}
a.anchor{color:var(--muted);text-decoration:none;margin-left:4px;opacity:.6} a.anchor:hover{opacity:1}
.tools{position:sticky;top:0;z-index:2;background:var(--bg);padding:10px 0;border-bottom:1px solid var(--line);display:grid;gap:8px}
.tools .row{display:flex;flex-wrap:wrap;gap:8px 12px;align-items:center}
.tools input,.tools select,.tools button.plain{background:#171a21;border:1px solid var(--line);color:var(--fg);border-radius:6px;padding:6px 10px;font:inherit;font-size:14px}
.tools input{flex:1;min-width:200px}
.chip{background:transparent;border:1px solid var(--line);color:var(--fg);border-radius:999px;padding:3px 10px;font:13px system-ui,sans-serif;cursor:pointer;display:inline-flex;align-items:center;gap:6px}
.chip[aria-pressed=true]{border-color:var(--fg);background:#232833} .chip .n{color:var(--muted)}
.sw{width:16px;height:8px;border-radius:2px;display:inline-block;box-sizing:border-box}
.sw.empty{border:1.5px solid var(--fg)} .sw.closed{border:1.5px dashed var(--fg)}
.lbl{color:var(--muted);font-size:13px;min-width:96px}
@media(max-width:720px){.c5,.c6{display:none} .meter,.axis{width:100px} .tools{position:static} tbody.core{scroll-margin-top:0}}"""

READ_KEY = {"mostly MAME": "mame", "both": "both", "mostly hardware": "hw", "not enough evidence": "none"}
CHIPS_RD = [("mame", "Mostly MAME", "background:var(--mame)"), ("both", "Both", "background:#777"),
            ("hw", "Mostly hardware", "background:var(--hw)"), ("none", "Not enough evidence", ""),
            ("closed", "Source not published", "")]
CONF = {"insufficient": 0, "low": 1, "medium": 2, "high": 3}

# Filtering, sorting and search run in the browser on the rows already in the page: the page stays one
# static file (GitHub Pages, no build step) and still reads in full with scripts off. Each core is one
# <tbody> so its evidence row moves with it; the state lives in the query string so a filtered view
# can be shared, and each core has an id so other sites (kiban's game pages) can link to it directly.
JS = """(()=>{
const T=document.getElementById('cores'),C=[...T.tBodies].filter(b=>b.classList.contains('core'));
const q=document.getElementById('q'),S=document.getElementById('sort'),N=document.getElementById('count'),
  E=document.getElementById('none'),X=document.getElementById('expand'),chips=[...document.querySelectorAll('.chip')];
const sel={db:new Set(),rd:new Set()},P=new URLSearchParams(location.search);
q.value=P.get('q')||'';if(P.get('sort'))S.value=P.get('sort');
for(const k in sel)(P.get(k)||'').split(',').filter(Boolean).forEach(v=>sel[k].add(v));
const num=(b,k)=>b.dataset[k]===''?null:+b.dataset[k],nm=(a,b)=>a.dataset.name.localeCompare(b.dataset.name);
const by=(k,d)=>(a,b)=>{const x=num(a,k),y=num(b,k);return(x==null)-(y==null)||(x==null?0:(x-y)*d)||nm(a,b)};
const SORT={db:(a,b)=>num(a,'dbo')-num(b,'dbo')||nm(a,b),name:nm,hw:by('score',-1),mame:by('score',1),
  conf:by('conf',-1),cov:by('cov',-1)};
const tok=()=>q.value.toLowerCase().split(/\\s+/).filter(Boolean);
const okq=(b,t)=>t.every(w=>b.dataset.s.includes(w)),ok=(b,k)=>!sel[k].size||sel[k].has(b.dataset[k]);
function apply(){
  const t=tok();let n=0;
  for(const b of C){const v=okq(b,t)&&ok(b,'db')&&ok(b,'rd');b.hidden=!v;n+=v}
  C.sort(SORT[S.value]).forEach(b=>T.appendChild(b));
  N.textContent=n===C.length?`${n} cores`:`${n} of ${C.length} cores`;E.hidden=n>0;
  for(const c of chips){const k=c.dataset.k,o=k==='db'?'rd':'db';c.setAttribute('aria-pressed',sel[k].has(c.dataset.v));
    c.querySelector('.n').textContent=C.filter(b=>b.dataset[k]===c.dataset.v&&okq(b,t)&&ok(b,o)).length}
  const u=new URLSearchParams();if(q.value)u.set('q',q.value);for(const k in sel)if(sel[k].size)u.set(k,[...sel[k]]);
  if(S.value!=='db')u.set('sort',S.value);const s=u.toString().replace(/%2C/g,',');
  history.replaceState(null,'',(s?'?'+s:location.pathname)+location.hash)}
q.addEventListener('input',apply);S.addEventListener('change',apply);
chips.forEach(c=>c.addEventListener('click',()=>{const s=sel[c.dataset.k];s.has(c.dataset.v)?s.delete(c.dataset.v):s.add(c.dataset.v);apply()}));
document.getElementById('reset').addEventListener('click',()=>{q.value='';sel.db.clear();sel.rd.clear();S.value='db';apply()});
X.addEventListener('click',()=>{const o=X.dataset.open!=='1';X.dataset.open=o?'1':'0';
  X.textContent=o?'Collapse all':'Expand all';C.forEach(b=>{if(!b.hidden)b.querySelectorAll('details.evidence').forEach(d=>d.open=o)})});
document.addEventListener('keydown',e=>{if(e.key==='/'&&document.activeElement!==q){e.preventDefault();q.focus()}});
function jump(){const b=location.hash&&document.getElementById(decodeURIComponent(location.hash.slice(1)));
  if(!b||!b.classList.contains('core'))return;if(b.hidden){q.value='';sel.db.clear();sel.rd.clear();apply()}
  b.querySelectorAll('details.evidence').forEach(d=>d.open=true);b.scrollIntoView()}
window.addEventListener('hashchange',jump);
document.querySelector('.tools').hidden=false;apply();jump()})();"""


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

    DBORDER = {k: i for i, k in enumerate(DBNAME)}

    def db_home(k):
        """Where a database's builds come from, for cores whose source is not published."""
        if k == "coinop":
            return "https://github.com/Coin-OpCollection/Distribution-MiSTerFPGA"
        url = meta.get("developer_databases", {}).get(k, {}).get("url", "")
        m = re.match(r"https://raw\.githubusercontent\.com/([^/]+/[^/]+)/", url)
        return f"https://github.com/{m.group(1)}" if m else re.sub(r"^(https://[^/]+).*$", r"\1/", url)

    def db_cell(r):
        extra = "developer database" if r["db"] in DEV_DBS else r.get("channel", "") if r["db"] == "coinop" else ""
        return DBNAME[r["db"]] + (f'<br><span class="muted small">{html.escape(extra)}</span>' if extra else "")

    def core_open(r, rd, score=None, conf=None, cov=None):
        """<tbody> for one core; the data-* attributes are what the page script filters and sorts on."""
        cid = f'{r["db"]}-{r["core"]}'
        s = " ".join([r["core"], *r.get("titles", []), *r.get("setnames", []), r.get("repo") or "",
                      r.get("subdir") or "", DBNAME[r["db"]]]).lower()
        v = lambda x: "" if x is None else x
        name = (f'<b>{html.escape(r["core"])}</b><a class="anchor" href="#{quote(cid)}" '
                f'title="Link to this core">#</a>')
        return (f'<tbody class="core" id="{html.escape(cid)}" data-name="{html.escape(r["core"].lower())}" '
                f'data-db="{r["db"]}" data-dbo="{DBORDER[r["db"]]}" data-rd="{rd}" data-score="{v(score)}" '
                f'data-conf="{v(conf)}" data-cov="{v(cov)}" data-s="{html.escape(s)}">'), name

    rows = []
    for r in sorted(res, key=lambda r: (DBORDER[r["db"]], r["core"].lower())):
        titles = html.escape(", ".join(r.get("titles", [])[:3]) + (" …" if len(r.get("titles", [])) > 3 else ""))
        if r.get("status") != "analyzed":
            closed = r.get("status") == "source not published"
            state = "Source not published" if closed else r.get("status", "")
            pub = published(r)
            src = ""
            if closed:   # a repo that was checked and holds no HDL is linked itself, so the reader can look
                src = (a(f"https://github.com/{r['repo']}/tree/{r['build_commit']}" + (f"/{r['subdir']}" if r.get("subdir") else ""),
                         r["repo"] + " @ " + r["build_commit"][:8]) if r.get("repo") and r.get("build_commit")
                       else a(db_home(r["db"]), "database (builds only)"))
            if r.get("note"):
                src += "<br>" + html.escape(r["note"])
            head, name = core_open(r, "closed")
            rows.append(f'{head}<tr class="main"><td>{name}<br><span class="muted small">{titles}<br>{src}</span></td>'
                        f'<td>{db_cell(r)}</td>'
                        f'<td>{meter(None, closed=True)}</td><td>{state}</td><td class="c5"></td><td class="c6"></td></tr>'
                        f'<tr class="ev"><td colspan="6">{pub}</td></tr></tbody>')
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
            how = r.get("match", "exact file")
            if not how.startswith("exact"):
                label = "approx." if how.startswith("approximate") else "matched by date"
                src += f' <span title="{html.escape(how)}">({label})</span>'
        drv = r.get("mame_drivers") or []
        extra = len(r.get("mame_files") or []) - len(drv)
        mame = ("MAME compared: " + ", ".join(mame_link(d) for d in drv) +
                (f" + {extra} related file(s)" if extra > 0 else "")) if drv else "MAME driver: not found"
        side = {"hardware": 0, "mame": 0, "neutral": 0}
        for i in sc["items"]:
            side[LABEL[i["rule"]][0]] += 1
        tally = ", ".join(t for t in (
            f'<span class="hw">{side["hardware"]} toward hardware</span>' if side["hardware"] else "",
            f'<span class="mm">{side["mame"]} toward MAME</span>' if side["mame"] else "",
            f'{side["neutral"]} not counted' if side["neutral"] else "") if t)
        ev = (f'<details class="evidence"><summary>Statements: {tally}</summary>{"".join(groups)}</details>'
              if groups else '<span class="muted small">No statements found</span>')
        head, name = core_open(r, READ_KEY[r["reading"]], score=None if pos is None else round(pos, 1),
                               conf=CONF.get(sc["confidence"]), cov=sc["coverage"])
        rows.append(f'{head}<tr class="main"><td>{name}<br><span class="muted small">{titles}<br>{src}<br>{mame}</span></td>'
                    f'<td>{db_cell(r)}</td><td>{meter(pos)}</td><td>{READING[r["reading"]]}</td>'
                    f'<td class="num c5">{sc["confidence"]}</td><td class="num c6">{sc["coverage"]}%</td></tr>'
                    f'<tr class="ev"><td colspan="6">{ev}</td></tr></tbody>')

    def chip(k, v, text, sw=None):
        swatch = "" if sw is None else f'<span class="sw {sw[0]}" style="{sw[1]}"></span>'
        return f'<button type="button" class="chip" data-k="{k}" data-v="{v}" aria-pressed="false">{swatch}{text} <span class="n"></span></button>'
    chips_db = "".join(chip("db", k, n) for k, n in DEFAULT_DBS.items())
    chips_dev = "".join(chip("db", k, n) for k, n in DEV_DBS.items())
    chips_rd = "".join(chip("rd", k, t, ("empty" if k == "none" else "closed" if k == "closed" else "", st))
                       for k, t, st in CHIPS_RD)
    tools = f"""<div class="tools" hidden>
<div class="row"><input id="q" type="search" placeholder="Search core, game title, ROM set or repository  ( / )" aria-label="Search">
<select id="sort" aria-label="Sort"><option value="db">Sort: database, then name</option><option value="name">Sort: name</option>
<option value="hw">Sort: toward hardware first</option><option value="mame">Sort: toward MAME first</option>
<option value="conf">Sort: confidence</option><option value="cov">Sort: coverage</option></select></div>
<div class="row"><span class="lbl">Reading</span><div class="chips">{chips_rd}</div></div>
<div class="row"><span class="lbl">update_all</span><div class="chips">{chips_db}</div></div>
<div class="row"><span class="lbl" title="Databases their developers publish; users add them to update_all by hand">Added by hand</span><div class="chips">{chips_dev}</div>
<span style="flex:1"></span><span id="count" class="muted small"></span>
<button type="button" id="expand" class="plain">Expand all</button><button type="button" id="reset" class="plain">Reset</button></div>
</div>"""

    legend = "".join(f'<tr><td>{t}</td><td class="num">{POINTS[k]}</td>'
                     f'<td>{ {"hardware": "hardware", "mame": "MAME"}.get(s, "neither") }</td><td class="muted">{n}</td></tr>'
                     for k, (s, t, n) in LABEL.items())
    page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>FPGA Verified Against</title><style>{CSS}</style></head><body>
<h1>FPGA cores: verified against hardware or MAME?</h1>
<p>Every arcade core in update_all's three default databases, and in six databases individual developers publish
for users to add by hand, analyzed at the commit its distributed build came from.
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
{tools}
<table id="cores"><thead><tr><td>Core</td><td>Database</td><td><div class="axis"><span>MAME</span><span>Hardware</span></div></td>
<td>Reading</td><td class="num c5">Confidence</td><td class="num c6">Coverage</td></tr></thead>{"".join(rows)}</table>
<p id="none" class="muted" hidden>No cores match. <a href="?">Show all</a></p>
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
<script>{JS}</script>
</body></html>"""
    out = os.path.join(RESULTS, "index.html")
    open(out, "w", encoding="utf-8").write(page)
    print(out, os.path.getsize(out) // 1024, "KB")
