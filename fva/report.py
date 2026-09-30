"""results/results.json -> results/index.html (and results/ja/index.html, fva/i18n.py): one row per core, a meter from MAME (left) to hardware
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

from .i18n import DETAIL_JA, LABEL_JA, LANGS, MSG, REASON_JA
from .paths import RESULTS

LABEL = {  # rule -> (side, title, what it includes)
    "hw_specific": ("hardware", "Cites hardware documentation that MAME's driver does not",
                    "schematic sheet, part number, chip location, dumped PAL, decap — only when MAME's driver for the game does not already give it"),
    "hw_ref_in_mame": ("neutral", "Cites hardware references or measurements that MAME's driver also gives",
                       "not counted: copying them from MAME would look the same"),
    "hw_verified": ("hardware", "Says it was checked against the original PCB", "explicitly the original board, PCB or arcade hardware"),
    "hw_measured": ("hardware", "Reports a measurement taken on the original PCB",
                    "states a value; measurements of the MiSTer itself (e.g. SignalTap) do not count"),
    "hw_verified_unclear": ("hardware", "Says it was checked on “real hardware”",
                            "may mean the MiSTer board itself rather than the original PCB, so it counts less"),
    "hw_files": ("hardware", "Ships hardware documentation files", "schematic sheets, schematic PDFs, PAL equations in the core's own folder"),
    "mame_diverge": ("hardware", "Notes where it differs from MAME", "a stated difference implies another reference"),
    "mame_cited": ("mame", "Cites MAME source", "a MAME file, function or line"),
    "mame_verified": ("mame", "Says it matches, follows or was checked against MAME", "includes “ground truth: MAME”"),
    "mame_transcribed": ("mame", "Says it was translated, ported or taken from MAME", ""),
    "mame_surrogate": ("mame", "Keeps a MAME approximation", "where MAME itself notes a guess or stand-in"),
    "copied_text": ("mame", "Shares text with the MAME driver without saying so", "a 6-word run in a comment"),
}
POINTS = {"hw_specific": "+0.5", "hw_ref_in_mame": "0", "hw_verified": "+2", "hw_verified_unclear": "+1",
          "hw_files": "+2", "hw_measured": "+3", "mame_diverge": "+3", "mame_cited": "−0.5",
          "mame_verified": "−2", "mame_transcribed": "−3", "mame_surrogate": "−1", "copied_text": "−1"}
DEFAULT_DBS = {"dist": "MiSTer official", "jt": "JTCORES", "coinop": "Coin-Op Collection"}
DEV_DBS = {"meat": "MeatCores", "slop": "Slop Cores", "kuze": "kuzecores", "jlrh": "jlrh", "arcfpga": "arcfpga",
           "blahm1d": "blahm1d",   # independent databases outside update_all's list; see fva/sources.py DEV_DATABASES
           "repo": "Repository only"}   # no database at all; found by fva/discover.py
DBNAME = {**DEFAULT_DBS, **DEV_DBS}
READING = {"mostly hardware": "Mostly hardware", "both": "Both", "mostly MAME": "Mostly MAME",
           "not enough evidence": "Not enough evidence in the code"}

# Palette and table conventions follow kiban.alamone.net (frontend/app/globals.css), where these
# readings will also appear: same background, panel, border, text, muted and accent values, links in
# the accent, sortable headers that sort on click and flip on a second click with the active column
# in the accent. MAME end blue (its logo), hardware end amber, not MiSTer's white: every core here is
# a MiSTer core, the right end means the original board, and white would blur into the outlined
# no-score bars and the white needle. Blue/amber stays distinct under red-green color blindness.
# Because links are blue too, MAME-side counts are marked with a colored dot, never colored text.
CSS = """:root{--bg:#0f1115;--panel:#171a21;--border:#272b35;--text:#e6e8ee;--muted:#9aa0ad;--accent:#4c9aff;
--hw:#e8a33d;--mame:#2f6fd6}
body{background:var(--bg);color:var(--text);font:15px/1.5 system-ui,sans-serif;margin:0 auto;padding:24px 16px;max-width:1100px}
a{color:var(--accent);text-decoration:none} a:hover{text-decoration:underline}
code{font-size:12.5px} .muted{color:var(--muted)} .small{font-size:13px}
.note{border-left:3px solid var(--muted);padding:4px 12px;margin:12px 0}
.meter{position:relative;height:16px;width:150px}
.meter .bar{position:absolute;top:5px;left:0;right:0;height:6px;border-radius:3px;background:linear-gradient(90deg,var(--mame),#777 50%,var(--hw))}
.meter.empty .bar{background:transparent;border:1.5px solid var(--text);height:10px;top:2px}
.meter.closed .bar{border-style:dashed}
.meter .needle{position:absolute;top:1px;width:3px;height:14px;margin-left:-1.5px;background:#fff;border-radius:2px;box-shadow:0 0 0 2px #0008}
.axis{display:flex;justify-content:space-between;width:150px;font-size:11px;color:var(--muted);font-weight:400}
details{border-left:3px solid var(--border);padding:2px 10px;margin:4px 0} details.hardware{border-color:var(--hw)}
details.mame{border-color:var(--mame)} details.neutral{border-color:#777}
details ul{margin:6px 0;padding-left:18px;max-height:320px;overflow:auto} li{margin:3px 0;overflow-wrap:anywhere}
table{border-collapse:collapse;width:100%;font-size:14px} th,td{text-align:left;padding:6px 8px;vertical-align:top}
td{border-bottom:1px solid var(--border)} th{color:var(--muted);font-weight:600;border-bottom:1px solid var(--border)}
th.sortable{cursor:pointer;user-select:none;white-space:nowrap} th.sortable:hover{color:var(--text)}
th.sortable.sorted{color:var(--accent)} th.sortable:focus-visible{outline:1px solid var(--accent)}
th.sortable .axis{display:inline-flex;vertical-align:middle}
tr.main td{border-bottom:0} tr.ev td{padding:0 8px 8px 24px} .num,th.num{text-align:right}
details.evidence{border:0;padding:0;margin:0} details.evidence>summary{color:var(--muted);font-size:13px;cursor:pointer}
.dot{display:inline-block;width:8px;height:8px;border-radius:50%;margin:0 4px 1px 0;vertical-align:middle}
.dot.hw{background:var(--hw)} .dot.mm{background:var(--mame)}
tbody.core{scroll-margin-top:110px} tbody.core:target td{background:var(--panel)}
a.anchor{color:var(--muted);text-decoration:none;margin-left:4px;opacity:.6} a.anchor:hover{opacity:1}
.tools{position:sticky;top:0;z-index:2;background:var(--bg);padding:10px 0;border-bottom:1px solid var(--border);display:grid;gap:8px}
.tools .row{display:flex;flex-wrap:wrap;gap:8px 12px;align-items:center}
.tools input,.tools button.plain{background:var(--panel);border:1px solid var(--border);color:var(--text);border-radius:8px;padding:6px 10px;font:inherit;font-size:14px}
.tools button.plain{cursor:pointer} .tools input{flex:1;min-width:200px}
.chip{background:transparent;border:1px solid var(--border);color:var(--text);border-radius:999px;padding:3px 10px;font:13px system-ui,sans-serif;cursor:pointer;display:inline-flex;align-items:center;gap:6px}
.chip[aria-pressed=true]{border-color:var(--accent);background:var(--panel)} .chip .n{color:var(--muted)}
.sw{width:16px;height:8px;border-radius:2px;display:inline-block;box-sizing:border-box}
.sw.empty{border:1.5px solid var(--text)} .sw.closed{border:1.5px dashed var(--text)}
.lbl{color:var(--muted);font-size:13px;min-width:96px}
.lang{float:right;font-size:13px;margin-top:6px}
@media(max-width:720px){.c5,.c6{display:none} .meter,.axis{width:100px} .tools{position:static} tbody.core{scroll-margin-top:0}}"""

READ_KEY = {"mostly MAME": "mame", "both": "both", "mostly hardware": "hw", "not enough evidence": "none"}
CHIPS_RD = [("mame", "Mostly MAME", "background:var(--mame)"), ("both", "Both", "background:#777"),
            ("hw", "Mostly hardware", "background:var(--hw)"), ("none", "Not enough evidence", ""),
            ("closed", "Source not published", "")]
CONF = {"insufficient": 0, "low": 1, "medium": 2, "high": 3}
RD_ORDER = {k: i for i, (k, _, _) in enumerate(CHIPS_RD)}   # Reading column sorts left to right along the meter

# Filtering, sorting and search run in the browser on the rows already in the page: the page stays one
# static file (GitHub Pages, no build step) and still reads in full with scripts off. Each core is one
# <tbody> so its evidence row moves with it; the state lives in the query string so a filtered view
# can be shared, and each core has an id so other sites (kiban's game pages) can link to it directly.
JS = """(()=>{
const L=window.FVA_L,LL=document.getElementById('langlink');
const T=document.getElementById('cores'),C=[...T.tBodies].filter(b=>b.classList.contains('core'));
const q=document.getElementById('q'),N=document.getElementById('count'),E=document.getElementById('none'),
  X=document.getElementById('expand'),chips=[...document.querySelectorAll('.chip')],H=[...T.tHead.querySelectorAll('th.sortable')];
const sel={db:new Set(),rd:new Set()},P=new URLSearchParams(location.search);
// First click on a column: names and databases A-Z, numbers highest first (the needle column starts
// at the hardware end). A second click on the same column reverses it, as in kiban's tables.
const FIRST={name:1,db:1,pos:-1,rd:1,conf:-1,cov:-1},st={key:'db',dir:1};
q.value=P.get('q')||'';
{const m=(P.get('sort')||'').match(/^(\\w+)-(asc|desc)$/);if(m&&m[1] in FIRST){st.key=m[1];st.dir=m[2]==='asc'?1:-1}}
for(const k in sel)(P.get(k)||'').split(',').filter(Boolean).forEach(v=>sel[k].add(v));
const num=(b,k)=>b.dataset[k]===''?null:+b.dataset[k],nm=(a,b)=>a.dataset.name.localeCompare(b.dataset.name);
// cores with no value (no needle, source not published) stay last in either direction
const by=k=>(a,b,d)=>{const x=num(a,k),y=num(b,k);return(x==null)-(y==null)||(x==null?0:(x-y)*d)||nm(a,b)};
const SORT={name:(a,b,d)=>nm(a,b)*d,db:(a,b,d)=>(num(a,'dbo')-num(b,'dbo'))*d||nm(a,b),pos:by('score'),
  rd:(a,b,d)=>(num(a,'rdo')-num(b,'rdo'))*d||nm(a,b),conf:by('conf'),cov:by('cov')};
const tok=()=>q.value.toLowerCase().split(/\\s+/).filter(Boolean);
const okq=(b,t)=>t.every(w=>b.dataset.s.includes(w)),ok=(b,k)=>!sel[k].size||sel[k].has(b.dataset[k]);
function apply(){
  const t=tok();let n=0;
  for(const b of C){const v=okq(b,t)&&ok(b,'db')&&ok(b,'rd');b.hidden=!v;n+=v}
  C.sort((a,b)=>SORT[st.key](a,b,st.dir)).forEach(b=>T.appendChild(b));
  for(const h of H){const on=h.dataset.sort===st.key;h.classList.toggle('sorted',on);
    h.setAttribute('aria-sort',on?(st.dir>0?'ascending':'descending'):'none');
    h.querySelector('.arr').textContent=on?(st.dir>0?' \u25B2':' \u25BC'):''}
  N.textContent=(n===C.length?L['count.all']:L['count.some']).replace('{n}',n).replace('{t}',C.length);E.hidden=n>0;
  for(const c of chips){const k=c.dataset.k,o=k==='db'?'rd':'db';c.setAttribute('aria-pressed',sel[k].has(c.dataset.v));
    c.querySelector('.n').textContent=C.filter(b=>b.dataset[k]===c.dataset.v&&okq(b,t)&&ok(b,o)).length}
  const u=new URLSearchParams();if(q.value)u.set('q',q.value);for(const k in sel)if(sel[k].size)u.set(k,[...sel[k]]);
  if(st.key!=='db'||st.dir!==1)u.set('sort',st.key+'-'+(st.dir>0?'asc':'desc'));
  const s=u.toString().replace(/%2C/g,',');
  history.replaceState(null,'',(s?'?'+s:location.pathname)+location.hash);
  if(LL)LL.href=LL.dataset.base+location.search+location.hash}   // the other language keeps the view
for(const h of H){const go=()=>{const k=h.dataset.sort;st.dir=st.key===k?-st.dir:FIRST[k];st.key=k;apply()};
  h.addEventListener('click',go);h.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();go()}})}
q.addEventListener('input',apply);
chips.forEach(c=>c.addEventListener('click',()=>{const s=sel[c.dataset.k];s.has(c.dataset.v)?s.delete(c.dataset.v):s.add(c.dataset.v);apply()}));
document.getElementById('reset').addEventListener('click',()=>{q.value='';sel.db.clear();sel.rd.clear();st.key='db';st.dir=1;apply()});
X.addEventListener('click',()=>{const o=X.dataset.open!=='1';X.dataset.open=o?'1':'0';
  X.textContent=o?L.collapse:L.expand;C.forEach(b=>{if(!b.hidden)b.querySelectorAll('details.evidence').forEach(d=>d.open=o)})});
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


def build(lang="en"):
    """One page per language: results/index.html (English) and results/ja/index.html. The rows,
    links and evidence are identical; only the page's own words change (fva/i18n.py)."""
    data = json.load(open(os.path.join(RESULTS, "results.json"), encoding="utf-8"))
    meta, res = data["meta"], data["cores"]
    M = MSG[lang]
    t = lambda k, **kw: M[k].format(**kw) if kw else M[k]
    label = (lambda rule: LABEL_JA[rule]) if lang == "ja" else (lambda rule: LABEL[rule][1:])
    mame_blob = f"https://github.com/mamedev/mame/blob/{meta['mame_commit']}/src/mame"

    def dbname(k):
        return t("db.dist") if k == "dist" else t("db.repo") if k == "repo" else DBNAME[k]

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
            files = t("pub.files", n=len(d["files"]), folder=folder) if d["files"] else t("pub.nofiles")
            lis.append("<li>" + t("pub.item", doc=a(docs_base + '/' + quote(d['doc']), d['doc']),
                                  title=html.escape(d['matched_title']), files=files) + "</li>")
        return (f'<details class="neutral"><summary>{t("pub.summary", n=len(lis))}</summary>'
                f'<p class="muted small">{t("pub.caveat")}</p><ul>{"".join(lis)}</ul></details>')

    def coinop_note():
        """Coin-Op's public components, listed once for the group and attached to no core."""
        g = meta.get("coinop_public_modules")
        if not g:
            return ""
        base = f"https://github.com/{g['repo']}/tree/{g['commit']}"
        mods = ", ".join(a(f"{base}/{quote(m['path'])}", m["module"]) for m in g["modules"])
        return f"<p class='muted small'>{t('coinop', mods=mods)}</p>"

    DBORDER = {k: i for i, k in enumerate(DBNAME)}

    def db_home(k):
        """Where a database's builds come from, for cores whose source is not published."""
        if k == "coinop":
            return "https://github.com/Coin-OpCollection/Distribution-MiSTerFPGA"
        url = meta.get("developer_databases", {}).get(k, {}).get("url", "")
        m = re.match(r"https://raw\.githubusercontent\.com/([^/]+/[^/]+)/", url)
        return f"https://github.com/{m.group(1)}" if m else re.sub(r"^(https://[^/]+).*$", r"\1/", url)

    def channel(r):
        ch = r.get("channel", "")
        m = re.match(r"opt-in \((.*)\)$", ch)
        if m:
            key = f"channel.optin.{m.group(1)}"
            return t(key) if key in M else t("channel.optin", x=m.group(1))
        return t("channel.default") if ch == "default" else ch

    def db_cell(r):
        if r["db"] == "repo":
            return (f'{html.escape(r["repo"].split("/")[0])}<br><span class="muted small">{t("db.repoonly")}'
                    + (f' · {t("db.byrequest")}' if r.get("found_via") == "extra_repos.tsv" else "") + "</span>")
        extra = t("db.independent") if r["db"] in DEV_DBS else channel(r) if r["db"] == "coinop" else ""
        return dbname(r["db"]) + (f'<br><span class="muted small">{html.escape(extra)}</span>' if extra else "")

    def reason(why, detail):
        if lang != "ja":
            return why[:1].upper() + why[1:], detail
        for pat, rep in DETAIL_JA:
            if re.match(pat, detail):
                detail = re.sub(pat, rep, detail)
                break
        return REASON_JA.get(why, why), detail

    def not_analyzed():
        """Repositories the discovery found but did not analyze, with the reason, so a developer can
        see why their core is missing and what would change it."""
        sk = (meta.get("discovery") or {}).get("skipped") or []
        if not sk:
            return ""
        noise = [s for s in sk if s["reason"].startswith("not an arcade core")]
        shown = [s for s in sk if s not in noise]
        by, seen = {}, set()
        for s in shown:   # "copy of a covered repository (X)" -> group "copy of a covered repository", detail X
            head, _, detail = s["reason"].partition(": ") if ": " in s["reason"] else s["reason"].partition(" (")
            if (s["repo"], head) not in seen:
                seen.add((s["repo"], head))
                by.setdefault(head, []).append((s, detail.rstrip(")")))
        parts = ""
        for why, ss in sorted(by.items(), key=lambda kv: -len(kv[1])):
            items = []
            for s, d in sorted(ss, key=lambda x: x[0]["repo"].lower()):
                _, d = reason(why, d)
                items.append(f'<li>{a("https://github.com/" + s["repo"], s["repo"])}'
                             + (f' <span class="muted">— {html.escape(d)}</span>' if d else "")
                             + (f' <span class="muted">{t("na.byrequest")}</span>' if s["via"] == "extra_repos.tsv" else "")
                             + "</li>")
            parts += f'<p class="small"><b>{html.escape(reason(why, "")[0])}</b> — {len(ss)}</p><ul class="small">{"".join(items)}</ul>'
        return (f'<details class="neutral"><summary>{t("na.summary", n=len(shown))}</summary>'
                f'<p class="muted small">{t("na.intro", n=len(noise))}</p>{parts}</details>')

    def core_open(r, rd, score=None, conf=None, cov=None):
        """<tbody> for one core; the data-* attributes are what the page script filters and sorts on."""
        cid = f'{r["db"]}-{r["core"]}'
        s = " ".join([r["core"], *r.get("titles", []), *r.get("setnames", []), r.get("repo") or "",
                      r.get("subdir") or "", *dict.fromkeys([DBNAME[r["db"]], dbname(r["db"])])]).lower()
        v = lambda x: "" if x is None else x
        name = (f'<b>{html.escape(r["core"])}</b><a class="anchor" href="#{quote(cid)}" '
                f'title="{html.escape(t("anchor"))}">#</a>')
        return (f'<tbody class="core" id="{html.escape(cid)}" data-name="{html.escape(r["core"].lower())}" '
                f'data-db="{r["db"]}" data-dbo="{DBORDER[r["db"]]}" data-rd="{rd}" data-rdo="{RD_ORDER[rd]}" '
                f'data-score="{v(score)}" '
                f'data-conf="{v(conf)}" data-cov="{v(cov)}" data-s="{html.escape(s)}">'), name

    NOTES = {"the repository holds builds or MRAs, no HDL": t("note.nohdl")}
    rows = []
    for r in sorted(res, key=lambda r: (DBORDER[r["db"]], r["core"].lower())):
        titles = html.escape(", ".join(r.get("titles", [])[:3]) + (" …" if len(r.get("titles", [])) > 3 else ""))
        if r.get("status") != "analyzed":
            closed = r.get("status") == "source not published"
            state = t("rd.closed") if closed else r.get("status", "")
            pub = published(r)
            src = ""
            if closed:   # a repo that was checked and holds no HDL is linked itself, so the reader can look
                src = (a(f"https://github.com/{r['repo']}/tree/{r['build_commit']}" + (f"/{r['subdir']}" if r.get("subdir") else ""),
                         r["repo"] + " @ " + r["build_commit"][:8]) if r.get("repo") and r.get("build_commit")
                       else a(db_home(r["db"]), t("buildsonly")))
            if r.get("note"):
                n = r["note"]
                n = NOTES.get(n) or (t("note.several", x=n.split(": ", 1)[1]) if n.startswith("several candidate") else n)
                src += "<br>" + html.escape(n)
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
            side = LABEL[rule][0]
            title = label(rule)[0]

            def mame_note(i):
                refs = i.get("mame_refs") or []
                if not refs:
                    return ""
                lead = t("sharestext") if i["rule"] == "copied_text" else t("alsoinmame")
                return f' <span class="muted">— {lead} ' + ", ".join(
                    (f"<b>{html.escape(x)}</b> " if i["rule"] != "copied_text" else "") + mame_link(rel, ln)
                    for x, rel, ln in refs) + "</span>"
            lis = "".join(f'<li>{a(permalink(r, i["at"]), i["at"])} '
                          f'{html.escape(i["text"] if i["text"] != i["at"] else "")}{mame_note(i)}</li>' for i in its[:300])
            more = f'<li class="muted">{t("more", n=len(its) - 300)}</li>' if len(its) > 300 else ""
            groups.append(f'<details class="{side}"><summary>{title} — {len(its)}</summary><ul>{lis}{more}</ul></details>')
        if r["db"] == "jt":
            src = a("https://github.com/jotego/jtcores", "jotego/jtcores") + " @ " + a(
                f"https://github.com/jotego/jtcores/tree/{r['build_commit']}/{r['subdir']}", r["build_commit"][:8])
            if r.get("match", "").startswith("approximate"):
                src += f' <span title="{html.escape(r["match"])}">({t("approx")})</span>'
        else:
            tree = f"https://github.com/{r['repo']}/tree/{r['build_commit']}" + (f"/{r['subdir']}" if r.get("subdir") else "")
            src = a(f"https://github.com/{r['repo']}", r["repo"]) + " @ " + a(tree, r["build_commit"][:8])
            how = r.get("match", "exact file")
            if not how.startswith("exact"):
                lbl = t("approx") if how.startswith("approximate") else t("bydate")
                src += f' <span title="{html.escape(how)}">({lbl})</span>'
        drv = r.get("mame_drivers") or []
        extra = len(r.get("mame_files") or []) - len(drv)
        mame = (t("mamecompared", files=", ".join(mame_link(d) for d in drv)) +
                (t("related", n=extra) if extra > 0 else "")) if drv else t("nodriver")
        if r.get("own_hdl_files") is not None:   # which files the reading rests on (fva/scope.py)
            scope = r.get("file_scope", "all HDL files: no Quartus project found")
            mame += "<br>" + t("read", files=r["own_hdl_files"], lines=f'{r.get("own_hdl_lines", 0):,}',
                               scope=html.escape(M.get("scope." + scope, scope)))
        side = {"hardware": 0, "mame": 0, "neutral": 0}
        for i in sc["items"]:
            side[LABEL[i["rule"]][0]] += 1
        tally = ", ".join(x for x in (
            f'<span class="dot hw"></span>{t("t.hw", n=side["hardware"])}' if side["hardware"] else "",
            f'<span class="dot mm"></span>{t("t.mame", n=side["mame"])}' if side["mame"] else "",
            t("t.neutral", n=side["neutral"]) if side["neutral"] else "") if x)
        ev = (f'<details class="evidence"><summary>{t("statements", tally=tally)}</summary>{"".join(groups)}</details>'
              if groups else f'<span class="muted small">{t("nostatements")}</span>')
        rk = READ_KEY[r["reading"]]
        head, name = core_open(r, rk, score=None if pos is None else round(pos, 1),
                               conf=CONF.get(sc["confidence"]), cov=sc["coverage"])
        rows.append(f'{head}<tr class="main"><td>{name}<br><span class="muted small">{titles}<br>{src}<br>{mame}</span></td>'
                    f'<td>{db_cell(r)}</td><td>{meter(pos)}</td><td>{t("rd." + rk)}</td>'
                    f'<td class="num c5">{t("conf." + sc["confidence"])}</td><td class="num c6">{sc["coverage"]}%</td></tr>'
                    f'<tr class="ev"><td colspan="6">{ev}</td></tr></tbody>')

    def chip(k, v, text, sw=None):
        swatch = "" if sw is None else f'<span class="sw {sw[0]}" style="{sw[1]}"></span>'
        return f'<button type="button" class="chip" data-k="{k}" data-v="{v}" aria-pressed="false">{swatch}{text} <span class="n"></span></button>'
    chips_db = "".join(chip("db", k, dbname(k)) for k in DEFAULT_DBS)
    chips_dev = "".join(chip("db", k, dbname(k)) for k in DEV_DBS)
    chips_rd = "".join(chip("rd", k, t("rd.none.chip") if k == "none" else t("rd." + k),
                            ("empty" if k == "none" else "closed" if k == "closed" else "", st))
                       for k, _, st in CHIPS_RD)
    tools = f"""<div class="tools" hidden>
<div class="row"><input id="q" type="search" placeholder="{html.escape(t("search"))}" aria-label="Search"></div>
<div class="row"><span class="lbl">{t("f.reading")}</span><div class="chips">{chips_rd}</div></div>
<div class="row"><span class="lbl">update_all</span><div class="chips">{chips_db}</div></div>
<div class="row"><span class="lbl" title="{html.escape(t("f.independent.title"))}">{t("f.independent")}</span><div class="chips">{chips_dev}</div>
<span style="flex:1"></span><span id="count" class="muted small"></span>
<button type="button" id="expand" class="plain">{t("expand")}</button><button type="button" id="reset" class="plain">{t("reset")}</button></div>
</div>"""

    def th(key, lbl, title="", cls=""):
        """A sortable column header, as in kiban's tables: click to sort, click again to reverse."""
        ti = f' title="{html.escape(title)}"' if title else ""
        return (f'<th class="sortable {cls}" data-sort="{key}" tabindex="0" aria-sort="none"{ti}>{lbl}'
                f'<span class="arr"></span></th>')

    legend = "".join(f'<tr><td>{label(k)[0]}</td><td class="num">{POINTS[k]}</td>'
                     f'<td>{t("side." + s)}</td><td class="muted">{label(k)[1]}</td></tr>'
                     for k, (s, _, _) in LABEL.items())
    strings = json.dumps({k: M[k] for k in ("count.all", "count.some", "expand", "collapse")}, ensure_ascii=False)
    switch = "ja/" if lang == "en" else "../"
    page = f"""<!doctype html><html lang="{lang}"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{t("title")}</title><style>{CSS}</style></head><body>
<nav class="lang"><a id="langlink" data-base="{switch}" href="{switch}" hreflang="{"ja" if lang == "en" else "en"}">{t("switch")}</a></nav>
<h1>{t("h1")}</h1>
<p>{t("intro", mame=a("https://github.com/mamedev/mame/tree/" + meta["mame_commit"], meta["mame_commit"][:10]))}</p>
<p class="note">{t("face")}</p>
<p class="muted small">{t("meta", rules=meta["rules_version"], tool=meta["tool_version"], gen=meta["generated"])}</p>
{tools}
<table id="cores"><thead><tr>{th("name", t("col.core"))}{th("db", t("col.db"))}
{th("pos", f'<div class="axis"><span>{t("axis.mame")}</span><span>{t("axis.hw")}</span></div>', t("col.pos"))}
{th("rd", t("col.reading"))}{th("conf", t("col.conf"), cls="num c5")}{th("cov", t("col.cov"), t("col.cov.title"), cls="num c6")}</tr></thead>{"".join(rows)}</table>
<p id="none" class="muted" hidden>{t("none")} <a href="?">{t("showall")}</a></p>
{coinop_note()}
{not_analyzed()}
<h2>{t("how.h")}</h2>
<p>{t("how")}</p>
<table><tr><td><b>{t("lg.statement")}</b></td><td class="num"><b>{t("lg.points")}</b></td><td><b>{t("lg.side")}</b></td><td><b>{t("lg.includes")}</b></td></tr>{legend}</table>
<p class="muted">{t("notcounted")}</p>
<script>window.FVA_L={strings};</script>
<script>{JS}</script>
</body></html>"""
    out_dir = RESULTS if lang == "en" else os.path.join(RESULTS, lang)
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, "index.html")
    open(out, "w", encoding="utf-8").write(page)
    print(out, os.path.getsize(out) // 1024, "KB")


def build_all():
    for lang in LANGS:
        build(lang)
