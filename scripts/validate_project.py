#!/usr/bin/env python3
"""Validate a Kimwing Writer project without changing it."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


REQUIRED_FILES = [
    "novel.json",
    "architecture/premise.md",
    "architecture/characters.json",
    "architecture/world.md",
    "architecture/outline.md",
    "style/author-voice.md",
    "style/negative-constraints.md",
    "memory/timeline.jsonl",
    "memory/character-states.json",
    "memory/knowledge-ledger.jsonl",
    "memory/foreshadowing.json",
    "memory/open-loops.json",
    "memory/author-decisions.md",
]

REQUIRED_DIRS = ["blueprints", "chapters", "exports"]
BLUEPRINT_FIELDS = {
    "chapterNumber",
    "title",
    "purpose",
    "conflict",
    "turn",
    "keyEvents",
    "characters",
    "knowledgeChanges",
    "continuityChecks",
    "endingPressure",
    "status",
}
VALID_STATUSES = {"planned", "drafted", "reviewed", "revised", "finalized"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="校验 Kimwing Writer 小说项目")
    parser.add_argument("project_dir")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    return parser.parse_args()


def load_json(path: Path, errors: list[str]) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        errors.append(f"JSON 无法读取：{path}: {exc}")
        return None


def validate_config(root: Path, errors: list[str], warnings: list[str]) -> None:
    config = load_json(root / "novel.json", errors)
    if not isinstance(config, dict):
        return
    required = {
        "schemaVersion",
        "title",
        "genre",
        "style",
        "pov",
        "plannedChapters",
        "wordsPerChapter",
        "batchLimit",
        "status",
        "currentChapter",
    }
    missing = sorted(required - config.keys())
    if missing:
        errors.append("novel.json 缺少字段：" + "、".join(missing))
    if config.get("schemaVersion") != 1:
        warnings.append(f"未知 schemaVersion：{config.get('schemaVersion')}")
    for field in ("plannedChapters", "wordsPerChapter", "batchLimit"):
        value = config.get(field)
        if not isinstance(value, int) or value <= 0:
            errors.append(f"novel.json 的 {field} 必须是正整数")
    if isinstance(config.get("batchLimit"), int) and config["batchLimit"] > 5:
        warnings.append("batchLimit 大于 5，长篇连贯性和作者化质量可能下降")


def validate_json_container(root: Path, relative: str, key: str, errors: list[str]) -> None:
    data = load_json(root / relative, errors)
    if data is not None and (not isinstance(data, dict) or not isinstance(data.get(key), list)):
        errors.append(f"{relative} 必须是包含数组字段 {key!r} 的对象")


def validate_jsonl(path: Path, errors: list[str]) -> None:
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        errors.append(f"JSONL 无法读取：{path}: {exc}")
        return
    for number, line in enumerate(lines, start=1):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            errors.append(f"{path.name} 第 {number} 行不是有效 JSON：{exc}")
            continue
        if not isinstance(value, dict):
            errors.append(f"{path.name} 第 {number} 行必须是 JSON 对象")


def validate_blueprints(root: Path, errors: list[str], warnings: list[str]) -> None:
    seen: set[int] = set()
    for path in sorted((root / "blueprints").glob("chapter-*.json")):
        data = load_json(path, errors)
        if not isinstance(data, dict):
            continue
        missing = sorted(BLUEPRINT_FIELDS - data.keys())
        if missing:
            errors.append(f"{path.name} 缺少字段：{'、'.join(missing)}")
        number = data.get("chapterNumber")
        if not isinstance(number, int) or number <= 0:
            errors.append(f"{path.name} 的 chapterNumber 必须是正整数")
            continue
        if number in seen:
            errors.append(f"章节编号重复：{number}")
        seen.add(number)
        expected = f"chapter-{number:04d}.json"
        if path.name != expected:
            warnings.append(f"蓝图文件名与章节编号不一致：{path.name}，建议 {expected}")
        status = data.get("status")
        if status not in VALID_STATUSES:
            errors.append(f"{path.name} 的 status 无效：{status}")
        chapter_dir = root / "chapters" / f"chapter-{number:04d}"
        stage_files = {
            "drafted": "draft.md",
            "reviewed": "review.json",
            "revised": "revised.md",
            "finalized": "final.md",
        }
        if status in stage_files and not (chapter_dir / stage_files[status]).is_file():
            errors.append(f"{path.name} 状态为 {status}，但缺少 {chapter_dir / stage_files[status]}")
        if status == "finalized" and not (chapter_dir / "notes.md").is_file():
            errors.append(f"{path.name} 已定稿，但缺少 {chapter_dir / 'notes.md'}")


def main() -> int:
    args = parse_args()
    root = Path(args.project_dir).expanduser().resolve()
    errors: list[str] = []
    warnings: list[str] = []

    if not root.is_dir():
        errors.append(f"项目目录不存在：{root}")
    else:
        for relative in REQUIRED_FILES:
            if not (root / relative).is_file():
                errors.append(f"缺少文件：{relative}")
        for relative in REQUIRED_DIRS:
            if not (root / relative).is_dir():
                errors.append(f"缺少目录：{relative}")

    if not errors:
        validate_config(root, errors, warnings)
        validate_json_container(root, "architecture/characters.json", "characters", errors)
        validate_json_container(root, "memory/character-states.json", "characters", errors)
        validate_json_container(root, "memory/foreshadowing.json", "items", errors)
        validate_json_container(root, "memory/open-loops.json", "items", errors)
        validate_jsonl(root / "memory/timeline.jsonl", errors)
        validate_jsonl(root / "memory/knowledge-ledger.jsonl", errors)
        if (root / "blueprints").is_dir():
            validate_blueprints(root, errors, warnings)

    report = {
        "project": str(root),
        "ok": not errors,
        "errors": errors,
        "warnings": warnings,
    }
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"项目：{root}")
        print("结果：" + ("通过" if not errors else "失败"))
        for item in errors:
            print(f"错误：{item}")
        for item in warnings:
            print(f"警告：{item}")
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
