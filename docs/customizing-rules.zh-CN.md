# 自定义规则

[English](customizing-rules.md) · **简体中文**

说明 `paperrules` 如何决定检查什么，以及如何修改。这里的一切都不需要写 Python：规则是 JSON。

## 1. 设置从哪里来

一个项目的有效规则按以下顺序合并：

1. `paperrules.json` 中列出的**规则包**（默认 `["default"]`，即 `paperrules/packs/default/` 中的内置包）。如果某个名称在 `paperrules.json` 旁边也是一个目录，就从那里读取，所以你可以把自己的规则包放在自己的仓库里。后面的规则包追加规则；后面规则包里的 `tree.json` 会替换各层；
2. 你的**本地覆盖**，`rules.local.json`；
3. **术语表**（`glossary.json`）与**例外**（`exceptions.json`），它们是输入，不是规则。

### `paperrules.json`

| 键 | 含义 | 默认值 |
|---|---|---|
| `main_tex` | 主 LaTeX 文件，相对本文件的路径（必填）。会跟进 `\input` 与 `\include`。 | – |
| `bib` | `.bib` 文件；未设置时，若 `\bibliography{}` 指向的文件存在，则使用它 | – |
| `packs` | 规则包：内置名称，或本文件旁边的目录 | `["default"]` |
| `glossary` | 术语表文件（会启用 `A3`、`A6`、`A7`） | – |
| `limitation_sections` | 与章节标题匹配的正则；这些章节里允许自我限定的措辞（`W8`、`W9`） | `["limitation", "discussion"]` |
| `local_rules` | 本地覆盖文件 | `rules.local.json` |
| `exceptions` | 例外文件 | `exceptions.json` |
| `output` | `report.html/json/txt` 所在目录 | `out` |

## 2. `rules.local.json`

| 键 | 作用 |
|---|---|
| `disable`、`enable` | 要关闭/打开的规则编号列表（期刊类规则 `J1`、`J3`、`T5`、`B4`、`E6` 以及严格的 `A6` 在规则包中默认关闭） |
| `severity` | `{"W6": "error"}`：`error` 使检查未通过（退出状态 1），`warn` 不会 |
| `rules_add` | 新规则（见第 3 节）。编号已存在会被拒绝。 |
| `rules_edit` | `{"W14": {"severity": "error"}}`：修改已有规则的字段 |
| `tone`、`syntax`、`heads`、`document` | 规则包各文件的设置（第 5 节），按下面的规则合并 |
| `tree` | 这里的 `stages` 列表会替换规则包的各层（用于增加节点）；复制 `packs/default/tree.json` 后修改 |

**合并规则。** 普通的键替换规则包中的值（字典逐键合并）。`键_add` 扩充列表或更新字典；`键_remove` 删除列表项或字典键。规则包本身不会被修改。

```json
{"tone": {"W8": {"patterns_add": ["\\bobviously\\b"], "patterns_remove": ["\\b(cannot|fails? to)\\b"]}},
 "heads": {"names_add": ["msrs", "llvip"], "general_nouns_add": {"robustness": "model robustness"}}}
```

## 3. 一条规则

登记中的一项（`rules_add`，或规则包的 `register.json`）：

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

* **`stage`、`node`**：规则在规则树中的位置（`paperrules rules tree` 列出各层与节点）。该组合不存在时 `R0` 未通过。
* **`scope`**：`sentence`、`paragraph` 或 `document`，即规则读取的单位（仅作说明；由检查本身决定）。
* **`method`**：`auto`（检查器判定）、`partial`（检查器标出、由你判断；报告中如此显示）、`manual`（人工检查；`check` 为 `{"type": "manual"}`，规则出现在核对清单里）。
* **`severity`**：`warn` 或 `error`。规则的状态为 `pass`、`warn` 或 `fail`（严重度为 `error` 且有待处理项）、`manual`、`skip`（缺少输入，例如没有术语表）、`off`。
* **`check.type`**：
  * `pattern`：对每个印刷句子运行正则。`pattern`（字符串或列表）、`flags`（`"i"` 表示不区分大小写，为默认；`""` 区分大小写）、`message`（结果的前缀）、`sections`（只检查标题匹配其中某个正则的章节）、`skip_sections`、`skip_kinds`（`abstract`、`paragraph`、`item`、`figure`、`table`）。同一规则对一个句子只报告一次。
  * `builtin`：`{"type": "builtin", "group": "voice"}`，随包提供的 Python 检查。多条规则共用一个组（见下表）。新增内置检查需要在 `paperrules/rules_sentence.py` 或 `rules_document.py` 中加函数，并在 `runner.run_group` 中加一个分支；欢迎提交 pull request。
  * `manual`。
* **`tests`**：规则必须标出的句子（`flag`）和必须放过的句子（`pass`）。段落规则的测试项是句子列表（每项一个段落）。**`R1` 会为每条规则运行这些测试**（包括已关闭的规则），所以规则不再做它声称的事时，会在碰到论文之前表现为规则系统未通过。

