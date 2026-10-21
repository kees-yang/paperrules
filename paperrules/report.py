"""Text and offline HTML reports of a check result (see runner.run). The HTML file has no external resources."""
import html
import json
from pathlib import Path

ICON = {'pass': '✓', 'warn': '!', 'fail': '✗', 'manual': '☐', 'skip': '–', 'off': '·', 'pending': '?'}
UI = {
    'title': ('Paper rule check', '论文规则检查'),
    'revise_first': ('Revise first', '先改这一层'),
    'nothing': ('No stage fails.', '没有未通过的层。'),
    'paper': ('Paper', '论文'), 'sentences': ('sentences', '句'), 'paragraphs': ('paragraphs', '段'), 'figures': ('figures', '图'),
    'tables': ('tables', '表'), 'citations': ('citations', '引用'), 'bib': ('bibliography entries', '参考文献条目'), 'abstract': ('abstract words', '摘要词数'),
    'rule_tree': ('Rule tree', '规则树'), 'findings': ('open findings', '待处理'), 'accepted': ('accepted with a reason', '已写明理由接受'),
    'sentence': ('Sentence', '句子'), 'where': ('Where', '位置'), 'why': ('Why flagged', '标出原因'),
    'manual_list': ('Checklist for the author (rules a person checks)', '作者核对清单（需人工检查的规则）'),
    'provisional': ('provisional: a stage above fails', '暂定：上一层未通过'),
    'more': ('more', '更多'), 'reason': ('Reason', '理由'),
    'checked': ('Checked', '检查时间'), 'project': ('Project', '项目'),
    'status': {'pass': ('pass', '通过'), 'warn': ('warn', '有提示'), 'fail': ('fail', '未通过'), 'manual': ('manual', '人工'),
               'skip': ('skipped', '跳过'), 'off': ('off', '关闭'), 'pending': ('pending', '待定')},
    'note': ('Findings are style-rule matches, not a judgement of the paper; open them as questions to the author.',
             '结果是风格规则的匹配，不是对论文的评价；请当作给作者的问题来读。'),
    'scope': {'sentence': ('sentence', '句'), 'paragraph': ('paragraph', '段'), 'document': ('document', '全文'), 'figure': ('figure', '图件')},
}


def esc(s):
    return html.escape(str(s), quote=True)


def bi(pair):
    """A bilingual span pair from a (en, zh) tuple or {en, zh} dict."""
    en, zh = (pair['en'], pair['zh']) if isinstance(pair, dict) else pair
    return f'<span lang="en">{esc(en)}</span><span lang="zh">{esc(zh)}</span>'


def text_report(res, verbose=False, limit=5):
    L = []
    s = res['summary']
    L.append(f'paperrules {res["checked_at"]} · {res["project"]["main_tex"]} · {res["paper"]["sentences"]} sentences, '
             f'{res["paper"]["figures"]} figures, {res["paper"]["tables"]} tables, {res["paper"]["citations"]} citations')
    L.append(f'rules: {s["pass"]} pass, {s["warn"]} warn, {s["fail"]} fail, {s["manual"]} manual, {s["skip"]} skipped, {s["off"]} off')
    by_id = {r['id']: r for r in res['rules']}
    for st in res['stages']:
        tag = st['status'] + (' · provisional' if st['gate'] == 'provisional' else '')
        L.append(f'\n{st["number"]}. {st["name"]["en"]}  [{tag}]')
        for n in st['nodes']:
            for rid in n['rules']:
                r = by_id[rid]
                if r['status'] in ('off',):
                    continue
                extra = f' — {r["note"]}' if r['note'] and r['status'] in ('skip', 'fail') else ''
                L.append(f'  [{r["status"]:6}] {r["id"]:3} {r["statement"]["en"][:78]}{"…" if len(r["statement"]["en"]) > 78 else ""}'
                         + (f'  ({r["open"]} open' + (f', {r["accepted"]} accepted' if r['accepted'] else '') + ')' if r['open'] or r['accepted'] else '') + extra)
                if r['open'] and (verbose or r['status'] in ('fail',)):
                    shown = [f for f in res['findings'] if f['rule'] == rid and f['status'] != 'accepted']
                    for f in shown[: (len(shown) if verbose else limit)]:
                        loc = f'{f["file"]}:{f["line"]}' if f['file'] else ''
                        L.append(f'        {f["id"]:8} {loc:24} {f["matched"][:100]}')
                    if len(shown) > limit and not verbose:
                        L.append(f'        … {len(shown) - limit} more (use --verbose or the HTML report)')
    if res['first_failing']:
        L.append(f'\nrevise first: {res["first_failing"]["en"]}')
    return '\n'.join(L)


