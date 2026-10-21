import json
from pathlib import Path
import unittest

from paperrules import runner
from paperrules.config import load_project, merge
from helpers import BIB, DOC, EXAMPLE, make_project


def rows(*sents, section='Method', kind='paragraph'):
    return [dict(id=f's{i}', para='p', section=section, kind=kind, en=s, file='t', line=1) for i, s in enumerate(sents)]


def rule_ids(findings):
    return {f['rule'] for f in findings}


class SentenceRules(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.proj = load_project(make_project({'main.tex': 'x'}))

    def ids(self, *s, **k):
        return rule_ids(runner.sentence_findings(rows(*s, **k), self.proj, include_disabled=True))

    def test_passive_and_we(self):
        self.assertIn('W10', self.ids('The model is trained on two datasets.'))
        self.assertNotIn('W10', self.ids('Training uses two datasets.'))
        self.assertIn('W12', self.ids('We evaluate all methods.'))
        self.assertNotIn('W12', self.ids('We propose a new method.'))

    def test_condition_after_action(self):
        self.assertIn('W11', self.ids('The update stops if the weight is zero.'))
        self.assertNotIn('W11', self.ids('If the weight is zero, the update stops.'))

    def test_limitations_only_in_discussion(self):
        s = 'The method cannot handle large shifts.'
        self.assertIn('W8', self.ids(s, section='Method'))
        self.assertNotIn('W8', self.ids(s, section='Discussion'))

    def test_captions_exempt_from_voice(self):
        self.assertNotIn('W10', self.ids('Results are shown for two datasets.', kind='figure'))

    def test_connectives_paragraph(self):
        two = ['The data are small.', 'Therefore, the model is simple.', 'Thus, it trains fast.']
        self.assertIn('W13', self.ids(*two))

    def test_register_tests_pass(self):
        n, problems = runner.test_rules(self.proj)
        self.assertGreater(n, 30)
        self.assertEqual(problems, [])
        self.assertEqual(runner.tree_problems(self.proj), [])


class DocumentRules(unittest.TestCase):
    def run_doc(self, doc=DOC, bib=BIB, **kw):
        d = make_project({'main.tex': doc, 'refs.bib': bib}, **kw)
        proj = load_project(d)
        return runner.run(proj)

    def finds(self, res, rid):
        return [f for f in res['findings'] if f['rule'] == rid]

    def test_missing_cite_key_and_unused_entry(self):
        res = self.run_doc()
        self.assertEqual([f['key'] for f in self.finds(res, 'B1')], ['b'])
        self.assertEqual([f['key'] for f in self.finds(res, 'B8')], ['c'])
        by = {r['id']: r for r in res['rules']}
        self.assertEqual(by['B1']['status'], 'fail')            # severity error
        self.assertEqual(by['B8']['status'], 'warn')

    def test_incomplete_entry(self):
        res = self.run_doc()
        self.assertEqual([f['key'] for f in self.finds(res, 'B7')], ['c'])   # inproceedings without booktitle

    def test_unknown_label(self):
        res = self.run_doc(doc=DOC.replace('\\ref{tab:two}', '\\ref{tab:nope}'))
        self.assertEqual([f['key'] for f in self.finds(res, 'B2')], ['tab:nope'])

    def test_float_order(self):
        res = self.run_doc()
        self.assertEqual(self.finds(res, 'T2'), [])             # both floats follow their first citation
        early = DOC.replace('Fusion \\cite{a,b} is hard.', '\\begin{figure}\\caption{Early.}\\label{fig:early}\\end{figure}\nFusion \\cite{a,b} is hard. See Fig.~\\ref{fig:early}.')
        res = self.run_doc(doc=early)
        self.assertEqual([f['key'] for f in self.finds(res, 'T2')], ['fig:early'])
        swapped = DOC.replace('See Fig.~\\ref{fig:one} and Table~\\ref{tab:two}.', 'See Table~\\ref{tab:two}.').replace('The model is trained', 'See Fig.~\\ref{fig:one}. The model is trained')
        self.assertEqual(self.finds(self.run_doc(doc=swapped), 'T1'), [])  # different float types are numbered separately

    def test_exception_accepts_finding(self):
        res = self.run_doc(exceptions=[{'rule': 'B8', 'key': 'c', 'status': 'accepted', 'reason': 'kept for the camera-ready'}])
        f = self.finds(res, 'B8')[0]
        self.assertEqual((f['status'], f['reason']), ('accepted', 'kept for the camera-ready'))
        self.assertEqual({r['id']: r for r in res['rules']}['B8']['status'], 'pass')

    def test_failing_stage_marks_lower_stages_provisional(self):
        res = self.run_doc()
        stages = {s['id']: s for s in res['stages']}
        self.assertEqual(stages['S1']['status'], 'fail')
        self.assertEqual(stages['S2']['gate'], 'provisional')
        self.assertEqual(res['first_failing']['en'], stages['S1']['name']['en'])


class NewDocumentRules(unittest.TestCase):
    """Algorithm floats (T1/T2), W20 abstract structure and T10 table order (0.2.0)."""

    def run_doc(self, doc, local=None):
        return runner.run(load_project(make_project({'main.tex': doc}, local=local)))

    def finds(self, res, rid):
        return [f for f in res['findings'] if f['rule'] == rid]

    ALG = (r"""\begin{document}
Algorithm~\ref{alg:main} gives the steps.
\begin{algorithm}
\caption{Inference.}\label{alg:main}
\begin{algorithmic}[1]
\REQUIRE Two images.
\ENSURE The fused image.
\STATE Fuse.
\end{algorithmic}
\end{algorithm}
\end{document}""")

    def test_algorithm_float_is_numbered_and_cited(self):
        from paperrules import texread
        d = make_project({'main.tex': self.ALG})
        p = texread.read(d / 'main.tex')
        self.assertEqual([(f['env'], f['number'], f['label']) for f in p.floats], [('algorithm', 1, 'alg:main')])
        self.assertEqual(self.finds(self.run_doc(self.ALG), 'T2'), [])
        early = self.ALG.replace('Algorithm~\\ref{alg:main} gives the steps.\n', '').replace('\\end{algorithm}\n', '\\end{algorithm}\nAlgorithm~\\ref{alg:main} gives the steps.\n')
        self.assertEqual([f['key'] for f in self.finds(self.run_doc(early), 'T2')], ['alg:main'])

    def test_abstract_structure(self):
        good = ('\\begin{document}\\begin{abstract}Scan models miss scale. We propose StateNet, which evolves one state. '
                'First, an injector maps the inputs. Second, a controller writes the state. StateNet provides a compact formulation. '
                'Results improve.\\end{abstract}Text.\\end{document}')
        on = {'enable': ['W20']}
        self.assertEqual(self.finds(self.run_doc(good, on), 'W20'), [])
        bad = good.replace('Second, a controller', 'Third, a controller').replace('StateNet provides a compact formulation. ', '')
        self.assertEqual(len(self.finds(self.run_doc(bad, on), 'W20')), 2)
        self.assertEqual(self.finds(self.run_doc(bad), 'W20'), [])          # opt-in: off by default

    def test_table_order(self):
        doc = (r"""\begin{document}
Table~\ref{tab:q} compares the methods.
\begin{table}\caption{Quality.}\label{tab:q}
\begin{tabular}{lr}\toprule Method & SCD\\ \midrule
\textbf{Ours} & 1.8\\
Base & 1.6\\ \bottomrule\end{tabular}
\end{table}
\end{document}""")
        on = {'enable': ['T10'], 'document': {'T10': {'method': 'Ours'}}}
        self.assertEqual([f['key'] for f in self.finds(self.run_doc(doc, on), 'T10')], ['tab:q'])
        last = doc.replace('\\textbf{Ours} & 1.8\\\\\nBase & 1.6\\\\', 'Base & 1.6\\\\\n\\midrule \\textbf{Ours} & 1.8\\\\')
        self.assertEqual(self.finds(self.run_doc(last, on), 'T10'), [])


class LocalOverrides(unittest.TestCase):
    def test_merge_add_remove(self):
        base = {'a': [1, 2], 'b': {'x': 1}, 'c': 5}
        out = merge(base, {'a_add': [3], 'a_remove': [1], 'b_add': {'y': 2}, 'c': 6})
        self.assertEqual(out, {'a': [2, 3], 'b': {'x': 1, 'y': 2}, 'c': 6})
        self.assertEqual(base['a'], [1, 2])

    def test_disable_enable_severity_and_new_rule(self):
        local = {'disable': ['W12'], 'enable': ['T5'], 'severity': {'W6': 'error'},
                 'rules_add': [{'id': 'U9', 'stage': 'S4', 'node': 'wording', 'scope': 'sentence', 'method': 'auto', 'severity': 'warn',
                                'statement': {'en': 'no very', 'zh': '不用very'}, 'why': {'en': '', 'zh': ''},
                                'check': {'type': 'pattern', 'pattern': ['\\bvery\\b'], 'message': 'filler:'},
                                'tests': {'flag': ['It is very good.'], 'pass': ['It is good.']}}]}
        d = make_project({'main.tex': '\\begin{document}\nWe test it. It is very good.\n\\end{document}'}, local=local)
        proj = load_project(d)
        self.assertFalse(proj.enabled(proj.rule('W12')))
        self.assertTrue(proj.enabled(proj.rule('T5')))
        self.assertEqual(proj.rule('W6')['severity'], 'error')
        res = runner.run(proj)
        self.assertEqual([f['rule'] for f in res['findings'] if f['rule'] == 'U9'], ['U9'])
        self.assertEqual([f for f in res['findings'] if f['rule'] == 'W12'], [])
        self.assertEqual(res['tests']['problems'], [])

    def test_broken_custom_test_is_reported(self):
        local = {'rules_add': [{'id': 'U8', 'stage': 'S4', 'node': 'wording', 'scope': 'sentence', 'method': 'auto', 'severity': 'warn',
                                'statement': {'en': 'x', 'zh': 'x'}, 'why': {'en': '', 'zh': ''},
                                'check': {'type': 'pattern', 'pattern': ['\\bvery\\b']},
                                'tests': {'flag': ['It is good.'], 'pass': []}}]}
        proj = load_project(make_project({'main.tex': '\\begin{document}\nHello there.\n\\end{document}'}, local=local))
        res = runner.run(proj)
        self.assertEqual({r['id']: r for r in res['rules']}['R1']['status'], 'fail')

    def test_glossary_rules_skip_without_glossary_and_run_with(self):
        doc = '\\begin{document}\nThe fusion result looks good.\n\\end{document}'
        res = runner.run(load_project(make_project({'main.tex': doc})))
        self.assertEqual({r['id']: r for r in res['rules']}['A3']['status'], 'skip')
        gl = [{'id': 'C1', 'en': 'fused image', 'avoid_en': ['fusion result']}]
        res = runner.run(load_project(make_project({'main.tex': doc}, glossary=gl)))
        self.assertEqual([f['rule'] for f in res['findings'] if f['rule'] == 'A3'], ['A3'])


class ExampleProject(unittest.TestCase):
    def test_example_reads_and_core_numbers_are_stable(self):
        res = runner.run(load_project(EXAMPLE))
        self.assertEqual(res['paper']['sentences'], 199)
        self.assertEqual((res['paper']['figures'], res['paper']['tables']), (7, 4))
        by = {r['id']: r for r in res['rules']}
        self.assertEqual(by['B1']['status'], 'pass')
        self.assertEqual(by['B2']['status'], 'pass')
        self.assertEqual(by['R0']['status'], 'pass')
        self.assertEqual(by['R1']['status'], 'pass')
        self.assertEqual(by['A3']['accepted'], 1)


if __name__ == '__main__':
    unittest.main()


class ExtraPacks(unittest.TestCase):
    def test_project_pack_adds_rules(self):
        reg = {'rules': [{'id': 'P1', 'stage': 'S4', 'node': 'tone', 'scope': 'sentence', 'method': 'auto', 'severity': 'warn',
                          'statement': {'en': 'no "obviously"', 'zh': '不用 obviously'}, 'why': {'en': '', 'zh': ''},
                          'check': {'type': 'pattern', 'pattern': ['\\bobviously\\b']}, 'tests': {'flag': ['It is obviously true.'], 'pass': ['It is true.']}}]}
        d = make_project({'main.tex': '\\begin{document}\nIt is obviously true.\n\\end{document}', 'mypack/register.json': json.dumps(reg)},
                         settings={'packs': ['default', 'mypack']})
        proj = load_project(d)
        self.assertIsNotNone(proj.rule('W14'))                 # the default rules are still there
        res = runner.run(proj)
        self.assertEqual([f['rule'] for f in res['findings'] if f['rule'] == 'P1'], ['P1'])
        self.assertEqual(res['tests']['problems'], [])


SERIF = Path('/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf')


@unittest.skipUnless(__import__('paperrules.rules_figure', fromlist=['x']).available(), 'PyMuPDF not installed')
class FigureRules(unittest.TestCase):
    """G1–G4 measure the included figure files at their printed size (0.3.0)."""

    DOC = ('\\documentclass[times]{elsarticle}\n\\begin{document}\nFig.~\\ref{fig:a} shows it.\n'
           '\\begin{figure}\\includegraphics[width=\\columnwidth]{%s}\\caption{A.}\\label{fig:a}\\end{figure}\n\\end{document}')

    def make_fig(self, d, name, width_bp, size, line, fontfile=None):
        import fitz
        doc = fitz.open()
        pg = doc.new_page(width=width_bp, height=width_bp / 2)
        kw = dict(fontname='F0', fontfile=str(fontfile)) if fontfile else dict(fontname='helv')
        pg.insert_text((10, 30), 'Label text', fontsize=size, **kw)
        pg.draw_line((10, 50), (100, 50), width=line)
        doc.save(str(d / name))

    def run_fig(self, width_bp, size, line, fontfile=None):
        d = make_project({'main.tex': self.DOC % 'fig.pdf'})
        self.make_fig(d, 'fig.pdf', width_bp, size, line, fontfile)
        res = runner.run(load_project(d))
        return {f['rule'] for f in res['findings'] if f['rule'].startswith('G')}, res

    def test_bad_figure(self):
        ids, _ = self.run_fig(252, 5, 0.2)                      # Helvetica, 5 pt, 0.2 pt line, not embedded
        self.assertTrue({'G1', 'G2', 'G3', 'G4'} <= ids, ids)

    def test_shrunk_figure_text(self):
        ids, _ = self.run_fig(504, 9, 1.0)                      # 9 pt text in a 504 bp drawing printed 252 pt wide
        self.assertIn('G3', ids)

    @unittest.skipUnless(SERIF.exists(), 'Liberation Serif not installed')
    def test_good_figure(self):
        ids, _ = self.run_fig(252, 9, 1.0, SERIF)
        self.assertEqual(ids, set())

    def test_missing_file(self):
        d = make_project({'main.tex': self.DOC % 'nofile'})
        res = runner.run(load_project(d))
        self.assertEqual([f['rule'] for f in res['findings'] if f['rule'].startswith('G')], ['G1'])
