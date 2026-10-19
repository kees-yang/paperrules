"""Command line: paperrules init | check | rules | test | sentences | accept."""
import argparse
import json
import re
import sys
import time
from pathlib import Path

from . import __version__, report, runner, texread
from .config import PROJECT_FILE, dump_json, load_json, load_project, resolve_project_file

LOCAL_TEMPLATE = {
    "note": "Local rule overrides. Keys ending in _add extend a list or dict of the pack, _remove deletes items; see docs/customizing-rules.md.",
    "disable": [],
    "enable": [],
    "severity": {},
    "tone": {},
    "heads": {},
    "document": {},
    "rules_add": []
}
GLOSSARY_TEMPLATE = {
    "note": "One entry per concept. 'en' is the main term; aliases_en and allowed are accepted forms (their head nouns may be used as subjects and objects); avoid_en lists old names that rule A3 flags.",
    "terms": []
}


def cmd_init(a):
    d = Path(a.dir)
    d.mkdir(parents=True, exist_ok=True)
    pf = d / PROJECT_FILE
    if pf.exists() and not a.force:
        raise SystemExit(f'{pf} exists (use --force to overwrite)')
    settings = {"main_tex": a.main, "packs": ["default"], "glossary": "glossary.json", "limitation_sections": ["limitation", "discussion"],
                "local_rules": "rules.local.json", "exceptions": "exceptions.json", "output": "out"}
    if a.bib:
        settings["bib"] = a.bib
    dump_json(pf, settings)
    for name, obj in (('rules.local.json', LOCAL_TEMPLATE), ('glossary.json', GLOSSARY_TEMPLATE), ('exceptions.json', {"exceptions": []})):
        if not (d / name).exists() or a.force:
            dump_json(d / name, obj)
    print(f'created {pf} and starter files; next: paperrules check {d}')


def cmd_check(a):
    proj = load_project(a.project)
    only = set(x.strip() for x in a.only.split(',')) if a.only else None
    if only:
        unknown = only - {r['id'] for r in proj.register['rules']}
        if unknown:
            raise SystemExit('unknown rule id(s): ' + ', '.join(sorted(unknown)))
    res = runner.run(proj, only)
    out_dir = Path(a.out) if a.out else proj.out_dir
    if not a.no_files:
        report.write_all(res, out_dir)
    if a.json:
        print(json.dumps(res, ensure_ascii=False, indent=1))
    else:
        print(report.text_report(res, verbose=a.verbose))
        if not a.no_files:
            print(f'\nreport: {out_dir / "report.html"}')
    s = res['summary']
    sys.exit(1 if s['fail'] or (a.strict and s['warn']) else 0)


def cmd_rules(a):
    proj = load_project(a.project)
    reg = proj.register['rules']
    if a.action == 'show':
        r = proj.rule(a.rule)
        if not r:
            raise SystemExit(f'unknown rule {a.rule}')
        print(json.dumps(r, ensure_ascii=False, indent=1))
        return
    lang = a.lang
    if a.action == 'markdown':
        print('| ID | Stage | Scope | Method | Default | Rule | 规则 |\n|---|---|---|---|---|---|---|')
        for r in reg:
            print(f'| {r["id"]} | {r["stage"]} | {r["scope"]} | {r["method"]} | {"on" if r.get("enabled", True) else "off"} | {r["statement"]["en"]} | {r["statement"]["zh"]} |')
        return
    if a.action == 'tree':
        for st in proj.rules['tree']['stages']:
            print(f'{st["id"]}  {st["name"][lang]}  —  {st["when"][lang]}')
            for n in st['nodes']:
                print(f'    {n["name"][lang]}')
                for r in reg:
                    if (r['stage'], r['node']) == (st['id'], n['id']):
                        flag = '' if proj.enabled(r) else '  (off)'
                        print(f'        {r["id"]:3} [{r["method"]:7}] {r["statement"][lang]}{flag}')
        return
    for r in reg:
        flag = '' if proj.enabled(r) else '  (off)'
        print(f'{r["id"]:3} {r["stage"]} {r["scope"]:9} {r["method"]:7} {r["severity"]:5} {r["statement"][lang][:90]}{flag}')


