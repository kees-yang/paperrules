"""Read a LaTeX paper into sentences and structure.

``read(main_tex)`` returns a ``Paper``:

    rows       one dict per printed sentence: id, para, section, kind (abstract | paragraph | item | figure | table),
               en (plain text), file, line
    floats     figures and tables in source order: env, number, label, caption, file, line
    labels     {label: number} for every \\label that can be numbered
    refs       every \\ref-like use: label, file, line, offset
    cites      citation keys in order of first use
    abstract   plain abstract text; keywords: list (empty when the paper has none)

The reader is deliberately simple. It expands \\input and \\include, drops comments and macro definitions, removes
display mathematics, turns inline mathematics into the symbol X, citations into [n] by order of first use and
cross-references into numbers, and keeps the text of ordinary text commands. Unknown commands with one argument keep
the argument. Rows are numbered in reading order: abstract, body, captions.
"""
import bisect
import re
from dataclasses import dataclass, field
from pathlib import Path

FLOAT_RE = re.compile(r'\\begin\{(figure\*?|table\*?)\}.*?\\end\{\1\}', re.S)
DISPLAY_ENVS = ('equation', 'align', 'gather', 'multline', 'eqnarray', 'displaymath', 'flalign')
CITE_RE = re.compile(r'\\(?:cite[a-zA-Z]*|nocite)\*?(?:\[[^\]]*\]){0,2}\{([^}]*)\}')
REF_RE = re.compile(r'\\(?:eqref|ref|autoref|cref|Cref)\{([^}]*)\}')
HEADING_RE = re.compile(r'\\(section|subsection|subsubsection)(\*?)\s*(?:\[[^\]]*\])?\s*\{')
LIST_ENV_RE = re.compile(r'\\(?:begin|end)\{(?:itemize|enumerate|description)\}(?:\[[^\]]*\])?')
DEF_RE = re.compile(r'\\(?:re)?newcommand\*?\s*\{?\\[a-zA-Z]+\}?(?:\s*\[\d\])*(?:\s*\[[^\]]*\])?\s*\{|\\(?:def|DeclareMathOperator\*?|providecommand)\s*\{?\\[a-zA-Z]+\}?[^{]*\{')
ABBREV = ['e.g.', 'i.e.', 'et al.', 'Fig.', 'Figs.', 'Eq.', 'Eqs.', 'Eqn.', 'Eqns.', 'Sec.', 'Secs.', 'Tab.', 'Tabs.', 'vs.', 'cf.',
          'resp.', 'approx.', 'No.', 'Dr.', 'Prof.', 'w.r.t.', 'a.k.a.']


@dataclass
class Paper:
    rows: list = field(default_factory=list)
    floats: list = field(default_factory=list)
    labels: dict = field(default_factory=dict)
    cites: list = field(default_factory=list)
    cite_locs: dict = field(default_factory=dict)
    refs: list = field(default_factory=list)
    abstract: str = ''
    abstract_loc: tuple = ('', 0)
    keywords: list = field(default_factory=list)
    headings: list = field(default_factory=list)
    bib_files: list = field(default_factory=list)
    main: str = ''


def braced(s, start):
    """(content, index after the closing brace) of the balanced {...} that opens at s[start]."""
    depth, k = 0, start
    while k < len(s):
        c = s[k]
        if c == '\\':
            k += 2
            continue
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                return s[start + 1:k], k + 1
        k += 1
    raise ValueError('unbalanced braces')


def strip_comment(line):
    k = 0
    while k < len(line):
        if line[k] == '\\':
            k += 2
            continue
        if line[k] == '%':
            return line[:k]
        k += 1
    return line


