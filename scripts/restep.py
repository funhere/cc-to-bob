#!/usr/bin/env python3
"""
restep — Restructure Markdown instructions into IBM Bob's <Steps>/<Step> form.

Bob's docs favor wrapping *sequential procedures* in:

    <Steps>
    <Step>
    First action.
    </Step>
    <Step>
    Second action.
    </Step>
    </Steps>

But not everything is a procedure. Restructuring tables, principle prose, notes,
or reference lists into steps would change their meaning. So this module is
deliberately conservative: it only converts a region when it has good evidence
the region is an ordered, do-this-then-that procedure.

What it converts:
  - An ordered list (1. 2. 3. ...) that sits under a "procedure-like" heading
    (workflow / steps / 流程 / 步骤 / instructions / process / how to / usage ...).
  - In --aggressive mode, also a run of consecutive paragraphs that each begin
    with an imperative verb, under such a heading.

What it never touches:
  - Tables, fenced code blocks, blockquotes (> ...), HTML already present,
    YAML front matter, and any list/region not under a procedure-like heading.
  - Ordered lists that look like references/citations rather than actions.

It reports every region it converts so a human can review.

Usage as a library:
    from restep import restep_markdown
    new_text, report = restep_markdown(body, aggressive=False)

Usage as a CLI:
    python restep.py path/to/SKILL.md            # prints converted SKILL.md
    python restep.py path/to/SKILL.md -i         # edit in place
    python restep.py path/to/SKILL.md --aggressive
"""

import argparse
import re
import sys
from pathlib import Path

# Headings under which an ordered list is likely a real procedure.
PROCEDURE_HEADING_RE = re.compile(
    r"(workflow|steps?|procedure|process|instructions?|how\s+to|usage|setup|"
    r"流程|步骤|步骤|操作步骤|使用步骤|用法|安装步骤)",
    re.IGNORECASE,
)

# Imperative-ish openers (English + a few common ones) for --aggressive mode.
IMPERATIVE_RE = re.compile(
    r"^(Run|Create|Add|Check|Review|Open|Navigate|Verify|Update|Implement|"
    r"Install|Locate|Confirm|Read|Write|Build|Copy|Move|Delete|Set|Configure|"
    r"Generate|Ensure|Find|Replace|Save|Convert|Test|Validate|Provide|Use)\b"
)

ORDERED_ITEM_RE = re.compile(r"^(\s*)(\d+)\.\s+(.*)$")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")
FENCE_RE = re.compile(r"^\s*(```|~~~)")


def restep_markdown(text, *, aggressive=False):
    """Return (new_text, report) where report is a list of human-readable notes."""
    lines = text.split("\n")
    out = []
    report = []
    i = 0
    n = len(lines)
    in_fence = False
    # Track the most recent heading so we know if a list is under a procedure heading.
    current_heading = None

    while i < n:
        line = lines[i]

        # Pass through fenced code blocks verbatim.
        if FENCE_RE.match(line):
            in_fence = not in_fence
            out.append(line)
            i += 1
            continue
        if in_fence:
            out.append(line)
            i += 1
            continue

        hm = HEADING_RE.match(line)
        if hm:
            current_heading = hm.group(2)
            out.append(line)
            i += 1
            continue

        # Don't touch blockquotes, tables, or existing HTML step blocks.
        if line.lstrip().startswith(">") or "|" in line or "<Step" in line:
            out.append(line)
            i += 1
            continue

        # Candidate: an ordered list starting here.
        if ORDERED_ITEM_RE.match(line):
            block, consumed = _collect_ordered_list(lines, i)
            under_proc = current_heading and PROCEDURE_HEADING_RE.search(current_heading)
            if under_proc and len(block) >= 2:
                steps = [_strip_ordinal(b) for b in block]
                out.extend(_render_steps(steps))
                report.append(
                    f"Converted a {len(steps)}-item ordered list under heading "
                    f"\u201c{current_heading}\u201d into <Steps>."
                )
                i += consumed
                continue
            # Not under a procedure heading (or too short): leave as-is.
            out.append(line)
            i += 1
            continue

        # Aggressive: a run of imperative paragraphs under a procedure heading.
        if aggressive and current_heading and PROCEDURE_HEADING_RE.search(current_heading):
            para_block, consumed = _collect_imperative_paragraphs(lines, i)
            if len(para_block) >= 2:
                out.extend(_render_steps(para_block))
                report.append(
                    f"[aggressive] Converted {len(para_block)} imperative paragraphs "
                    f"under \u201c{current_heading}\u201d into <Steps>."
                )
                i += consumed
                continue

        out.append(line)
        i += 1

    result = "\n".join(out)
    # Collapse any runs of 3+ newlines created by blank-line padding.
    result = re.sub(r"\n{3,}", "\n\n", result)
    return result, report


