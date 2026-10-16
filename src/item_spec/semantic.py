"""第二层：语义检查。只在结构检查通过之后运行，所以可以放心假定字段类型正确。

检查内容：
- 题号唯一；变式的锚题、样例的上一级都存在；
- 答案自洽：选择题有且只有该有的正确项，分数、括号、公式定界符写对；
- 题库题只带 id 和标注，不带题面；原创题题面和答案齐全；
- 题型和推送时机匹配：探索题在看片前且不判对错，回测题必须是变式；
- 变式阶梯（锚题 → 变条件 → 变结论 → 逆向 → 方法比较）和样例渐隐（完整 → 半 → 独立）按顺序上升；
- 练习包覆盖规划 §3.1 的各个时机（只给警告）；
- 给了配套 scene-spec 文件时，核对预测题的 beat、单元和集数。
"""

from __future__ import annotations

import re

from scene_spec.report import Report

DEFAULT_SLOT = {"explore": "pre", "predict": "video"}
CONCEPT_TYPES = ("why", "representation")
CONFIDENCE_TYPES = ("why", "representation", "transfer")
LADDER = {"condition": 1, "conclusion": 2, "reverse": 3, "method": 4}
SCAFFOLD_RANK = {"worked": 0, "faded": 1, "independent": 2}
CONTENT_KEYS = {
    "choice": ("options",),
    "number": ("value",),
    "expression": ("value",),
    "open": ("rubric",),
}
BANK_FORBIDDEN = ("stem", "steps")
BANK_ANSWER_ALLOWED = {"kind"}

_DOLLAR = re.compile(r"(?<!\\)\$")


def slot_of(item: dict) -> str:
    """题目的推送时机：写了 slot 就用 slot，否则由题型推出。"""
    return item.get("slot") or DEFAULT_SLOT.get(item["type"], "post")


def ladder_level(item: dict) -> int:
    var = item.get("variation")
    if not var:
        return 0
    return max(LADDER[c] for c in var["changes"])


