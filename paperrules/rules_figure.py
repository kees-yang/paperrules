"""Figure rules (G1–G4): read the files that \\includegraphics places in each figure and measure them at their printed size.

G1  print-ready files: every figure file exists, PDF figures embed their fonts and use no Type 3 fonts, raster images have
    at least ``min_dpi`` at the printed width.
G2  figure text uses the body font family (math fonts are always allowed).
G3  figure text is readable at the printed size: the main text size lies in ``main_pt`` and no text is smaller than
    ``min_pt`` (subscripts included).
G4  lines survive printing: no stroke is thinner than ``min_line_pt`` at the printed size (partial: grid lines may be
    thinner on purpose).

The printed size comes from the \\includegraphics options (width, height, scale) and the column and text widths in
document.json ``figures``. PDF figures need PyMuPDF (``pip install pymupdf``); without it the group is skipped.
Settings: document.json ``figures``.
"""
import re
from pathlib import Path

try:
    import fitz  # PyMuPDF
except ImportError:  # pragma: no cover - optional dependency
    fitz = None

UNITS_PT = {'pt': 1.0, 'bp': 72.27 / 72, 'mm': 72.27 / 25.4, 'cm': 72.27 / 2.54, 'in': 72.27, 'pc': 12.0}
INCLUDE_RE = re.compile(r'\\includegraphics\*?\s*(?:\[([^\]]*)\])?\s*\{([^}]*)\}')
MATH_FONT = re.compile(r'CM(?:MI|SY|EX|BSY|MIB)|MSAM|MSBM|Symbol|STIX|Math|txsy|txmi|txex|NewTX(?:MI|SY)|rsfs|eufm|esint|LMMathItalic|Cambria', re.I)
FAMILIES = {
    'times': r'Times|Termes|NimbusRom|NimbusRoman|LiberationSerif|Tinos|TXTT|ntx|newtx|STIXTwoText|TeXGyreTermes|ptmr',
    'cm': r'CMR|CMBX|CMTI|CMSS|CMTT|LMRoman|LMSans|LMMono|SFRM|SFBX|SFTI|SFSS|cmr|lmr',
    'helvetica': r'Helvetica|Arial|NimbusSans|LiberationSans|Arimo|TeXGyreHeros|phvr',
    'libertine': r'Libertine|LinLibertine|Biolinum',
}


def available():
    return fitz is not None


def _body_family(preamble, setting):
    if setting and setting != 'auto':
        return setting
    if re.search(r'\\usepackage(?:\[[^\]]*\])?\{[^}]*\b(?:times|newtxtext|mathptmx|txfonts|newtx|tgtermes|stix2?)\b', preamble) \
            or re.search(r'\\documentclass(?:\[[^\]]*\btimes\b[^\]]*\])?\{IEEEtran\}', preamble) \
            or re.search(r'\\documentclass\[[^\]]*\btimes\b', preamble):
        return 'times'
    if re.search(r'\\documentclass(?:\[[^\]]*\])?\{acmart\}|libertine', preamble):
        return 'libertine'
    if re.search(r'\\usepackage(?:\[[^\]]*\])?\{[^}]*\b(?:helvet|arial|tgheros)\b', preamble):
        return 'helvetica'
    return 'cm'


def _printed_width_pt(opts, natural_w_pt, natural_h_pt, star, cfg):
    """Printed width in TeX pt from the \\includegraphics options; None when it cannot be read."""
    col, text = cfg.get('column_width_pt', 252.0), cfg.get('text_width_pt', 516.0)
    lengths = {'columnwidth': col, 'textwidth': text, 'linewidth': text if star else col, 'hsize': text if star else col}
    kv = dict((k.strip(), v.strip()) for k, _, v in (p.partition('=') for p in (opts or '').split(',')) if k.strip())

    def length(v):
        m = re.fullmatch(r'([\d.]*)\s*\\(columnwidth|textwidth|linewidth|hsize)', v)
        if m:
            return float(m.group(1) or 1) * lengths[m.group(2)]
        m = re.fullmatch(r'([\d.]+)\s*(pt|bp|mm|cm|in|pc)', v)
        return float(m.group(1)) * UNITS_PT[m.group(2)] if m else None
    if 'width' in kv:
        return length(kv['width'])
    if 'height' in kv and natural_h_pt:
        h = length(kv['height'])
        return h * natural_w_pt / natural_h_pt if h else None
    if 'scale' in kv:
        try:
            return float(kv['scale']) * natural_w_pt
        except ValueError:
            return None
    return natural_w_pt


def _resolve(name, roots):
    for r in roots:
        p = r / name
        for cand in ([p] if p.suffix else [p.with_suffix(e) for e in ('.pdf', '.png', '.jpg', '.jpeg', '.eps')]):
            if cand.exists():
                return cand
    return None


