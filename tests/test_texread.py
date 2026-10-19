import unittest
from paperrules import texread
from helpers import DOC, make_project


class TexReadTest(unittest.TestCase):
    def setUp(self):
        d = make_project({'main.tex': DOC, 'refs.bib': ''})
        self.p = texread.read(d / 'main.tex')
        self.rows = {r['id']: r for r in self.p.rows}

    def texts(self):
        return [r['en'] for r in self.p.rows]

    def test_abstract_first(self):
        self.assertEqual(self.p.rows[0]['kind'], 'abstract')
        self.assertEqual(self.p.rows[0]['section'], 'Abstract')

    def test_citation_numbers_and_refs(self):
        self.assertIn('Fusion [1, 2] is hard.', self.texts())
        self.assertIn('See Fig. 1 and Table 1.', self.texts())
        self.assertEqual(self.p.cites, ['a', 'b'])

    def test_comment_and_math(self):
        t = ' '.join(self.texts())
        self.assertNotIn('comment sentence', t)
        self.assertIn('where X is the input.', t)          # inline math becomes X, display math disappears

    def test_abbreviation_does_not_split(self):
        self.assertIn('The model is trained on pairs, e.g. two images.', self.texts())
        self.assertIn('We then test it, where X is the input.', self.texts())

    def test_items_and_captions(self):
        kinds = {r['en']: r['kind'] for r in self.p.rows}
        self.assertEqual(kinds['First item.'], 'item')
        self.assertEqual(kinds['One caption.'], 'figure')
        self.assertEqual(kinds['Two caption.'], 'table')

    def test_floats_and_labels(self):
        self.assertEqual([(f['env'], f['number'], f['label']) for f in self.p.floats], [('figure', 1, 'fig:one'), ('table', 1, 'tab:two')])
        self.assertEqual(self.p.labels['eq:1'], 1)

    def test_section_title_and_line(self):
        r = next(r for r in self.p.rows if r['en'].startswith('Fusion'))
        self.assertEqual(r['section'], 'Introduction')
        self.assertEqual((r['file'], r['line']), ('main.tex', 7))

    def test_input_expansion(self):
        d = make_project({'main.tex': '\\begin{document}\n\\input{sec/a}\n\\end{document}', 'sec/a.tex': '\\section{A}\nHello world again.\n'})
        p = texread.read(d / 'main.tex')
        self.assertEqual((p.rows[0]['en'], p.rows[0]['file'], p.rows[0]['line']), ('Hello world again.', 'sec/a.tex', 2))


if __name__ == '__main__':
    unittest.main()
