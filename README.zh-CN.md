# paperrules

[English](README.md) · **简体中文**

面向 LaTeX 论文的规则化写作检查。你把“对你的这篇论文来说什么算好的写作”写成规则；`paperrules` 读取 LaTeX 源文件，逐句、逐段、逐篇地应用这些规则，并按**规则树**输出一份离线报告，告诉你应该先改论文的哪一层。

<p align="center"><img src="docs/img/report-desktop.png" alt="示例论文的检查报告：规则树与待处理项" width="760"></p>

* **规则是数据，不是代码。** 每条规则是 JSON 登记中的一项：中英文表述、理由、在规则树中的层、测试句。十行 JSON 就能加一条模式规则；测试立刻告诉你它是否做了你想做的事。
* **规则树，而不是一长串清单。** 源头 → 主线 → 段落 → 句子 → 格式 → 规则系统本身。某一层未通过，其下各层都只是“暂定”：*在最高的未通过层修改*（段落要改时，先改句子是白费功夫）。
* **标出的是问题，不是判决。** 被标出的句子可以保留，只要写明理由（`exceptions.json`）；报告里仍能看到已接受的例外。
* **离线、双语的报告。** 一个 HTML 文件（不需要服务器、CDN 或下载字体），可在 English / 中文 间切换，手机上也能读；另有 JSON 与纯文本。

