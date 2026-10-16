"""第一层：结构检查（JSON Schema）。"""

from __future__ import annotations

import json
from functools import lru_cache
from importlib import resources
from pathlib import Path

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError, best_match
from scene_spec.report import Report

SCHEMA_NAME = "item-spec-0.1.schema.json"


@lru_cache(maxsize=1)
def schema() -> dict:
    """优先读仓库里的 schema/，安装成包之后读包内副本。"""
    repo_copy = Path(__file__).resolve().parents[2] / "schema" / SCHEMA_NAME
    if repo_copy.exists():
        return json.loads(repo_copy.read_text(encoding="utf-8"))
    return json.loads(resources.files("item_spec").joinpath("schema", SCHEMA_NAME).read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def validator() -> Draft202012Validator:
    Draft202012Validator.check_schema(schema())
    return Draft202012Validator(schema())


def _path(error: ValidationError) -> str:
    out = ""
    for part in error.absolute_path:
        out += f"[{part}]" if isinstance(part, int) else (f".{part}" if out else str(part))
    return out


def _explain(error: ValidationError) -> ValidationError:
    """oneOf / anyOf 的报错信息很笼统，换成最贴近的那条子错误。"""
    if error.validator in ("oneOf", "anyOf") and error.context:
        return best_match(error.context)
    return error


def check(doc: object, report: Report) -> None:
    for error in sorted(validator().iter_errors(doc), key=lambda e: list(map(str, e.absolute_path))):
        detail = _explain(error)
        report.error("IS100", _path(detail) or _path(error), f"结构不符合规范：{detail.message}")