def figure_rules(paper, project, cfg):
    """Findings of G1–G4 for every figure of the paper."""
    c = cfg.get('figures', {})
    root = Path(project.main_tex).parent
    pre = Path(project.main_tex).read_text(encoding='utf-8', errors='replace').split('\\begin{document}')[0]
    roots = [root] + [root / d for d in re.findall(r'\{([^{}]+)\}', (re.search(r'\\graphicspath\{((?:\{[^}]*\})+)\}', pre) or [None, ''])[1])]
    fam = _body_family(pre, c.get('body_font', 'auto'))
    fam_re = re.compile(FAMILIES.get(fam, fam), re.I)
    min_pt, (lo, hi), min_line, min_dpi = c.get('min_pt', 6.0), c.get('main_pt', [8.0, 10.0]), c.get('min_line_pt', 0.4), c.get('min_dpi', 300)
    out = []
    for fl in paper.floats:
        if fl['env'] != 'figure':
            continue
        star = '\\begin{figure*}' in fl['tex']
        key = fl['label'] or f'figure {fl["number"]}'

        def add(rule, msg):
            out.append(dict(rule=rule, key=key, file=fl.get('file', ''), line=fl.get('line', 0), matched=f'Fig. {fl["number"]}: {msg}'))
        for m in INCLUDE_RE.finditer(fl['tex']):
            name = m.group(2).strip()
            path = _resolve(name, roots)
            if path is None:
                add('G1', f'figure file “{name}” not found')
                continue
            if path.suffix.lower() in ('.png', '.jpg', '.jpeg'):
                pix = fitz.Pixmap(str(path))
                w_pt = _printed_width_pt(m.group(1), pix.width * 72.27 / 72, pix.height * 72.27 / 72, star, c)
                if w_pt:
                    dpi = pix.width / (w_pt / 72.27)
                    if dpi < min_dpi:
                        add('G1', f'{path.name} prints at {dpi:.0f} dpi (want ≥ {min_dpi}); export it larger or as vector')
                continue
            if path.suffix.lower() != '.pdf':
                continue
            doc = fitz.open(str(path))
            pg = doc[0]
            nat_w, nat_h = pg.rect.width * 72.27 / 72, pg.rect.height * 72.27 / 72
            w_pt = _printed_width_pt(m.group(1), nat_w, nat_h, star, c)
            scale = (w_pt / nat_w) if w_pt else 1.0
            fonts = pg.get_fonts(full=True)
            t3 = sorted({f[3] for f in fonts if f[2] == 'Type3'})
            notemb = sorted({f[3] for f in fonts if f[1] in ('n/a', '') and f[2] != 'Type3'})
            if t3:
                add('G1', f'{path.name} uses Type 3 fonts ({", ".join(t3[:3])}); embed real fonts (avoid bold math and missing glyphs)')
            if notemb:
                add('G1', f'{path.name} does not embed {", ".join(notemb[:3])}')
            nm = lambda s: re.sub(r'^[A-Z]{6}\+', '', s).replace(' ', '').replace('-', '')
            other = sorted({re.sub(r'^[A-Z]{6}\+', '', f[3]) for f in fonts if f[3]
                            and not fam_re.search(nm(f[3])) and not MATH_FONT.search(nm(f[3])) and f[2] != 'Type3'})
            if other:
                add('G2', f'{path.name} uses {", ".join(other[:4])}; the body font is {fam} (document.json figures.body_font)')
            sizes = []
            for b in pg.get_text('dict')['blocks']:
                for ln in b.get('lines', []):
                    for sp in ln['spans']:
                        t = sp['text'].strip()
                        if t:
                            sizes.append((sp['size'] * scale * 72.27 / 72, t))
            if sizes:
                small = sorted(s for s in sizes if s[0] < min_pt)
                chars = sorted((s for s, t in sizes for _ in t))
                main = chars[len(chars) // 2]
                if small:
                    add('G3', f'{path.name}: {len(small)} text span(s) print below {min_pt} pt, smallest {small[0][0]:.1f} pt (“{small[0][1][:20]}”)')
                if not lo <= main <= hi:
                    add('G3', f'{path.name}: main text prints at {main:.1f} pt (want {lo}–{hi} pt)')
            thin = [d['width'] * scale * 72.27 / 72 for d in pg.get_drawings() if d.get('width') and d.get('color') is not None]
            thin = [w for w in thin if 0 < w < min_line]
            if thin:
                add('G4', f'{path.name}: {len(thin)} stroke(s) print below {min_line} pt, thinnest {min(thin):.2f} pt')
    return out
