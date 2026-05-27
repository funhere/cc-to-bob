#!/usr/bin/env python3
"""
cc2bob — Convert Claude Code Skills into IBM Bob Skills.

Claude Code skills and IBM Bob skills are structurally similar (both use a
SKILL.md with YAML front matter plus supporting files), but differ in a few
ways this converter handles:

  - Front matter: Claude allows extra keys (compatibility, license, allowed-tools,
    metadata...). Bob recognizes only `name` and `description`. Extra keys are
    moved into the instructions body as a "Compatibility & metadata" note so no
    information is lost, rather than silently dropped.
  - Supporting layout: Claude conventionally nests scripts/, references/,
    assets/. Bob reads supporting files that sit alongside SKILL.md and does not
    prescribe subdirectories. By default we PRESERVE the subdirectories (Bob can
    still read nested files), but --flatten will hoist them to the top level and
    rewrite path references in SKILL.md.
  - name field: Claude uses a lowercase-hyphenated identifier; Bob treats `name`
    as a display name but the docs' own examples are hyphenated, so we keep it
    as-is (validated to be non-empty).
  - Advanced mode: Bob skills require Advanced mode. We optionally inject a short
    reminder note (off by default; enable with --note-advanced-mode).

Usage:
    # Single skill folder (contains SKILL.md)
    python convert.py path/to/claude-skill/ -o out/

    # A single SKILL.md file
    python convert.py path/to/SKILL.md -o out/

    # Batch: a directory that contains many skill folders (e.g. ~/.claude/skills)
    python convert.py ~/.claude/skills/ -o ~/.bob/skills/ --batch

Exit codes: 0 ok, 1 usage error, 2 nothing converted.
"""

import argparse
import re
import shutil
import sys
from pathlib import Path

# Keys IBM Bob recognizes in front matter. Everything else is preserved in-body.
BOB_KNOWN_KEYS = {"name", "description"}
# Subdirectories Claude Code conventionally uses for supporting files.
CLAUDE_SUPPORT_DIRS = ("scripts", "references", "assets")


# --------------------------------------------------------------------------- #
# Minimal YAML front-matter parsing (no external deps).
# We only need flat key: value pairs, block scalars (>/|), and simple lists.
# --------------------------------------------------------------------------- #
def split_front_matter(text):
    """Return (frontmatter_dict, ordered_keys, body_str).

    Raises ValueError if there is no valid front matter block.
    """
    if not text.startswith("---"):
        raise ValueError("SKILL.md has no YAML front matter (must start with '---').")
    # Match the opening --- and the next --- on its own line.
    m = re.match(r"^---[ \t]*\r?\n(.*?)\r?\n---[ \t]*\r?\n?(.*)$", text, re.DOTALL)
    if not m:
        raise ValueError("SKILL.md front matter is not closed with a '---' line.")
    fm_raw, body = m.group(1), m.group(2)
    fm, order = _parse_simple_yaml(fm_raw)
    return fm, order, body


def _parse_simple_yaml(raw):
    """Parse a small subset of YAML: scalars, block scalars, and simple lists.

    Returns (dict, ordered_key_list). Values are strings or list[str].
    """
    data, order = {}, []
    lines = raw.split("\n")
    i = 0
    key_re = re.compile(r"^([A-Za-z0-9_\-]+):[ \t]*(.*)$")
    while i < len(lines):
        line = lines[i]
        if not line.strip() or line.lstrip().startswith("#"):
            i += 1
            continue
        km = key_re.match(line)
        if not km:
            i += 1
            continue
        key, inline = km.group(1), km.group(2).strip()
        if inline in (">", "|", ">-", "|-", ">+", "|+"):
            # Block scalar: collect subsequent more-indented lines.
            block, i = [], i + 1
            base_indent = None
            while i < len(lines):
                nxt = lines[i]
                if nxt.strip() == "":
                    block.append("")
                    i += 1
                    continue
                indent = len(nxt) - len(nxt.lstrip())
                if base_indent is None:
                    base_indent = indent
                if indent < (base_indent or 1) and nxt.strip():
                    break
                block.append(nxt[base_indent:] if len(nxt) >= base_indent else nxt.strip())
                i += 1
            joiner = " " if inline.startswith(">") else "\n"
            val = joiner.join(s for s in block).strip()
            data[key] = val
            _add(order, key)
            continue
        if inline == "":
            # Could be a list on following lines: "- item"
            items, j = [], i + 1
            while j < len(lines) and re.match(r"^[ \t]+-[ \t]+", lines[j]):
                items.append(re.sub(r"^[ \t]+-[ \t]+", "", lines[j]).strip())
                j += 1
            if items:
                data[key] = items
                _add(order, key)
                i = j
                continue
            data[key] = ""
            _add(order, key)
            i += 1
            continue
        # Plain scalar; strip surrounding quotes.
        val = inline
        if (val.startswith('"') and val.endswith('"')) or (
            val.startswith("'") and val.endswith("'")
        ):
            val = val[1:-1]
        data[key] = val
        _add(order, key)
        i += 1
    return data, order


