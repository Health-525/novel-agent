# novel-agent

AI-driven Chinese novel writing assistant with Obsidian knowledge base.

写长篇网文的最大挑战是角色一致性——写到50章之后很容易忘记某个配角的口头禅、性格特征或关系变化。**novel-agent** 把角色档案存在 Obsidian vault 里，每次写作时自动将相关角色信息注入 LLM 上下文，确保角色不跑偏。

## Quick Start

```bash
# 安装
pip install -e .

# 配置 API key
cat > config.local.yaml << EOF
llm:
  provider: anthropic
  api_key: "sk-ant-xxx"
  model: claude-opus-4-7
EOF

# 创建项目
novel-agent project create "我的小说" --genre xianxia

# 添加角色
novel-agent character add "我的小说" 主角名

# 写章节
novel-agent chapter write "我的小说" 1
```

## 项目结构

```
novel-agent/
├── engine/             # 核心引擎
│   ├── context_builder.py   # 组装 LLM 写作上下文
│   ├── writer.py            # 调用 LLM 生成正文
│   ├── reviewer.py          # 角色一致性审校
│   ├── archive_updater.py   # 从新章节更新角色档案
│   ├── tts.py               # Edge TTS 语音合成
│   └── logging_setup.py     # 统一日志
├── knowledge/          # 数据持久化
│   ├── character.py         # 角色 .md 档案管理
│   ├── chapter.py           # 章节 .md 管理
│   ├── worldview.py         # 世界观文档
│   ├── obsidian_utils.py    # YAML frontmatter / wiki-link
│   └── vector_store.py      # 向量搜索（ChromaDB/内存）
├── llm/                # LLM 抽象层
│   ├── client.py            # Anthropic / OpenAI 统一接口
│   └── prompts.py           # 系统提示词模板
├── ui/                 # CLI
│   └── cli.py               # Typer 命令行
├── data/               # 小说项目数据
│   └── 修仙尽头是开源/      # 示例项目
├── tests/              # 测试
└── pyproject.toml
```

## CLI 命令

### 项目管理
```bash
novel-agent project create <name> [--genre]   # 创建新项目
novel-agent project info <name>               # 查看项目信息
```

### 角色管理
```bash
novel-agent character add <project> <name>    # 添加角色
novel-agent character list <project>          # 列出角色
novel-agent character show <project> <name>   # 查看角色详情
```

### 章节管理
```bash
novel-agent chapter create <project> <num>    # 创建章节大纲
novel-agent chapter write <project> <num>     # AI 生成章节
novel-agent chapter list <project>            # 列出章节
```

### TTS 语音合成
```bash
novel-agent tts read <project> <num> [--voice] [--output]  # 章节转 MP3
novel-agent tts voices                                      # 列出音色
```

音色别名：`nv`（活泼女声）、`nr`（叙事男声）、`nv2`（温柔女声）、`nr2`（沉稳男声）

## 角色档案格式

`characters/角色名.md` 使用 YAML frontmatter + 自由正文：

```yaml
---
name: 苏墨
age: 19
gender: 男
identity: 青岚宗杂役
appearance: 瘦削，手掌有劈柴厚茧
aliases: [小苏, 苏兄弟]
tags: [主角, 开源者]

personality:
  traits: [固执, 沉默, 一根筋]
  core_motivation: 让所有人都能修炼
  fears: [功法被封禁, 连累他人]

speech:
  habits: [话少但每句都在点上]
  style: 短句
  taboos: [不称"大人"]
  typical_lines: ["走吧", "功法不是我的"]

relationships:
  - target: "[[白芷]]"
    type: 师门
    state: 师妹，互相信任
  - target: "[[陆沉]]"
    type: 合作
    state: 功法源头，引路人

timeline:
  - chapter: 1
    event: 从陆沉手中获得开源功法玉简
  - chapter: 3
    event: 五百人同修共振，被动筑基
---

# 补充描述

（自由正文，用于补充 frontmatter 无法表达的细节）
```

## 配置

`config.yaml`（版本控制）和 `config.local.yaml`（本地私密配置，自动合并覆盖）：

```yaml
llm:
  provider: anthropic
  model: claude-opus-4-7
  max_tokens: 8192
  temperature: 0.8
  max_retries: 3

data:
  root: ./data
```

API key 可以通过 `config.local.yaml` 或环境变量 `ANTHROPIC_API_KEY` / `OPENAI_API_KEY` 设置。

## 开发

```bash
pip install -e ".[dev]"
pytest tests/ -v
```
