# cc-to-bob

日本語版: [日本語はこちら](README.ja.md)

**Convert [Claude Code](https://claude.ai/code) Skills into [IBM Bob](https://bob.ibm.com) Skills.**

Claude Code and IBM Bob both use a `SKILL.md`-based skill format, but differ in
front-matter rules, directory conventions, and preferred prose style. `cc-to-bob`
bridges that gap automatically — no data loss, no manual editing.

```
.claude/skills/my-skill/   →   cc2bob   →   .bob/skills/my-skill/
```

[![CI](https://github.com/funhere/cc-to-bob/actions/workflows/ci.yml/badge.svg)](https://github.com/funhere/cc-to-bob/actions)
[![Python](https://img.shields.io/badge/python-3.9%2B-blue)](https://www.python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

---

## Table of Contents

- [Why this tool exists](#why-this-tool-exists)
- [Format differences at a glance](#format-differences-at-a-glance)
- [Installation](#installation)
- [Quick start](#quick-start)
- [Tool 1 — cc2bob (convert.py)](#tool-1--cc2bob-convertpy)
- [Tool 2 — cc2bob-restep (restep.py)](#tool-2--cc2bob-restep-resteppy)
- [Typical migration workflow](#typical-migration-workflow)
- [Using as a Claude Code / Bob Skill](#using-as-a-claude-code--bob-skill)
- [Running tests](#running-tests)
- [Project layout](#project-layout)
- [Contributing](#contributing)
- [License](#license)

---

## Why this tool exists

Claude Code and IBM Bob skills share DNA — both are a `SKILL.md` file with YAML
front matter (`name`, `description`) above a Markdown body, optionally accompanied
by supporting files. A naive copy almost works, but breaks in subtle ways:

| Issue | Consequence |
|---|---|
| Bob only reads `name` + `description` from front matter | Extra keys (`license`, `compatibility`, `allowed-tools`, …) are silently ignored — information is lost |
| Bob ignores skills with no `description` | A multi-line block-scalar `description: >` may parse as empty |
| Bob's docs favour `<Steps>`/`<Step>` for ordered procedures | Markdown numbered lists work but look non-idiomatic |

`cc-to-bob` fixes all three automatically.

---

## Format differences at a glance

| | Claude Code | IBM Bob |
|---|---|---|
| Skills directory | `.claude/skills/` or `~/.claude/skills/` | `.bob/skills/` or `~/.bob/skills/` |
| Front-matter keys | `name`, `description`, + anything | **`name` and `description` only** |
| `description` format | multi-line block scalar OK | must be a single line |
| Supporting files | nested `scripts/`, `references/`, `assets/` | flat alongside `SKILL.md` (nesting works too) |
| Procedure markup | plain Markdown lists | `<Steps>`/`<Step>` recommended |
| Runtime requirement | always available | **Advanced mode required** |

---

## Installation

**Requirements:** Python 3.9 or later. No third-party dependencies.

### Option A — pip (recommended)

```bash
pip install cc-to-bob
```

Two commands become available globally:

```
cc2bob          # format converter
cc2bob-restep   # optional Steps restructurer
```

### Option B — run directly from the repo

```bash
git clone https://github.com/funhere/cc-to-bob.git
cd cc-to-bob

# converter
python cc_to_bob/convert.py --help

# Steps restructurer
python cc_to_bob/restep.py --help
```

### Option C — editable install for development

```bash
git clone https://github.com/funhere/cc-to-bob.git
cd cc-to-bob
pip install -e ".[dev]"
```

---

## Quick start

```bash
# Convert a single skill
cc2bob ~/.claude/skills/my-skill/ -o ~/.bob/skills/

# Convert all skills at once
cc2bob ~/.claude/skills/ -o ~/.bob/skills/ --batch

# Then optionally restructure ordered procedures into Bob's <Steps> style
cc2bob-restep ~/.bob/skills/my-skill/SKILL.md -i
```

---

## Tool 1 — `cc2bob` (convert.py)

Converts Claude Code skill(s) into IBM Bob format. This tool handles:

- **Front-matter normalisation** — strips all keys except `name` and `description`;
  moves extras into a blockquote note in the body so nothing is lost.
- **Description flattening** — collapses multi-line block scalars to a single line.
- **File copying** — copies all supporting files; silently skips `evals/` directories.

### Synopsis

```
cc2bob <input> -o <output> [options]
```

| Argument / Flag | Description |
|---|---|
| `input` | A skill folder, a `SKILL.md` file, or (with `--batch`) a directory of skill folders |
| `-o / --output` | Output directory, e.g. `~/.bob/skills` |
| `--batch` | Treat `input` as a root containing multiple skill folders; convert all of them |
| `--flatten` | Hoist `scripts/`, `references/`, `assets/` to the skill root and rewrite path references in `SKILL.md` |
| `--note-advanced-mode` | Prepend a reminder note that the skill requires Bob's Advanced mode |

### Examples

```bash
# Single skill folder
cc2bob ./my-skill/ -o ./bob-skills/

# Single SKILL.md file
cc2bob ./my-skill/SKILL.md -o ./bob-skills/

# Batch: whole skills directory
cc2bob ~/.claude/skills/ -o ~/.bob/skills/ --batch

# Flat layout (hoist supporting files)
cc2bob ./my-skill/ -o ./bob-skills/ --flatten

# Add an Advanced-mode reminder (useful when sharing with teammates)
cc2bob ~/.claude/skills/ -o ~/.bob/skills/ --batch --note-advanced-mode
```

Example Output (Bulk Import of 52 Skills)
```bash
$ cc2bob ~/.claude/skills/gstack -o .bob/skills --batch 

converted: autoplan -> .bob/skills/autoplan  (+1 files)  [moved to body: preamble-tier, version, benefits-from, triggers, allowed-tools]
converted: benchmark -> .bob/skills/benchmark  (+1 files)  [moved to body: preamble-tier, version, triggers, allowed-tools]
converted: benchmark-models -> .bob/skills/benchmark-models  (+1 files)  [moved to body: preamble-tier, version, triggers, allowed-tools]
converted: browse -> .bob/skills/browse  (+211 files)  [moved to body: preamble-tier, version, triggers, allowed-tools]
converted: canary -> .bob/skills/canary  (+1 files)  [moved to body: preamble-tier, version, allowed-tools, triggers]
converted: careful -> .bob/skills/careful  (+2 files)  [moved to body: version, triggers, allowed-tools, hooks]
converted: codex -> .bob/skills/codex  (+1 files)  [moved to body: preamble-tier, version, triggers, allowed-tools]
converted: open-gstack-browser -> .bob/skills/connect-chrome  (+1 files)  [moved to body: version, triggers, allowed-tools]
converted: context-restore -> .bob/skills/context-restore  (+1 files)  [moved to body: preamble-tier, version, allowed-tools, triggers]
converted: context-save -> .bob/skills/context-save  (+1 files)  [moved to body: preamble-tier, version, allowed-tools, triggers]
converted: cso -> .bob/skills/cso  (+2 files)  [moved to body: preamble-tier, version, allowed-tools, triggers]
......

Done. 52/52 skill(s) converted into .bob/skills
```

<img width="3370" height="1560" alt="cc2bob_2" src="https://github.com/user-attachments/assets/644c415d-b231-4c7c-8a78-6a80f1b35ac4" />

<img width="2392" height="1934" alt="cc2bob_3" src="https://github.com/user-attachments/assets/aabd6904-e876-4b48-ad8e-95a4d9f31f2a" />


### What happens to extra front-matter keys?

Claude Code skills often carry metadata that Bob doesn't recognise:

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

`cc2bob` moves those extra keys into a blockquote note at the top of the body —
information is preserved, and Bob's front-matter constraint is satisfied:

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

### Exit codes

| Code | Meaning |
|---|---|
| `0` | All skills converted successfully |
| `1` | Usage / input error |
| `2` | Nothing was converted (all targets failed or no targets found) |

In `--batch` mode, individual skill failures are reported and skipped; the process
exits `0` as long as at least one skill succeeded.

---

## Tool 2 — `cc2bob-restep` (restep.py)

Restructures sequential procedures in a converted `SKILL.md` into Bob's idiomatic
`<Steps>`/`<Step>` format. This is a **separate, optional step** — run it after
`cc2bob` and only when you want the Bob-specific markup.

### Why separate?

Restructuring changes prose meaning if applied blindly. Keeping it independent
means you can review each conversion in isolation, and skip it entirely for skills
where the Markdown lists read fine as-is.

### Conservative default

By default `cc2bob-restep` only converts an **ordered list** (`1.` `2.` `3.`)
that sits directly under a **procedure-like heading**:

> workflow · steps · procedure · process · instructions · usage · how to ·
> 流程 · 步骤 · 操作步骤 · 安装步骤 · …

It **never touches**:

- Tables
- Fenced code blocks
- Blockquotes / callout notes
- Ordered lists not under a procedure heading
- Lists that look like references rather than actions

### Synopsis

```
cc2bob-restep <input> [options]
```

| Flag | Description |
|---|---|
| `-i / --in-place` | Edit the file in place (default: print to stdout) |
| `--aggressive` | Also convert runs of consecutive imperative paragraphs (Run…, Create…, Check…) |
| `-q / --quiet` | Suppress the conversion report on stderr |

### Examples

```bash
# Preview what would change (dry run)
cc2bob-restep ~/.bob/skills/deploy/SKILL.md

# Edit in place
cc2bob-restep ~/.bob/skills/deploy/SKILL.md -i

# Aggressive mode (imperative paragraphs too)
cc2bob-restep ~/.bob/skills/setup/SKILL.md -i --aggressive

# Suppress report
cc2bob-restep ~/.bob/skills/deploy/SKILL.md -i --quiet
```

### What it converts

```markdown
## Workflow

1. Build the artifact with `make build`.
2. Run the test suite and confirm it passes.
3. Tag the commit and push to the registry.
```

becomes:

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

The conversion report tells you exactly which regions were changed:

```
--- restep report for deploy/SKILL.md ---
  • Converted a 3-item ordered list under heading "Workflow" into <Steps>.
```

---

## Typical migration workflow

```bash
# Step 1: Convert format
cc2bob ~/.claude/skills/ -o ~/.bob/skills/ --batch

# Step 2: Review the output for any skills with Claude-specific tool references
# (the converter moves text faithfully, but can't know your Bob tool setup)
ls ~/.bob/skills/

# Step 3 (optional): Restructure procedures into <Steps>
# Do this per-skill, previewing first
cc2bob-restep ~/.bob/skills/my-skill/SKILL.md        # preview
cc2bob-restep ~/.bob/skills/my-skill/SKILL.md -i     # apply

# Step 4: Install — place converted folders under .bob/skills/
# Bob reads project-level skills from <project>/.bob/skills/
# and global skills from ~/.bob/skills/
# Project-level skills take precedence over global ones.

# Step 5: Enable Advanced mode in Bob, then test the skill
```

---

## Using as a Claude Code / Bob Skill

The `skill/` directory in this repo contains `cc-to-bob` packaged as a Claude Code
Skill (and a valid Bob Skill). Drop it into your skills directory and Claude Code
or Bob can run the migration for you conversationally.

```bash
# Claude Code (global install)
cp -r skill/ ~/.claude/skills/cc-to-bob/

# IBM Bob (global install)
cp -r skill/ ~/.bob/skills/cc-to-bob/
```

Then in Claude Code or Bob (Advanced mode):

> "Convert my Claude Code skills in `~/.claude/skills/` to Bob format."

The skill drives `convert.py` and `restep.py` under the hood.

---

## Running tests

The test suite uses Python's built-in `unittest` — no extra packages required.

```bash
# From the repo root
python -m unittest discover tests -v
```

Expected output:

```
test_single_skill ... ok
test_skill_md_file_input ... ok
...
----------------------------------------------------------------------
Ran 30 tests in 0.01s

OK
```

The suite covers:

- YAML front-matter parsing (scalars, block scalars, lists)
- Front-matter normalisation and extra-key migration
- `--flatten` path rewriting
- CLI: single skill, file input, batch, error handling
- File copy and `evals/` exclusion
- `restep`: conservative and aggressive modes
- `restep`: non-conversion of tables, fenced code, blockquotes
- Spacing (no triple blank lines in output)

---

## Project layout

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
└── README.md
```

---

## Contributing

1. Fork the repository and create a feature branch.
2. Make your changes and add tests for new behaviour.
3. Run the test suite: `python -m unittest discover tests -v`
4. Open a pull request against `main`.

Please keep `cc_to_bob/convert.py` and `cc_to_bob/restep.py` free of third-party
dependencies — zero-dependency operation is a core design goal.

---

## License

MIT — see [LICENSE](LICENSE).
