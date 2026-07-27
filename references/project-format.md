# 小说项目格式

## 目录

```text
project/
├── novel.json
├── architecture/
│   ├── premise.md
│   ├── characters.json
│   ├── world.md
│   └── outline.md
├── style/
│   ├── author-voice.md
│   ├── content-boundaries.md
│   └── negative-constraints.md
├── blueprints/
│   └── chapter-0001.json
├── chapters/
│   └── chapter-0001/
│       ├── draft.md
│       ├── review.json
│       ├── revised.md
│       ├── final.md
│       └── notes.md
├── memory/
│   ├── timeline.jsonl
│   ├── character-states.json
│   ├── knowledge-ledger.jsonl
│   ├── foreshadowing.json
│   ├── open-loops.json
│   └── author-decisions.md
└── exports/
```

## `novel.json`

必须包含：

```json
{
  "schemaVersion": 2,
  "title": "书名",
  "genre": "mystery",
  "style": "restrained",
  "pov": "third-limited",
  "targetAudience": "",
  "plannedChapters": 100,
  "wordsPerChapter": 2500,
  "batchLimit": 3,
  "contentPolicy": "strict-clean",
  "status": "planning",
  "currentChapter": 0,
  "createdAt": "ISO-8601",
  "updatedAt": "ISO-8601"
}
```

不要在配置文件里保存 API Key、个人隐私或平台凭据。

`contentPolicy` 必须为 `strict-clean`，并且 `style/content-boundaries.md` 必须保留 `policy: strict-clean` 标记。详细边界见 [content-safety.md](content-safety.md)。

## 角色卡

`architecture/characters.json` 使用：

```json
{
  "characters": [
    {
      "name": "角色名",
      "role": "protagonist",
      "surfaceGoal": "表面目标",
      "deepNeed": "深层需求",
      "fear": "恐惧",
      "secret": "秘密",
      "abilities": [],
      "limits": [],
      "relationships": [],
      "arc": "变化弧",
      "voice": {
        "rhythm": "说话节奏",
        "vocabulary": [],
        "avoid": [],
        "subtextHabit": "隐藏意图的方式"
      }
    }
  ]
}
```

动态状态只写入 `memory/character-states.json`，不要把当前伤势或位置混入静态人物设定。

## 章节蓝图与前三章钩子

所有章节蓝图使用 `SKILL.md` 定义的基础字段。第 1–3 章还必须包含：

```json
{
  "openingHook": {
    "id": "opening-core-01",
    "readerQuestion": "读者最想知道的具体问题",
    "stage": "plant",
    "clueOrConsequence": "本章新增的线索、排除项或可见后果",
    "nextChapterPull": "继续阅读下一章的即时理由"
  }
}
```

- 三章的 `id` 必须相同，表示它们推进同一个核心好奇问题。
- `stage` 按章节依次为 `plant`、`deepen`、`partial-payoff`。
- 四个值都必须是非空字符串，不能用“待定”“之后揭晓”等占位语。
- 第一章出现钩子后，第二章必须增加证据或代价，第三章必须给出部分答案或可验证后果。
- 第 4 章以后可以省略 `openingHook`，继续使用 `endingPressure` 管理章末余压。

所有章节蓝图都必须包含以下对象，五个值只能是布尔值 `false`：

```json
{
  "contentSafety": {
    "explicitSexualContent": false,
    "gambling": false,
    "illegalDrugs": false,
    "politics": false,
    "organizedCrime": false
  }
}
```

该对象是写作前的明确确认，不替代语义审稿。无法确认任一项为 `false` 时，停止进入正文。

## 记忆规则

- `timeline.jsonl`：每行一个已定稿事实，必须含 `chapter`、`sequence`、`event`、`consequence`。
- `knowledge-ledger.jsonl`：记录 `character`、`knows`、`believes`、`sourceChapter`；区分事实和误解。
- `foreshadowing.json`：每项含 `id`、`setup`、`plantedAt`、`expectedWindow`、`status`、`resolution`。
- `open-loops.json`：记录尚未解决的目标、威胁、承诺和读者问题。
- `author-decisions.md`：记录作者确认的重大选择、禁区和变更理由。

只从 `final.md` 更新上述记忆。保留来源章节和不确定性，不把模型推测写入正史。

## 状态流

章节蓝图的 `status` 只能按下列方向推进：

```text
planned -> drafted -> reviewed -> revised -> finalized
```

允许从 `reviewed` 返回 `drafted`，或从 `revised` 返回 `reviewed`。定稿后如需改写，先记录作者决定，再产生新修订版本；不要悄悄覆盖正史。

## 打开项目

1. 运行 `scripts/validate_project.py`。
2. 读取 `novel.json` 和当前任务所需资产。
3. 以最新 `finalized` 章节确定正史断点，不以文件修改时间猜测。
4. 发现格式较旧时先备份并迁移，不在未知结构上批量写入。
5. 若旧项目的前三章缺少 `openingHook`，先从定稿内容回填真实钩子推进，不为通过校验虚构未发生的线索。
6. 将旧项目迁移到 `schemaVersion: 2` 时，先备份项目，再添加 `contentPolicy` 和 `style/content-boundaries.md`，逐章审查后回填 `contentSafety`；不要批量写入虚假的 `false`。
