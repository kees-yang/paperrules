"""Run the rules of a project against its paper and arrange the result along the rule tree."""
import time
from pathlib import Path

from . import rules_document as RD
from . import rules_sentence as RS
from . import texread
from .config import Project

RANK = {'fail': 3, 'warn': 2, 'pending': 2, 'manual': 1, 'skip': 0, 'off': 0, 'pass': 0}
SENTENCE_GROUPS = ('voice', 'connectives', 'heads', 'glossary_terms', 'repeated')


class Ctx:
    def __init__(self, project, paper, bib):
        self.project, self.paper, self.bib = project, paper, bib
        self.rows = paper.rows


def _rows_findings(items):
    out = []
    for it in items:
        r = it['row']
        out.append(dict(rule=it['rule'], id=r['id'], key='', section=r['section'], kind=r['kind'], en=r['en'],
                        file=r['file'], line=r['line'], matched=it['matched'], word=it.get('word', '')))
    return out


def _doc_findings(items):
    return [dict(rule=it['rule'], id=it['key'], key=it['key'], section='', kind='document', en='', file=it.get('file', ''),
                 line=it.get('line', 0), matched=it['matched'], word='') for it in items]


def run_group(name, c, force=False):
    """Findings of one group of builtin checks, or None when the input the group needs is missing (reason in c.skip)."""
    p, proj = c.paper, c.project
    if name == 'voice':
        return _rows_findings(RS.tone_and_voice(c.rows, proj.rules, proj.limitation_sections))
    if name == 'connectives':
        return _rows_findings(RS.connectives(c.rows, proj.rules))
    if name == 'repeated':
        return _rows_findings(RS.repeated_sentences(c.rows))
    if name in ('heads', 'glossary_terms'):
        if not proj.glossary and not (force and name == 'heads'):
            return None
        return _rows_findings(RS.head_nouns(c.rows, proj.rules, proj.glossary) if name == 'heads' else RS.glossary_terms(c.rows, proj.glossary))
    if name in ('bib_citations', 'bib_entries'):
        if c.bib is None:
            return None
        bib_name = proj.bib.name if proj.bib else 'bib'
        return _doc_findings(RD.bib_citations(p, c.bib, bib_name) if name == 'bib_citations' else RD.bib_entries(c.bib, proj.rules['document'], bib_name))
    if name == 'abstract':
        return _doc_findings(RD.abstract_rules(p, proj.rules['document']))
    if name == 'keywords':
        return _doc_findings(RD.keyword_rules(p, proj.rules['document']))
    if name == 'floats':
        return _doc_findings(RD.float_rules(p))
    if name == 'abstract_structure':
        return _doc_findings(RD.abstract_structure(p, proj.rules['document']))
    if name == 'table_order':
        return _doc_findings(RD.table_order(p, proj.rules['document']))
    if name == 'register':
        return []                      # R0 and R1 are computed in run()
    raise KeyError(name)


def sentence_findings(rows, project, only=None, include_disabled=False):
    """Findings of the sentence- and paragraph-level rules on given rows (used by the checker and by the rule tests)."""
    ctx = Ctx(project, texread.Paper(rows=rows), None)
    out = []
    enabled = [r for r in project.register['rules'] if (include_disabled or project.enabled(r)) and (only is None or r['id'] in only)]
    groups = {r['check']['group'] for r in enabled if r['check']['type'] == 'builtin' and r['check']['group'] in SENTENCE_GROUPS}
    for g in groups:
        out += run_group(g, ctx, force=True) or []
    for r in enabled:
        if r['check']['type'] == 'pattern':
            out += _rows_findings(RS.pattern_rules(rows, r))
    return [f for f in out if only is None or f['rule'] in only]