CSS = """
:root{--bg:#f7f7f4;--fg:#1c1c1a;--mut:#62625c;--card:#fff;--line:#dcdcd4;--pass:#2c7a4b;--warn:#a86a00;--fail:#b3261e;--man:#4a5ab8;--off:#8c8c84;--acc:#2b5fb4}
@media (prefers-color-scheme:dark){:root:not([data-theme=light]){--bg:#161615;--fg:#ececE6;--mut:#a3a39b;--card:#201f1d;--line:#3a3935;--pass:#58c27d;--warn:#e0a13a;--fail:#f0746c;--man:#8c9bf0;--off:#77776f;--acc:#7fa8ee}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.5 system-ui,-apple-system,"Segoe UI","Noto Sans SC","PingFang SC",sans-serif}
main{max-width:1100px;margin:0 auto;padding:16px}
header{display:flex;flex-wrap:wrap;gap:8px;align-items:center;justify-content:space-between}
h1{font-size:1.4rem;margin:.2em 0}h2{font-size:1.1rem;margin:1.6em 0 .5em}
.mut{color:var(--mut)}.small{font-size:.85rem}
button{font:inherit;background:var(--card);color:var(--fg);border:1px solid var(--line);border-radius:6px;padding:4px 10px;cursor:pointer}
.cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(110px,1fr));gap:8px;margin:12px 0}
.card{background:var(--card);border:1px solid var(--line);border-radius:8px;padding:8px 10px}.card b{display:block;font-size:1.4rem}
.banner{background:var(--card);border:1px solid var(--line);border-left:4px solid var(--fail);border-radius:6px;padding:8px 12px;margin:8px 0}
.banner.ok{border-left-color:var(--pass)}
.stage{background:var(--card);border:1px solid var(--line);border-radius:8px;margin:10px 0;padding:6px 12px 10px}
.stage>h3{font-size:1rem;margin:6px 0;display:flex;gap:8px;flex-wrap:wrap;align-items:baseline}
.node{margin:6px 0 0 6px}.node>h4{font-size:.85rem;color:var(--mut);margin:6px 0 2px;font-weight:600}
.chip{display:inline-block;min-width:1.5em;text-align:center;border-radius:4px;padding:0 6px;font-size:.78rem;font-weight:700;color:#fff}
.chip.pass{background:var(--pass)}.chip.warn,.chip.pending{background:var(--warn)}.chip.fail{background:var(--fail)}.chip.manual{background:var(--man)}.chip.skip,.chip.off{background:var(--off)}
.rule{border-top:1px solid var(--line);padding:5px 0}.rule:first-of-type{border-top:0}
.rule summary{cursor:pointer;display:flex;gap:8px;align-items:baseline;flex-wrap:wrap}.rule summary::-webkit-details-marker{margin-right:2px}
.rid{font-family:ui-monospace,Menlo,Consolas,monospace;font-weight:700;min-width:2.4em}
.cnt{font-size:.8rem;color:var(--mut)}
.why{color:var(--mut);font-size:.88rem;margin:2px 0 6px}
table{border-collapse:collapse;width:100%;font-size:.88rem}th,td{text-align:left;vertical-align:top;border-top:1px solid var(--line);padding:4px 6px}
td.s{min-width:40%;overflow-wrap:anywhere}td.w{white-space:nowrap}
.tablewrap{overflow-x:auto}
.prov{opacity:.75}
[data-lang=en] [lang=zh],[data-lang=zh] [lang=en]{display:none}
footer{margin:24px 0 8px;color:var(--mut);font-size:.85rem}
@media (max-width:640px){main{padding:10px}td.w{white-space:normal}}
"""

JS = """
(function(){var d=document.documentElement,l='en';try{l=localStorage.getItem('pr-lang')||l}catch(e){}
function set(x){d.setAttribute('data-lang',x);try{localStorage.setItem('pr-lang',x)}catch(e){}}
set(l);document.getElementById('lang').addEventListener('click',function(){set(d.getAttribute('data-lang')==='en'?'zh':'en')})})();
"""


