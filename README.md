# item-spec

[中文](#中文) | [English](#english)

## 中文

数学练习题的结构化描述格式：一集视频配一个练习包（`<id>.items.yaml`），一道题一段结构化描述。人和模型都能写，能自动校验，调度器（[practice-engine](../practice-engine)）和播放器直接读。

和 [scene-spec](../scene-spec) 同一个思路，也复用它的受限 YAML 读取器和检查报告。

### 安装

```bash
pip install "item-spec @ git+https://github.com/animind-ai/item-spec@v0.1.0"
```

scene-spec 会按对应的 tag 一起装上（这两个包还没有发布到 PyPI）。要改代码时，把依赖的几个仓库和本仓库并排检出到同一个目录，再 `uv sync`（见「开发」）。

### 一个练习包长什么样

```yaml
spec: "0.1"
pack:
  id: ep21
  title: 勾股定理：拼一拼就看见
  line: insight            # insight 洞察 | worked 例题讲解 | contest 竞赛
  units: [J11]             # 单元编号，单元表见 practice-engine 的 data/units.yaml
  episode: 21
  scene: ep21              # 配套视频的 scene-spec meta.id
  misconceptions: [a+b=c]  # 写了这一项，题目里的迷思必须取自这里
  author: Boxi Yu
  license: CC-BY-4.0
items:
  - id: ep21-why-1
    type: why
    skill: pythagoras-why
    stem: 为什么直角三角形的斜边不是 $a+b$？用一句话说明。
    answer:
      kind: open
      rubric:
        - 提到两边之和大于第三边，或提到用面积拼图得到 $c^2=a^2+b^2$
    misconception: a+b=c
    confidence: true
    source: original
```

完整示例：
- [`examples/ep21.items.yaml`](examples/ep21.items.yaml)：洞察系列 #21 勾股定理。看片前探索题、视频中预测题（对应 `Predict` 暂停）、为什么题和自我解释、钝角非例、样例 → 半样例 → 独立的程序题、方法比较、沿 变条件 → 变结论 → 逆向 上升的回测变式、单元末交错题。
- [`examples/s67-p01.items.yaml`](examples/s67-p01.items.yaml)：§6.7 例题讲解（高阶等差数列）。程序题是一条四级渐隐链，每步带同一组子目标标签（往下做差 / 在等差那层补全 / 逐层加回）；还有一道只存 id 和标注的题库题。

### 题目字段

| 字段 | 说明 |
|---|---|
| `id` | 题号，小写字母、数字、连字符；建议以包名开头 |
| `type` | `explore` 探索 · `predict` 预测 · `why` 为什么 · `representation` 表征判断 · `procedure` 程序 · `transfer` 迁移 · `compare` 方法比较 |
| `slot` | 推送时机：`pre` 看片前 · `video` 视频中 · `post` 看片后立即 · `retest` 间隔回测 · `interleave` 单元末交错。不写时 explore → pre，predict → video，其余 → post |
| `units` | 单元编号，不写时用练习包的 |
| `episode` | 集数，不写时用练习包的 |
| `skill` | 题型标签，交错练习按它混排 |
| `confusable_with` | 容易和本题混淆的题型标签 |
| `stem` | 题面，可以写 `$...$` 公式 |
| `answer` | `kind` 为 `choice`（`options`：`text` / `correct` / 干扰项的 `misconception`；多选写 `multiple: true`）、`number`（`value`，分数写成 `'-3/4'`；可选 `tolerance`、`unit`）、`expression`（`value`、`equivalent`、`vars`）、`open`（`rubric` 评分要点、`sample` 参考答案）。都可以带 `explain` 解析 |
| `steps` | 样例的步骤：`label` 子目标标签、`work` 做法、`shown` 是否直接给出（默认给出） |
| `scaffold` | `level`：`worked` 完整样例 · `faded` 半样例 · `independent` 独立解题；`from`：上一级样例的题号 |
| `variation` | `anchor` 锚题，`changes`：`condition` 变条件 · `conclusion` 变结论 · `reverse` 逆向 · `method` 方法比较 |
| `misconception` | 这道题专门检测的迷思（学生错误说法原文） |
| `confidence` | 作答后加一项自信度评分（1–5）；"高自信 + 答错"是理解错觉的信号 |
| `self_explain` | 自我解释提示题 |
| `non_example` | 非例题：规律在什么情况下失效 |
| `feedback` | 是否当场判对错；探索题写 `false`，只记录答案 |
| `beat` | 预测题对应的 scene-spec beat id |
| `difficulty` | 1–5 |
| `tags` | 自由标签 |
| `source` | `original` 原创，或 `bank:<题库 id>` |
| `license` | `CC-BY-4.0` 或 `CC-BY-SA-4.0`，不写时用练习包的 |

**题库题**（`source: bank:...`）只存 id 和标注（题型、单元、题型标签、变式维度、迷思、难度、`answer.kind`），**不存题面、选项、答案和解析**。题面版权归原命题方，按 `OPEN_SOURCE.md` 4.2 单独处理；播放器按 id 从题库取题面。

### 检查

```bash
uv run item-spec check examples/*.items.yaml
uv run item-spec check examples/ep21.items.yaml --scene ../scene-spec/examples/ep21.scene.yaml
uv run item-spec check examples/*.items.yaml --units ../practice-engine/data/units.yaml --strict
```

```python
from item_spec import check_file

report = check_file("examples/ep21.items.yaml")
for issue in report.issues:
    print(issue.level, issue.code, issue.path, issue.message)
```

退出码：0 通过（可以有警告）；1 有错误（`--strict` 时警告也算）；2 用法错误。

| 层 | 代码 | 内容 |
|---|---|---|
| 读取 | IS000–IS003 | 受限 YAML：禁用锚点、别名、合并键、自定义标签；重复的键报错 |
| 版本 | IS010 | `spec` 必须是 `"0.1"` |
| 结构 | IS100 | JSON Schema（[`schema/item-spec-0.1.schema.json`](schema/item-spec-0.1.schema.json)） |
| 题号 | IS201 重复 · IS202 不以包名开头（警告）· IS203 集数和包不一致（警告）· IS204 单元不在 `--units` 表里 | |
| 答案 | IS220 正确选项个数不对 · IS221 选项重复 · IS222 正确项标了迷思 · IS223 分母为 0 · IS224 括号不配对 · IS225 `$` 不配对（警告） | |
| 来源 | IS230 题库题带了题面或答案 · IS231 原创题缺题面或答案 · IS233 答案缺 `options` / `value` / `rubric` | |
| 时机 | IS240 题型和推送时机不符 · IS241 探索题当场判分（警告）· IS242 预测题没写 beat（警告）· IS243 回测题不是变式 / 交错题没写 skill · IS244 自我解释题不是开放题（警告）· IS245 概念题没加自信度（警告）· IS246 迷思没在包里声明 | |
| 变式 | IS250 锚题不存在 · IS251 锚题是自己 · IS252 锚题本身是变式（警告）· IS253 方法比较不是 compare 题（警告）· IS254 同一锚题、同一时机的变式阶梯倒退（警告） | |
| 渐隐 | IS260 非程序题写了 scaffold · IS261 上一级不存在或不是样例 · IS262 渐隐倒退 · IS263 完整样例有隐去的步、半样例没隐去任何一步、独立题给出了步骤 · IS264 上一级隐去的步这里又给出 · IS265 子目标标签和上一级不一致（警告）· IS266 样例没写 steps | |
| 覆盖 | IS270–IS276（警告） | 练习包的建议结构：探索题、预测题（洞察集）、2 道以上概念题和程序题、自我解释、非例（洞察集）、2 道以上回测变式、程序题从样例过渡到独立 |
| 视频 | IS280 beat 不存在 · IS281 beat 没有 predict / think 暂停 · IS282 暂停点的 `app_item` 对不上（警告）· IS283 单元或集数和视频不一致（警告）· IS284 `pack.scene` 不是这个视频 | 需要 `--scene` |

结构不通过时不运行语义检查。

### 开发

```bash
uv sync        # 以可编辑路径依赖同级目录的 ../scene-spec
uv run pytest
uvx ruff check .
```

### 作者与许可

作者：Boxi Yu（[@BoxiYu](https://github.com/BoxiYu)）

代码以 [MIT 许可](LICENSE)发布。`examples/` 里的原创题目、解析和评分要点以 CC BY 4.0 发布。题库题只引用 id，题面不在本仓库。

## English

A structured description format for math practice items: one practice pack (`<id>.items.yaml`) per video, one structured entry per item. Both people and models can write it, it can be validated automatically, and the scheduler ([practice-engine](../practice-engine)) and the player read it directly.

Same approach as [scene-spec](../scene-spec), and it reuses scene-spec's restricted YAML reader and check reports.

### Installation

```bash
pip install "item-spec @ git+https://github.com/animind-ai/item-spec@v0.1.0"
```

scene-spec is installed from its matching tag (neither package is on PyPI yet). To work on the code, check out the repositories it depends on next to this one in the same directory and run `uv sync` (see "Development").

### What a practice pack looks like

```yaml
spec: "0.1"
pack:
  id: ep21
  title: 勾股定理：拼一拼就看见
  line: insight            # insight 洞察 | worked 例题讲解 | contest 竞赛
  units: [J11]             # 单元编号，单元表见 practice-engine 的 data/units.yaml
  episode: 21
  scene: ep21              # 配套视频的 scene-spec meta.id
  misconceptions: [a+b=c]  # 写了这一项，题目里的迷思必须取自这里
  author: Boxi Yu
  license: CC-BY-4.0
items:
  - id: ep21-why-1
    type: why
    skill: pythagoras-why
    stem: 为什么直角三角形的斜边不是 $a+b$？用一句话说明。
    answer:
      kind: open
      rubric:
        - 提到两边之和大于第三边，或提到用面积拼图得到 $c^2=a^2+b^2$
    misconception: a+b=c
    confidence: true
    source: original
```

(Comments in the example, in order: `line` is insight | worked (worked problem) | contest; `units` are unit ids from the unit table in practice-engine's `data/units.yaml`; `scene` is the scene-spec `meta.id` of the companion video; when `misconceptions` is given, item misconceptions must be taken from it. The title is "Pythagorean theorem: see it by rearranging pieces"; the item asks "Why isn't the hypotenuse of a right triangle $a+b$? Explain in one sentence.", and the rubric is "mentions that the sum of two sides is greater than the third, or uses an area rearrangement to get $c^2=a^2+b^2$".)

Full examples:
- [`examples/ep21.items.yaml`](examples/ep21.items.yaml): insight series #21, the Pythagorean theorem. Pre-video exploration item, in-video predict item (matching the `Predict` pause), why items and self-explanation, an obtuse-triangle non-example, procedural items going worked example → faded example → independent, method comparison, retest variations climbing change the condition → change the conclusion → reverse, and end-of-unit interleaved items.
- [`examples/s67-p01.items.yaml`](examples/s67-p01.items.yaml): §6.7 worked problem (higher-order arithmetic sequences). The procedural items form a four-level fading chain, each step carrying the same set of subgoal labels (take differences downward / complete at the arithmetic layer / add back layer by layer); there is also an item-bank item stored with only its id and annotations.

### Item fields

| Field | Description |
|---|---|
| `id` | Item id: lowercase letters, digits, hyphens; recommended to start with the pack name |
| `type` | `explore` exploration · `predict` prediction · `why` why · `representation` representation judgment · `procedure` procedural · `transfer` transfer · `compare` method comparison |
| `slot` | Push slot: `pre` before the video · `video` during the video · `post` right after the video · `retest` spaced retest · `interleave` end-of-unit interleaving. If omitted: explore → pre, predict → video, everything else → post |
| `units` | Unit numbers; the pack's if omitted |
| `episode` | Episode number; the pack's if omitted |
| `skill` | Skill tag; interleaved practice mixes items by it |
| `confusable_with` | Skill tags easily confused with this item |
| `stem` | Problem text; may contain `$...$` formulas |
| `answer` | `kind` is `choice` (`options`: `text` / `correct` / `misconception` for distractors; `multiple: true` for multiple choice), `number` (`value`, fractions written as `'-3/4'`; optional `tolerance`, `unit`), `expression` (`value`, `equivalent`, `vars`), or `open` (`rubric` scoring points, `sample` reference answer). All may carry an `explain` explanation |
| `steps` | Steps of a worked example: `label` subgoal label, `work` the work, `shown` whether it is given directly (default: given) |
| `scaffold` | `level`: `worked` full worked example · `faded` faded example · `independent` independent solving; `from`: id of the previous-level example |
| `variation` | `anchor` anchor item, `changes`: `condition` change the condition · `conclusion` change the conclusion · `reverse` reverse · `method` method comparison |
| `misconception` | The misconception this item specifically probes (the student's wrong statement, verbatim) |
| `confidence` | Add a confidence rating (1–5) after answering; "high confidence + wrong" signals an illusion of understanding |
| `self_explain` | Self-explanation prompt item |
| `non_example` | Non-example item: when the pattern fails |
| `feedback` | Whether correctness is shown on the spot; `false` for exploration items, which only record the answer |
| `beat` | The scene-spec beat id a predict item corresponds to |
| `difficulty` | 1–5 |
| `tags` | Free-form tags |
| `source` | `original`, or `bank:<item-bank id>` |
| `license` | `CC-BY-4.0` or `CC-BY-SA-4.0`; the pack's if omitted |

**Item-bank items** (`source: bank:...`) store only the id and annotations (type, unit, skill tag, variation dimension, misconception, difficulty, `answer.kind`), **not the problem text, options, answer, or explanation**. Copyright in the problem text belongs to the original setter and is handled separately per `OPEN_SOURCE.md` 4.2; the player fetches the problem text from the item bank by id.

### Checks

```bash
uv run item-spec check examples/*.items.yaml
uv run item-spec check examples/ep21.items.yaml --scene ../scene-spec/examples/ep21.scene.yaml
uv run item-spec check examples/*.items.yaml --units ../practice-engine/data/units.yaml --strict
```

```python
from item_spec import check_file

report = check_file("examples/ep21.items.yaml")
for issue in report.issues:
    print(issue.level, issue.code, issue.path, issue.message)
```

Exit codes: 0 passed (warnings allowed); 1 errors (warnings count too with `--strict`); 2 usage error.

| Layer | Codes | Contents |
|---|---|---|
| Reading | IS000–IS003 | Restricted YAML: anchors, aliases, merge keys, and custom tags are disallowed; duplicate keys are errors |
| Version | IS010 | `spec` must be `"0.1"` |
| Structure | IS100 | JSON Schema ([`schema/item-spec-0.1.schema.json`](schema/item-spec-0.1.schema.json)) |
| Item ids | IS201 duplicate · IS202 doesn't start with the pack name (warning) · IS203 episode inconsistent with the pack (warning) · IS204 unit not in the `--units` table | |
| Answers | IS220 wrong number of correct options · IS221 duplicate options · IS222 correct option marked with a misconception · IS223 zero denominator · IS224 unbalanced brackets · IS225 unbalanced `$` (warning) | |
| Source | IS230 item-bank item carries problem text or answer · IS231 original item missing problem text or answer · IS233 answer missing `options` / `value` / `rubric` | |
| Slot | IS240 item type doesn't fit push slot · IS241 exploration item graded on the spot (warning) · IS242 predict item has no beat (warning) · IS243 retest item isn't a variation / interleave item has no skill · IS244 self-explanation item isn't open-ended (warning) · IS245 conceptual item has no confidence rating (warning) · IS246 misconception not declared in the pack | |
| Variation | IS250 anchor doesn't exist · IS251 anchor is itself · IS252 anchor is itself a variation (warning) · IS253 method comparison isn't a compare item (warning) · IS254 variation ladder goes backwards for the same anchor and slot (warning) | |
| Fading | IS260 non-procedural item has a scaffold · IS261 previous level missing or not an example · IS262 fading goes backwards · IS263 full worked example hides a step, faded example hides no step, or independent item gives steps · IS264 a step hidden at the previous level is shown again here · IS265 subgoal labels inconsistent with the previous level (warning) · IS266 example has no steps | |
| Coverage | IS270–IS276 (warnings) | Recommended pack structure: exploration item, predict item (insight episodes), 2+ conceptual and procedural items, self-explanation, non-example (insight episodes), 2+ retest variations, procedural items moving from worked example to independent |
| Video | IS280 beat doesn't exist · IS281 beat has no predict / think pause · IS282 pause point's `app_item` doesn't match (warning) · IS283 unit or episode inconsistent with the video (warning) · IS284 `pack.scene` isn't this video | Requires `--scene` |

Semantic checks don't run if the structure check fails.

### Development

```bash
uv sync        # editable path dependency on the sibling directory ../scene-spec
uv run pytest
uvx ruff check .
```

### Author and license

Author: Boxi Yu ([@BoxiYu](https://github.com/BoxiYu))

The code is released under the [MIT License](LICENSE). Original items, explanations, and scoring rubrics in `examples/` are released under CC BY 4.0. Item-bank items are referenced by id only; their problem text is not in this repository.
