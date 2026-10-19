"""Project configuration, rule packs and local overrides.

A *pack* is a directory of JSON files under ``paperrules/packs/<name>/``:

    register.json   every rule: id, stage, scope, method, severity, statement, check, tests
    tree.json       the stages (and their nodes) the rules are arranged in
    tone.json       patterns of the tone and voice rules (W7-W13)
    syntax.json     settings of the sentence-structure rules (W10b, W11b, W14-W16)
    heads.json      closed noun lists and concept rules of the head-noun rules (A6, A7)
    document.json   settings of the document rules (abstract, keywords, floats, bibliography)

A *project* is a ``paperrules.json`` next to the paper. It names the main LaTeX file and may add a local override file
(``rules.local.json``) that is merged onto the packs:

    key           replace the value (dicts are merged recursively)
    key_add       extend a list or update a dict
    key_remove    delete list items or dict keys
    disable       list of rule ids to switch off
    enable        list of rule ids to switch on that the pack leaves off
    severity      {rule id: "error" | "warn"}
    rules_add     new rules (see docs/customizing-rules.md)
"""
import copy
import json
from pathlib import Path

PACK_DIR = Path(__file__).resolve().parent / 'packs'
PACK_FILES = ('register', 'tree', 'tone', 'syntax', 'heads', 'document')
PROJECT_FILE = 'paperrules.json'


def load_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def dump_json(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=1) + '\n', encoding='utf-8')


def merge(base, patch):
    """Merge ``patch`` onto ``base`` with the ``_add`` / ``_remove`` convention (returns a new object)."""
    out = copy.deepcopy(base)
    for key, val in patch.items():
        if key.endswith('_add'):
            name, cur = key[:-4], out.get(key[:-4])
            if isinstance(cur, list):
                out[name] = cur + [x for x in val if x not in cur]
            elif isinstance(cur, dict):
                out[name] = merge(cur, val)
            else:
                out[name] = copy.deepcopy(val)
        elif key.endswith('_remove'):
            name, cur = key[:-7], out.get(key[:-7])
            if isinstance(cur, list):
                out[name] = [x for x in cur if x not in val]
            elif isinstance(cur, dict):
                out[name] = {k: v for k, v in cur.items() if k not in val}
        elif isinstance(val, dict) and isinstance(out.get(key), dict):
            out[key] = merge(out[key], val)
        else:
            out[key] = copy.deepcopy(val)
    return out


def load_pack(name, root=None):
    """A pack directory: next to the project (``root/name``) if it exists there, else a built-in pack."""
    d = Path(root) / name if root and (Path(root) / name).is_dir() else PACK_DIR / name
    if not d.is_dir():
        raise SystemExit(f'unknown rule pack "{name}" (looked in {root or "."} and {PACK_DIR})')
    return {f: load_json(d / f'{f}.json') for f in PACK_FILES if (d / f'{f}.json').exists()}


def combine(rules, pack):
    """Add a further pack: its rules are appended to the register, every other file is merged (a tree.json replaces the stages)."""
    out = merge(rules, {k: v for k, v in pack.items() if k != 'register'})
    if 'register' in pack:
        known = {r['id'] for r in out['register']['rules']}
        for r in pack['register']['rules']:
            if r['id'] in known:
                raise SystemExit(f'pack adds rule {r["id"]} which already exists; use rules_edit in rules.local.json to change a rule')
            out['register']['rules'].append(r)
    return out


class Project:
    """Resolved settings of one paper: files, merged rules, glossary and exceptions."""

    def __init__(self, root, settings, rules, glossary, exceptions):
        self.root = Path(root)
        self.settings = settings
        self.rules = rules              # merged pack + local overrides
        self.glossary = glossary        # list of terms (may be empty)
        self.exceptions = exceptions    # list of dicts
        self.main_tex = self.root / settings['main_tex']
        bib = settings.get('bib')
        self.bib = (self.root / bib) if bib else None
        self.limitation_sections = settings.get('limitation_sections', ['limitation', 'discussion'])
        self.out_dir = self.root / settings.get('output', 'out')

    @property
    def register(self):
        return self.rules['register']

    def rule(self, rid):
        return next((r for r in self.register['rules'] if r['id'] == rid), None)

    def enabled(self, rule):
        return rule.get('enabled', True)


def resolve_project_file(arg):
    p = Path(arg)
    if p.is_dir():
        p = p / PROJECT_FILE
    if not p.exists():
        raise SystemExit(f'no {PROJECT_FILE} at {p}; create one with "paperrules init <dir>"')
    return p


def load_project(arg='.'):
    pf = resolve_project_file(arg)
    root = pf.parent
    s = load_json(pf)
    if 'main_tex' not in s:
        raise SystemExit(f'{pf}: "main_tex" is required')
    rules = None
    for name in s.get('packs', ['default']):
        pack = load_pack(name, root)
        rules = pack if rules is None else combine(rules, pack)
    local = root / s.get('local_rules', 'rules.local.json')
    patch = load_json(local) if local.exists() else {}
    rules = apply_local(rules, patch)
    gl = []
    if s.get('glossary') and (root / s['glossary']).exists():
        gl = load_json(root / s['glossary']).get('terms', [])
    ex_path = root / s.get('exceptions', 'exceptions.json')
    ex = load_json(ex_path).get('exceptions', []) if ex_path.exists() else []
    return Project(root, s, rules, gl, ex)


def apply_local(rules, patch):
    """Apply a local override file to the merged pack."""
    patch = dict(patch)
    disable, enable = set(patch.pop('disable', [])), set(patch.pop('enable', []))
    severity = patch.pop('severity', {})
    rules_add = patch.pop('rules_add', [])
    rules_edit = patch.pop('rules_edit', {})
    patch.pop('note', None)
    rules = merge(rules, patch)
    reg = rules['register']
    known = {r['id'] for r in reg['rules']}
    for r in rules_add:
        if r['id'] in known:
            raise SystemExit(f'rules_add: rule id {r["id"]} already exists (use rules_edit to change a rule)')
        reg['rules'].append(r)
    by_id = {r['id']: r for r in reg['rules']}
    for rid, ed in rules_edit.items():
        if rid not in by_id:
            raise SystemExit(f'rules_edit: unknown rule {rid}')
        by_id[rid].update(merge(by_id[rid], ed))
    for rid in disable | enable | set(severity):
        if rid not in by_id:
            raise SystemExit(f'local rules: unknown rule id {rid}')
    for rid in disable:
        by_id[rid]['enabled'] = False
    for rid in enable:
        by_id[rid]['enabled'] = True
    for rid, sev in severity.items():
        by_id[rid]['severity'] = sev
    return rules
