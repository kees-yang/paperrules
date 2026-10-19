"""Document-level rules: abstract, keywords, figures and tables, cross-references and the bibliography.

All checks read the LaTeX source (and the .bib file); none needs a compiled PDF. Each function returns findings
``dict(rule, key, file, line, matched)``; ``key`` names the thing the finding is about (a label, a citation key, ...).
"""
import re
from pathlib import Path


# ---------------------------------------------------------------------------------------------------- bibliography
def parse_bib(path):
    """Entries of a .bib file: dict(key, type, fields, line). Macros (@string) and comments are skipped."""
    text = Path(path).read_text(encoding='utf-8', errors='replace')
    entries = []
    for m in re.finditer(r'@(\w+)\s*([{(])', text):
        typ = m.group(1).lower()
        if typ in ('string', 'comment', 'preamble'):
            continue
        open_, close = m.group(2), '}' if m.group(2) == '{' else ')'
        depth, k = 0, m.end() - 1
        while k < len(text):
            c = text[k]
            if c == '\\':
                k += 2
                continue
            if c == open_:
                depth += 1
            elif c == close:
                depth -= 1
                if depth == 0:
                    break
            k += 1
        inner = text[m.end():k]
        key, _, rest = inner.partition(',')
        fields = {}
        for fm in re.finditer(r'(\w+)\s*=\s*', rest):
            v = rest[fm.end():]
            if v.startswith('{'):
                depth, j = 0, 0
                for j, c in enumerate(v):
                    depth += (c == '{') - (c == '}')
                    if depth == 0:
                        break
                val = v[1:j]
            elif v.startswith('"'):
                j = 1
                while j < len(v) and v[j] != '"':
                    j += 2 if v[j] == '\\' else 1
                val = v[1:j]
            else:
                val = re.match(r'[^,\s]*', v).group(0)
            fields.setdefault(fm.group(1).lower(), val.strip())
        entries.append(dict(key=key.strip(), type=typ, fields=fields, line=text.count('\n', 0, m.start()) + 1))
    return entries


def bib_citations(paper, entries, bib_name):
    """B1 every cited key exists in the bibliography; B8 every bibliography entry is cited."""
    keys = {e['key'] for e in entries}
    out = []
    for k in paper.cites:
        if k not in keys and k != '*':
            f, ln = paper.cite_locs.get(k, ('', 0))
            out.append(dict(rule='B1', key=k, file=f, line=ln, matched=f'cited key “{k}” is not in the bibliography'))
    for e in entries:
        if e['key'] not in paper.cites:
            out.append(dict(rule='B8', key=e['key'], file=bib_name, line=e['line'], matched=f'entry “{e["key"]}” is never cited'))
    return out


def bib_entries(entries, cfg, bib_name):
    """B7 required fields, complete author lists, optional initials; B4 no DOI or URL; B9 duplicate keys."""
    out, seen = [], {}
    req = cfg['B7']['required']
    for e in entries:
        f, key = e['fields'], e['key']
        if key in seen:
            out.append(dict(rule='B9', key=key, file=bib_name, line=e['line'], matched=f'duplicate key (first at line {seen[key]})'))
        seen.setdefault(key, e['line'])
        miss = [x for x in req.get(e['type'], req.get('default', [])) if not any(f.get(a) for a in x.split('|'))]
        if miss:
            out.append(dict(rule='B7', key=key, file=bib_name, line=e['line'], matched='missing field(s): ' + ', '.join(miss)))
        au = f.get('author', '')
        if re.search(r'\band others\b|\bet al\b', au) and cfg['B7'].get('complete_authors', True):
            out.append(dict(rule='B7', key=key, file=bib_name, line=e['line'], matched='author list is cut ("and others" / "et al.")'))
        if cfg['B7'].get('initials') and au:
            for name in re.split(r'\s+and\s+', au):
                given = name.split(',', 1)[1].strip() if ',' in name else ' '.join(name.split()[:-1])
                if any(len(w.strip('.')) > 1 for w in re.split(r'[\s\-]+', given) if w):
                    out.append(dict(rule='B7', key=key, file=bib_name, line=e['line'], matched=f'given name not an initial: “{name.strip()}”'))
                    break
        if f.get('doi') or f.get('url'):
            out.append(dict(rule='B4', key=key, file=bib_name, line=e['line'], matched='entry carries a ' + ('DOI' if f.get('doi') else 'URL')))
    return out


# ---------------------------------------------------------------------------------------------------- abstract and keywords
def abstract_rules(paper, cfg):
    out = []
    a = paper.abstract
    f, ln = paper.abstract_loc
    if not a:
        return out
    n = len(re.findall(r"[A-Za-z0-9][A-Za-z0-9'’\-]*", a))
    lo, hi = cfg['J1']['min'], cfg['J1']['max']
    if n < lo or n > hi:
        out.append(dict(rule='J1', key='abstract', file=f, line=ln, matched=f'the abstract has {n} words (allowed {lo}–{hi})'))
    if re.search(r'\[\d+(?:,\s*\d+)*\]|\[\?\]', a):
        out.append(dict(rule='J2', key='abstract', file=f, line=ln, matched='the abstract contains a citation'))
    nums = re.findall(r'(?<![\w.])\d+(?:\.\d+)?%?', a)
    mx = cfg.get('E6', {}).get('max_numbers')
    if mx is not None and len(nums) > mx:
        out.append(dict(rule='E6', key='abstract', file=f, line=ln, matched=f'the abstract has {len(nums)} numbers (allowed {mx}): ' + ', '.join(nums)))
    return out


def keyword_rules(paper, cfg):
    if not paper.keywords:
        return []
    lo, hi = cfg['J3']['min'], cfg['J3']['max']
    n = len(paper.keywords)
    return [] if lo <= n <= hi else [dict(rule='J3', key='keywords', file=paper.abstract_loc[0], line=0, matched=f'{n} keywords (allowed {lo}–{hi})')]


# ---------------------------------------------------------------------------------------------------- floats and references
def float_rules(paper):
    """T1 numbering follows the order of first citation; T2 a float is cited before it appears; B2 every reference has a label."""
    out = []
    first = {}
    for r in paper.refs:
        first.setdefault(r['label'], r)
    labelled = {f['label']: f for f in paper.floats if f['label']}
    for env in ('figure', 'table'):
        cited = sorted((first[l]['offset'], f) for l, f in labelled.items() if f['env'] == env and l in first)
        top = 0
        for _, f in cited:
            if f['number'] < top:
                out.append(dict(rule='T1', key=f['label'], file=f['file'], line=f['line'],
                                matched=f'{env} {f["number"]} is first cited after {env} {top}; number floats in the order of first citation'))
            top = max(top, f['number'])
    for l, f in labelled.items():
        if l not in first:
            out.append(dict(rule='T2', key=l, file=f['file'], line=f['line'], matched=f'{f["env"]} {f["number"]} is never cited in the text'))
        elif f['offset'] < first[l]['offset']:
            out.append(dict(rule='T2', key=l, file=f['file'], line=f['line'],
                            matched=f'{f["env"]} {f["number"]} appears before its first citation (line {first[l]["line"]} of {first[l]["file"]})'))
    for r in paper.refs:
        if r['label'] not in paper.labels:
            out.append(dict(rule='B2', key=r['label'], file=r['file'], line=r['line'], matched=f'reference to unknown label “{r["label"]}”'))
    return out