def test_rules(project):
    """R1: every testable rule flags its ``flag`` tests and passes its ``pass`` tests. Returns (count, problems)."""
    problems, n = [], 0
    for r in project.register['rules']:
        t = r.get('tests')
        if not t or r['check']['type'] == 'manual':
            continue
        for kind in ('flag', 'pass'):
            for s in t.get(kind, []):
                n += 1
                sents = s if isinstance(s, list) else [s]
                rows = [dict(id=f't{i}', para='t', section='test', kind='paragraph', en=x, file='test', line=0) for i, x in enumerate(sents)]
                hit = any(f['rule'] == r['id'] for f in sentence_findings(rows, project, only={r['id']}, include_disabled=True))
                if kind == 'flag' and not hit:
                    problems.append(dict(rule=r['id'], issue='should be flagged but is not', text=' / '.join(sents)))
                if kind == 'pass' and hit:
                    problems.append(dict(rule=r['id'], issue='should pass but is flagged', text=' / '.join(sents)))
    return n, problems


def tree_problems(project):
    """R0: every rule of the register is in exactly one node of the tree; every node of the tree exists."""
    tree = project.rules['tree']
    nodes = {(s['id'], n['id']) for s in tree['stages'] for n in s['nodes']}
    ids = [r['id'] for r in project.register['rules']]
    items = [dict(rule=i, issue='duplicate rule id') for i in sorted({x for x in ids if ids.count(x) > 1})]
    for r in project.register['rules']:
        if (r['stage'], r['node']) not in nodes:
            items.append(dict(rule=r['id'], issue=f'stage/node {r["stage"]}/{r["node"]} is not in the rule tree'))
        if r['check']['type'] == 'builtin' and 'group' not in r['check']:
            items.append(dict(rule=r['id'], issue='builtin check without a group'))
    return items


def apply_exceptions(findings, exceptions):
    ex = [e for e in exceptions]
    for f in findings:
        f['status'], f['reason'] = 'open', ''
        for e in ex:
            if e['rule'] != f['rule']:
                continue
            if e.get('key') and e['key'] == f['key'] or e.get('sentence_en') and e['sentence_en'].strip() == f['en'].strip() \
                    and (not e.get('word') or e['word'].lower() == (f['word'] or '').lower()):
                f['status'] = 'accepted' if e.get('status') == 'accepted' else 'pending'
                f['reason'] = e.get('reason', '')
                break
    return findings


