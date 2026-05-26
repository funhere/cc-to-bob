# Format Mapping: Claude Code Skills → IBM Bob Skills

A detailed reference for how each part of a Claude Code skill maps onto IBM Bob's
skill format. Source: IBM Bob official docs, "Skills" page
(https://bob.ibm.com/docs/ide/features/skills).

## Directory and discovery

| Concern | Claude Code | IBM Bob |
|---|---|---|
| Per-project skills | `<project>/.claude/skills/<name>/` | `<project>/.bob/skills/<name>/` |
| Global skills | `~/.claude/skills/<name>/` | `~/.bob/skills/<name>/` |
| Entry file | `SKILL.md` in the skill folder | `SKILL.md` in the skill folder |
| Name collision | — | project-level skill takes precedence over global |
| Activation | model decides from description | model decides from description; Bob asks approval unless "Always allow skills" is enabled in Auto-Approve settings |
| Runtime requirement | always available | **Advanced mode only** |

## Front matter

Both formats use YAML front matter delimited by `---`.

**Claude Code** commonly includes, beyond the required `name` and `description`:
- `compatibility` — tools/dependencies
- `license`
- `allowed-tools` (a.k.a. `allowed_tools`)
- `metadata` (arbitrary nested data)
- other custom keys

**IBM Bob** recognizes only:
- `name` — the skill's display name in the Bob interface (required)
- `description` — a clear summary Bob uses to decide when to activate the skill
  (required; **skills without a description are ignored**)

### Conversion rule

1. Keep `name` as-is. (Claude uses a lowercase-hyphenated identifier; Bob's own
   examples are also hyphenated, e.g. `code-review`, so this transfers cleanly.)
2. Normalize `description` to a single line. Claude often writes multi-line block
   scalars (`description: >`); collapse to one line so Bob parses it reliably.
3. Move every other key into a short blockquote note at the top of the
   instructions body ("Compatibility & metadata"), so the information survives
   even though Bob won't parse it from front matter.

## Instructions body

Everything below the closing `---` is the instruction set Bob receives on
activation — identical in spirit to Claude Code.

- Plain Markdown carries over unchanged.
- Bob idiomatically uses `<Steps>` / `<Step>` tags for sequential procedures.
  The converter does **not** auto-rewrite prose into this structure (it would
  risk changing meaning), but a human can do so afterward for readability.

## Supporting files

| | Claude Code | IBM Bob |
|---|---|---|
| Convention | nested: `scripts/`, `references/`, `assets/` | flat files alongside `SKILL.md`; no required subdirs |
| Reading | referenced from `SKILL.md` by relative path | Bob reads supporting files automatically once activated |

### Conversion rule

- **Default (preserve):** copy supporting files keeping their subdirectories.
  Bob reads nested files fine, and preserving structure keeps relative path
  references in `SKILL.md` valid.
- **`--flatten`:** hoist all supporting files to the skill's top level and
  rewrite `scripts/…`, `references/…`, `assets/…` references in `SKILL.md` to
  bare filenames. Use when a flat layout is explicitly preferred.

Note: `evals/` directories (Claude Code test harnesses) are **not** copied — they
are not part of a shippable skill.

## What does not transfer automatically

- **Tool assumptions.** If a Claude skill assumes specific Anthropic-side tools,
  those references move as text but may not match the user's Bob tool setup. Flag
  these for manual review.
- **Nested front-matter values.** A simple parser may not expand nested mappings
  (e.g. `metadata: { version: 2.1 }`); the note will point back to the original
  skill for those details.