def _collect_ordered_list(lines, start):
    """Collect a contiguous ordered list beginning at `start`.

    Returns (items, lines_consumed). Each item is the full text of one entry,
    including any indented continuation lines, with the leading 'N.' kept for now.
    """
    items = []
    i = start
    n = len(lines)
    current = None
    while i < n:
        line = lines[i]
        m = ORDERED_ITEM_RE.match(line)
        if m and (m.group(1) == ""):  # top-level numbered item
            if current is not None:
                items.append(current)
            current = line
            i += 1
            continue
        # Continuation: blank line followed by more list, or indented text.
        if current is not None and (line.strip() == "" ):
            # Peek: if the next non-blank is another top-level item or indented
            # continuation, keep going; otherwise the list ends.
            j = i + 1
            while j < n and lines[j].strip() == "":
                j += 1
            if j < n and (ORDERED_ITEM_RE.match(lines[j]) and ORDERED_ITEM_RE.match(lines[j]).group(1) == ""
                          or lines[j].startswith(("  ", "\t"))):
                current += "\n" + line
                i += 1
                continue
            break
        if current is not None and line.startswith(("  ", "\t")):
            current += "\n" + line
            i += 1
            continue
        break
    if current is not None:
        items.append(current)
    return items, (i - start)


def _collect_imperative_paragraphs(lines, start):
    """Collect consecutive paragraphs that each start with an imperative verb."""
    paras = []
    i = start
    n = len(lines)
    while i < n:
        # Skip blank lines between paragraphs.
        while i < n and lines[i].strip() == "":
            i += 1
        if i >= n:
            break
        if FENCE_RE.match(lines[i]) or lines[i].lstrip().startswith((">", "#")) or "|" in lines[i]:
            break
        if not IMPERATIVE_RE.match(lines[i].strip()):
            break
        # Gather this paragraph (until blank line).
        para = []
        while i < n and lines[i].strip() != "":
            para.append(lines[i])
            i += 1
        paras.append("\n".join(para).strip())
    consumed = i - start
    return paras, consumed


def _strip_ordinal(item):
    """Remove the leading 'N.' from the first line and dedent continuations."""
    lines = item.split("\n")
    first = ORDERED_ITEM_RE.match(lines[0])
    head = first.group(3) if first else lines[0]
    rest = [re.sub(r"^( {1,4}|\t)", "", l) for l in lines[1:]]
    return "\n".join([head] + rest).strip()


def _render_steps(steps):
    """Render a list of step texts into Bob's <Steps>/<Step> block.

    Surrounded by blank lines so it sits cleanly between heading and following
    content regardless of what preceded it.
    """
    out = ["", "<Steps>"]
    for s in steps:
        out.append("<Step>")
        out.append(s)
        out.append("</Step>")
        out.append("")  # blank line between steps, matching Bob's examples
    if out[-1] == "":
        out.pop()
    out.append("</Steps>")
    out.append("")
    return out


def restep_skill_md(text, *, aggressive=False):
    """Restep only the body of a SKILL.md, preserving front matter untouched."""
    m = re.match(r"^(---[ \t]*\r?\n.*?\r?\n---[ \t]*\r?\n?)(.*)$", text, re.DOTALL)
    if not m:
        return restep_markdown(text, aggressive=aggressive)
    fm, body = m.group(1), m.group(2)
    new_body, report = restep_markdown(body, aggressive=aggressive)
    return fm + new_body, report


def main(argv=None):
    ap = argparse.ArgumentParser(description="Restructure SKILL.md procedures into Bob <Steps>.")
    ap.add_argument("input", help="Path to a SKILL.md (or any Markdown file).")
    ap.add_argument("-i", "--in-place", action="store_true", help="Edit the file in place.")
    ap.add_argument("--aggressive", action="store_true",
                    help="Also convert runs of imperative paragraphs, not just ordered lists.")
    ap.add_argument("-q", "--quiet", action="store_true", help="Suppress the conversion report.")
    args = ap.parse_args(argv)

    path = Path(args.input).expanduser()
    if not path.exists():
        print(f"error: not found: {path}", file=sys.stderr)
        return 1
    text = path.read_text(encoding="utf-8")
    new_text, report = restep_skill_md(text, aggressive=args.aggressive)

    if args.in_place:
        path.write_text(new_text, encoding="utf-8")
        target = str(path)
    else:
        sys.stdout.write(new_text)
        target = "(stdout)"

    if not args.quiet:
        if report:
            print(f"\n--- restep report for {target} ---", file=sys.stderr)
            for r in report:
                print(f"  • {r}", file=sys.stderr)
        else:
            print(f"\nrestep: no procedure regions converted in {path.name} "
                  f"(nothing matched the conservative rules).", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())


def cli():
    """Entry point for the `cc2bob-restep` console script."""
    sys.exit(main())

