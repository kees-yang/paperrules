"""Sentence- and paragraph-level rules.

Every function takes the rows of ``texread.read`` (dicts with id, para, section, kind, en, file, line) and the merged
rule settings, and returns a list of findings ``dict(rule, row, matched)``. Exceptions are applied later (runner.py).

Tone (W7-W9), voice (W10-W12) and connective (W13) rules are patterns in ``tone.json``. The structure rules (W10 passive,
W11 late condition, W14-W16) and the head-noun rules (A6, A7) use spaCy ``en_core_web_sm`` dependency parses. User-defined
pattern rules (``check.type == "pattern"`` in the register) run through ``pattern_rules``.
"""
import re
from functools import lru_cache

COND = {'if', 'unless', 'when', 'whenever', 'before', 'after', 'until', 'once'}
HEAD_DEPS = {'nsubj', 'nsubjpass', 'dobj', 'pobj', 'attr', 'dative', 'oprd'}
TAIL_PREP = r'(?:outside|inside|from|across|with|without|at|in|on|for|over|under|between|through|within|via|by|to|toward|towards|along|among|per)'


def _re(p, flags=re.I):
    return re.compile(p, flags)


def in_sections(section, patterns):
    return any(re.search(p, section or '', re.I) for p in patterns)


# ---------------------------------------------------------------------------------------------------- spaCy helpers
@lru_cache(maxsize=1)
def nlp():
    try:
        import spacy
        return spacy.load('en_core_web_sm')
    except OSError as e:  # model missing
        raise SystemExit('spaCy model missing: run  python -m spacy download en_core_web_sm') from e
    except ImportError as e:
        raise SystemExit('spaCy missing: run  pip install spacy && python -m spacy download en_core_web_sm') from e


@lru_cache(maxsize=8192)
def doc(en):
    return nlp()(en)


def _finite(d):
    return [t for t in d if t.pos_ in ('VERB', 'AUX') and any(c.dep_ in ('nsubj', 'nsubjpass', 'expl', 'csubj') for c in t.children)]


def _subclause(t):
    return t.dep_ in ('relcl', 'advcl', 'ccomp', 'acl', 'csubj') and any(c.dep_ in ('nsubj', 'nsubjpass', 'expl', 'mark') or c.tag_ in ('WDT', 'WRB', 'WP') for c in t.children)


def passive(en):
    return [f'{t.text} {t.head.text}' for t in doc(en) if t.dep_ == 'auxpass' and t.lemma_ == 'be']


def late_condition(en):
    return [f'{t.text} … after “{t.head.head.text}”' for t in doc(en)
            if t.dep_ == 'mark' and t.lower_ in COND and t.head.dep_ == 'advcl' and t.head.head.i < t.i and t.i > 0]


def clauses(en):
    d = doc(en)
    nested = []
    for t in d:
        if _subclause(t):
            a = t.head
            while a.dep_ != 'ROOT' and a.head is not a:
                if _subclause(a):
                    nested.append(f'{t.text} in {a.text}')
                    break
                a = a.head
    sentential = re.findall(r',\s+which\s+(lets|makes|means|allows|enables|gives|keeps|set|sets|show|shows|leads|causes)\b', en)
    return len(_finite(d)), nested, sentential


def participle(en):
    d, out = doc(en), []
    for t in d:
        if t.tag_ in ('VBG', 'VBN') and t.dep_ in ('advcl', 'acl', 'conj') and t.i > 0 and d[t.i - 1].text == ',' or \
           t.tag_ in ('VBG', 'VBN') and t.dep_ in ('advcl', 'acl') and t.i > 1 and d[t.i - 1].lower_ in ('thereby', 'thus') and d[t.i - 2].text == ',':
            if t.lower_ in ('including', 'according', 'following', 'given', 'compared'):
                continue
            k = t.i - 1 if d[t.i - 1].text == ',' else t.i - 2
            if all(x.pos_ in ('ADV', 'CCONJ', 'SCONJ') for x in d[:k]):   # "Therefore, conditioning ...": a gerund subject after an opening connective
                continue
            out.append(', ' + t.text)
    out += [m.group(0) for m in re.finditer(r',\s+(possible|available|necessary|visible)\s+(because|since|when|if)\b', en)]
    out += [m.group(0)[:-1] for m in re.finditer(r',\s+(?!compared\b|according\b)\w+ed\s+(?:to|as|by|from|with|into|in|for|over)\b[^,;]*,', en)
            if not any(m.group(0) in x for x in out)]
    return list(dict.fromkeys(out))


