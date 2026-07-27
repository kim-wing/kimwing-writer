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
    "style/content-boundaries.md",
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
    "contentSafety",
    "endingPressure",
    "status",
}
VALID_STATUSES = {"planned", "drafted", "reviewed", "revised", "finalized"}
OPENING_HOOK_FIELDS = {
    "id",
    "readerQuestion",
    "stage",
    "clueOrConsequence",
    "nextChapterPull",
}
OPENING_HOOK_STAGES = {1: "plant", 2: "deepen", 3: "partial-payoff"}
CONTENT_SAFETY_FIELDS = {
    "explicitSexualContent",
    "gambling",
    "illegalDrugs",
    "modernRealWorldPolitics",
    "organizedCrime",
}
CONTENT_BOUNDARY_MARKERS = (
    "色情露骨",
    "赌博",
    "非法毒品",
    "现代现实政治",
    "黑社会",
)


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
        "contentPolicy",
        "status",
        "currentChapter",
    }
    missing = sorted(required - config.keys())
    if missing:
        errors.append("novel.json 缺少字段：" + "、".join(missing))
    if config.get("schemaVersion") != 2:
        errors.append("novel.json 的 schemaVersion 必须是 2；请先执行内容红线迁移")
    if config.get("contentPolicy") != "strict-clean":
        errors.append("novel.json 的 contentPolicy 必须是 'strict-clean'")
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


def validate_content_boundaries(root: Path, errors: list[str]) -> None:
    path = root / "style/content-boundaries.md"
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        errors.append(f"内容红线文件无法读取：{path}: {exc}")
        return
    if "policy: strict-clean" not in content:
        errors.append("style/content-boundaries.md 缺少 'policy: strict-clean' 标记")
    missing_markers = [marker for marker in CONTENT_BOUNDARY_MARKERS if marker not in content]
    if missing_markers:
        errors.append(
            "style/content-boundaries.md 缺少红线类别：" + "、".join(missing_markers)
        )


def validate_blueprints(root: Path, errors: list[str], warnings: list[str]) -> None:
    seen: set[int] = set()
    opening_hooks: dict[int, dict[str, Any]] = {}
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
        if "contentSafety" in data:
            content_safety = data["contentSafety"]
            if not isinstance(content_safety, dict):
                errors.append(f"{path.name} 的 contentSafety 必须是对象")
            else:
                missing_safety_fields = sorted(
                    CONTENT_SAFETY_FIELDS - content_safety.keys()
                )
                if missing_safety_fields:
                    errors.append(
                        f"{path.name} 的 contentSafety 缺少字段："
                        + "、".join(missing_safety_fields)
                    )
                for field in sorted(CONTENT_SAFETY_FIELDS & content_safety.keys()):
                    if content_safety.get(field) is not False:
                        errors.append(
                            f"{path.name} 的 contentSafety.{field} 必须是 false"
                        )
        if number in OPENING_HOOK_STAGES:
            hook = data.get("openingHook")
            if not isinstance(hook, dict):
                errors.append(f"{path.name} 的 openingHook 必须是对象")
            else:
                opening_hooks[number] = hook
                missing_hook_fields = sorted(OPENING_HOOK_FIELDS - hook.keys())
                if missing_hook_fields:
                    errors.append(
                        f"{path.name} 的 openingHook 缺少字段："
                        + "、".join(missing_hook_fields)
                    )
                for field in sorted(OPENING_HOOK_FIELDS - {"stage"}):
                    value = hook.get(field)
                    if not isinstance(value, str) or not value.strip():
                        errors.append(
                            f"{path.name} 的 openingHook.{field} 必须是非空字符串"
                        )
                expected_stage = OPENING_HOOK_STAGES[number]
                if hook.get("stage") != expected_stage:
                    errors.append(
                        f"{path.name} 的 openingHook.stage 必须是 {expected_stage!r}"
                    )
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

    opening_chapters = set(OPENING_HOOK_STAGES)
    if seen & opening_chapters:
        missing_chapters = sorted(opening_chapters - seen)
        if missing_chapters:
            errors.append(
                "开篇蓝图必须同时规划第 1–3 章；缺少第 "
                + "、".join(str(number) for number in missing_chapters)
                + " 章"
            )
        if opening_chapters <= opening_hooks.keys():
            hook_ids = {
                opening_hooks[number].get("id", "").strip()
                for number in opening_chapters
                if isinstance(opening_hooks[number].get("id"), str)
            }
            if len(hook_ids) != 1 or "" in hook_ids:
                errors.append("第 1–3 章必须共享同一个非空 openingHook.id")


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
        validate_content_boundaries(root, errors)
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