def cmd_test(a):
    proj = load_project(a.project)
    n, problems = runner.test_rules(proj)
    tb = runner.tree_problems(proj)
    for x in tb:
        print(f'R0  {x["rule"]}: {x["issue"]}')
    for x in problems:
        print(f'R1  {x["rule"]}: {x["issue"]}: {x["text"][:110]}')
    print(f'{n} test sentences, {len(problems)} test problem(s), {len(tb)} tree problem(s)')
    sys.exit(1 if problems or tb else 0)


def cmd_sentences(a):
    proj = load_project(a.project)
    paper = texread.read(proj.main_tex)
    rx = re.compile(a.grep, re.I) if a.grep else None
    for r in paper.rows:
        if rx and not rx.search(r['en']):
            continue
        print(f'{r["id"]} {r["para"]} {r["kind"]:9} {r["file"]}:{r["line"]:<4} [{r["section"][:24]}] {r["en"]}')


def cmd_accept(a):
    proj = load_project(a.project)
    pf = resolve_project_file(a.project)
    path = pf.parent / proj.settings.get('exceptions', 'exceptions.json')
    data = load_json(path) if path.exists() else {"exceptions": []}
    if not proj.rule(a.rule):
        raise SystemExit(f'unknown rule {a.rule}')
    entry = {"rule": a.rule, "status": 'accepted', "reason": a.reason, "decided": time.strftime('%Y-%m-%d')}
    entry['key' if a.key else 'sentence_en'] = a.target
    if a.word:
        entry['word'] = a.word
    data['exceptions'].append(entry)
    dump_json(path, data)
    print(f'recorded in {path}')


def main(argv=None):
    ap = argparse.ArgumentParser(prog='paperrules', description='Rule-based writing checks for LaTeX papers.')
    ap.add_argument('--version', action='version', version=f'paperrules {__version__}')
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('init', help='create a project (paperrules.json and starter files)')
    p.add_argument('dir')
    p.add_argument('--main', default='main.tex', help='main LaTeX file, relative to the project directory')
    p.add_argument('--bib', default=None, help='.bib file, relative to the project directory (default: from \\bibliography)')
    p.add_argument('--force', action='store_true')
    p.set_defaults(fn=cmd_init)
    p = sub.add_parser('check', help='run the rules against the paper and write the report')
    p.add_argument('project', nargs='?', default='.')
    p.add_argument('--only', help='comma-separated rule ids, e.g. W10,W14')
    p.add_argument('--strict', action='store_true', help='exit with status 1 on warnings too')
    p.add_argument('--verbose', '-v', action='store_true', help='print every open finding')
    p.add_argument('--out', help='output directory (default: the project "output", out/)')
    p.add_argument('--no-files', action='store_true', help='print only; write no report files')
    p.add_argument('--json', action='store_true', help='print the result as JSON')
    p.set_defaults(fn=cmd_check)
    p = sub.add_parser('rules', help='list the rules, show one, or print the rule tree')
    p.add_argument('action', nargs='?', choices=['list', 'tree', 'show', 'markdown'], default='list')
    p.add_argument('rule', nargs='?')
    p.add_argument('--project', default='.')
    p.add_argument('--lang', choices=['en', 'zh'], default='en')
    p.set_defaults(fn=cmd_rules)
    p = sub.add_parser('test', help='run the rule tests (R0 tree, R1 test sentences) of the merged rules')
    p.add_argument('project', nargs='?', default='.')
    p.set_defaults(fn=cmd_test)
    p = sub.add_parser('sentences', help='print the sentences the checker reads (to debug a rule or the reader)')
    p.add_argument('project', nargs='?', default='.')
    p.add_argument('--grep')
    p.set_defaults(fn=cmd_sentences)
    p = sub.add_parser('accept', help='record an exception: a flagged sentence or key that stays, with a reason')
    p.add_argument('rule')
    p.add_argument('target', help='the exact sentence (or, with --key, a label / citation key)')
    p.add_argument('--reason', required=True)
    p.add_argument('--key', action='store_true')
    p.add_argument('--word', help='for A6: the head noun the exception covers')
    p.add_argument('--project', default='.')
    p.set_defaults(fn=cmd_accept)
    a = ap.parse_args(argv)
    a.fn(a)


if __name__ == '__main__':
    main()
