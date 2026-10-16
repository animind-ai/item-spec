"""item-spec：数学练习题的结构化描述格式。

    from item_spec import check_file
    report = check_file("examples/ep21.items.yaml")
    report.ok, report.errors, report.warnings
"""

from __future__ import annotations

from pathlib import Path

from scene_spec.loader import SpecLoadError, load_text
from scene_spec.report import Issue, Report

from . import semantic, structure

__all__ = ["check", "check_file", "check_text", "load_file", "Issue", "Report", "SPEC_VERSION"]
__version__ = "0.1.0"
SPEC_VERSION = "0.1"


def check(doc: object, *, scene: dict | None = None, units: set[str] | None = None) -> Report:
    """对已经读成 Python 对象的练习包做结构检查；通过后再做语义检查。

    scene：配套视频的 scene-spec 文档（可选），用来核对预测题的 beat 和单元。
    units：已知的单元编号（可选），例如 practice-engine 的 data/units.yaml 里的全部 id。
    """
    report = Report()
    structure.check(doc, report)
    if report.ok:
        semantic.check(doc, report, scene=scene, units=units)
    return report


def _renumber(report: Report) -> Report:
    """读取器沿用 scene-spec 的实现，问题代码换成本规范的 IS 前缀。"""
    out = Report()
    for issue in report.issues:
        code = "IS" + issue.code[2:] if issue.code.startswith("SS") else issue.code
        out.issues.append(Issue(issue.level, code, issue.path, issue.message))
    return out


def load_text_doc(text: str) -> object:
    """读取受限 YAML；失败时抛 SpecLoadError，问题代码为 IS000–IS003。"""
    try:
        return load_text(text)
    except SpecLoadError as exc:
        raise SpecLoadError(_renumber(exc.report)) from exc


def load_file(path: str | Path) -> object:
    return load_text_doc(Path(path).read_text(encoding="utf-8"))


def check_text(text: str, **kwargs) -> Report:
    try:
        doc = load_text_doc(text)
    except SpecLoadError as exc:
        return exc.report
    if isinstance(doc, dict) and doc.get("spec") not in (None, SPEC_VERSION):
        report = Report()
        report.error("IS010", "spec", f"本工具只认 item-spec {SPEC_VERSION}，文件写的是 {doc.get('spec')!r}")
        return report
    return check(doc, **kwargs)


def check_file(path: str | Path, **kwargs) -> Report:
    return check_text(Path(path).read_text(encoding="utf-8"), **kwargs)
