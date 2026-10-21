# Rule reference · 规则一览

The rules of the `default` pack, generated with `python -m paperrules rules markdown`. *Default* shows whether a rule is on out of the box.
Stages S1–S6 are the stages of the rule tree (read top-down). **Scope** is the unit the rule reads; **Method** says who decides:
`auto` the checker decides, `partial` the checker flags and the author decides, `manual` a person checks (the rule appears on the report's checklist).

`default` 规则包的全部规则，由 `python -m paperrules rules markdown` 生成。*Default* 表示开箱是否启用。S1–S6 是规则树的层（自上而下读）。
**Scope** 是规则读取的单位；**Method** 说明由谁判断：`auto` 由检查器判定，`partial` 检查器标出、作者判断，`manual` 由人检查（出现在报告的核对清单里）。

| ID | Stage | Scope | Method | Default | Rule | 规则 |
|---|---|---|---|---|---|---|
| B1 | S1 | document | auto | on | Every cited key exists in the bibliography. | 每个被引用的键都在参考文献库中。 |
| B8 | S1 | document | auto | on | Every bibliography entry is cited. | 参考文献库中的每个条目都被引用。 |
| B9 | S1 | document | auto | on | No duplicate keys in the bibliography. | 参考文献库中没有重复的键。 |
| B7 | S1 | document | auto | on | Bibliography entries are complete: required fields present, full author lists; optional: given names as initials. | 参考文献条目完整：必备字段齐全、作者列表完整；可选：名用首字母。 |
| B4 | S1 | document | auto | off | Bibliography entries carry no DOI or URL (venue style). | 参考文献条目不含DOI与URL（视期刊格式）。 |
| A3 | S1 | sentence | auto | on | The text uses the glossary term, not the old name or alias (glossary field avoid_en). | 全文使用术语表中的主术语，不用旧名与别名（术语表字段avoid_en）。 |
| W1 | S2 | document | manual | on | The abstract states, in order: the state of the field, the gap, the motivation, the method, the results. | 摘要按顺序写：研究现状、不足、动机、方法、结果。 |
| E6 | S2 | document | auto | off | The abstract carries at most a few numbers (document.json: E6.max_numbers). | 摘要只写少数几个数字（document.json：E6.max_numbers）。 |
| W20 | S2 | document | auto | off | The abstract states what the paper does in one sentence (“We propose …”), lists the mechanisms as First/Second/Third, and states what the method provides in one sentence (document.json: W20). | 摘要用一句说明本文做什么（“We propose …”），机制按First/Second/Third分层列出，再用一句说明方法的作用（document.json：W20）。 |
| W4 | S2 | document | manual | on | The conclusion echoes the abstract and adds no new claim. | 结论回扣摘要，不引入新的主张。 |
| W6 | S2 | sentence | partial | on | A comparative or superiority claim is traced to a table, a figure or a citation (the checker flags; the author decides). | 比较性或优势性表述须有依据：表、图或引用（自动标出，作者判断）。 |
| W2 | S3 | document | manual | on | In the introduction the problem and the motivation each have their own paragraph, both before the method. | 引言中“问题”与“动机”各成一段，均在“方法”段之前。 |
| F2 | S3 | sentence | auto | on | No sentence is printed twice. | 同一句话不出现两次。 |
| O2 | S3 | document | manual | on | The discussion answers the research question and does not list limitations item by item. | 讨论回答研究问题，不逐条罗列局限。 |
| W14 | S4 | sentence | partial | on | One main action per sentence: at most two finite clauses (a main clause plus one complete supporting clause), no clause nested in a subordinate clause, no “which” that refers to a whole clause. Flagged sentences are rewritten or kept with a written reason. | 一句一个主要动作：至多两个限定小句（主句加一个完整从句），不嵌套从句，不用指代整句的which；标出的句子改写，或写明理由后保留。 |
| W15 | S4 | sentence | auto | on | Complete clauses: no participle phrase set off by a comma (“…, thereby joining …”) and no verbless adjective clause (“…, possible because …”). | 完整从句：不用逗号后的分词短语（“…, thereby joining …”）或无动词的形容词从句（“…, possible because …”）。 |
| W16 | S4 | sentence | auto | on | Qualifiers first: no prepositional qualifier appended after the last comma of a sentence. | 限定成分在前：不在句末逗号后追加介词短语。 |
| W11 | S4 | sentence | auto | on | A real condition or time clause (if, unless, only when, when, before, after, until, once) comes before the action. | 真实的条件与时间从句（if、unless、only when、when、before、after、until、once）放在动作之前。 |
| W10 | S4 | sentence | auto | on | Active voice: body sentences have no passive (captions excepted); an adjectival use is an exception with a written reason. | 主动语态：正文句不用被动（图注除外）；形容词用法逐句写明理由后作为例外。 |
| W12 | S4 | sentence | auto | on | “We” only where the authors are the actor (proposing the method, stating contributions); otherwise the item is the subject. | 少用“we”：作者是施事时（提出方法、贡献）才用，其余以事物作主语。 |
| W7 | S4 | sentence | partial | on | No filler: no sentence without information (signposts, restatements, display or processing disclaimers). Restatement needs a reading. | 不写空话：无信息的路标句、重述句、显示或处理说明（重述靠通读）。 |
| W8 | S4 | sentence | auto | on | No self-criticism outside the discussion or limitation sections (project setting limitation_sections). | 讨论与局限章节以外不写自我限定或自我批评（项目设置limitation_sections）。 |
| W9 | S4 | sentence | auto | on | No sentence implies that an experiment that could have been run is missing. | 不写暗示缺少本可做的实验的句子。 |
| W13 | S4 | paragraph | partial | on | Consequence connectives (therefore, thus, so, thereby) mark only a real consequence: at most one per sentence, no repeat in a paragraph, not in two consecutive sentences, not before “we propose”. The premise is checked by hand. | 结果连接词（therefore、thus、so、thereby）只标真实的结果：每句至多一个、同段不重复、不连续两句、不用于“we propose”之前；前提逐句人工核对。 |
| A6 | S4 | sentence | auto | off | The head noun of every subject and object comes from the glossary or from the closed noun lists; otherwise use a pronoun. | 主语、宾语的中心名词取自术语表或闭合名词清单，否则用代词。 |
| A7 | S4 | sentence | auto | on | One thing keeps one head noun: concept rules list phrases that name a glossary concept with another noun. | 同一事物同一中心名词：概念规则列出用别的名词指称术语表概念的短语。 |
| M1 | S4 | sentence | manual | on | Plain words and direct verbs; no decoration with elevated words; necessary terms stay. | 用常见词和直接动词，不用高级词装饰；必要术语保留。 |
| M2 | S4 | sentence | manual | on | While, whereas, instead, unlike mark a real parallel, contrast or replacement, never a cause. | while、whereas、instead、unlike只用于真实的并行、对照或替代关系，不代替因果。 |
| J1 | S5 | document | auto | off | The abstract length is within the venue limit (document.json: J1.min, J1.max). | 摘要字数在期刊限制内（document.json：J1.min、J1.max）。 |
| J2 | S5 | document | auto | on | The abstract contains no citation. | 摘要不含引用。 |
| J3 | S5 | document | auto | off | The number of keywords is within the venue limit (document.json: J3). | 关键词数量在期刊限制内（document.json：J3）。 |
| T5 | S5 | sentence | auto | off | Running text refers to figures as “Fig. N” (not “Figure N” inside a sentence). | 正文用“Fig. N”引用图（句中不写“Figure N”）。 |
| T1 | S5 | document | auto | on | Figures, tables and algorithms are numbered in the order of their first citation (checked on the source). | 图、表与算法各自按首次引用的顺序编号（按源文件核查）。 |
| T2 | S5 | document | auto | on | A text citation comes before the figure or table it cites, and every figure and table is cited. A float placed above its citation on purpose is accepted in exceptions.json by its label. | 正文引用先于对应的图表出现，且每个图表都被引用。有意排在引用之上的图表在exceptions.json中按标签登记为例外。 |
| T10 | S5 | document | auto | off | The proposed method is not the first row of a table; comparison tables list it last (document.json: T10.method). | 本文方法不放在表格第一行；对比表把它列在最后（document.json：T10.method）。 |
| B2 | S5 | document | auto | on | Every \ref, \eqref, \autoref and \cref points to an existing \label. | 每个\ref、\eqref、\autoref、\cref都指向存在的\label。 |
| T9 | S5 | document | manual | on | Captions are short: only what is needed to read the figure; the mechanism belongs in the text. | 图注、表题简短：只写看图所需，机制放正文。 |
| M5 | S5 | document | manual | on | Text inside figures is readable at the final column width (about 8 pt or more in print). | 图内文字在最终栏宽下可读（印刷字号约8 pt以上）。 |
| R0 | S6 | document | auto | on | Every rule is in the register exactly once and sits in the rule tree. | 每条规则都在规则登记中且只出现一次，并位于规则树中。 |
| R1 | S6 | document | auto | on | Every testable rule flags its “flag” sentences and passes its “pass” sentences. | 每条可测试的规则都标出它的“flag”测试句、放过它的“pass”测试句。 |
