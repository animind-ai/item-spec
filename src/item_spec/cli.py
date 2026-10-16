"""命令行：item-spec check 文件... [--scene 场景文件] [--units 单元表]

退出码：0 全部通过（可以有警告）；1 有错误；2 用法错误。
"""

from __future__ import annotations

import argparse
import json
import sys

from scene_spec.loader import SpecLoadError, load_file

from . import __version__, check_file


def _load_units(path: str) -> set[str]:
    """单元表：practice-engine 的 data/units.yaml（units: [{id: ...}, ...]），或者一个 id 列表。"""
    doc = load_file(path)
    rows = doc.get("units", []) if isinstance(doc, dict) else doc
    return {row["id"] if isinstance(row, dict) else str(row) for row in rows}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="item-spec", description="检查 item-spec 练习包文件")
    parser.add_argument("--version", action="version", version=f"item-spec {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)
    check = sub.add_parser("check", help="结构 + 语义检查")
    check.add_argument("files", nargs="+")
    check.add_argument("--scene", help="配套视频的 scene-spec 文件，核对预测题的 beat、单元和集数（只能配一个练习包）")
    check.add_argument("--units", help="单元表（如 practice-engine/data/units.yaml），核对单元编号是否存在")
    check.add_argument("--json", action="store_true", help="以 JSON 输出结果")
    check.add_argument("--strict", action="store_true", help="警告也算失败")
    args = parser.parse_args(argv)

    if args.scene and len(args.files) != 1:
        print("--scene 只能配一个练习包文件", file=sys.stderr)
        return 2
    kwargs: dict = {}
    try:
        if args.scene:
            kwargs["scene"] = load_file(args.scene)
        if args.units:
            kwargs["units"] = _load_units(args.units)
    except (OSError, SpecLoadError) as exc:
        print(f"无法读取 --scene / --units：{exc}", file=sys.stderr)
        return 2

    failed = False
    results = {}
    for name in args.files:
        try:
            report = check_file(name, **kwargs)
        except OSError as exc:
            print(f"{name}: 无法读取：{exc}", file=sys.stderr)
            return 2
        results[name] = report.to_dict()
        bad = not report.ok or (args.strict and report.warnings)
        failed = failed or bool(bad)
        if args.json:
            continue
        status = "通过" if not bad else "未通过"
        print(f"{name}: {status}（{len(report.errors)} 个错误，{len(report.warnings)} 个警告）")
        for issue in report.issues:
            print(f"  {issue}")
        if report.stats:
            print("  统计：" + "，".join(f"{k}={v}" for k, v in report.stats.items()))
    if args.json:
        print(json.dumps(results, ensure_ascii=False, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
