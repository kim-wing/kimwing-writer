#!/usr/bin/env python3
"""Report potentially mechanical prose patterns; never infer authorship."""

from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class Rule:
    name: str
    pattern: str
    threshold: int
    severity: str
    note: str


@dataclass
class Hit:
    line: int
    column: int
    severity: str
    rule: str
    excerpt: str
    note: str


RULES = [
    Rule(
        "模板化收束",
        r"命运的齿轮|一切才刚刚开始|故事(?:才)?刚刚开始|真正的考验(?:才)?刚刚开始",
        1,
        "strong",
        "结尾或段尾可能使用了通用总结模板。",
    ),
    Rule(
        "通用身体反应",
        r"瞳孔(?:猛地|骤然|微微)?(?:一缩|收缩)|呼吸(?:猛地|骤然)?一滞|心头一震|脊背一凉|空气(?:仿佛)?凝固",
        2,
        "medium",
        "身体反应可能替代了人物独有的行为。",
    ),
    Rule(
        "显性比喻连接词",
        r"仿佛|犹如|宛如",
        4,
        "medium",
        "显性比喻较密，检查意象是否来自人物经验且彼此相关。",
    ),
    Rule(
        "固定转场词",
        r"就在这时|与此同时|下一秒|然而|话音未落",
        5,
        "weak",
        "转折可能依赖固定连接词，检查能否由动作或因果自然完成。",
    ),
    Rule(
        "认知总结",
        r"(?:他|她|我)(?:终于)?(?:知道|明白|意识到)[，,：:]",
        3,
        "medium",
        "旁白可能在总结人物已经表现出的认知。",
    ),
    Rule(
        "泛化时刻",
        r"这一刻|此时此刻",
        3,
        "weak",
        "检查该时刻是否有具体变化，而非泛化强调。",
    ),
    Rule(
        "下意识反应",
        r"不由得|下意识地?|莫名地",
        4,
        "weak",
        "可能用泛化副词跳过了动作或心理因果。",
    ),
    Rule(
        "翻转句式",
        r"不是[^。！？\n]{1,30}(?:而是|是)[^。！？\n]{1,30}",
        3,
        "weak",
        "高密度翻转句式容易形成解释腔或伪深刻。",
    ),
    Rule(
        "意义升华",
        r"(?:真正的意义|这意味着|归根结底|本质上)[^。！？\n]{0,40}",
        2,
        "medium",
        "检查叙述者是否替人物或读者过度总结。",
    ),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="检查小说文本中的机械化写作模式")
    parser.add_argument("file", help="UTF-8 文本或 Markdown 文件")
    parser.add_argument("--json", action="store_true", help="输出 JSON")
    return parser.parse_args()


def coefficient_of_variation(values: list[int]) -> float | None:
    if len(values) < 2:
        return None
    mean = statistics.mean(values)
    if mean == 0:
        return None
    return statistics.pstdev(values) / mean


def location(text: str, offset: int) -> tuple[int, int]:
    line = text.count("\n", 0, offset) + 1
    previous_newline = text.rfind("\n", 0, offset)
    column = offset + 1 if previous_newline == -1 else offset - previous_newline
    return line, column


def excerpt(text: str, start: int, end: int, radius: int = 30) -> str:
    left = max(0, start - radius)
    right = min(len(text), end + radius)
    return re.sub(r"\s+", " ", text[left:right]).strip()


def collect_pattern_hits(text: str) -> list[Hit]:
    hits: list[Hit] = []
    for rule in RULES:
        matches = list(re.finditer(rule.pattern, text))
        if len(matches) < rule.threshold:
            continue
        for match in matches:
            line, column = location(text, match.start())
            hits.append(
                Hit(
                    line=line,
                    column=column,
                    severity=rule.severity,
                    rule=rule.name,
                    excerpt=excerpt(text, match.start(), match.end()),
                    note=rule.note,
                )
            )
    return sorted(hits, key=lambda item: (item.line, item.column, item.rule))


def rhythm_metrics(text: str) -> dict[str, object]:
    sentences = [part.strip() for part in re.split(r"[。！？!?…]+", text) if len(part.strip()) >= 2]
    paragraphs = [re.sub(r"\s+", "", part) for part in re.split(r"\n\s*\n", text) if part.strip()]
    sentence_lengths = [len(item) for item in sentences]
    paragraph_lengths = [len(item) for item in paragraphs]
    sentence_cv = coefficient_of_variation(sentence_lengths)
    paragraph_cv = coefficient_of_variation(paragraph_lengths)
    warnings: list[str] = []
    if len(sentence_lengths) >= 12 and sentence_cv is not None and sentence_cv < 0.28:
        warnings.append("句长分布较均匀；结合场景压力检查节奏是否缺少变化。")
    if len(paragraph_lengths) >= 6 and paragraph_cv is not None and paragraph_cv < 0.25:
        warnings.append("段长分布较均匀；检查排版是否被固定模板控制。")

    starts: dict[str, int] = {}
    for paragraph in paragraphs:
        key = paragraph[:4]
        if len(key) == 4:
            starts[key] = starts.get(key, 0) + 1
    repeated_starts = {key: count for key, count in starts.items() if count >= 3}
    if repeated_starts:
        warnings.append("多个段落使用相同开头：" + "、".join(f"{k}×{v}" for k, v in repeated_starts.items()))

    return {
        "sentenceCount": len(sentence_lengths),
        "sentenceMean": round(statistics.mean(sentence_lengths), 2) if sentence_lengths else 0,
        "sentenceCV": round(sentence_cv, 3) if sentence_cv is not None else None,
        "paragraphCount": len(paragraph_lengths),
        "paragraphMean": round(statistics.mean(paragraph_lengths), 2) if paragraph_lengths else 0,
        "paragraphCV": round(paragraph_cv, 3) if paragraph_cv is not None else None,
        "warnings": warnings,
    }


def main() -> int:
    args = parse_args()
    path = Path(args.file).expanduser()
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        print(f"错误：无法读取 {path}: {exc}", file=sys.stderr)
        return 2

    hits = collect_pattern_hits(text)
    metrics = rhythm_metrics(text)
    report = {
        "file": str(path.resolve()),
        "characterCount": len(re.sub(r"\s+", "", text)),
        "disclaimer": "本报告只标记机械化风格线索，不判断文本来源，也不能证明内容由 AI 生成。",
        "hits": [asdict(item) for item in hits],
        "rhythm": metrics,
    }

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
        return 0

    print("作者化文本诊断")
    print(report["disclaimer"])
    print(f"文件：{report['file']}")
    print(f"字符数：{report['characterCount']}；命中线索：{len(hits)}")
    for index, item in enumerate(hits, start=1):
        print(f"\n{index}. 第 {item.line} 行，第 {item.column} 列 [{item.severity}] {item.rule}")
        print(f"   > {item.excerpt}")
        print(f"   {item.note}")
    for warning in metrics["warnings"]:
        print(f"\n节奏提示：{warning}")
    if not hits and not metrics["warnings"]:
        print("未发现达到阈值的机械化模式；不要为了输出报告而硬改。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