def tail(en):
    s = re.sub(r'\([^()]*\)', '', en).rstrip()
    m = re.search(r',\s+(' + TAIL_PREP + r'\b[^,;:]*)[.?!]$', s)
    if not m or re.match(r'(such as|including|e\.g\.)', m.group(1)):
        return []
    return [m.group(1)]


# ---------------------------------------------------------------------------------------------------- tone and voice
def tone_and_voice(rows, rules, limitation):
    """W7 filler, W8 self-criticism, W9 implied missing experiment, W10 passive, W11 late condition, W12 'we', W14-W16 structure."""
    tone, syn = rules['tone'], rules['syntax']
    w7 = tone['W7']
    subj, verb = _re(w7['meta_subject']), _re(w7['meta_verb'])
    pats = {k: [_re(p) for p in tone[k]['patterns']] for k in ('W7', 'W8', 'W9')}
    pas, adj = _re(tone['W10']['pattern']), set(tone['W10'].get('adjectives', []))
    cond = [_re(p) for p in tone['W11']['patterns']]
    we, allowed = _re(tone['W12']['pattern']), tone['W12']['allowed_starts']
    skip_voice = set(tone['W10']['skip_kinds'])
    skip_syntax = set(syn['skip_kinds'])
    out, seen = [], set()
    for r in rows:
        en = r['en'].strip()
        if not en or en in seen:
            continue
        seen.add(en)
        found = {}
        if r['kind'] not in skip_voice:
            ps = [m.group(0) for m in pas.finditer(en) if m.group(3).lower() not in adj]
            if ps:
                found['W10'] = 'passive: ' + ps[0]
            elif passive(en):
                found['W10'] = 'passive: ' + passive(en)[0]
        if any(p.search(en) for p in cond):
            found['W11'] = 'condition after the action'
        elif r['kind'] not in skip_syntax and late_condition(en):
            found['W11'] = late_condition(en)[0]
        if we.search(en) and not any(en.startswith(s) for s in allowed):
            found['W12'] = '"we" with an item available as subject'
        if r['kind'] not in skip_syntax and not en.startswith('•'):
            n, nested, sw = clauses(en)
            if n >= 3 or nested or sw:
                found['W14'] = f'{n} finite clauses' + (f'; nested: {nested[0]}' if nested else '') + (f'; which refers to a clause: {sw[0]}' if sw else '')
            pa = participle(en)
            if pa:
                found['W15'] = 'participle or verbless clause after a comma: ' + pa[0]
            tl = tail(en)
            if tl:
                found['W16'] = 'qualifier appended after a comma: ' + tl[0][:60]
        in_limit = in_sections(r['section'], limitation)
        for k in pats:
            if k != 'W7' and in_limit:
                continue
            why = [p.pattern for p in pats[k] if p.search(en)]
            if k == 'W7' and subj.search(en) and verb.search(en) and not re.search(r'\d', en) and len(en.split()) <= w7['meta_max_words']:
                why.append('meta sentence (demonstrative subject + meta verb, no number)')
            if why:
                found[k] = why[0]
        for k, why in found.items():
            out.append(dict(rule=k, row=r, matched=why))
    return out


def connectives(rows, rules):
    """W13: consequence connectives per paragraph."""
    w = rules['tone']['W13']
    en_re, pe = _re(w['en']), _re(w['propose_en'])
    out, paras = [], {}
    for r in rows:
        paras.setdefault(r['para'], []).append(r)
    for sents in paras.values():
        seen_words = []
        for i, r in enumerate(sents):
            ce = [(m.group(1) or m.group(2)).lower() for m in en_re.finditer(r['en'])]
            why = []
            if len(ce) > 1:
                why.append('more than one consequence connective in a sentence: ' + ', '.join(ce))
            if ce and pe.search(r['en']):
                why.append('connective in a sentence that proposes the method (the method answers the problem; it does not follow from the sentence before)')
            if i and ce and (en_re.search(sents[i - 1]['en'])):
                why.append('connective in two consecutive sentences')
            for c in set(ce):
                if c in seen_words:
                    why.append(f'“{c}” repeated in the paragraph')
            seen_words += ce
            if why:
                out.append(dict(rule='W13', row=r, matched='; '.join(why)))
    return out


# ---------------------------------------------------------------------------------------------------- glossary and head nouns
def glossary_heads(terms):
    heads, forms = set(), []
    for t in terms:
        for e in [t['en']] + t.get('aliases_en', []) + t.get('allowed', []):
            e = re.sub(r'\([^)]*\)', '', e).strip()
            if not e:
                continue
            forms.append(e.lower())
            d = nlp()(e)
            ns = [x for x in d if x.pos_ in ('NOUN', 'PROPN')]
            if ns:
                heads.add(ns[-1].lemma_.lower())
            root = [x for x in d if x.dep_ == 'ROOT']
            if root and root[0].pos_ in ('NOUN', 'PROPN'):
                heads.add(root[0].lemma_.lower())
    return heads, sorted({f for f in forms if len(f) > 3}, key=len, reverse=True)


