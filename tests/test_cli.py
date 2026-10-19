import io
import json
import unittest
from contextlib import redirect_stdout

from paperrules import cli
from helpers import BIB, DOC, make_project


def run(*argv):
    out = io.StringIO()
    code = 0
    with redirect_stdout(out):
        try:
            cli.main(list(argv))
        except SystemExit as e:
            code = e.code or 0
    return code, out.getvalue()


class CliTest(unittest.TestCase):
    def test_init_check_and_exit_codes(self):
        import tempfile
        from pathlib import Path
        d = Path(tempfile.mkdtemp(prefix='paperrules-cli-'))
        (d / 'main.tex').write_text(DOC)
        (d / 'refs.bib').write_text(BIB)
        code, out = run('init', str(d), '--main', 'main.tex')
        self.assertEqual(code, 0)
        self.assertTrue((d / 'paperrules.json').exists() and (d / 'rules.local.json').exists())
        code, out = run('check', str(d))
        self.assertEqual(code, 1)                      # B1 fails (cited key b is missing)
        self.assertTrue((d / 'out' / 'report.html').exists())
        res = json.loads((d / 'out' / 'report.json').read_text())
        self.assertEqual(res['summary']['fail'], 1)
        code, out = run('check', str(d), '--only', 'W10', '--no-files')
        self.assertEqual(code, 0)

    def test_rules_and_test_commands(self):
        d = make_project({'main.tex': '\\begin{document}\nHello there.\n\\end{document}'})
        code, out = run('rules', 'tree', '--project', str(d))
        self.assertEqual(code, 0)
        self.assertIn('W14', out)
        code, out = run('rules', 'markdown', '--project', str(d))
        self.assertIn('一句一个主要动作', out)
        code, out = run('test', str(d))
        self.assertEqual(code, 0)

    def test_accept_writes_exception(self):
        d = make_project({'main.tex': '\\begin{document}\nWe evaluate it.\n\\end{document}'})
        code, out = run('accept', 'W12', 'We evaluate it.', '--reason', 'authors are the actor', '--project', str(d))
        self.assertEqual(code, 0)
        ex = json.loads((d / 'exceptions.json').read_text())['exceptions']
        self.assertEqual(ex[0]['rule'], 'W12')
        code, out = run('check', str(d), '--only', 'W12', '--json')
        res = json.loads(out)
        self.assertEqual([f['status'] for f in res['findings']], ['accepted'])


if __name__ == '__main__':
    unittest.main()
