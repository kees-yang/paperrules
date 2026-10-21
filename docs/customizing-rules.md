# Customizing the rules

**English** · [简体中文](customizing-rules.zh-CN.md)

How `paperrules` decides what to check, and how to change it. Nothing here needs Python: rules are JSON.

## 1. Where settings come from

The effective rules of a project are merged, in this order:

1. the **packs** named in `paperrules.json` (default: `["default"]`, the built-in pack in `paperrules/packs/default/`). A name that is also a directory next to `paperrules.json` is read from there, so you can keep your own pack in your repository. Later packs append their rules; a `tree.json` in a later pack replaces the stages;
2. your **local overrides**, `rules.local.json`;
3. the **glossary** (`glossary.json`) and the **exceptions** (`exceptions.json`), which are inputs, not rules.

### `paperrules.json`

| key | meaning | default |
|---|---|---|
| `main_tex` | main LaTeX file, relative to this file (required). `\input` and `\include` are followed. | – |
| `bib` | `.bib` file; if absent, the file named in `\bibliography{}` is used when it exists | – |
| `packs` | rule packs, built-in names or directories next to this file | `["default"]` |
| `glossary` | glossary file (switches on `A3`, `A6`, `A7`) | – |
| `limitation_sections` | regular expressions matched against section titles; self-critical wording (`W8`, `W9`) is allowed there | `["limitation", "discussion"]` |
| `local_rules` | local override file | `rules.local.json` |
| `exceptions` | exceptions file | `exceptions.json` |
| `output` | directory of `report.html/json/txt` | `out` |

## 2. `rules.local.json`

| key | effect |
|---|---|
| `disable`, `enable` | lists of rule ids to switch off / on (venue rules such as `J1`, `J3`, `T5`, `B4`, `E6`, the strict `A6` and the style rules `W20` and `T10` are off in the pack) |
| `severity` | `{"W6": "error"}`: `error` fails the check (exit status 1), `warn` does not |
| `rules_add` | new rules (§3). An id that exists is refused. |
| `rules_edit` | `{"W14": {"severity": "error"}}`: change fields of an existing rule |
| `tone`, `syntax`, `heads`, `document` | settings of the packs' files (§5), merged by the rule below |
| `tree` | a `stages` list here replaces the pack's stages (to add nodes); copy `packs/default/tree.json` and edit it |

**Merge rule.** A plain key replaces the pack's value (dictionaries are merged key by key). `key_add` extends a list or updates a dictionary; `key_remove` deletes list items or dictionary keys. The pack is never modified.

```json
{"tone": {"W8": {"patterns_add": ["\\bobviously\\b"], "patterns_remove": ["\\b(cannot|fails? to)\\b"]}},
 "heads": {"names_add": ["msrs", "llvip"], "general_nouns_add": {"robustness": "model robustness"}}}
```

## 3. A rule

An entry of the register (`rules_add`, or `register.json` of a pack):

```json
{
  "id": "U2",
  "stage": "S4", "node": "tone",
  "scope": "sentence",
  "method": "auto",
  "severity": "warn",
  "enabled": true,
  "statement": {"en": "…", "zh": "…"},
  "why":       {"en": "…", "zh": "…"},
  "check": {"type": "pattern", "pattern": ["^Besides,"], "flags": "", "message": "sentence opens with:",
            "sections": [], "skip_sections": [], "skip_kinds": ["figure", "table"]},
  "tests": {"flag": ["Besides, the data are costly."], "pass": ["In addition, the data are costly."]}
}
```

* **`stage`, `node`**: where the rule sits in the rule tree (`paperrules rules tree` lists stages and nodes). `R0` fails if the pair does not exist.
* **`scope`**: `sentence`, `paragraph` or `document`: the unit the rule reads (informational; the check decides).
* **`method`**: `auto` (the checker decides), `partial` (it flags, you decide; shown as such in the report), `manual` (a person checks; `check` is `{"type": "manual"}` and the rule appears on the checklist).
* **`severity`**: `warn` or `error`. A rule's status is `pass`, `warn` or `fail` (open findings with severity `error`), `manual`, `skip` (input missing, e.g. no glossary) or `off`.
* **`check.type`**:
  * `pattern`: regular expressions over each printed sentence. `pattern` (string or list), `flags` (`"i"` = case-insensitive, the default; `""` = case-sensitive), `message` (prefix of the finding), `sections` (only sections whose title matches one of these regexes), `skip_sections`, `skip_kinds` (`abstract`, `paragraph`, `item`, `figure`, `table`). A sentence is reported once per rule.
  * `builtin`: `{"type": "builtin", "group": "voice"}`: a Python check shipped with the package. Several rules share one group (table below). Adding a new builtin check means adding a function to `paperrules/rules_sentence.py` or `rules_document.py` and a branch in `runner.run_group`; a pull request is welcome.
  * `manual`.
* **`tests`**: sentences the rule must flag (`flag`) and must pass (`pass`). A paragraph rule takes lists of sentences (one paragraph each). **`R1` runs these tests for every rule**, including disabled ones, so a rule that stops doing what it says shows up as a failing rule system, before it touches the paper.