def _add(order, key):
    if key not in order:
        order.append(key)


def _yaml_escape(value):
    """Render a scalar safely on one line for Bob's front matter.

    Only quote when YAML would actually misparse the value: a leading
    indicator char, a ': ' or ' #' sequence, or surrounding whitespace.
    Ordinary punctuation (commas, periods, parentheses) is left bare.
    """
    v = str(value).replace("\n", " ").strip()
    needs_quote = (
        v == ""
        or v[0] in "!&*?|>%@`\"'#[]{},:-"
        or ": " in v
        or " #" in v
        or v != v.strip()
    )
    if needs_quote:
        return '"' + v.replace("\\", "\\\\").replace('"', '\\"') + '"'
    return v


# --------------------------------------------------------------------------- #
# Conversion core
# --------------------------------------------------------------------------- #
def convert_skill_md(text, *, flatten=False, note_advanced_mode=False, skill_name_hint=None):
    """Convert SKILL.md content. Returns (new_text, info_dict)."""
    fm, order, body = split_front_matter(text)

    name = (fm.get("name") or skill_name_hint or "").strip()
    description = fm.get("description", "")
    if isinstance(description, list):
        description = " ".join(description)
    description = " ".join(str(description).split()).strip()

    if not name:
        raise ValueError("front matter is missing required 'name'.")
    if not description:
        raise ValueError("front matter is missing required 'description'.")

    # Collect extra (non-Bob) keys, preserving original order.
    extra = [(k, fm[k]) for k in order if k not in BOB_KNOWN_KEYS]

    # Build Bob front matter: name + description only.
    new_fm = ["---", f"name: {_yaml_escape(name)}", f"description: {_yaml_escape(description)}", "---"]

    preface_blocks = []
    if note_advanced_mode:
        preface_blocks.append(
            "> **Note:** This skill requires IBM Bob's **Advanced mode** to run."
        )
    if extra:
        lines = ["> **Compatibility & metadata** (carried over from the original Claude Code skill):", ">"]
        for k, v in extra:
            if isinstance(v, list):
                v = ", ".join(v)
            v = " ".join(str(v).split())
            lines.append(f"> - `{k}`: {v}" if v else f"> - `{k}` (see original skill for nested values)")
        preface_blocks.append("\n".join(lines))

    new_body = body.lstrip("\n")
    if flatten:
        new_body = _rewrite_support_paths(new_body)

    parts = ["\n".join(new_fm), ""]
    if preface_blocks:
        parts.append("\n\n".join(preface_blocks))
        parts.append("")
    parts.append(new_body.rstrip() + "\n")
    return "\n".join(parts), {
        "name": name,
        "description": description,
        "extra_keys": [k for k, _ in extra],
    }


def _rewrite_support_paths(body):
    """When flattening, rewrite scripts/foo -> foo etc. in the instructions."""
    for d in CLAUDE_SUPPORT_DIRS:
        body = re.sub(rf"(?<![\w/]){d}/", "", body)
    return body


