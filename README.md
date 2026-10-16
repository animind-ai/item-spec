# item-spec

数学练习题的结构化描述格式：一集视频配一个练习包（`<id>.items.yaml`），一道题一段结构化描述。人和模型都能写，能自动校验，调度器（[practice-engine](../practice-engine)）和播放器直接读。

和 [scene-spec](../scene-spec) 同一个思路，也复用它的受限 YAML 读取器和检查报告。

## 一个练习包长什么样

```yaml
spec: "0.1"
pack:
  id: ep21
  title: 勾股定理：拼一拼就看见
  line: insight            # insight 洞察 | worked 例题讲解 | contest 竞赛
  units: [J11]             # 规划 §1.2 的单元编号
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

## 题目字段

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

## 检查

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
| 覆盖 | IS270–IS276（警告） | 规划 §3.1 练习包：探索题、预测题（洞察集）、2 道以上概念题和程序题、自我解释、非例（洞察集）、2 道以上回测变式、程序题从样例过渡到独立 |
| 视频 | IS280 beat 不存在 · IS281 beat 没有 predict / think 暂停 · IS282 暂停点的 `app_item` 对不上（警告）· IS283 单元或集数和视频不一致（警告）· IS284 `pack.scene` 不是这个视频 | 需要 `--scene` |

结构不通过时不运行语义检查。

## 开发

```bash
uv sync        # 以可编辑路径依赖同级目录的 ../scene-spec
uv run pytest
uvx ruff check .
```

## 作者与许可

作者：Boxi Yu（[@BoxiYu](https://github.com/BoxiYu)）

代码以 [MIT 许可](LICENSE)发布。`examples/` 里的原创题目、解析和评分要点以 CC BY 4.0 发布。题库题只引用 id，题面不在本仓库。