| builtin group | rules |
|---|---|
| `voice` | `W7` `W8` `W9` `W10` `W11` `W12` `W14` `W15` `W16` |
| `connectives` | `W13` |
| `heads` | `A6` `A7` |
| `glossary_terms` | `A3` |
| `repeated` | `F2` |
| `bib_citations` | `B1` `B8` |
| `bib_entries` | `B4` `B7` `B9` |
| `abstract` | `E6` `J1` `J2` |
| `abstract_structure` | `W20` |
| `keywords` | `J3` |
| `floats` | `B2` `T1` `T2` (figures, tables and `algorithm` floats) |
| `table_order` | `T10` |
| `register` | `R0` `R1` |

### Workflow for a new rule

1. Write the statement and **two sentences it must flag and two it must pass**. Put real sentences from your paper among them.
2. Write the pattern. `python -m paperrules test my-paper` tells you whether it does what the tests say.
3. `python -m paperrules check my-paper --only U2 -v` shows every hit in the paper. Too many false hits? Tighten the pattern (add a pass test first).
4. Choose the stage: the highest stage whose content the rule is about (a wording rule is S4; a rule about what the abstract must say is S2).

## 4. What the checker reads

`python -m paperrules sentences my-paper` prints one line per sentence: `id paragraph kind file:line [section] text`.

* Comments and macro definitions are dropped. Display mathematics is removed, inline mathematics becomes `X`, `\cite{…}` becomes `[n]` by order of first use, `\ref{…}` becomes the number of the figure, table, equation or section.
* Rows are numbered in reading order: abstract, body, then captions. `kind` is `abstract`, `paragraph`, `item` (a list item), `figure` or `table` (a caption). `section` is the title of the enclosing section, `(caption)` for captions.
* Sentences are split on `. ! ?` before a capital letter or digit; common abbreviations (`e.g.`, `i.e.`, `et al.`, `Fig.`, `Eq.`, …) do not split.
* A display equation that ends a clause (`…, \begin{equation}…\end{equation} where X is …`) leaves the sentence in one piece.

## 5. Settings of the pack files

* **`tone.json`**: `W7` (`meta_subject`, `meta_verb`, `meta_max_words`, `patterns`), `W8` and `W9` (`patterns`), `W10` (`pattern`, `skip_kinds`, `adjectives`: participles allowed as adjectives), `W11` (`patterns`), `W12` (`pattern`, `allowed_starts`: sentences that may use "we"), `W13` (`en`: the connectives; `propose_en`: sentences that propose the method).
* **`syntax.json`**: `skip_kinds` for the parser rules (`W14`–`W16`).
* **`heads.json`** (rules `A6`, `A7`): `general_nouns` (noun → its one meaning; matched on the lemma), `scene_nouns`, `names` (lower case: datasets, metrics, methods), `symbol_pattern`, `concepts` (`A7`: `{"concept", "canonical", "forbidden": [regex], "note"}`).
* **`document.json`**: `J1` (`min`, `max` words), `J3` (`min`, `max`), `E6` (`max_numbers`), `W20` (`propose`, `ordinals`, `function`: patterns of the proposal sentence, the mechanism ordinals and the function sentence), `T10` (`method`: the name of your method in the first table column; empty = inactive), `B7` (`required`: fields per entry type, `a|b` means either, `complete_authors`, `initials`).

## 6. Glossary, `glossary.json`

```json
{"terms": [
  {"id": "C02", "en": "fused image", "zh": "融合图像",
   "aliases_en": ["fusion output"], "allowed": [], "avoid_en": ["fusion result"]}
]}
```

`en` is the main term. `avoid_en` lists names that `A3` flags. For `A6`, the head noun of `en`, of every alias and of every `allowed` form becomes an accepted head noun, and the printed forms themselves are accepted wherever they occur. `zh` is for you and for future bilingual features.

`A6` is strict on purpose (every subject and object must use a glossary noun or a listed general noun), so it is off in the pack. Switch it on once the glossary exists, and grow `general_nouns_add` as you meet legitimate nouns.

## 7. Exceptions, `exceptions.json`

```json
{"exceptions": [
  {"rule": "W12", "sentence_en": "We evaluate all methods on four datasets.", "status": "accepted",
   "reason": "the authors ran the evaluation; the sentence states the protocol", "decided": "2026-10-19"},
  {"rule": "B8", "key": "someone2020", "status": "accepted", "reason": "cited in the supplement"}
]}
```

An exception matches a finding by rule and by the **exact sentence** (`sentence_en`) or, for document findings, by `key` (a label or citation key). For `A6` add `"word"` to cover one head noun only. `status: "accepted"` passes the finding and keeps it in the report with the reason; any other status (for example `pending`) leaves it open and shows the reason. `paperrules accept RULE "sentence" --reason "…"` appends an entry (`--key` for a key).

An exception names the sentence, so editing the sentence ends the exception: the rule looks at the new sentence again.

## 8. Reading the result

`report.json` holds, for every rule, `status`, `open`, `accepted`; the stages with their `status` and `gate` (`provisional` when a stage above fails); `first_failing` (revise there first); and every finding with rule, id, file, line, section, sentence and the reason it was flagged. Treat the findings as questions to the author.
