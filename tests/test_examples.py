import pytest
from conftest import EXAMPLES, SCENES

from item_spec import check_file, load_file
from item_spec.cli import main

PACKS = sorted(EXAMPLES.glob("*.items.yaml"))


@pytest.mark.parametrize("path", PACKS, ids=lambda p: p.name)
def test_examples_pass_without_warnings(path):
    report = check_file(path)
    assert report.issues == []


@pytest.mark.parametrize("name", ["ep21", "s67-p01"])
def test_examples_match_their_scene(name):
    scene_path = SCENES / f"{name}.scene.yaml"
    if not scene_path.exists():
        pytest.skip("同级目录没有 scene-spec")
    from scene_spec.loader import load_file as load_scene

    report = check_file(EXAMPLES / f"{name}.items.yaml", scene=load_scene(scene_path))
    assert report.issues == []


def test_ep21_follows_the_practice_plan():
    """练习包的建议结构：探索 1、预测 1、概念 2–3 以上（含自我解释和非例）、程序题渐隐、回测变式、交错题。"""
    items = load_file(EXAMPLES / "ep21.items.yaml")["items"]
    by_type = {}
    for it in items:
        by_type.setdefault(it["type"], []).append(it)
    assert len(by_type["explore"]) == 1 and by_type["explore"][0]["feedback"] is False
    assert len(by_type["predict"]) == 1
    assert any(i.get("self_explain") for i in items)
    assert any(i.get("non_example") for i in items)
    levels = [i["scaffold"]["level"] for i in items if "scaffold" in i]
    assert levels == ["worked", "faded", "independent"]
    retest = [i for i in items if i.get("slot") == "retest"]
    assert len(retest) >= 4 and all("variation" in i for i in retest)
    assert {c for i in retest for c in i["variation"]["changes"]} >= {"condition", "conclusion", "reverse"}


def test_s67_worked_line_fades_subgoals():
    items = load_file(EXAMPLES / "s67-p01.items.yaml")["items"]
    chain = [i for i in items if "scaffold" in i]
    assert [i["scaffold"]["level"] for i in chain] == ["worked", "faded", "faded", "independent"]
    labels = [s["label"] for s in chain[0]["steps"]]
    assert labels == ["往下做差", "在等差那层补全", "逐层加回"]
    hidden = [sum(not s.get("shown", True) for s in i.get("steps", [])) for i in chain[:3]]
    assert hidden == [0, 2, 3]


def test_bank_item_has_no_problem_text():
    items = load_file(EXAMPLES / "s67-p01.items.yaml")["items"]
    bank = [i for i in items if i["source"].startswith("bank:")]
    assert bank and all("stem" not in i and set(i.get("answer", {})) <= {"kind"} for i in bank)


def test_cli_exit_codes(tmp_path, capsys):
    assert main(["check", *map(str, PACKS)]) == 0
    bad = tmp_path / "bad.items.yaml"
    bad.write_text("spec: '0.1'\npack: {}\nitems: []\n", encoding="utf-8")
    assert main(["check", str(bad)]) == 1
    assert "IS100" in capsys.readouterr().out


def test_cli_scene_and_units(capsys):
    scene = SCENES / "ep21.scene.yaml"
    units = EXAMPLES.parents[1] / "practice-engine" / "data" / "units.yaml"
    if not scene.exists():
        pytest.skip("同级目录没有 scene-spec")
    assert main(["check", str(EXAMPLES / "ep21.items.yaml"), "--scene", str(scene)]) == 0
    assert main(["check", *map(str, PACKS), "--scene", str(scene)]) == 2
    if units.exists():
        assert main(["check", *map(str, PACKS), "--units", str(units), "--strict"]) == 0


def test_cli_json(capsys):
    import json

    assert main(["check", "--json", str(PACKS[0])]) == 0
    out = json.loads(capsys.readouterr().out)
    assert out[str(PACKS[0])]["ok"] is True
