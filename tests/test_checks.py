"""结构与语义检查的单项用例。每个用例从一份能通过的练习包出发，只改一处。"""

import pytest

from item_spec import check, check_text


def codes(doc, **kw) -> list[str]:
    return check(doc, **kw).codes()


def item(doc, iid):
    return next(i for i in doc["items"] if i["id"] == iid)


def test_minimal_pack_is_clean(pack):
    assert codes(pack) == []


# ---------- 读取与结构 ----------

def test_loader_codes_are_renumbered():
    assert check_text("a: &x 1\nb: *x\n").codes()[0] == "IS001"
    assert check_text("a: [1\n").codes() == ["IS000"]
    assert check_text("a: 1\na: 2\n").codes() == ["IS000"]


def test_wrong_spec_version():
    assert check_text("spec: '0.2'\n").codes() == ["IS010"]


def test_unknown_type_is_structural(pack):
    item(pack, "t-why")["type"] = "essay"
    assert codes(pack) == ["IS100"]


def test_answer_fields_depend_on_kind(pack):
    item(pack, "t-why")["answer"]["value"] = 3  # open 题不能写 value
    assert codes(pack) == ["IS100"]


def test_bad_unit_and_source_patterns(pack):
    item(pack, "t-why")["units"] = ["Q1"]
    item(pack, "t-rep")["source"] = "bank"
    assert codes(pack) == ["IS100", "IS100"]


def test_semantic_layer_skipped_when_structure_fails(pack):
    pack["items"].append(dict(item(pack, "t-why")))  # 重复题号，结构通过时会报 IS201
    pack["pack"]["line"] = "movie"
    assert set(codes(pack)) == {"IS100"}


# ---------- 题号 ----------

def test_duplicate_id(pack):
    pack["items"].append(dict(item(pack, "t-why")))
    assert "IS201" in codes(pack)


def test_id_prefix_warning(pack):
    item(pack, "t-why")["id"] = "why-1"
    assert codes(pack) == ["IS202"]


def test_episode_mismatch(pack):
    pack["pack"]["episode"] = 21
    item(pack, "t-why")["episode"] = 22
    assert codes(pack) == ["IS203"]


def test_unknown_unit_with_unit_table(pack):
    item(pack, "t-why")["units"] = ["J99"]
    assert codes(pack, units={"J11"}) == ["IS204"]
    assert codes(pack) == []


def test_undeclared_misconception(pack):
    pack["pack"]["misconceptions"] = ["a+b=c"]
    item(pack, "t-why")["misconception"] = "a+b=c"
    assert codes(pack) == []
    item(pack, "t-why")["misconception"] = "别的"
    item(pack, "t-predict")["answer"]["options"][1]["misconception"] = "也没声明"
    assert codes(pack) == ["IS246", "IS246"]


# ---------- 来源 ----------

def test_bank_item_must_not_carry_text(pack):
    it = item(pack, "t-r1")
    it["source"] = "bank:013cff3cc259d10d-Q001"
    assert codes(pack) == ["IS230"]
    del it["stem"]
    assert codes(pack) == ["IS230"]  # answer.value 也是题库内容
    it["answer"] = {"kind": "number"}
    assert codes(pack) == []


def test_original_item_needs_stem_and_answer(pack):
    del item(pack, "t-why")["stem"]
    del item(pack, "t-rep")["answer"]
    assert codes(pack) == ["IS231", "IS231"]


@pytest.mark.parametrize("iid,key", [("t-why", "rubric"), ("t-rep", "options"), ("t-p2", "value")])
def test_incomplete_answer(pack, iid, key):
    del item(pack, iid)["answer"][key]
    assert codes(pack) == ["IS233"]


# ---------- 答案 ----------

def test_choice_needs_a_correct_option(pack):
    item(pack, "t-rep")["answer"]["options"][0]["correct"] = False
    assert codes(pack) == ["IS220"]


def test_multiple_correct_needs_multiple_flag(pack):
    ans = item(pack, "t-rep")["answer"]
    ans["options"][1]["correct"] = True
    assert codes(pack) == ["IS220"]
    ans["multiple"] = True
    assert codes(pack) == []