def expand(path, base=None, seen=frozenset()):
    """Lines of a file with \\input / \\include expanded: (display file, line number, text without comment)."""
    path = Path(path)
    base = base or path.parent
    if path in seen:
        return []
    out = []
    for i, raw in enumerate(path.read_text(encoding='utf-8', errors='replace').splitlines(), 1):
        line = strip_comment(raw)
        m = re.fullmatch(r'\s*\\(?:input|include)\{([^}]+)\}\s*', line)
        if m:
            f = base / m.group(1)
            if not f.suffix:
                f = f.with_suffix('.tex')
            if f.exists():
                out.extend(expand(f, base, seen | {path}))
                continue
        try:
            shown = path.relative_to(base).as_posix()
        except ValueError:
            shown = path.name
        out.append((shown, i, line))
    return out


class Located:
    """Text with a map from offsets back to (file, line)."""

    def __init__(self, lines):
        self.lines = lines
        self.text = '\n'.join(l[2] for l in lines)
        self.starts, pos = [], 0
        for l in lines:
            self.starts.append(pos)
            pos += len(l[2]) + 1

    def at(self, offset):
        k = max(0, bisect.bisect_right(self.starts, offset) - 1)
        return self.lines[k][0], self.lines[k][1]


def blank(s):
    """Same length, newlines kept: offsets stay valid."""
    return re.sub(r'[^\n]', ' ', s)


def split_sentences(text):
    t = text
    for a in ABBREV:
        t = t.replace(a, a.replace('.', '\x00'))
    parts = re.split(r'(?<=[.!?])["”’)\]]*\s+(?=["“‘(\[]*[A-Z0-9])', t)
    return [p.replace('\x00', '.').strip() for p in parts if p.strip()]


def unwrap(text, names):
    """Replace \\name{arg} by arg (balanced braces) for the given command names."""
    rx = re.compile(r'\\(?:' + names + r')\*?\s*(?:\[[^\]]*\])?\s*\{')
    while True:
        m = rx.search(text)
        if not m:
            return text
        try:
            arg, end = braced(text, m.end() - 1)
        except ValueError:
            return text[:m.start()] + text[m.end():]
        text = text[:m.start()] + arg + text[end:]


def drop_commands(text, names, nargs=1):
    """Remove \\name{...}{...} including the arguments."""
    rx = re.compile(r'\\(?:' + names + r')\*?\s*(?:\[[^\]]*\])?\s*\{')
    while True:
        m = rx.search(text)
        if not m:
            return text
        end = m.end() - 1
        try:
            for i in range(nargs):
                if i:
                    while end < len(text) and text[end] in ' \n':
                        end += 1
                _, end = braced(text, end)
        except ValueError:
            return text[:m.start()] + text[m.end():]
        text = text[:m.start()] + text[end:]


def plain(tex, cite_no, ref_no):
    """Plain text of a LaTeX fragment (see the module docstring)."""
    t = tex
    t = re.sub(r'\\begin\{(' + '|'.join(DISPLAY_ENVS) + r')\*?\}.*?\\end\{\1\*?\}', ' ', t, flags=re.S)
    t = re.sub(r'\\\[.*?\\\]|\$\$.*?\$\$', ' ', t, flags=re.S)
    t = re.sub(r'(?<!\\)\$[^$]*(?<!\\)\$|\\\(.*?\\\)', 'X', t, flags=re.S)
    t = CITE_RE.sub(lambda m: '[' + ', '.join(str(cite_no.get(k.strip(), '?')) for k in m.group(1).split(',') if k.strip()) + ']', t)
    t = REF_RE.sub(lambda m: ', '.join(str(ref_no.get(k.strip(), '?')) for k in m.group(1).split(',')), t)
    t = drop_commands(t, 'label|vspace|hspace|vskip|hskip|setlength|footnote|footnotemark|thanks|index|paragraph|subparagraph')
    t = re.sub(r'\\(?:textcolor|colorbox)\s*\{[^}]*\}', '', t)
    t = unwrap(t, 'textit|textbf|emph|textrm|textsf|texttt|textsc|textsl|text|mbox|mathrm|underline|uline|textnormal')
    t = re.sub(r'\{\\(?:em|it|bf|sc|sl|rm|sf|tt|small|large|footnotesize)\s+([^{}]*)\}', r'\1', t)
    t = re.sub(r'\\begin\{[^}]*\}(?:\[[^\]]*\])?|\\end\{[^}]*\}', ' ', t)
    t = re.sub(r'\\\\(?:\[[^\]]*\])?', ' ', t)
    t = re.sub(r'\\(?:item|centering|noindent|newline|clearpage|newpage|medskip|smallskip|bigskip|par|maketitle)\b', ' ', t)
    t = t.replace('``', '“').replace("''", '”').replace('---', '—').replace('--', '–')
    t = re.sub(r'\\([&%$#_{}])', r'\1', t)
    t = re.sub(r'\\[,;:!> ]', ' ', t)
    t = t.replace('~', ' ')
    t = re.sub(r'\\[a-zA-Z]+\*?', ' ', t)          # remaining command names; their arguments stay as text
    t = re.sub(r'[{}]', '', t)
    return re.sub(r'\s+', ' ', t).strip()