class _Checker:
    def __init__(self, doc: dict, report: Report, scene: dict | None, units: set[str] | None):
        self.doc = doc
        self.r = report
        self.pack = doc["pack"]
        self.items: list[dict] = doc["items"]
        self.scene = scene
        self.units = units
        self.by_id: dict[str, dict] = {}
        self.index: dict[str, int] = {}
        declared = self.pack.get("misconceptions")
        self.misconceptions = set(declared) if declared is not None else None

    def run(self) -> None:
        self.collect_ids()
        for i, item in enumerate(self.items):
            p = f"items[{i}]"
            self.check_meta(item, p)
            self.check_source(item, p)
            if item["source"] == "original":
                self.check_answer(item, p)
                self.check_math_text(item, p)
            self.check_slot(item, p)
            self.check_variation(item, p)
            self.check_scaffold(item, p)
        self.check_ladder_order()
        self.check_coverage()
        if self.scene is not None:
            self.check_scene()
        self.stats()

    # ---------- 题号 ----------

    def collect_ids(self) -> None:
        for i, item in enumerate(self.items):
            iid = item["id"]
            if iid in self.by_id:
                self.r.error("IS201", f"items[{i}].id", f"题号 {iid!r} 重复（第一次出现在 items[{self.index[iid]}]）")
                continue
            self.by_id[iid] = item
            self.index[iid] = i

    def check_meta(self, item: dict, p: str) -> None:
        prefix = self.pack["id"] + "-"
        if not item["id"].startswith(prefix):
            self.r.warning("IS202", f"{p}.id", f"题号建议以包名 {prefix!r} 开头，方便跨包引用时不重名")
        ep = self.pack.get("episode")
        if "episode" in item and ep is not None and item["episode"] != ep:
            self.r.warning("IS203", f"{p}.episode", f"题目写的是第 {item['episode']} 集，练习包是第 {ep} 集")
        if self.units is not None:
            for u in item.get("units", []):
                if u not in self.units:
                    self.r.error("IS204", f"{p}.units", f"未知的单元编号 {u!r}")
        mis = item.get("misconception")
        if mis is not None and self.misconceptions is not None and mis not in self.misconceptions:
            self.r.error("IS246", f"{p}.misconception", f"迷思 {mis!r} 不在 pack.misconceptions 里")

    # ---------- 来源 ----------

    def check_source(self, item: dict, p: str) -> None:
        if item["source"].startswith("bank:"):
            leaked = [k for k in BANK_FORBIDDEN if k in item]
            answer = item.get("answer", {})
            leaked += [f"answer.{k}" for k in answer if k not in BANK_ANSWER_ALLOWED]
            if leaked:
                self.r.error(
                    "IS230", p,
                    f"题库题只存 id 和标注，不能带题面、选项、答案或解析（出现了 {'、'.join(leaked)}）；题面版权归原命题方",
                )
            return
        missing = [k for k in ("stem", "answer") if k not in item]
        if missing:
            self.r.error("IS231", p, f"原创题必须写 {'、'.join(missing)}")

    # ---------- 答案 ----------

    def check_answer(self, item: dict, p: str) -> None:
        answer = item.get("answer")
        if answer is None:
            return
        kind = answer["kind"]
        missing = [k for k in CONTENT_KEYS[kind] if k not in answer]
        if missing:
            self.r.error("IS233", f"{p}.answer", f"{kind} 题的答案缺少 {'、'.join(missing)}")
            return
        if kind == "choice":
            self.check_choice(answer, item, f"{p}.answer")
        elif kind == "number":
            value = answer["value"]
            if isinstance(value, str) and "/" in value and int(value.split("/")[1]) == 0:
                self.r.error("IS223", f"{p}.answer.value", f"分母不能为 0：{value!r}")
        elif kind == "expression":
            for j, expr in enumerate([answer["value"], *answer.get("equivalent", [])]):
                where = f"{p}.answer.value" if j == 0 else f"{p}.answer.equivalent[{j - 1}]"
                if not _balanced(expr):
                    self.r.error("IS224", where, f"括号不配对：{expr!r}")
        if item.get("self_explain") and kind != "open":
            self.r.warning("IS244", f"{p}.answer.kind", "自我解释题建议用 open 答案和评分要点，让学生用自己的话说")

    def check_choice(self, answer: dict, item: dict, p: str) -> None:
        options = answer["options"]
        correct = [j for j, o in enumerate(options) if o.get("correct")]
        if not correct:
            self.r.error("IS220", f"{p}.options", "选择题没有标出正确选项（correct: true）")
        elif len(correct) > 1 and not answer.get("multiple"):
            self.r.error("IS220", f"{p}.options", f"有 {len(correct)} 个正确选项，多选题请写 multiple: true")
        seen: dict[str, int] = {}
        for j, o in enumerate(options):
            text = o["text"].strip()
            if text in seen:
                self.r.error("IS221", f"{p}.options[{j}]", f"选项和 options[{seen[text]}] 重复")
            seen.setdefault(text, j)
            if o.get("correct") and "misconception" in o:
                self.r.error("IS222", f"{p}.options[{j}]", "正确选项不能标迷思；迷思写在干扰项上")
            mis = o.get("misconception")
            if mis is not None and self.misconceptions is not None and mis not in self.misconceptions:
                self.r.error("IS246", f"{p}.options[{j}].misconception", f"迷思 {mis!r} 不在 pack.misconceptions 里")

    def check_math_text(self, item: dict, p: str) -> None:
        texts: list[tuple[str, str]] = []
        if "stem" in item:
            texts.append((f"{p}.stem", item["stem"]))
        answer = item.get("answer", {})
        for j, o in enumerate(answer.get("options", [])):
            texts.append((f"{p}.answer.options[{j}].text", o["text"]))
        for j, r in enumerate(answer.get("rubric", [])):
            texts.append((f"{p}.answer.rubric[{j}]", r))
        if "explain" in answer:
            texts.append((f"{p}.answer.explain", answer["explain"]))
        for j, s in enumerate(item.get("steps", [])):
            texts.append((f"{p}.steps[{j}].work", s["work"]))
        for where, text in texts:
            if len(_DOLLAR.findall(text)) % 2:
                self.r.warning("IS225", where, "公式定界符 $ 不配对")

    # ---------- 时机 ----------

    def check_slot(self, item: dict, p: str) -> None:
        typ, slot = item["type"], slot_of(item)
        if typ in DEFAULT_SLOT and slot != DEFAULT_SLOT[typ]:
            self.r.error("IS240", f"{p}.slot", f"{typ} 题只能放在 {DEFAULT_SLOT[typ]}，不能放在 {slot}")
        elif slot in ("pre", "video") and typ not in DEFAULT_SLOT:
            self.r.error("IS240", f"{p}.slot", f"{slot} 只放探索题或预测题，{typ} 题请放在 post / retest / interleave")
        if typ == "explore" and item.get("feedback", True):
            self.r.warning("IS241", f"{p}.feedback", "探索题只记录答案、不当场判对错，请写 feedback: false")
        if typ == "predict" and "beat" not in item:
            self.r.warning("IS242", p, "预测题建议写 beat，对应视频里的暂停点")
        if slot == "retest" and "variation" not in item:
            self.r.error("IS243", p, "回测题必须是变式题（写 variation），不能和视频里、看片后练过的题一样")
        if slot == "interleave" and "skill" not in item:
            self.r.error("IS243", p, "交错题必须写 skill，调度器按题型标签混排")
        if typ in CONFIDENCE_TYPES and not item.get("confidence"):
            self.r.warning("IS245", f"{p}.confidence", f"{typ} 题建议加自信度评分：高自信答错是理解错觉的信号")

    # ---------- 变式 ----------

    def check_variation(self, item: dict, p: str) -> None:
        var = item.get("variation")
        if not var:
            return
        anchor = var["anchor"]
        if anchor == item["id"]:
            self.r.error("IS251", f"{p}.variation.anchor", "锚题不能是自己")
            return
        target = self.by_id.get(anchor)
        if target is None:
            self.r.error("IS250", f"{p}.variation.anchor", f"找不到锚题 {anchor!r}")
            return
        if target.get("variation"):
            self.r.warning("IS252", f"{p}.variation.anchor", f"{anchor!r} 本身是变式题；变式应直接挂在锚题上")
        if "method" in var["changes"] and item["type"] != "compare":
            self.r.warning("IS253", f"{p}.variation.changes", "方法比较（method）一级建议用 compare 题型")

    def check_ladder_order(self) -> None:
        """同一锚题、同一推送时机的变式，按文件顺序逐级上升（看片后一组、回测一组分开算）。"""
        last: dict[tuple[str, str], tuple[int, str]] = {}
        for i, item in enumerate(self.items):
            var = item.get("variation")
            if not var:
                continue
            level = ladder_level(item)
            key = (var["anchor"], slot_of(item))
            prev = last.get(key)
            if prev and level < prev[0]:
                self.r.warning(
                    "IS254", f"items[{i}].variation.changes",
                    f"变式阶梯倒退：{prev[1]!r} 已经到了更高一级；同一锚题的变式请按 变条件 → 变结论 → 逆向 → 方法比较 排列",
                )
            if not prev or level >= prev[0]:
                last[key] = (level, item["id"])

    # ---------- 样例渐隐 ----------

    def check_scaffold(self, item: dict, p: str) -> None:
        sc = item.get("scaffold")
        if not sc:
            return
        if item["type"] != "procedure":
            self.r.error("IS260", f"{p}.scaffold", "只有 procedure 题有样例 → 半样例 → 独立的分级")
            return
        level = sc["level"]
        steps = item.get("steps", [])
        shown = [s.get("shown", True) for s in steps]
        if level in ("worked", "faded") and not steps and item["source"] == "original":
            self.r.error("IS266", f"{p}.steps", f"{level} 样例必须写 steps（每步带子目标标签）")
        if level == "worked" and not all(shown):
            self.r.error("IS263", f"{p}.steps", "完整样例（worked）的每一步都要给出（shown 不能是 false）")
        if level == "faded" and steps and all(shown):
            self.r.error("IS263", f"{p}.steps", "半样例（faded）至少要隐去一步（shown: false）")
        if level == "independent" and any(shown):
            self.r.error("IS263", f"{p}.steps", "独立解题（independent）不给出任何一步；steps 只作评分参考，请写 shown: false")
        src_id = sc.get("from")
        if src_id is None:
            return
        src = self.by_id.get(src_id)
        if src is None or src_id == item["id"]:
            self.r.error("IS261", f"{p}.scaffold.from", f"找不到上一级样例 {src_id!r}")
            return
        if src["type"] != "procedure" or "scaffold" not in src:
            self.r.error("IS261", f"{p}.scaffold.from", f"{src_id!r} 不是带 scaffold 的 procedure 题")
            return
        if SCAFFOLD_RANK[src["scaffold"]["level"]] > SCAFFOLD_RANK[level]:
            self.r.error(
                "IS262", f"{p}.scaffold.level",
                f"渐隐不能倒退：上一级 {src_id!r} 是 {src['scaffold']['level']}，这一题是 {level}",
            )
        src_steps = src.get("steps", [])
        if not steps or not src_steps:
            return
        if [s["label"] for s in src_steps] != [s["label"] for s in steps]:
            self.r.warning("IS265", f"{p}.steps", f"子目标标签和上一级 {src_id!r} 不一致；同一条渐隐链建议沿用同一组标签")
            return
        for j, (a, b) in enumerate(zip(src_steps, steps)):
            if not a.get("shown", True) and b.get("shown", True):
                self.r.error("IS264", f"{p}.steps[{j}]", f"上一级 {src_id!r} 已经隐去了「{a['label']}」，这里又给出来了；渐隐要单调")

    # ---------- 覆盖（规划 §3.1 练习包） ----------

    def check_coverage(self) -> None:
        line = self.pack["line"]
        by_slot: dict[str, list[dict]] = {}
        for item in self.items:
            by_slot.setdefault(slot_of(item), []).append(item)
        post = by_slot.get("post", [])
        if not by_slot.get("pre"):
            self.r.warning("IS270", "items", "没有看片前的探索题（explore）")
        if line == "insight" and not by_slot.get("video"):
            self.r.warning("IS271", "items", "洞察集没有视频中的预测题（predict）")
        concept = [i for i in post if i["type"] in CONCEPT_TYPES]
        if len(concept) < 2:
            self.r.warning("IS272", "items", f"看片后的概念题（why / representation）只有 {len(concept)} 道，规划要求 2–3 道")
        procedure = [i for i in post if i["type"] == "procedure"]
        if len(procedure) < 2:
            self.r.warning("IS272", "items", f"看片后的程序题只有 {len(procedure)} 道，规划要求 2–4 道")
        if not any(i.get("self_explain") for i in self.items):
            self.r.warning("IS273", "items", "没有自我解释提示题（self_explain: true）")
        if line == "insight" and not any(i.get("non_example") for i in self.items):
            self.r.warning("IS274", "items", "洞察集没有非例题（non_example: true）")
        if len(by_slot.get("retest", [])) < 2:
            self.r.warning("IS275", "items", "回测变式题少于 2 道：2–3 天后和 1–2 周后各要 1–2 道")
        levels = {i["scaffold"]["level"] for i in procedure if "scaffold" in i}
        if procedure and not {"worked", "independent"} <= levels:
            self.r.warning("IS276", "items", "看片后的程序题没有从完整样例（worked）过渡到独立解题（independent）")

    # ---------- 和 scene-spec 交叉核对 ----------

    def check_scene(self) -> None:
        scene = self.scene
        meta = scene.get("meta", {}) if isinstance(scene, dict) else {}
        if "scene" in self.pack and meta.get("id") != self.pack["scene"]:
            self.r.error("IS284", "pack.scene", f"练习包对应 {self.pack['scene']!r}，给的 scene 文件是 {meta.get('id')!r}")
        if meta.get("units") and list(meta["units"]) != list(self.pack["units"]):
            self.r.warning("IS283", "pack.units", f"和视频的单元 {meta['units']} 不一致")
        if meta.get("episode") is not None and self.pack.get("episode") not in (None, meta["episode"]):
            self.r.warning("IS283", "pack.episode", f"视频是第 {meta['episode']} 集")
        beats = {b.get("id"): b for b in scene.get("beats", []) if isinstance(b, dict)}
        for i, item in enumerate(self.items):
            if "beat" not in item:
                continue
            b = beats.get(item["beat"])
            if b is None:
                self.r.error("IS280", f"items[{i}].beat", f"视频里没有 beat {item['beat']!r}")
                continue
            pause = b.get("pause")
            if not pause or pause.get("type") not in ("predict", "think"):
                self.r.error("IS281", f"items[{i}].beat", f"beat {item['beat']!r} 没有 predict / think 暂停")
                continue
            app_item = pause.get("app_item")
            if app_item is not None and app_item != item["id"]:
                self.r.warning("IS282", f"items[{i}].beat", f"视频暂停点的 app_item 写的是 {app_item!r}")
        for bid, b in beats.items():
            app_item = (b.get("pause") or {}).get("app_item")
            if app_item is not None and app_item not in self.by_id:
                self.r.warning("IS282", "items", f"视频 beat {bid!r} 的 app_item {app_item!r} 不在这个练习包里")

    def stats(self) -> None:
        st = self.r.stats
        st["items"] = len(self.items)
        for item in self.items:
            key = f"type_{item['type']}"
            st[key] = st.get(key, 0) + 1
        st["retest"] = sum(1 for i in self.items if slot_of(i) == "retest")
        st["interleave"] = sum(1 for i in self.items if slot_of(i) == "interleave")
        st["variants"] = sum(1 for i in self.items if i.get("variation"))
        st["bank"] = sum(1 for i in self.items if i["source"].startswith("bank:"))


def _balanced(expr: str) -> bool:
    pairs = {")": "(", "]": "[", "}": "{"}
    stack: list[str] = []
    for ch in expr:
        if ch in "([{":
            stack.append(ch)
        elif ch in pairs:
            if not stack or stack.pop() != pairs[ch]:
                return False
    return not stack


def check(doc: dict, report: Report, *, scene: dict | None = None, units: set[str] | None = None) -> None:
    _Checker(doc, report, scene, units).run()