def test_duplicate_option(pack):
    item(pack, "t-rep")["answer"]["options"][1]["text"] = "甲 "
    assert codes(pack) == ["IS221"]


def test_correct_option_cannot_carry_misconception(pack):
    item(pack, "t-rep")["answer"]["options"][0]["misconception"] = "a+b=c"
    assert codes(pack) == ["IS222"]


def test_zero_denominator(pack):
    item(pack, "t-p2")["answer"]["value"] = "3/0"
    assert codes(pack) == ["IS223"]
    item(pack, "t-p2")["answer"]["value"] = "-3/4"
    assert codes(pack) == []


def test_unbalanced_expression(pack):
    item(pack, "t-p2")["answer"] = {"kind": "expression", "value": "2+(n-1)*n)", "equivalent": ["((n)"]}
    assert codes(pack) == ["IS224", "IS224"]


def test_unbalanced_dollar_warning(pack):
    item(pack, "t-why")["stem"] = "为什么 $a+b 不对"
    item(pack, "t-rep")["stem"] = r"价格是 \$5，公式 $a^2$"
    assert codes(pack) == ["IS225"]


def test_self_explain_prefers_open(pack):
    item(pack, "t-rep")["self_explain"] = True
    assert codes(pack) == ["IS244"]


# ---------- 时机 ----------

def test_explore_must_be_pre(pack):
    item(pack, "t-explore")["slot"] = "post"
    assert codes(pack) == ["IS240", "IS270"]


def test_pre_slot_only_for_explore(pack):
    item(pack, "t-why")["slot"] = "pre"
    assert "IS240" in codes(pack)


def test_explore_should_not_give_feedback(pack):
    del item(pack, "t-explore")["feedback"]
    assert codes(pack) == ["IS241"]


def test_predict_should_name_beat(pack):
    del item(pack, "t-predict")["beat"]
    assert codes(pack) == ["IS242"]


def test_retest_must_be_variant(pack):
    del item(pack, "t-r1")["variation"]
    assert codes(pack) == ["IS243"]


def test_interleave_needs_skill(pack):
    item(pack, "t-r1")["slot"] = "interleave"
    assert codes(pack) == ["IS243", "IS275"]
    item(pack, "t-r1")["skill"] = "hyp"
    assert codes(pack) == ["IS275"]


def test_concept_items_want_confidence(pack):
    del item(pack, "t-why")["confidence"]
    assert codes(pack) == ["IS245"]


# ---------- 变式 ----------

def test_missing_anchor(pack):
    item(pack, "t-r1")["variation"]["anchor"] = "t-nope"
    assert codes(pack) == ["IS250"]


def test_self_anchor(pack):
    item(pack, "t-r1")["variation"]["anchor"] = "t-r1"
    assert codes(pack) == ["IS251"]


def test_anchor_should_not_be_a_variant(pack):
    item(pack, "t-r2")["variation"]["anchor"] = "t-r1"
    assert codes(pack) == ["IS252"]


def test_method_change_wants_compare(pack):
    item(pack, "t-r2")["variation"]["changes"] = ["method"]
    assert codes(pack) == ["IS253"]


def test_ladder_goes_up_within_a_slot(pack):
    item(pack, "t-r1")["variation"]["changes"] = ["reverse"]
    item(pack, "t-r2")["variation"]["changes"] = ["condition"]
    assert codes(pack) == ["IS254"]


# ---------- 样例渐隐 ----------

def faded(pack, shown=(True, False), labels=("甲", "乙"), level="faded", src="t-p1"):
    pack["items"].insert(5, {
        "id": "t-pf", "type": "procedure", "scaffold": {"level": level, "from": src}, "stem": "半样例",
        "steps": [{"label": lab, "work": "w", "shown": s} for lab, s in zip(labels, shown)],
        "answer": {"kind": "number", "value": 5}, "source": "original",
    })
    return pack


def test_faded_chain_is_clean(pack):
    assert codes(faded(pack)) == []


def test_scaffold_only_on_procedure(pack):
    item(pack, "t-why")["scaffold"] = {"level": "worked"}
    assert codes(pack) == ["IS260"]


