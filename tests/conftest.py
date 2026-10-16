import copy
from pathlib import Path

import pytest

from item_spec import load_file

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "examples"
SCENES = ROOT.parent / "scene-spec" / "examples"


@pytest.fixture
def ep21() -> dict:
    """勾股定理练习包的一份可随意修改的副本。"""
    return copy.deepcopy(load_file(EXAMPLES / "ep21.items.yaml"))


@pytest.fixture
def s67() -> dict:
    return copy.deepcopy(load_file(EXAMPLES / "s67-p01.items.yaml"))


def minimal_pack() -> dict:
    """一份能通过检查、没有任何警告的最小练习包。"""
    def proc(iid, level, **extra):
        return {"id": iid, "type": "procedure", "scaffold": {"level": level}, "stem": "求斜边",
                "answer": {"kind": "number", "value": 5}, "source": "original", **extra}

    return {
        "spec": "0.1",
        "pack": {"id": "t", "title": "测试", "line": "insight", "units": ["J11"], "author": "Boxi Yu", "license": "CC-BY-4.0"},
        "items": [
            {"id": "t-explore", "type": "explore", "stem": "猜", "answer": {"kind": "number", "value": 5},
             "feedback": False, "source": "original"},
            {"id": "t-predict", "type": "predict", "beat": "Predict", "stem": "猜",
             "answer": {"kind": "choice", "options": [{"text": "甲", "correct": True}, {"text": "乙"}]}, "source": "original"},
            {"id": "t-why", "type": "why", "self_explain": True, "confidence": True, "stem": "为什么",
             "answer": {"kind": "open", "rubric": ["要点"]}, "source": "original"},
            {"id": "t-rep", "type": "representation", "non_example": True, "confidence": True, "stem": "哪个",
             "answer": {"kind": "choice", "options": [{"text": "甲", "correct": True}, {"text": "乙"}]}, "source": "original"},
            proc("t-p1", "worked", steps=[{"label": "甲", "work": "x"}, {"label": "乙", "work": "y"}]),
            proc("t-p2", "independent"),
            {"id": "t-r1", "type": "procedure", "slot": "retest", "variation": {"anchor": "t-p1", "changes": ["condition"]},
             "stem": "变式", "answer": {"kind": "number", "value": 13}, "source": "original"},
            {"id": "t-r2", "type": "procedure", "slot": "retest", "variation": {"anchor": "t-p1", "changes": ["reverse"]},
             "stem": "逆向", "answer": {"kind": "number", "value": 12}, "source": "original"},
        ],
    }


@pytest.fixture
def pack() -> dict:
    return minimal_pack()