| 内置组 | 规则 |
|---|---|
| `voice` | `W7` `W8` `W9` `W10` `W11` `W12` `W14` `W15` `W16` |
| `connectives` | `W13` |
| `heads` | `A6` `A7` |
| `glossary_terms` | `A3` |
| `repeated` | `F2` |
| `bib_citations` | `B1` `B8` |
| `bib_entries` | `B4` `B7` `B9` |
| `abstract` | `E6` `J1` `J2` |
| `keywords` | `J3` |
| `floats` | `B2` `T1` `T2` |
| `register` | `R0` `R1` |

### 新增一条规则的流程

1. 写出规则表述，以及**两个必须标出的句子和两个必须放过的句子**。其中要有你论文里的真实句子。
2. 写模式。`python -m paperrules test my-paper` 会告诉你它是否做了测试所说的事。
3. `python -m paperrules check my-paper --only U2 -v` 列出论文中的每一处命中。误报太多？收紧模式（先加一个 pass 测试）。
4. 选择层：规则所涉内容所在的最高层（用词规则属于 S4；摘要必须写什么的规则属于 S2）。

## 4. 检查器读到什么

`python -m paperrules sentences my-paper` 每句输出一行：`编号 段落 类型 文件:行 [章节] 文本`。

* 注释与宏定义被丢弃。行间公式被删除，行内公式变成 `X`，`\cite{…}` 按首次引用顺序变成 `[n]`，`\ref{…}` 变成图、表、公式或章节的编号。
* 句子按阅读顺序编号：摘要、正文、最后是图表标题。`kind` 为 `abstract`、`paragraph`、`item`（列表项）、`figure` 或 `table`（标题）。`section` 是所在章节的标题，标题行记为 `(caption)`。
* 句子在 `. ! ?` 之后、大写字母或数字之前切分；常见缩写（`e.g.`、`i.e.`、`et al.`、`Fig.`、`Eq.` 等）不切分。
* 以行间公式收尾的从句（`…, \begin{equation}…\end{equation} where X is …`）保持为一个句子。

## 5. 规则包各文件的设置

* **`tone.json`**：`W7`（`meta_subject`、`meta_verb`、`meta_max_words`、`patterns`），`W8` 与 `W9`（`patterns`），`W10`（`pattern`、`skip_kinds`、`adjectives`：允许作形容词的分词），`W11`（`patterns`），`W12`（`pattern`、`allowed_starts`：可以用 “we” 的句子），`W13`（`en`：连接词；`propose_en`：提出方法的句子）。
* **`syntax.json`**：解析类规则（`W14`–`W16`）的 `skip_kinds`。
* **`heads.json`**（规则 `A6`、`A7`）：`general_nouns`（名词 → 其唯一含义；按词形还原后匹配）、`scene_nouns`、`names`（小写：数据集、指标、方法）、`symbol_pattern`、`concepts`（`A7`：`{"concept", "canonical", "forbidden": [正则], "note"}`）。
* **`document.json`**：`J1`（`min`、`max` 词数）、`J3`（`min`、`max`）、`E6`（`max_numbers`）、`B7`（`required`：各条目类型的必备字段，`a|b` 表示任一，`complete_authors`、`initials`）。

## 6. 术语表，`glossary.json`

```json
{"terms": [
  {"id": "C02", "en": "fused image", "zh": "融合图像",
   "aliases_en": ["fusion output"], "allowed": [], "avoid_en": ["fusion result"]}
]}
```

`en` 是主术语。`avoid_en` 列出 `A3` 要标出的名称。对 `A6`，`en`、每个别名和每个 `allowed` 形式的中心名词都成为被接受的中心名词，这些形式本身出现时也被接受。`zh` 供你自己和以后的双语功能使用。

`A6` 有意设得严格（每个主语和宾语都必须用术语表名词或列出的通用名词），所以规则包中默认关闭。术语表建好后再打开，遇到合理的名词就扩充 `general_nouns_add`。

## 7. 例外，`exceptions.json`

```json
{"exceptions": [
  {"rule": "W12", "sentence_en": "We evaluate all methods on four datasets.", "status": "accepted",
   "reason": "the authors ran the evaluation; the sentence states the protocol", "decided": "2026-10-19"},
  {"rule": "B8", "key": "someone2020", "status": "accepted", "reason": "cited in the supplement"}
]}
```

例外按规则，并按**完全相同的句子**（`sentence_en`）匹配结果；文档级结果按 `key`（标签或引用键）匹配。对 `A6` 加 `"word"` 则只覆盖一个中心名词。`status: "accepted"` 使该项通过，并在报告中保留它与理由；其他状态（如 `pending`）使它保持待处理并显示理由。`paperrules accept 规则 "句子" --reason "…"` 追加一条（键用 `--key`）。

例外指向的是那句话，所以改了句子，例外随之失效：规则会重新检查新句子。

## 8. 读结果

`report.json` 中，每条规则有 `status`、`open`、`accepted`；各层有 `status` 与 `gate`（上层未通过时为 `provisional`）；`first_failing` 指出先改哪一层；每个结果有规则、编号、文件、行、章节、句子和被标出的原因。请把这些结果当作给作者的问题来读。
