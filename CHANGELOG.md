# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] — 2025-05-26

### Added
- `cc2bob` CLI (`convert.py`): converts Claude Code `SKILL.md` format to IBM Bob format
  - Normalises `description` block scalars to a single line
  - Moves unrecognised front-matter keys into the instructions body (no data loss)
  - `--batch` flag for converting an entire skills directory at once
  - `--flatten` flag to hoist `scripts/`/`references/`/`assets/` to the skill root
  - `--note-advanced-mode` flag to inject an Advanced-mode reminder note
  - Copies all supporting files; deliberately excludes `evals/` directories
- `cc2bob-restep` CLI (`restep.py`): optionally restructures ordered procedures into Bob's `<Steps>`/`<Step>` tags
  - Conservative default: only converts ordered lists under procedure-like headings
  - `--aggressive` flag to also convert imperative paragraph runs
  - `-i` / `--in-place` for direct file editing
  - Conversion report printed to stderr
- `skill/` directory: the tool itself as an installable Claude Code / IBM Bob Skill
- 30-test unittest suite covering all major code paths
- GitHub Actions CI across Python 3.9–3.12
