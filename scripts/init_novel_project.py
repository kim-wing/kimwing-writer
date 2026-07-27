#!/usr/bin/env python3
"""Initialize a file-based Kimwing Writer novel project without overwriting data."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


GENRES = {
    "xuanhuan",
    "xianxia",
    "science-fiction",
    "fantasy",
    "urban",
    "modern-romance",
    "historical-romance",
    "mystery",
    "history",
    "horror",
    "realist",
}

STYLES = {
    "fast-web",
    "restrained",
    "delicate",
    "classical",
    "cinematic",
    "hard-edged",
    "humorous",
    "lyrical",
    "documentary",
    "ensemble",
}

POVS = {"first-person", "third-limited", "third-omniscient", "multi-pov"}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="创建 Kimwing Writer 小说项目")
    parser.add_argument("project_dir", help="新项目目录；必须不存在或为空")
    parser.add_argument("--title", required=True, help="小说暂定名")
    parser.add_argument("--genre", choices=sorted(GENRES), default="mystery")
    parser.add_argument("--style", choices=sorted(STYLES), default="restrained")
    parser.add_argument("--pov", choices=sorted(POVS), default="third-limited")
    parser.add_argument("--target-audience", default="")
    parser.add_argument("--planned-chapters", type=int, default=100)
    parser.add_argument("--words-per-chapter", type=int, default=2500)
    parser.add_argument("--idea", default="", help="一句话灵感，可留空")
    return parser.parse_args()


def write_text(path: Path, content: str) -> None:
    if path.exists():
        raise FileExistsError(f"拒绝覆盖已有文件：{path}")
    path.write_text(content, encoding="utf-8")


def write_json(path: Path, value: object) -> None:
    write_text(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def main() -> int:
    args = parse_args()
    if args.planned_chapters <= 0:
        print("错误：--planned-chapters 必须大于 0", file=sys.stderr)
        return 2
    if args.words_per_chapter < 300:
        print("错误：--words-per-chapter 不应小于 300", file=sys.stderr)
        return 2

    root = Path(args.project_dir).expanduser().resolve()
    if root.exists() and (not root.is_dir() or any(root.iterdir())):
        print(f"错误：目标目录必须不存在或为空：{root}", file=sys.stderr)
        return 2

    root.mkdir(parents=True, exist_ok=True)
    for relative in (
        "architecture",
        "style",
        "blueprints",
        "chapters",
        "memory",
        "exports",
    ):
        (root / relative).mkdir()

    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    write_json(
        root / "novel.json",
        {
            "schemaVersion": 2,
            "title": args.title,
            "genre": args.genre,
            "style": args.style,
            "pov": args.pov,
            "targetAudience": args.target_audience,
            "plannedChapters": args.planned_chapters,
            "wordsPerChapter": args.words_per_chapter,
            "batchLimit": 3,
            "contentPolicy": "strict-clean",
            "status": "planning",
            "currentChapter": 0,
            "createdAt": now,
            "updatedAt": now,
        },
    )

    idea = args.idea.strip() or "（由作者补充）"
    write_text(
        root / "architecture/premise.md",
        f"""# 故事前提

## 原始灵感

{idea}

## 一句话前提

（当谁遭遇什么，必须做什么，否则会失去什么）

## 主角欲望与深层需求

（待补充）

## 核心冲突与失败代价

（待补充）

## 独特卖点与深层问题

（待补充）
""",
    )
    write_json(root / "architecture/characters.json", {"characters": []})
    write_text(
        root / "architecture/world.md",
        """# 世界观

## 核心规则与边界

（待补充）

## 资源、阶层与权力

（待补充）

## 地理、历史与被掩盖的事实

（待补充）

## 能力或技术的成本与失败条件

（待补充）
""",
    )
    write_text(
        root / "architecture/outline.md",
        """# 全书大纲

## 开局状态

（待补充）

## 触发事件

（待补充）

## 主要结构阶段

（逐阶段记录决定、代价、局势变化与信息揭露）

## 终局选择与余波

（待补充）
""",
    )
    write_text(
        root / "style/author-voice.md",
        f"""# 作者声纹

- 基础文笔：{args.style}
- 叙事视角：{args.pov}
- 声音关键词：（待补充）
- 句长与段长：（待补充）
- 叙述距离：（待补充）
- 对白习惯：（待补充）
- 描写优先级：（待补充）
- 核心意象：（待补充）
- 刻意保留的不规则：（待补充）
- 主要角色声音差异：（待补充）
""",
    )
    write_text(
        root / "style/content-boundaries.md",
        """# 内容红线

policy: strict-clean

- 严禁色情露骨内容；正常克制的恋爱描写可以保留，亲密场景点到为止或淡出。
- 严禁赌博及相关场所、下注、赌债、玩法和获利机制。
- 严禁非法毒品及相关制造、交易、使用和美化。
- 严禁现实或虚构政治人物、组织、事件、斗争、宣传和影射。
- 严禁黑社会、帮派及其他有组织犯罪相关设定、人物和情节。

命中任一项时停止该方向，使用不含禁区的关系、职业、自然环境、技术限制或个人选择冲突替代。
""",
    )
    write_text(
        root / "style/negative-constraints.md",
        """# 负面约束

- 不用旁白重复解释已经通过动作或对白表达的情绪。
- 不强迫每段收束成金句。
- 不固定使用神秘来客、突发声响或震惊台词断章。
- 不把人物未知的信息写进其内心或行动依据。
- 不为凑字数增加无功能五感、动作步骤或世界观说明。

## 项目专属禁用表达

（由作者补充）
""",
    )

    write_text(root / "memory/timeline.jsonl", "")
    write_json(root / "memory/character-states.json", {"characters": []})
    write_text(root / "memory/knowledge-ledger.jsonl", "")
    write_json(root / "memory/foreshadowing.json", {"items": []})
    write_json(root / "memory/open-loops.json", {"items": []})
    write_text(
        root / "memory/author-decisions.md",
        "# 作者决定\n\n记录已批准的重大选择、禁区、设定变更及其理由。\n",
    )

    print(f"已创建 Kimwing Writer 项目：{root}")
    print(f"题材={args.genre} 文笔={args.style} 视角={args.pov}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
