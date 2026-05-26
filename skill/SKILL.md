---
name: cc-to-bob
description: Convert Claude Code Skills into IBM Bob Skills. Use this whenever the user wants to port, migrate, or convert a Claude Code skill (a SKILL.md folder under .claude/skills) into IBM Bob's skill format (.bob/skills), including single skills, whole skill folders with scripts/references/assets, or batch-converting an entire skills directory. Trigger on phrases like "convert this skill to Bob", "port my Claude skills to IBM Bob", "turn this SKILL.md into a Bob skill", or any mention of moving skills between Claude Code and IBM Bob.
---

# Claude Code → IBM Bob Skill Converter

Convert Claude Code skills into IBM Bob skills. The two formats are close
cousins — both use a `SKILL.md` with YAML front matter (`name`, `description`)
plus supporting files — so most of the work is normalizing the front matter and
laying files out where Bob expects them. The bundled `scripts/convert.py` does
the mechanical transformation; this file tells you how to drive it and verify
the result.

## When to use this

The user wants to move one or more Claude Code skills into IBM Bob. Inputs can be:
- a single skill folder (containing `SKILL.md`),
- a single `SKILL.md` file, or
- a directory of many skill folders (e.g. `~/.claude/skills/`) for batch conversion.

## The format difference (why conversion is needed)

Read `references/format-mapping.md` for the full table. The essentials:

| | Claude Code | IBM Bob |
|---|---|---|
| Skills dir | `.claude/skills/` or `~/.claude/skills/` | `.bob/skills/` or `~/.bob/skills/` |
| Front matter | `name`, `description`, sometimes extras (`license`, `compatibility`, `allowed-tools`, `metadata`…) | **only** `name` and `description` are recognized |
| Supporting files | conventionally nested in `scripts/`, `references/`, `assets/` | read from alongside `SKILL.md`; no prescribed subdirs (nesting still works) |
| Runtime | always available | requires Bob **Advanced mode** |

The converter preserves any extra front-matter keys by moving them into a short
note at the top of the instructions body, so no information is lost.

## Workflow

### Step 1 — Locate the input and confirm the output location

Find the skill(s). If the user didn't say where to write the result, default to
a sibling `bob-skills/` directory (or `~/.bob/skills/` if they're installing
globally) and tell them where it's going.

### Step 2 — Run the converter

```bash
# single skill folder
python3 scripts/convert.py <skill-folder> -o <output-dir>

# a single SKILL.md
python3 scripts/convert.py <path>/SKILL.md -o <output-dir>

# batch: a directory containing many skill folders
python3 scripts/convert.py <skills-root> -o <output-dir> --batch
```

Useful flags:
- `--flatten` — hoist `scripts/`, `references/`, `assets/` files to the skill's
  top level and rewrite those path references inside `SKILL.md`. Use this only
  if the user wants a flat layout; Bob reads nested files fine, so the default
  (preserve structure) is usually best.
- `--note-advanced-mode` — inject a one-line reminder that the skill needs Bob's
  Advanced mode. Helpful when handing skills to teammates unfamiliar with Bob.

`convert.py` deliberately does **not** restructure prose into Bob `<Steps>`.
That is a separate, opt-in step handled by `scripts/restep.py` (see below), so
that conversion and restructuring stay independent and individually reviewable.

The script reports each conversion, including which extra keys were moved to the
body and how many supporting files were copied. In batch mode it skips and
reports any folder that fails (e.g. missing or malformed front matter) and
continues with the rest.

### Step 3 — Verify the output

Always sanity-check before declaring success:
- `SKILL.md` starts with `---`, has exactly `name` and `description` in the front
  matter, and the description is a single line (Bob ignores skills without a
  description, so this matters).
- Supporting files were copied across.
- If `--flatten` was used, confirm path references in the body no longer point at
  `scripts/`, `references/`, or `assets/`.

Read the converted `SKILL.md` back and skim it. If the original used Claude-only
constructs that won't carry meaning in Bob (for example, instructions that assume
Anthropic-specific tools), flag them to the user — the converter moves text
faithfully but can't know your Bob tool setup.

### Step 4 — Tell the user how to install

Bob discovers skills under `.bob/skills/` (project) or `~/.bob/skills/` (global).
Tell the user to place the converted folder there, and remind them skills run in
**Advanced mode** only. If both a project and global skill share a name, the
project one wins.

## Restructuring into Bob Steps (optional, standalone)

Bob's docs favor wrapping *sequential procedures* in `<Steps>`/`<Step>` tags.
This is handled by a **separate standalone script**, `scripts/restep.py`, run
after conversion only when the user wants it — it is intentionally not part of
`convert.py`, keeping the two concerns independent.

`restep.py` is **conservative by default**, and that default is the recommended
mode: it only converts an ordered list (`1.` `2.` `3.`) that sits under a
procedure-like heading (workflow, steps, procedure, process, instructions,
usage, 流程, 步骤…). It never touches tables, fenced code blocks,
blockquotes/notes, content not under a procedure heading, or ordered lists that
read as references rather than actions. This avoids changing the meaning of
non-procedural prose.

```bash
python3 scripts/restep.py path/to/SKILL.md            # print to stdout
python3 scripts/restep.py path/to/SKILL.md -i          # edit in place
```

It prints exactly which regions it restructured so the result can be reviewed.
Always skim the converted body and confirm the steps read correctly before
shipping.

There is also an `--aggressive` flag that additionally converts runs of
imperative paragraphs (not just numbered lists). It has more reach but a higher
chance of misreading prose, so prefer the conservative default unless a specific
skill needs it and you can review the output.

## Notes

- The converter has no third-party dependencies (pure Python 3 standard library).
- It never deletes or modifies the source skill; it only writes to the output dir.
- `evals/` directories in the source are intentionally not copied — they're test
  harnesses, not part of the shippable skill.