def head_nouns(rows, rules, terms):
    """A6: the head noun of every subject and object comes from the glossary, a closed list, or is a name or symbol.
    A7: one thing keeps one head noun (concept rules)."""
    cfg = rules['heads']
    heads, forms = glossary_heads(terms)
    allowed = heads | set(cfg['general_nouns']) | set(cfg['scene_nouns']) | {n.lower() for n in cfg['names']}
    sym = re.compile(cfg['symbol_pattern'])
    concepts = [(c, [_re(p) for p in c['forbidden']]) for c in cfg.get('concepts', [])]
    out, seen = [], set()
    for r in rows:
        en = r['en'].strip()
        if not en or en in seen:
            continue
        seen.add(en)
        if r['kind'] in ('figure', 'table', 'algorithm'):
            for c, pats in concepts:
                out += [dict(rule='A7', row=r, matched=f'“{m.group(0)}” names {c["concept"]}; use “{c["canonical"]}”') for p in pats for m in [p.search(en)] if m]
            continue
        low = en.lower()
        spans = [(m.start(), m.end()) for f in forms for m in re.finditer(r'(?<![a-z])' + re.escape(f) + r's?(?![a-z])', low)]
        for tok in doc(en):
            if tok.dep_ not in HEAD_DEPS or tok.pos_ != 'NOUN':
                continue
            if tok.dep_ == 'nsubj' and any(c.dep_ in ('dobj', 'nsubj') for c in tok.children):
                continue                                   # a verb tagged as a noun
            lem = tok.lemma_.lower()
            if lem in allowed or sym.search(tok.text) or any(a <= tok.idx < b for a, b in spans):
                continue
            out.append(dict(rule='A6', row=r, word=tok.text,
                            matched=f'head noun “{tok.text}” ({tok.dep_}) is not a glossary noun: “{doc(en)[tok.left_edge.i:tok.right_edge.i + 1].text[:70]}”'))
        for c, pats in concepts:
            out += [dict(rule='A7', row=r, matched=f'“{m.group(0)}” names {c["concept"]}; use “{c["canonical"]}”') for p in pats for m in [p.search(en)] if m]
    return out


def glossary_terms(rows, terms):
    """A3: phrases the glossary lists under avoid_en."""
    out = []
    pats = [(t, _re(r'(?<![A-Za-z])' + re.escape(a) + r'(?![A-Za-z])')) for t in terms for a in t.get('avoid_en', [])]
    for r in rows:
        for t, p in pats:
            m = p.search(r['en'])
            if m:
                out.append(dict(rule='A3', row=r, matched=f'“{m.group(0)}” — the glossary term is “{t["en"]}”'))
    return out


# ---------------------------------------------------------------------------------------------------- user-defined pattern rules
def pattern_rules(rows, rule):
    """A rule of ``check.type == "pattern"``: regex over each sentence, optionally limited to sections or kinds."""
    c = rule['check']
    pats = c['pattern'] if isinstance(c['pattern'], list) else [c['pattern']]
    flags = re.I if 'i' in c.get('flags', 'i') else 0
    pats = [re.compile(p, flags) for p in pats]
    only, skip = c.get('sections'), c.get('skip_sections', [])
    skip_kinds = set(c.get('skip_kinds', []))
    out, seen = [], set()
    for r in rows:
        if r['kind'] in skip_kinds:
            continue
        if only and not in_sections(r['section'], only):
            continue
        if skip and in_sections(r['section'], skip):
            continue
        if r['en'] in seen:
            continue
        seen.add(r['en'])
        for p in pats:
            m = p.search(r['en'])
            if m:
                out.append(dict(rule=rule['id'], row=r, matched=c.get('message', '') + (' ' if c.get('message') else '') + f'“{m.group(0)}”'))
                break
    return out


def repeated_sentences(rows, min_words=6):
    """F2: one sentence printed twice."""
    first, out = {}, []
    for r in rows:
        key = re.sub(r'\W+', ' ', r['en'].lower()).strip()
        if len(key.split()) < min_words:
            continue
        if key in first:
            out.append(dict(rule='F2', row=r, matched=f'same sentence as {first[key]["id"]} (line {first[key]["line"]})'))
        else:
            first[key] = r
    return out