def run(project: Project, only=None):
    t0 = time.time()
    paper = texread.read(project.main_tex)
    bib = None
    bib_path = project.bib
    if bib_path is None and paper.bib_files:
        cand = project.root / (paper.bib_files[0] if paper.bib_files[0].endswith('.bib') else paper.bib_files[0] + '.bib')
        bib_path = cand if cand.exists() else None
    if bib_path is not None and Path(bib_path).exists():
        bib = RD.parse_bib(bib_path)
        project.bib = Path(bib_path)
    ctx = Ctx(project, paper, bib)

    rules = [r for r in project.register['rules']]
    findings, skipped, ran = [], {}, {}
    for g in sorted({r['check']['group'] for r in rules if r['check']['type'] == 'builtin' and project.enabled(r) and (only is None or r['id'] in only)}):
        res = run_group(g, ctx)
        if res is None:
            skipped[g] = {'heads': 'no glossary in the project (set "glossary" in paperrules.json)', 'glossary_terms': 'no glossary in the project',
                          'bib_citations': 'no .bib file found', 'bib_entries': 'no .bib file found'}[g]
            continue
        ran[g] = True
        findings += res
    for r in rules:
        if r['check']['type'] == 'pattern' and project.enabled(r) and (only is None or r['id'] in only):
            findings += _rows_findings(RS.pattern_rules(paper.rows, r))
    sev = {r['id']: r for r in rules}
    findings = [f for f in findings if f['rule'] in sev and project.enabled(sev[f['rule']]) and (only is None or f['rule'] in only)]
    apply_exceptions(findings, project.exceptions)

    n_tests, test_problems = test_rules(project)
    tree_bad = tree_problems(project)
    results = []
    for r in rules:
        fs = [f for f in findings if f['rule'] == r['id']]
        open_ = [f for f in fs if f['status'] != 'accepted']
        row = dict(id=r['id'], stage=r['stage'], node=r['node'], scope=r['scope'], method=r['method'], severity=r['severity'],
                   statement=r['statement'], why=r['why'], open=len(open_), accepted=len(fs) - len(open_), note='')
        grp = r['check'].get('group')
        if not project.enabled(r):
            row['status'] = 'off'
        elif only is not None and r['id'] not in only:
            row['status'] = 'off'
            row['note'] = 'not selected (--only)'
        elif r['check']['type'] == 'manual':
            row['status'] = 'manual'
        elif r['id'] == 'R0':
            row['status'], row['open'] = ('fail' if tree_bad else 'pass'), len(tree_bad)
            row['note'] = '; '.join(f'{x["rule"]}: {x["issue"]}' for x in tree_bad[:5])
        elif r['id'] == 'R1':
            row['status'], row['open'] = ('fail' if test_problems else 'pass'), len(test_problems)
            row['note'] = f'{n_tests} test sentences' + ('; ' + '; '.join(f'{x["rule"]}: {x["issue"]}' for x in test_problems[:5]) if test_problems else '')
        elif grp in skipped:
            row['status'], row['note'] = 'skip', skipped[grp]
        elif r['id'] == 'J3' and not paper.keywords:
            row['status'], row['note'] = 'skip', 'the paper has no keywords'
        else:
            row['status'] = ('fail' if r['severity'] == 'error' else 'warn') if open_ else 'pass'
            if r['method'] == 'partial':
                row['note'] = 'partly automatic: the checker flags, the author decides'
        results.append(row)
    stages, blocked_by = [], None
    by_id = {r['id']: r for r in results}
    for i, s in enumerate(project.rules['tree']['stages']):
        nodes = [dict(id=n['id'], name=n['name'], rules=[r['id'] for r in results if (r['stage'], r['node']) == (s['id'], n['id'])]) for n in s['nodes']]
        ids = [rid for n in nodes for rid in n['rules']]
        status = max((by_id[x]['status'] for x in ids), key=RANK.get, default='pass')
        stages.append(dict(id=s['id'], number=i + 1, name=s['name'], role=s['role'], when=s['when'], status=status,
                           gate='provisional' if blocked_by else 'open', blocked_by=blocked_by, nodes=nodes))
        if status == 'fail' and not blocked_by:
            blocked_by = s['name']
    first_failing = next((s['name'] for s in stages if s['status'] == 'fail'), None)
    first_warn = next((s['name'] for s in stages if s['status'] in ('warn', 'pending')), None)
    summary = {k: sum(r['status'] == k for r in results) for k in ('pass', 'warn', 'fail', 'manual', 'skip', 'off')}
    paras = {r['para'] for r in paper.rows}
    return dict(schema='paperrules-result/1', checked_at=time.strftime('%Y-%m-%d %H:%M:%S'), seconds=round(time.time() - t0, 1),
                project=dict(main_tex=str(project.main_tex.relative_to(project.root)), bib=str(Path(project.bib).name) if project.bib else None,
                             packs=project.settings.get('packs', ['default']), glossary_terms=len(project.glossary), exceptions=len(project.exceptions)),
                paper=dict(sentences=len(paper.rows), paragraphs=len(paras), figures=sum(f['env'] == 'figure' for f in paper.floats),
                           algorithms=sum(f['env'] == 'algorithm' for f in paper.floats),
                           tables=sum(f['env'] == 'table' for f in paper.floats), citations=len(paper.cites), bib_entries=len(bib) if bib else 0,
                           abstract_words=len(paper.abstract.split()), keywords=len(paper.keywords)),
                summary=summary, first_failing=first_failing, first_warning=first_warn, stages=stages, rules=results,
                findings=findings, tests=dict(count=n_tests, problems=test_problems))
