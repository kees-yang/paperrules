import json
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / 'examples' / 'aptp-cvpr2026'


def make_project(files, settings=None, local=None, glossary=None, exceptions=None):
    """Write a throw-away project to a temp directory and return its path."""
    d = Path(tempfile.mkdtemp(prefix='paperrules-test-'))
    for name, text in files.items():
        p = d / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding='utf-8')
    s = {'main_tex': 'main.tex'}
    s.update(settings or {})
    (d / 'paperrules.json').write_text(json.dumps(s), encoding='utf-8')
    if local is not None:
        (d / 'rules.local.json').write_text(json.dumps(local), encoding='utf-8')
    if glossary is not None:
        (d / 'glossary.json').write_text(json.dumps({'terms': glossary}), encoding='utf-8')
        s['glossary'] = 'glossary.json'
        (d / 'paperrules.json').write_text(json.dumps(s), encoding='utf-8')
    if exceptions is not None:
        (d / 'exceptions.json').write_text(json.dumps({'exceptions': exceptions}), encoding='utf-8')
    return d


DOC = r"""\documentclass{article}
\begin{document}
\begin{abstract}
We study fusion. The method leads on all datasets.
\end{abstract}
\section{Introduction}
Fusion \cite{a,b} is hard. See Fig.~\ref{fig:one} and Table~\ref{tab:two}.

\begin{figure}
\caption{One caption.}\label{fig:one}
\end{figure}
% a comment sentence that must not be read.
The model is trained on pairs, e.g. \textit{two} images. We then test it,
\begin{equation} x = y \label{eq:1} \end{equation}
where $x$ is the input.
\begin{itemize}
\item First item.
\item Second item.
\end{itemize}
\begin{table}\caption{Two caption.}\label{tab:two}\end{table}
\bibliography{refs}
\end{document}
"""
BIB = """@article{a, author={Doe, Jane and Roe, Richard}, title={T}, journal={J}, year={2020}}
@inproceedings{c, author={Doe, Jane}, title={U}, year={2021}}
"""
