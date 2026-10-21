# Agent guide: writing a paper with paperrules

This file is for coding and writing agents (Claude Code, Codex and similar) that help authors revise a LaTeX paper. It says how
to set the checker up in a new paper project, how to run the revision loop, and how to turn an author's feedback into rules
that hold for the rest of the project. Humans can read [README.md](README.md) first. The sources the rules and the interface draw on are cited in
[CREDITS.md](CREDITS.md). When a rule you add adapts a published guide, cite the guide there as well.

## 1. Ground rules

These come before any finding of the checker.

1. **The author decides.** A sentence, title or abstract the author dictates is used verbatim. If it breaks a rule, record an
   exception with the author's reason (`accept`). Do not rewrite it.
2. **Invent nothing.** Never make up numbers, baselines, citations, author names, affiliations, e-mail addresses, funding or
   declarations. Every number in the text traces to a result file or table the authors produced. Every reference is checked
   against its published record. If something is missing, ask for it or leave a visible placeholder.
3. **Findings are questions.** For each finding, rewrite the sentence, accept it with a reason, or change the rule. A clean
   report does not make a good paper. The checker does not judge the science.
4. **Keep the author's files.** Do not delete, reset or overwrite sources, figures, data or earlier versions. Write each
   revision as a new version and leave earlier versions as they were delivered.
5. **Never edit the pack in place.** Project settings go in the paper's `rules.local.json`. Change `paperrules/packs/default/`
   only for a change meant for every user, with its tests.
6. **Keep private material out of public repositories.** Unpublished text, results, author data and local paths stay in the
   paper's own repository. See §9.

## 2. Set up a paper project

```bash
git clone https://github.com/kees-yang/paperrules && cd paperrules
pip install -e ".[figures]"                      # spaCy + PyMuPDF (PyMuPDF is only for the figure rules G1–G4)
python -m spacy download en_core_web_sm
python -m paperrules test examples/aptp-cvpr2026  # the install works: R0 and R1 pass

python -m paperrules init <paper-dir> --main main.tex --bib refs.bib
```

`init` writes `paperrules.json` and starter files into `<paper-dir>`. All paths in it are relative to that file, so
`"main_tex": "../manuscript/main.tex"` works. `\input` and `\include` are followed.

| File in `<paper-dir>` | Holds |
|---|---|
| `paperrules.json` | main `.tex`, `.bib`, packs, glossary, `limitation_sections` (where self-critical wording is allowed), output directory |
| `rules.local.json` | rules switched on or off, severities, numbers of rules, extra patterns, new rules with test sentences |
| `glossary.json` | one English term per concept, with aliases and retired names. It switches on `A3`, `A6` and `A7` |
| `exceptions.json` | flagged sentences or keys that stay, each with a reason and a date (written by `accept`) |

Then set the venue in `rules.local.json`. Read the numbers from the venue's guide for authors. Do not guess them.

```jsonc
{
  "enable": ["J1", "J3", "W20", "T10", "E6"],          // abstract length, keywords, abstract structure, table order, numbers in the abstract
  "document": {
    "J1": {"min": 150, "max": 250},                    // abstract words, from the guide for authors
    "figures": {"column_width_pt": 252.0, "text_width_pt": 516.0}   // measured, see §6
  }
}
```

The rules a pack leaves off (`(off)` in `rules list`) are venue or style choices. Switch each one on only when the venue or the
author asks for it. `docs/customizing-rules.md` gives the schema of every file.

## 3. The revision loop

```bash
python -m paperrules check <paper-dir>            # summary + out/report.html, report.json, report.txt
python -m paperrules check <paper-dir> -v         # every open finding in the terminal
python -m paperrules check <paper-dir> --json     # machine-readable, for an agent
python -m paperrules check <paper-dir> --only W10,W14
```

1. **Work top-down along the rule tree.** Go S1 sources → S2 thread → S3 paragraphs → S4 sentences → S5 format → S6 rules.
   Fix the highest failing stage first. A paragraph that will be rewritten makes its sentence findings provisional.
2. **For each finding, choose one action:**
   - rewrite the sentence (the usual case);
   - accept it with a reason:
     `python -m paperrules accept W12 "<exact sentence>" --reason "<why>" --project <paper-dir>`
     (with `--key` for a label or citation key, and `--word` for an A6 head noun);
   - change the rule in `rules.local.json` when it is wrong for this paper.
