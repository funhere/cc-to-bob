# cc-to-bob

English: [README.md](README.md)

**[Claude Code](https://claude.ai/code) の Skill を [IBM Bob](https://bob.ibm.com) の Skill に変換します。**

Claude Code と IBM Bob はどちらも `SKILL.md` ベースの Skill 形式を採用していますが、
フロントマターのルール、ディレクトリ構成、推奨される記述スタイルに違いがあります。
`cc-to-bob` はその差分を自動で吸収します。データ欠落なし、手動編集なしで移行できます。

```
.claude/skills/my-skill/   →   cc2bob   →   .bob/skills/my-skill/
```

[![CI](https://github.com/funhere/cc-to-bob/actions/workflows/ci.yml/badge.svg)](https://github.com/funhere/cc-to-bob/actions)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## 目次

- [このツールが必要な理由](#このツールが必要な理由)
- [形式の違いをひと目で確認](#形式の違いをひと目で確認)
- [インストール](#インストール)
- [クイックスタート](#クイックスタート)
- [ツール 1 — cc2bob (convert.py)](#ツール-1--cc2bob-convertpy)
- [ツール 2 — cc2bob-restep (restep.py)](#ツール-2--cc2bob-restep-resteppy)
- [典型的な移行ワークフロー](#典型的な移行ワークフロー)
- [Claude Code / Bob Skill として使う](#claude-code--bob-skill-として使う)
- [テストの実行](#テストの実行)
- [プロジェクト構成](#プロジェクト構成)
- [コントリビュート](#コントリビュート)
- [ライセンス](#ライセンス)

---

## このツールが必要な理由

Claude Code と IBM Bob の Skill は共通点が多く、どちらも Markdown 本文の上に
YAML フロントマター（`name`, `description`）を持つ `SKILL.md` ファイルを中心に、
必要に応じて補助ファイルを添える構成です。単純コピーでも一見動きそうですが、
細かい差異によって問題が起きます。

| 問題 | 影響 |
|---|---|
| Bob はフロントマターから `name` と `description` しか読み取らない | `license`, `compatibility`, `allowed-tools` などの追加キーは黙って無視され、情報が失われる |
| Bob は `description` がない Skill を無視する | 複数行ブロックスカラーの `description: >` が空として解釈される場合がある |
| Bob のドキュメントでは順序付き手順に `<Steps>` / `<Step>` を推奨している | Markdown の番号付きリストでも動くが、Bob 流の書き方としては不自然に見える |

`cc-to-bob` はこの 3 点を自動で解決します。

---

## 形式の違いをひと目で確認

| | Claude Code | IBM Bob |
|---|---|---|
| Skill ディレクトリ | `.claude/skills/` または `~/.claude/skills/` | `.bob/skills/` または `~/.bob/skills/` |
| フロントマターのキー | `name`, `description`, その他任意 | **`name` と `description` のみ** |
| `description` の形式 | 複数行ブロックスカラー可 | 1 行である必要がある |
| 補助ファイル | `scripts/`, `references/`, `assets/` などをネスト可能 | `SKILL.md` と同階層にフラット配置が基本（ネストも動作はする） |
| 手順のマークアップ | 通常の Markdown リスト | `<Steps>` / `<Step>` 推奨 |
| 実行要件 | 常に利用可能 | **Advanced mode が必要** |

---

## インストール

**要件:** Python 3.9 以上。サードパーティ依存なし。

### オプション A — pip（推奨）

```bash
pip install cc-to-bob
```

以下の 2 つのコマンドがグローバルに利用可能になります。

```
cc2bob          # 形式変換ツール
cc2bob-restep   # 任意の Steps 再構成ツール
```

### オプション B — リポジトリから直接実行

```bash
git clone https://github.com/funhere/cc-to-bob.git
cd cc-to-bob

# converter
python cc_to_bob/convert.py --help

# Steps restructurer
python cc_to_bob/restep.py --help
```

### オプション C — 開発用 editable install

```bash
git clone https://github.com/funhere/cc-to-bob.git
cd cc-to-bob
pip install -e ".[dev]"
```

---

## クイックスタート

```bash
# 単一 Skill を変換
cc2bob ~/.claude/skills/my-skill/ -o ~/.bob/skills/

# すべての Skill を一括変換
cc2bob ~/.claude/skills/ -o ~/.bob/skills/ --batch

# その後、必要に応じて順序付き手順を Bob の <Steps> スタイルへ再構成
cc2bob-restep ~/.bob/skills/my-skill/SKILL.md -i
```

---

## ツール 1 — `cc2bob` (convert.py)

Claude Code の Skill を IBM Bob 形式へ変換します。このツールは次を処理します。

- **フロントマター正規化** — `name` と `description` 以外のキーを除去し、
  追加情報は本文中の blockquote ノートへ移して情報欠落を防ぎます。
- **description の 1 行化** — 複数行ブロックスカラーを 1 行へ畳み込みます。
- **ファイルコピー** — すべての補助ファイルをコピーし、`evals/` ディレクトリは黙ってスキップします。

### 概要

```
cc2bob <input> -o <output> [options]
```

| 引数 / フラグ | 説明 |
|---|---|
| `input` | Skill フォルダ、`SKILL.md` ファイル、または（`--batch` 使用時）複数 Skill フォルダを含むディレクトリ |
| `-o / --output` | 出力先ディレクトリ。例: `~/.bob/skills` |
| `--batch` | `input` を複数 Skill フォルダのルートとして扱い、すべて変換する |
| `--flatten` | `scripts/`, `references/`, `assets/` を Skill ルートへ持ち上げ、`SKILL.md` 内のパス参照も書き換える |
| `--note-advanced-mode` | Bob の Advanced mode が必要であることを示す注意書きを先頭に追加する |

### 例

```bash
# 単一 Skill フォルダ
cc2bob ./my-skill/ -o ./bob-skills/

# 単一 SKILL.md ファイル
cc2bob ./my-skill/SKILL.md -o ./bob-skills/

# 一括: skills ディレクトリ全体
cc2bob ~/.claude/skills/ -o ~/.bob/skills/ --batch

# フラット構成（補助ファイルをルートへ集約）
cc2bob ./my-skill/ -o ./bob-skills/ --flatten

# Advanced mode の注意書きを追加（チーム共有時に便利）
cc2bob ~/.claude/skills/ -o ~/.bob/skills/ --batch --note-advanced-mode
```

### 追加のフロントマターキーはどうなるか

Claude Code の Skill には、Bob が認識しないメタデータが含まれていることがあります。

```yaml
# Before (Claude Code)
---
name: pdf-filler
description: >
  Fill PDF forms from structured data.
license: MIT
compatibility: Python 3.10+
allowed-tools:
  - bash
---
```

`cc2bob` はこれらの追加キーを本文先頭の blockquote ノートへ移動します。
情報は保持され、Bob のフロントマター制約も満たせます。

```yaml
# After (IBM Bob)
---
name: pdf-filler
description: Fill PDF forms from structured data.
---

> **Compatibility & metadata** (carried over from the original Claude Code skill):
>
> - `license`: MIT
> - `compatibility`: Python 3.10+
> - `allowed-tools`: bash
```

### 終了コード

| コード | 意味 |
|---|---|
| `0` | すべての Skill が正常に変換された |
| `1` | 使い方または入力エラー |
| `2` | 何も変換されなかった（すべて失敗、または対象が見つからない） |

`--batch` モードでは、個別 Skill の失敗は報告されたうえでスキップされます。
少なくとも 1 つ成功していれば、プロセス全体は `0` で終了します。

---

## ツール 2 — `cc2bob-restep` (restep.py)

変換済み `SKILL.md` 内の連続した手順を、Bob でより自然な
`<Steps>` / `<Step>` 形式へ再構成します。これは **別の任意ステップ** です。
`cc2bob` の後に実行し、Bob 固有のマークアップが必要な場合だけ使ってください。

### なぜ分離されているのか

再構成は無条件に適用すると文章の意味を変えてしまう可能性があります。
独立ツールにしているため、各変換結果を個別にレビューでき、
Markdown リストのままで十分な Skill では完全に省略できます。

### 保守的なデフォルト動作

デフォルトでは `cc2bob-restep` は **順序付きリスト**（`1.` `2.` `3.`）のみを変換し、
しかもそれが **手順系の見出し** の直下にある場合に限ります。

> workflow · steps · procedure · process · instructions · usage · how to ·
> 流程 · 步骤 · 操作步骤 · 安装步骤 · …

以下には **一切触れません**。

- 表
- フェンス付きコードブロック
- blockquote / callout ノート
- 手順見出しの下にない順序付きリスト
- 参照一覧のように見えるリスト

### 概要

```
cc2bob-restep <input> [options]
```

| フラグ | 説明 |
|---|---|
| `-i / --in-place` | ファイルを直接編集する（デフォルトは stdout に出力） |
| `--aggressive` | 連続する命令文段落（Run…, Create…, Check…）も変換対象にする |
| `-q / --quiet` | stderr の変換レポートを抑制する |

### 例

```bash
# 変更内容を確認（dry run）
cc2bob-restep ~/.bob/skills/deploy/SKILL.md

# 直接編集
cc2bob-restep ~/.bob/skills/deploy/SKILL.md -i

# aggressive モード（命令文段落も対象）
cc2bob-restep ~/.bob/skills/setup/SKILL.md -i --aggressive

# レポートを抑制
cc2bob-restep ~/.bob/skills/deploy/SKILL.md -i --quiet
```

### 変換例

```markdown
## Workflow

1. Build the artifact with `make build`.
2. Run the test suite and confirm it passes.
3. Tag the commit and push to the registry.
```

以下のように変換されます。

```markdown
## Workflow

<Steps>
<Step>
Build the artifact with `make build`.
</Step>

<Step>
Run the test suite and confirm it passes.
</Step>

<Step>
Tag the commit and push to the registry.
</Step>
</Steps>
```

変換レポートには、どの領域が変更されたかが明示されます。

```
--- restep report for deploy/SKILL.md ---
  • Converted a 3-item ordered list under heading "Workflow" into <Steps>.
```

---

## 典型的な移行ワークフロー

```bash
# Step 1: 形式変換
cc2bob ~/.claude/skills/ -o ~/.bob/skills/ --batch

# Step 2: Claude 固有のツール参照が残っていないか出力を確認
# （コンバータは忠実にテキストを移すが、Bob 側のツール構成までは判断できない）
ls ~/.bob/skills/

# Step 3（任意）: 手順を <Steps> に再構成
# Skill ごとに、まずプレビューしてから適用
cc2bob-restep ~/.bob/skills/my-skill/SKILL.md        # preview
cc2bob-restep ~/.bob/skills/my-skill/SKILL.md -i     # apply

# Step 4: インストール — 変換済みフォルダを .bob/skills/ 配下へ配置
# Bob はプロジェクト単位の Skill を <project>/.bob/skills/ から読み込み、
# グローバル Skill を ~/.bob/skills/ から読み込む
# プロジェクト単位の Skill がグローバルより優先される

# Step 5: Bob で Advanced mode を有効化し、Skill をテスト
```

---

## Claude Code / Bob Skill として使う

このリポジトリの `skill/` ディレクトリには、Claude Code Skill
かつ有効な Bob Skill としてパッケージ化された `cc-to-bob` が含まれています。
これを skills ディレクトリへ配置すれば、Claude Code または Bob から
会話形式で移行処理を実行できます。

```bash
# Claude Code（グローバルインストール）
cp -r skill/ ~/.claude/skills/cc-to-bob/

# IBM Bob（グローバルインストール）
cp -r skill/ ~/.bob/skills/cc-to-bob/
```

その後、Claude Code または Bob（Advanced mode）で次のように指示できます。

> "Convert my Claude Code skills in `~/.claude/skills/` to Bob format."

内部ではこの Skill が `convert.py` と `restep.py` を呼び出します。

---

## テストの実行

テストスイートは Python 標準の `unittest` を使用しており、追加パッケージは不要です。

```bash
# リポジトリルートで実行
python -m unittest discover tests -v
```

想定出力:

```
test_single_skill ... ok
test_skill_md_file_input ... ok
...
----------------------------------------------------------------------
Ran 30 tests in 0.01s

OK
```

テスト対象は以下を含みます。

- YAML フロントマター解析（スカラー、ブロックスカラー、リスト）
- フロントマター正規化と追加キー移送
- `--flatten` のパス書き換え
- CLI: 単一 Skill、ファイル入力、一括変換、エラーハンドリング
- ファイルコピーと `evals/` 除外
- `restep`: 保守的モードと aggressive モード
- `restep`: 表、フェンス付きコード、blockquote を変換しないこと
- 余分な空行制御（出力に空行 3 連続を作らない）

---

## プロジェクト構成

```
cc-to-bob/
├── cc_to_bob/
│   ├── __init__.py          # package, exposes __version__
│   ├── convert.py           # cc2bob CLI — format converter
│   └── restep.py            # cc2bob-restep CLI — Steps restructurer
│
├── tests/
│   └── test_cc_to_bob.py    # 30-test unittest suite
│
├── skill/                   # the tool itself as a Claude Code / Bob Skill
│   ├── SKILL.md
│   └── references/
│       └── format-mapping.md
│
├── docs/                    # additional documentation (format mapping, etc.)
│
├── .github/
│   └── workflows/
│       └── ci.yml           # CI: test on Python 3.9–3.12
│
├── pyproject.toml
├── LICENSE
├── CHANGELOG.md
├── README.md
└── README.ja.md
```

---

## コントリビュート

1. リポジトリを fork し、機能ブランチを作成します。
2. 変更を加え、新しい挙動にはテストを追加します。
3. テストを実行します: `python -m unittest discover tests -v`
4. `main` に対して pull request を作成します。

`cc_to_bob/convert.py` と `cc_to_bob/restep.py` にはサードパーティ依存を追加しないでください。
依存ゼロで動作することは、このプロジェクトの中核設計方針です。

---

## ライセンス

MIT — 詳細は [LICENSE](LICENSE) を参照してください。