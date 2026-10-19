# Example: a CVPR 2026 infrared–visible image fusion paper

**English** · [简体中文](#简体中文)

The paper in `paper/` is

> Yanglin Deng, Tianyang Xu, Chunyang Cheng, Hui Li, Xiao-jun Wu, Josef Kittler.
> *Beyond Strict Pairing: Arbitrarily Paired Training for High-Performance Infrared and Visible Image Fusion.*
> CVPR 2026. [arXiv:2603.21820](https://arxiv.org/abs/2603.21820), licensed
> [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/).

It was chosen because arXiv lists it under CC BY 4.0, which allows redistribution with attribution.
**Changes:** none to the LaTeX sources (`paper/main.tex`, `preamble.tex`, `sec/*.tex`, `main.bib` are the files of the arXiv source package). The figures and the CVPR style files (`cvpr.sty`, `ieeenat_fullname.bst`) are left out; the checker reads the text, not the PDF, so the paper does not need to compile here. Everything else in this directory (configuration, glossary, local rules, exceptions, reports) was written for this repository and is not endorsed by the authors of the paper.

**What the reports are.** The output applies the writing rules of this repository to the paper. The rules are one author's preferences (see the top-level README); a finding is a question, not a criticism of the paper.

## Files

| file | purpose |
|---|---|
| `paperrules.json` | project settings: main file, bibliography, glossary, `limitation_sections` (the paper has no Discussion, so its Conclusion may state limits) |
| `rules.local.json` | local rules: switches on `J1` (abstract 150–250 words), `T5` (“Fig.”) and `A6`; adds dataset and metric names and general nouns; two rules of its own, `U1` and `U2`, with tests |
| `glossary.json` | a small **illustrative** glossary (terms for rules `A3`, `A6`) — not the authors' terminology |
| `exceptions.json` | one accepted finding, with the reason |
| `expected/` | the reference output (`report.html`, `report.json`, `report.txt`) |

## Run it

```bash
python -m paperrules test  examples/aptp-cvpr2026       # R0 and R1: 42 test sentences
python -m paperrules check examples/aptp-cvpr2026       # writes examples/aptp-cvpr2026/out/
python -m paperrules check examples/aptp-cvpr2026 --only W15,A3 -v
```

## What to look at

* `B1`, `B2` pass: every cited key exists, every `\ref` has a label.
* `T2` finds that figure 1 is never cited in the text; `T1` finds three figures whose numbers differ from the order of first citation. Both read the source order of the floats.
* `A6` still has about 160 open findings: the glossary and noun lists in this example are a first pass. Extend `general_nouns_add` or the glossary and run again; that is the workflow.
* `W12` (“we”), `W10` (passive) and `W15` (participle after a comma) are the largest style groups. Whether they matter is your decision; switch them off in `rules.local.json` or accept single sentences with a reason.

---

## 简体中文

`paper/` 中的论文是

> Yanglin Deng, Tianyang Xu, Chunyang Cheng, Hui Li, Xiao-jun Wu, Josef Kittler。
> *Beyond Strict Pairing: Arbitrarily Paired Training for High-Performance Infrared and Visible Image Fusion*。
> CVPR 2026。[arXiv:2603.21820](https://arxiv.org/abs/2603.21820)，授权 [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/)。

选它是因为 arXiv 将它列为 CC BY 4.0，允许注明出处后再分发。**改动：** LaTeX 源文件未作任何修改（`paper/main.tex`、`preamble.tex`、`sec/*.tex`、`main.bib` 即 arXiv 源码包中的文件）。图片和 CVPR 样式文件（`cvpr.sty`、`ieeenat_fullname.bst`）已省略；检查器读文本而不读 PDF，所以这里不需要编译论文。本目录中的其余内容（配置、术语表、本地规则、例外、报告）为本仓库而写，并未得到该论文作者的认可。

**报告是什么。** 输出是把本仓库的写作规则应用到这篇论文上的结果。规则是一位作者的偏好（见顶层 README）；标出的项是问题，不是对论文的批评。

### 文件

| 文件 | 作用 |
|---|---|
| `paperrules.json` | 项目设置：主文件、参考文献、术语表、`limitation_sections`（这篇论文没有 Discussion，因此结论中可以写局限） |
| `rules.local.json` | 本地规则：打开 `J1`（摘要150–250词）、`T5`（“Fig.”）与 `A6`；加入数据集与指标名称、通用名词；两条自带测试的新规则 `U1`、`U2` |
| `glossary.json` | 一个小型**示意**术语表（供规则 `A3`、`A6` 使用）——不是作者的术语 |
| `exceptions.json` | 一条已接受的结果及其理由 |
| `expected/` | 参考输出（`report.html`、`report.json`、`report.txt`） |

### 运行

```bash
python -m paperrules test  examples/aptp-cvpr2026       # R0 与 R1：42 个测试句
python -m paperrules check examples/aptp-cvpr2026       # 写入 examples/aptp-cvpr2026/out/
python -m paperrules check examples/aptp-cvpr2026 --only W15,A3 -v
```

### 看什么

* `B1`、`B2` 通过：每个被引用的键都存在，每个 `\ref` 都有标签。
* `T2` 发现图1在正文中从未被引用；`T1` 发现三幅图的编号与首次引用的顺序不同。两者读取的都是图表在源文件中的顺序。
* `A6` 仍有约160个待处理项：本示例中的术语表与名词清单只是第一版。扩充 `general_nouns_add` 或术语表后重新运行，这就是工作流程。
* `W12`（“we”）、`W10`（被动）、`W15`（逗号后的分词）是数量最多的风格类。它们是否重要由你决定；可在 `rules.local.json` 中关掉，或写明理由后逐句接受。