def _iter_support_files(skill_dir):
    """Yield (src_path, relative_dst) for every supporting file (not SKILL.md)."""
    for p in sorted(skill_dir.rglob("*")):
        if p.is_dir():
            continue
        rel = p.relative_to(skill_dir)
        if rel.parts[0] == "evals":  # never ship test harness into the Bob skill
            continue
        if rel.name == "SKILL.md" and len(rel.parts) == 1:
            continue
        yield p, rel


def convert_one(skill_dir, out_root, *, flatten=False, note_advanced_mode=False):
    """Convert a single skill folder. Returns info dict."""
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        raise FileNotFoundError(f"no SKILL.md in {skill_dir}")
    text = skill_md.read_text(encoding="utf-8")
    new_text, info = convert_skill_md(
        text,
        flatten=flatten,
        note_advanced_mode=note_advanced_mode,
        skill_name_hint=skill_dir.name,
    )
    dst_dir = out_root / skill_dir.name
    dst_dir.mkdir(parents=True, exist_ok=True)
    (dst_dir / "SKILL.md").write_text(new_text, encoding="utf-8")

    copied = []
    for src, rel in _iter_support_files(skill_dir):
        if flatten:
            dst = dst_dir / rel.name
        else:
            dst = dst_dir / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        copied.append(str(dst.relative_to(dst_dir)))
    info["output_dir"] = str(dst_dir)
    info["support_files"] = copied
    return info


def _looks_like_skill(d):
    return (d / "SKILL.md").exists()


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Convert Claude Code skill(s) into IBM Bob skill(s)."
    )
    ap.add_argument("input", help="A skill folder, a SKILL.md file, or (with --batch) a skills root.")
    ap.add_argument("-o", "--output", required=True, help="Output directory (e.g. ~/.bob/skills).")
    ap.add_argument("--batch", action="store_true",
                    help="Treat input as a directory containing multiple skill folders.")
    ap.add_argument("--flatten", action="store_true",
                    help="Hoist scripts/references/assets to top level and rewrite paths.")
    ap.add_argument("--note-advanced-mode", action="store_true",
                    help="Inject a note that the skill requires Bob Advanced mode.")
    args = ap.parse_args(argv)

    in_path = Path(args.input).expanduser()
    out_root = Path(args.output).expanduser()
    out_root.mkdir(parents=True, exist_ok=True)

    if not in_path.exists():
        print(f"error: input not found: {in_path}", file=sys.stderr)
        return 1

    targets = []
    if in_path.is_file() and in_path.name == "SKILL.md":
        targets = [in_path.parent]
    elif args.batch:
        if not in_path.is_dir():
            print("error: --batch requires a directory input.", file=sys.stderr)
            return 1
        targets = [d for d in sorted(in_path.iterdir()) if d.is_dir() and _looks_like_skill(d)]
        if not targets:
            print(f"error: no skill folders (with SKILL.md) found under {in_path}", file=sys.stderr)
            return 2
    elif in_path.is_dir() and _looks_like_skill(in_path):
        targets = [in_path]
    else:
        print("error: input is not a SKILL.md, a skill folder, or a --batch root.", file=sys.stderr)
        return 1

    ok = 0
    for d in targets:
        try:
            info = convert_one(
                d, out_root,
                flatten=args.flatten,
                note_advanced_mode=args.note_advanced_mode,
            )
            extra = f"  (+{len(info['support_files'])} files)" if info["support_files"] else ""
            moved = f"  [moved to body: {', '.join(info['extra_keys'])}]" if info["extra_keys"] else ""
            print(f"converted: {info['name']} -> {info['output_dir']}{extra}{moved}")
            ok += 1
        except Exception as e:  # noqa: BLE001 - report and continue in batch
            print(f"SKIPPED {d.name}: {e}", file=sys.stderr)

    if ok == 0:
        return 2
    print(f"\nDone. {ok}/{len(targets)} skill(s) converted into {out_root}")
    return 0


if __name__ == "__main__":
    sys.exit(main())


def cli():
    """Entry point for the `cc2bob` console script."""
    sys.exit(main())