def number_floats(body):
    floats, counts = [], {'figure': 0, 'table': 0}
    for m in FLOAT_RE.finditer(body):
        env = m.group(1).rstrip('*')
        counts[env] += 1
        tex = m.group(0)
        cap, cm = '', re.search(r'\\caption(?![a-zA-Z])\*?\s*(?:\[[^\]]*\])?\s*\{', tex)
        if cm:
            try:
                cap = braced(tex, cm.end() - 1)[0]
            except ValueError:
                pass
        label = re.search(r'\\label\{([^}]*)\}', tex)
        floats.append(dict(env=env, number=counts[env], label=label.group(1) if label else None, caption=cap,
                           offset=m.start(), end=m.end()))
    return floats


def read(main_tex):
    main_tex = Path(main_tex)
    full = Located(expand(main_tex))
    text = full.text
    p = Paper(main=str(main_tex))
    b, e = re.search(r'\\begin\{document\}', text), re.search(r'\\end\{document\}', text)
    start = b.end() if b else 0
    end = e.start() if e else len(text)
    stop = re.search(r'\\(?:bibliography\{|printbibliography|begin\{thebibliography\})', text[start:end])
    if stop:
        end = start + stop.start()
    p.bib_files = [x.strip() for m in re.finditer(r'\\bibliography\{([^}]*)\}', text) for x in m.group(1).split(',')]
    body = text[start:end]

    def where(off):
        return full.at(start + off)

    cite_no = {}
    for m in CITE_RE.finditer(body):
        for k in m.group(1).split(','):
            if k.strip() and k.strip() not in cite_no:
                cite_no[k.strip()] = len(cite_no) + 1
                p.cite_locs[k.strip()] = where(m.start())
    p.cites = list(cite_no)

    floats = number_floats(body)
    for f in floats:
        f['file'], f['line'] = where(f['offset'])
    p.floats = floats
    labels = {f['label']: f['number'] for f in floats if f['label']}
    n = 0
    for m in re.finditer(r'\\begin\{(?:equation|align|gather|multline|eqnarray)\*?\}(.*?)\\end\{(?:equation|align|gather|multline|eqnarray)\*?\}', body, re.S):
        for lm in re.finditer(r'\\label\{([^}]*)\}', m.group(1)):
            n += 1
            labels[lm.group(1)] = n
    sec = [0, 0, 0]
    heads = []                                   # (start, end, level, title)
    for hm in HEADING_RE.finditer(body):
        try:
            title, hend = braced(body, hm.end() - 1)
        except ValueError:
            continue
        lvl = ('section', 'subsection', 'subsubsection').index(hm.group(1))
        num = ''
        if not hm.group(2):
            sec[lvl] += 1
            for j in range(lvl + 1, 3):
                sec[j] = 0
            num = '.'.join(str(x) for x in sec[:lvl + 1])
        heads.append((hm.start(), hend, lvl, title))
        lm = re.match(r'\s*\\label\{([^}]*)\}', body[hend:])
        if lm and num:
            labels[lm.group(1)] = num
        p.headings.append(dict(level=lvl, title=title, number=num, file=where(hm.start())[0], line=where(hm.start())[1]))
    p.labels = labels
    for m in REF_RE.finditer(body):
        for k in m.group(1).split(','):
            f, ln = where(m.start())
            p.refs.append(dict(label=k.strip(), offset=m.start(), file=f, line=ln))

    # abstract and keywords
    am = re.search(r'\\begin\{abstract\}(.*?)\\end\{abstract\}', body, re.S)
    if am:
        p.abstract = plain(am.group(1), cite_no, labels)
        p.abstract_loc = where(am.start())
    km = re.search(r'\\begin\{(?:keyword|IEEEkeywords|keywords)\}(.*?)\\end\{(?:keyword|IEEEkeywords|keywords)\}', body, re.S) \
        or re.search(r'\\keywords\{([^}]*)\}', body)
    if km:
        p.keywords = [x.strip() for x in re.split(r'[;,]|\\sep|—|·', plain(km.group(1), cite_no, labels)) if x.strip()]

    # work text: floats, abstract, keywords, headings and macro definitions blanked (same length)
    work = body
    cuts = [(f['offset'], f['end']) for f in floats]
    if am:
        cuts.append((am.start(), am.end()))
    if km:
        cuts.append((km.start(), km.end()))
    for dm in DEF_RE.finditer(body):
        try:
            cuts.append((dm.start(), braced(body, dm.end() - 1)[1]))
        except ValueError:
            pass
    for a, bnd in sorted(cuts, reverse=True):
        work = work[:a] + blank(work[a:bnd]) + work[bnd:]
    for a, bnd, _, _ in heads:
        work = work[:a] + '\n\n' + blank(work[a + 2:bnd]) + work[bnd:]
    work = LIST_ENV_RE.sub(lambda m: '\n\n' + blank(m.group(0)[2:]), work)
    head_starts = [h[0] for h in heads]

    rows, n_row, n_para = [], 0, 0

    def emit(txt, section, kind, loc):
        nonlocal n_row, n_para
        n_para += 1
        for s in split_sentences(txt):
            if len(re.findall(r'[A-Za-z]{2,}', s)) < 2:
                continue
            n_row += 1
            rows.append(dict(id=f'S{n_row:03d}', para=f'P{n_para:03d}', section=section, kind=kind, en=s, file=loc[0], line=loc[1]))

    if p.abstract:
        emit(p.abstract, 'Abstract', 'abstract', p.abstract_loc)
    for pm in re.finditer(r'(?:[^\n]|\n(?!\s*\n))+', work):
        if not pm.group(0).strip():
            continue
        k = bisect.bisect_right(head_starts, pm.start()) - 1
        section = plain(heads[k][3], cite_no, labels) if k >= 0 else ''
        pieces = [(pm.start(), pm.group(0))]
        items = list(re.finditer(r'\\item\b', pm.group(0)))
        if items:
            idx = [0] + [m.end() for m in items]
            pieces = [(pm.start() + a, pm.group(0)[a:(items[i].start() if i < len(items) else len(pm.group(0)))])
                      for i, a in enumerate(idx)]
        for i, (off, seg) in enumerate(pieces):
            if not seg.strip():
                continue
            txt = plain(seg, cite_no, labels)
            if not txt or re.fullmatch(r'X?\.?', txt):
                continue
            emit(txt, section, 'item' if items and i > 0 else 'paragraph', where(off + len(seg) - len(seg.lstrip())))
    for f in floats:
        f['caption_plain'] = plain(f['caption'], cite_no, labels)
        if f['caption_plain']:
            emit(f['caption_plain'], '(caption)', f['env'], (f['file'], f['line']))
    p.rows = rows
    return p