def html_report(res, limit=60):
    by_id = {r['id']: r for r in res['rules']}
    s, p = res['summary'], res['paper']
    o = []
    o.append('<!doctype html><html lang="en" data-lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">')
    o.append(f'<title>{esc(UI["title"][0])}</title><style>{CSS}</style></head><body><main>')
    o.append(f'<header><h1>{bi(UI["title"])}</h1><button id="lang" type="button">EN / 中文</button></header>')
    o.append(f'<p class="mut small">{bi(UI["project"])}: {esc(res["project"]["main_tex"])} · {bi(UI["checked"])}: {esc(res["checked_at"])} · '
             f'packs: {esc(", ".join(res["project"]["packs"]))}</p>')
    cards = [(s['fail'], 'fail'), (s['warn'], 'warn'), (s['pass'], 'pass'), (s['manual'], 'manual'), (s['skip'], 'skip'), (s['off'], 'off')]
    o.append('<div class="cards">' + ''.join(f'<div class="card"><b style="color:var(--{"pass" if k=="pass" else "warn" if k=="warn" else "fail" if k=="fail" else "man" if k=="manual" else "off"})">{n}</b>{bi(UI["status"][k])}</div>' for n, k in cards) + '</div>')
    if res['first_failing']:
        o.append(f'<div class="banner"><b>{bi(UI["revise_first"])}:</b> {bi(res["first_failing"])}</div>')
    else:
        o.append(f'<div class="banner ok">{bi(UI["nothing"])}</div>')
    o.append(f'<p class="small mut">{bi(UI["paper"])}: {p["sentences"]} {bi(UI["sentences"])} · {p["paragraphs"]} {bi(UI["paragraphs"])} · {p["figures"]} {bi(UI["figures"])} · '
             f'{p["tables"]} {bi(UI["tables"])} · {p["citations"]} {bi(UI["citations"])} · {p["bib_entries"]} {bi(UI["bib"])} · {p["abstract_words"]} {bi(UI["abstract"])}</p>')
    o.append(f'<h2>{bi(UI["rule_tree"])}</h2>')
    for st in res['stages']:
        prov = st['gate'] == 'provisional'
        o.append(f'<section class="stage{" prov" if prov else ""}"><h3><span class="chip {st["status"]}">{ICON[st["status"]]}</span>'
                 f'<span>{st["number"]}. {bi(st["name"])}</span>' + (f'<span class="cnt">{bi(UI["provisional"])}</span>' if prov else '')
                 + f'<span class="cnt">— {bi(st["when"])}</span></h3>')
        for n in st['nodes']:
            if not n['rules']:
                continue
            o.append(f'<div class="node"><h4>{bi(n["name"])}</h4>')
            for rid in n['rules']:
                r = by_id[rid]
                fs = [f for f in res['findings'] if f['rule'] == rid]
                openf = [f for f in fs if f['status'] != 'accepted']
                acc = [f for f in fs if f['status'] == 'accepted']
                opened = ' open' if r['status'] == 'fail' else ''
                o.append(f'<details class="rule"{opened}><summary><span class="chip {r["status"]}">{ICON[r["status"]]}</span><span class="rid">{esc(rid)}</span>'
                         f'<span>{bi(r["statement"])}</span><span class="cnt">{bi(UI["scope"][r["scope"]])} · {bi(UI["status"][r["status"]])}'
                         + (f' · {len(openf)} {bi(UI["findings"])}' if openf else '') + (f' · {len(acc)} {bi(UI["accepted"])}' if acc else '')
                         + '</span></summary>')
                o.append(f'<div class="why">{bi(r["why"])}' + (f' <i>{esc(r["note"])}</i>' if r['note'] else '') + '</div>')
                if openf or acc:
                    o.append('<div class="tablewrap"><table><thead><tr><th>#</th><th>' + bi(UI['where']) + '</th><th>' + bi(UI['sentence']) + '</th><th>' + bi(UI['why']) + '</th></tr></thead><tbody>')
                    for f in (openf + acc)[:limit]:
                        loc = f'{f["file"]}:{f["line"]}' if f['file'] else ''
                        sent = esc(f['en']) if f['en'] else '<span class="mut">—</span>'
                        extra = f'<br><span class="mut small">{bi(UI["reason"])}: {esc(f["reason"])}</span>' if f['status'] == 'accepted' else ''
                        o.append(f'<tr><td class="w">{esc(f["id"])}</td><td class="w">{esc(loc)}</td><td class="s">{sent}</td><td>{esc(f["matched"])}{extra}</td></tr>')
                    o.append('</tbody></table></div>')
                    if len(openf + acc) > limit:
                        o.append(f'<p class="small mut">… {len(openf + acc) - limit} {bi(UI["more"])} (report.json)</p>')
                o.append('</details>')
            o.append('</div>')
        o.append('</section>')
    man = [r for r in res['rules'] if r['status'] == 'manual']
    if man:
        o.append(f'<h2>{bi(UI["manual_list"])}</h2><ul>')
        o += [f'<li><b class="rid">{esc(r["id"])}</b> {bi(r["statement"])}<div class="why">{bi(r["why"])}</div></li>' for r in man]
        o.append('</ul>')
    o.append(f'<footer>{bi(UI["note"])}</footer></main><script>{JS}</script></body></html>')
    return ''.join(o)


def write_all(res, out_dir):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / 'report.json').write_text(json.dumps(res, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')
    (out / 'report.html').write_text(html_report(res), encoding='utf-8')
    (out / 'report.txt').write_text(text_report(res, verbose=True) + '\n', encoding='utf-8')
    return out