> **状态：v0.1。** 默认规则包写入的是一位作者的英文写作偏好（主动语态、一句一个主要动作、先写优势、不写空话……）。这些是主张，不是定论。不同意的规则可以关掉；另见[检查器不做什么](#检查器不做什么)。

## 快速开始

```bash
git clone <本仓库> && cd paperrules
pip install -e .                                  # 会安装 spaCy
pip install -e ".[figures]"                       # 可选：PyMuPDF，用于图件文件规则 G1–G4
python -m spacy download en_core_web_sm           # 结构类规则使用的句法模型

python -m paperrules test examples/aptp-cvpr2026  # 规则通过自身的测试（R0、R1）
python -m paperrules check examples/aptp-cvpr2026 # 检查示例论文（几秒钟）
# 打开 examples/aptp-cvpr2026/out/report.html
```

示例是一篇已发表的 CVPR 2026 红外–可见光图像融合论文，以 CC BY 4.0 授权（见 [`examples/aptp-cvpr2026/README.md`](examples/aptp-cvpr2026/README.md)）。参考输出在 `examples/aptp-cvpr2026/expected/`。

## 检查你自己的论文

```bash
python -m paperrules init my-paper --main main.tex --bib refs.bib   # 生成 paperrules.json 与起始文件
# 把 LaTeX 源文件放进 my-paper/（或在配置里写 "main_tex": "../paper/main.tex"）
python -m paperrules check my-paper               # 文本摘要 + out/report.html、report.json、report.txt
python -m paperrules check my-paper -v            # 在终端列出全部待处理项
python -m paperrules check my-paper --only W10,W14
python -m paperrules check my-paper --strict      # 有提示也以状态码1退出（用于CI）
```

自上而下读报告。对每一项，你可以：

1. **改写这句话**（最常见）；
2. **保留，并写明理由**：`python -m paperrules accept W12 "We evaluate …" --reason "作者是施事" --project my-paper`；下次这句通过，理由留在报告中；
3. **改规则**——规则不适合你的论文时：见[自定义规则](#自定义规则)。

`python -m paperrules sentences my-paper --grep "正则"` 按检查器读到的样子打印句子：某条结果看起来奇怪时很有用。

### 退出状态

`0`：没有规则未通过（有提示可以，除非加 `--strict`）。`1`：严重度为 `error` 的规则有待处理项，或加了 `--strict` 且有提示。风格规则默认 `warn`；参考文献与测试规则（`B1`、`B2`、`B9`、`R0`、`R1`）为 `error`。

## 规则树

| 层 | 读取 | 例子 |
|---|---|---|
| **S1 源头** | 参考文献、术语表 | 被引用的键存在、条目完整、使用术语表中的术语（`B1`、`B7`、`B8`、`A3`） |
| **S2 主线** | 摘要、主张 | 优势性表述须有依据（`W6`）；摘要与结论（人工 `W1`、`W4`） |
| **S3 段落** | 段落内容 | 同一句不出现两次（`F2`）；人工检查（`W2`、`O2`） |
| **S4 句子** | 结构、语态、语气、用词 | 一句一个主要动作（`W14`）、主动语态（`W10`）、“we”（`W12`）、空话（`W7`）、结果连接词（`W13`）、中心名词（`A6`） |
| **S5 格式** | 期刊限制、图表、引用 | 摘要字数（`J1`）、图表与算法顺序（`T1`、`T2`）、本文方法排在表格最后（`T10`，需打开）、未知标签（`B2`）；按印刷尺寸测量图件文件——嵌入字体、正文字族、字号≥8 pt、线宽（`G1`–`G4`），以及图件设计核对清单（`G5`–`G9`：统一视觉语言与颜色角色、线型语法、框图内不写公式与灰色小字、方框按内容定尺寸、真实或示意图像取自登记文件） |
| **S6 规则系统** | 规则登记本身 | 每条规则都在树中（`R0`）；每条规则通过自身测试（`R1`） |

49 条规则的中英文对照见 [`docs/rules.md`](docs/rules.md)（`python -m paperrules rules tree --lang zh` 打印规则树，`rules show W14` 看单条规则）。规则按**方法**分为：`auto`（检查器判定）、`partial`（检查器标出、由你判断）、`manual`（人工检查；这类规则出现在报告末尾的核对清单里）。

## 自定义规则

所有设置由 `paperrules/packs/default/` 中的规则包与论文旁的本地文件 `rules.local.json` 合并而来。完整指南与各文件的格式见 [`docs/customizing-rules.zh-CN.md`](docs/customizing-rules.zh-CN.md)。常用做法：

```jsonc
// my-paper/rules.local.json
{
  "disable": ["W12"],                         // 关掉一条规则
  "enable":  ["J1", "T5"],                    // 打开规则包默认关闭的期刊规则
  "severity": {"W6": "error"},                // warn → error
  "document": {"J1": {"min": 150, "max": 250}},   // 规则的数值
  "tone": {"W8": {"patterns_add": ["\\bobviously\\b"]}},   // 扩充某条规则的模式（_add / _remove）
  "rules_add": [{                             // 新规则，自带测试
    "id": "U1", "stage": "S4", "node": "wording", "scope": "sentence", "method": "auto", "severity": "warn",
    "statement": {"en": "Write “vs.” (not “v.s.”).", "zh": "写“vs.”，不写“v.s.”。"},
    "why": {"en": "One spelling across the paper.", "zh": "全文同一种写法。"},
    "check": {"type": "pattern", "pattern": ["\\bv\\.s\\.?"], "message": "write vs.:"},
    "tests": {"flag": ["It is compared v.s. the baseline."], "pass": ["It is compared vs. the baseline."]}
  }]
}
```

然后运行 `python -m paperrules test my-paper`（R1 会运行每条规则的全部测试句，包括你的）和 `python -m paperrules check my-paper --only U1`。术语表（`glossary.json`）会启用术语类规则：`A3` 标出你已弃用的名称（`avoid_en`），`A6` 标出中心名词不在术语表中的主语与宾语，`A7` 标出用别的名词指称同一概念的短语。

## 检查器不做什么

* **它不评判科学内容或论证。** 它读句子与结构。报告干净不等于论文好；一篇好论文上的标出项也不是对它的批评。
* **它读 LaTeX 源文件，不读 PDF。** 图表顺序指源文件中的顺序；页面版式、溢出盒、字体和图内文字可读性不检查（相关规则为 `manual`）。
* **只支持英文。** 句子规则与 spaCy 模型针对英文。报告是双语的，论文不是。
* **句法解析会出错。** `W14`–`W16` 与 `A6` 使用小型 spaCy 模型，有时会读错句子。写明理由后接受即可。
* **本版不包含：** 数字到来源的证据登记（正文每个数字追溯到结果文件）、跨章节的故事线与语义流检查、中英文逐句对齐、PDF 版式检查。它们存在于本项目所源自的研究工作区中，是后续版本的候选。

## 目录

```
paperrules/             包（读取、规则、运行、报告、命令行）与 packs/default/*.json（规则）
examples/aptp-cvpr2026/ 一篇 CC BY 4.0 论文、术语表、本地规则、例外、expected/ 输出
docs/                   自定义规则（English、中文）、rules.md、截图
tests/                  python -m unittest discover -s tests   （29 个测试）
```

## 许可

代码：MIT（见 [`LICENSE`](LICENSE)）。示例论文保留其自身的 CC BY 4.0 许可（见 [`NOTICE`](NOTICE)）。