3. **Keep the meaning.** A rewrite must not change a number, a claim, a citation or a term. Check each changed sentence against
   the one it replaces.
4. **Re-run until the check passes.** Exit status `0` means no `error` rule is open. Use `--strict` to make warnings fail too,
   for CI or a final pass. Then run `python -m paperrules test <paper-dir>`, so the rules still pass their own tests.
5. **Compile the PDF and look at it.** The checker reads the source. Float placement, blank space and page breaks need the PDF.

If a finding looks wrong, run `python -m paperrules sentences <paper-dir> --grep "<regex>"` to print the sentence as the
checker reads it. The structure rules `W14`–`W16` and `A6` use a small parser. When it misreads a sentence, accept the
finding and give that as the reason.

## 4. Turn author feedback into rules

Authors repeat the same corrections. Write each standing preference down once, as a rule, so it is checked in every later
pass and on the next paper.

1. **Record the author's words verbatim** with the date, in the paper's revision log.
2. **Decide the scope.** A one-off edit ("move this table") is applied and logged. A standing preference ("never start with
   our method in a table", "one sentence for what we do") becomes a rule.
3. **Write the rule in `rules.local.json` → `rules_add`:** id, stage, node, scope, method (`auto`, `partial` or `manual`),
   severity, a bilingual statement, a reason, a check, and at least one `flag` and one `pass` test sentence. Write the test
   sentences in neutral, invented wording, never sentences from the paper.
4. **If the preference already exists as a pack rule,** switch it on, change its number, or extend its patterns with
   `patterns_add`. Do not add a duplicate.
5. **Run `test`, then `check --only <id>`.** Fix the paper, or record exceptions for sentences the author keeps.
6. **If an instruction replaces an earlier one,** say so in the log ("supersedes: …") and change or switch off the old rule.
   Two rules must never contradict each other.

```jsonc
"rules_add": [{
  "id": "U3", "stage": "S4", "node": "wording", "scope": "sentence", "method": "auto", "severity": "warn",
  "statement": {"en": "Write “state of the art”, not “SOTA”, in running text.", "zh": "正文写“state of the art”，不写“SOTA”。"},
  "why": {"en": "Abbreviations from slides read as informal.", "zh": "幻灯片缩写在正文中显得随意。"},
  "check": {"type": "pattern", "pattern": ["\\bSOTA\\b"], "message": "abbreviation:"},
  "tests": {"flag": ["The method reaches SOTA results."], "pass": ["The method reaches state-of-the-art results."]}
}]
```

A preference that cannot be tested by a pattern or the parser still goes in the register, with `"method": "manual"`. It then
shows up in the report's checklist, so it is not forgotten.

## 5. Conventions in the default pack

These preferences came out of many revision rounds with supervisors and co-authors. All of them can be changed.

- **Abstract (S2).** It runs field → gap → motivation → method → results. `W20` asks for one "We propose …" sentence, the
  mechanisms as First/Second/Third, and one sentence on what the method provides. `E6` keeps only a few numbers. `J2` allows
  no citations. The conclusion echoes the abstract and adds no new claim (`W4`).
- **Introduction (S3).** The problem and the motivation get separate paragraphs (`W2`). Experiments appear only as the last
  contribution.
- **Sentences (S4).**
  - One main action per sentence (`W14`).
  - Complete clauses, not comma participle phrases (`W15`).
  - Conditions and qualifiers come first (`W11`, `W16`).
  - Active voice with the thing as subject (`W10`). "We" only for what the authors did (`W12`).
  - No filler (`W7`). No self-criticism outside the discussion (`W8`). No hint of a missing experiment (`W9`).
  - Consequence words only for real consequences (`W13`).
  - One head noun per concept, from the glossary (`A6`, `A7`).
- **Format (S5).**
  - Floats come after their first citation and are numbered in citation order (`T1`, `T2`). Figures are cited as "Fig. N" (`T5`).
  - Captions are short (`T9`).
  - The proposed method is the last row of comparison tables, and ablation groups end with the full model (`T10`).
  - Pseudocode is an `algorithm` float with Input and Output lines, not a table. It has no final `return` step when the Output
    line already names the result.
- **References (S1).** Every key exists (`B1`). There are no duplicates (`B9`). Entries are complete with full author lists
  (`B7`). The DOI policy follows the venue (`B4`).

## 6. Figures

`G1`–`G4` open every file that `\includegraphics` places and measure it **at its printed size**. The printed size comes from
the `width`, `height` or `scale` option and the template's column and text widths:

- **G1 print-ready.** Each file exists. PDF fonts are embedded, and none are Type 3. Raster images reach at least 300 dpi.
- **G2 body font.** Figure text uses the body font family. Math fonts are allowed.
- **G3 readable text.** Main text prints at 8–10 pt, and nothing, subscripts included, prints below 6 pt.
- **G4 line weight.** No stroke prints thinner than 0.4 pt.

**Measure the widths once per template.** Put `\typeout{COL=\the\columnwidth\space TEXT=\the\textwidth}` after
`\begin{document}`, compile, read the log, and set `document.figures` to those values. `body_font` is detected from the
preamble. Set it by hand (`times`, `cm`, `helvetica`, `libertine` or a regular expression) if detection is wrong.

**When you make a figure:**

- Draw it at its final printed width, so font sizes in the plotting code are the printed sizes.
- Export a vector PDF with embedded fonts. In matplotlib, set `pdf.fonttype: 42` and use the body font family.
- Keep labels at 8–9 pt and lines at 0.5 pt or more.
- Rerun `check --only G1,G2,G3,G4` after every export.

`G5`–`G9` are a manual checklist, ticked by eye on the compiled PDF:

- **G5 one visual language.** All figures share fonts, line weights and colour roles. The proposed method has one highlight
  colour, and the captions name it.
- **G6 line grammar.** Data flow is a solid arrow, a parameter is a dashed line, and an expansion link is a dashed line without
  an arrowhead. Arrowheads are visible and end on box edges. No line crosses a label.
- **G7 framework figures.** Modules, symbols and data labels only. Formulas and explanations belong in the equations and the
  caption.
- **G8 boxes.** Boxes fit their content and labels sit inside them. A module keeps the same icon and name in every figure.
- **G9 images and plots.** Within a panel group, images are all real or all schematic. Real images come from saved result
  files, never from generated pixels. Plots are drawn from frozen data files.

## 7. Practices outside the checker

These steps worked well in practice. The checker does not enforce them.

- **Version folders.** Write every delivered revision to a new folder, such as `submission/<date>_v<version>/`, with its
  `.tex`, PDF, figures and a short README. Point a `latest.pdf` link at it.
- **Revision log.** For each round, record the author's words, the changes made, the evidence, the checks run and the rules it
  supersedes. Keep a style guide beside it with the standing preferences.
- **Evidence map.** For each table and each number in the text, record the file it comes from. Before changing a number,
  trace it there.
- **Glossary first.** To rename a concept, change the glossary, then the text, figures and captions.
- **Supporting documents.** Write the cover letter, highlights and code-availability statement from the manuscript PDF.
  Check every number against the PDF and every reference against the `.bib`. Use the venue's limits: highlights are usually
  3–5 bullets of at most 85 characters. Check the limit for the venue at hand.
- **Placeholders.** Mark anything only the authors can supply as an open item: declarations, funding, author data and
  repository links. Do not fill it in.

## 8. Commands at a glance

| Task | Command |
|---|---|
| list rules / the tree / one rule | `python -m paperrules rules list\|tree\|show W14 --project <dir>` |
| rules as Markdown | `python -m paperrules rules markdown --project <dir>` |
| check, report files in `out/` | `python -m paperrules check <dir>` |
| check for CI | `python -m paperrules check <dir> --strict --no-files` |
| run the rule tests | `python -m paperrules test <dir>` |
| keep a flagged sentence | `python -m paperrules accept <rule> "<sentence>" --reason "<why>" --project <dir>` |
| debug the reader | `python -m paperrules sentences <dir> --grep "<regex>"` |
| package tests | `python -m unittest discover -s tests` |

Exit status: `0` when no `error` rule is open; `1` otherwise, or when a warning is open under `--strict`.

## 9. Contributing back

You can generalize a rule learned on one paper into the default pack (`paperrules/packs/default/register.json` and the matching
settings file). Before committing:

- Make the statement general. Remove the paper's method names, datasets, numbers and author names.
- Write test sentences in invented, neutral wording.
- Run `python -m unittest discover -s tests` and `python -m paperrules test examples/aptp-cvpr2026`. Regenerate
  `examples/aptp-cvpr2026/expected/` and `docs/rules.md` if the rules changed.
- Search the diff for e-mail addresses, personal names, local paths, unpublished titles and API keys before you push.