def test_scaffold_from_must_exist(pack):
    assert codes(faded(pack, src="t-nope")) == ["IS261"]


def test_scaffold_from_must_be_scaffolded_procedure(pack):
    assert codes(faded(pack, src="t-why")) == ["IS261"]


def test_scaffold_cannot_go_back(pack):
    item(pack, "t-p2")["scaffold"]["from"] = "t-p1"
    faded(pack, src="t-p2")
    assert codes(pack) == ["IS262"]


def test_worked_shows_every_step(pack):
    item(pack, "t-p1")["steps"][1]["shown"] = False
    assert codes(pack) == ["IS263"]


def test_faded_hides_something(pack):
    assert codes(faded(pack, shown=(True, True))) == ["IS263"]


def test_independent_shows_nothing(pack):
    item(pack, "t-p2")["steps"] = [{"label": "甲", "work": "x"}]
    assert codes(pack) == ["IS263"]


def test_fading_is_monotonic(pack):
    faded(pack, shown=(False, True))
    pack["items"].insert(6, {
        "id": "t-pf2", "type": "procedure", "scaffold": {"level": "faded", "from": "t-pf"}, "stem": "更少提示",
        "steps": [{"label": "甲", "work": "w", "shown": True}, {"label": "乙", "work": "w", "shown": False}],
        "answer": {"kind": "number", "value": 5}, "source": "original",
    })
    assert codes(pack) == ["IS264"]


def test_subgoal_labels_should_match(pack):
    assert codes(faded(pack, labels=("甲", "丙"))) == ["IS265"]


def test_worked_needs_steps(pack):
    del item(pack, "t-p1")["steps"]
    assert codes(pack) == ["IS266"]


# ---------- 覆盖 ----------

@pytest.mark.parametrize("iid,code", [
    ("t-explore", "IS270"), ("t-predict", "IS271"),
])
def test_missing_slots(pack, iid, code):
    pack["items"].remove(item(pack, iid))
    assert codes(pack) == [code]


def test_worked_line_does_not_need_predict_or_non_example(pack):
    pack["pack"]["line"] = "worked"
    pack["items"].remove(item(pack, "t-predict"))
    del item(pack, "t-rep")["non_example"]
    assert codes(pack) == []


def test_too_few_concept_and_procedure_items(pack):
    pack["items"].remove(item(pack, "t-rep"))
    pack["items"].remove(item(pack, "t-p2"))
    assert codes(pack) == ["IS272", "IS272", "IS274", "IS276"]


def test_no_self_explain(pack):
    del item(pack, "t-why")["self_explain"]
    assert codes(pack) == ["IS273"]


def test_too_few_retests(pack):
    pack["items"].remove(item(pack, "t-r2"))
    assert codes(pack) == ["IS275"]


def test_stats(pack):
    st = check(pack).stats
    assert st["items"] == 8 and st["retest"] == 2 and st["variants"] == 2 and st["type_procedure"] == 4


# ---------- scene 交叉核对 ----------

def scene(**pause):
    return {"meta": {"id": "t", "units": ["J11"]},
            "beats": [{"id": "Predict", "pause": {"type": "predict", "prompt": "?", **pause}}, {"id": "Hook"}]}


def test_scene_clean(pack):
    assert codes(pack, scene=scene(app_item="t-predict")) == []


def test_scene_beat_missing(pack):
    item(pack, "t-predict")["beat"] = "Nope"
    assert codes(pack, scene=scene()) == ["IS280"]


def test_scene_beat_without_pause(pack):
    item(pack, "t-predict")["beat"] = "Hook"
    assert codes(pack, scene=scene()) == ["IS281"]


def test_scene_app_item_mismatch(pack):
    assert codes(pack, scene=scene(app_item="t-other")) == ["IS282", "IS282"]


def test_scene_units_and_id(pack):
    pack["pack"]["scene"] = "ep99"
    sc = scene()
    sc["meta"]["units"] = ["J12"]
    assert codes(pack, scene=sc) == ["IS284", "IS283"]
