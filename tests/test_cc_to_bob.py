"""Tests for cc-to-bob: convert.py and restep.py."""

import sys
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from scripts.convert import convert_skill_md, split_front_matter, main as convert_main
from scripts.restep import restep_markdown, restep_skill_md


def _skill(fm: str, body: str = "Some instructions.") -> str:
    return f"---\n{fm.strip()}\n---\n\n{body}\n"


class TestSplitFrontMatter(unittest.TestCase):
    def test_simple(self):
        fm, order, _ = split_front_matter(_skill("name: foo\ndescription: bar"))
        self.assertEqual(fm["name"], "foo")
        self.assertEqual(fm["description"], "bar")
        self.assertEqual(order, ["name", "description"])

    def test_block_scalar_gt(self):
        fm, _, _ = split_front_matter(_skill("name: foo\ndescription: >\n  line one\n  line two"))
        self.assertEqual(fm["description"], "line one line two")

    def test_list_value(self):
        fm, _, _ = split_front_matter(_skill("name: foo\ndescription: bar\nallowed-tools:\n  - bash\n  - read"))
        self.assertEqual(fm["allowed-tools"], ["bash", "read"])

    def test_no_front_matter_raises(self):
        with self.assertRaisesRegex(ValueError, "no YAML front matter"):
            split_front_matter("just some text\n")

    def test_unclosed_raises(self):
        with self.assertRaisesRegex(ValueError, "not closed"):
            split_front_matter("---\nname: foo\n")


class TestConvertSkillMd(unittest.TestCase):
    def test_passthrough_minimal(self):
        out, info = convert_skill_md(_skill("name: my-skill\ndescription: Does things"))
        self.assertIn("name: my-skill", out)
        self.assertEqual(info["extra_keys"], [])

    def test_extra_keys_moved_to_body(self):
        out, info = convert_skill_md(_skill("name: s\ndescription: d\nlicense: MIT\ncompatibility: Python 3.10+"))
        fm_block = out.split("---")[1]
        self.assertNotIn("license", fm_block)
        self.assertIn("`license`: MIT", out)
        self.assertIn("`compatibility`: Python 3.10+", out)
        self.assertEqual(info["extra_keys"], ["license", "compatibility"])

    def test_block_scalar_flattened(self):
        out, _ = convert_skill_md(_skill("name: s\ndescription: >\n  first\n  second"))
        self.assertIn("description: first second", out)

    def test_note_advanced_mode(self):
        out, _ = convert_skill_md(_skill("name: s\ndescription: d"), note_advanced_mode=True)
        self.assertIn("Advanced mode", out)

    def test_missing_name_raises(self):
        with self.assertRaisesRegex(ValueError, "missing required 'name'"):
            convert_skill_md(_skill("description: d"))

    def test_missing_description_raises(self):
        with self.assertRaisesRegex(ValueError, "missing required 'description'"):
            convert_skill_md(_skill("name: n"))

    def test_flatten_rewrites_paths(self):
        out, _ = convert_skill_md(_skill("name: n\ndescription: d", "Run scripts/helper.py\nSee references/guide.md"), flatten=True)
        self.assertNotIn("scripts/", out)
        self.assertNotIn("references/", out)
        self.assertIn("helper.py", out)

    def test_list_value_joined(self):
        out, _ = convert_skill_md(_skill("name: n\ndescription: d\nallowed-tools:\n  - bash\n  - read"))
        self.assertIn("`allowed-tools`: bash, read", out)

    def test_only_bob_keys_in_front_matter(self):
        out, _ = convert_skill_md(_skill("name: n\ndescription: d\nlicense: MIT"))
        fm_block = out.split("---")[1]
        self.assertNotIn("license", fm_block)


class TestConvertMain(unittest.TestCase):
    def setUp(self):
        import tempfile, os
        self.tmpdir = tempfile.mkdtemp()
        self.tmp = Path(self.tmpdir)

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmpdir)

    def test_single_skill(self):
        d = self.tmp / "sk"; d.mkdir()
        (d / "SKILL.md").write_text(_skill("name: sk\ndescription: d"))
        rc = convert_main([str(d), "-o", str(self.tmp / "out")])
        self.assertEqual(rc, 0)
        self.assertTrue((self.tmp / "out" / "sk" / "SKILL.md").exists())

    def test_skill_md_file_input(self):
        d = self.tmp / "sk"; d.mkdir()
        md = d / "SKILL.md"; md.write_text(_skill("name: sk\ndescription: d"))
        rc = convert_main([str(md), "-o", str(self.tmp / "out")])
        self.assertEqual(rc, 0)

    def test_batch(self):
        for name in ("alpha", "beta", "gamma"):
            d = self.tmp / "src" / name; d.mkdir(parents=True)
            (d / "SKILL.md").write_text(_skill(f"name: {name}\ndescription: desc"))
        rc = convert_main([str(self.tmp / "src"), "-o", str(self.tmp / "out"), "--batch"])
        self.assertEqual(rc, 0)
        for name in ("alpha", "beta", "gamma"):
            self.assertTrue((self.tmp / "out" / name / "SKILL.md").exists())

    def test_batch_skips_bad_skill(self):
        good = self.tmp / "src" / "good"; good.mkdir(parents=True)
        (good / "SKILL.md").write_text(_skill("name: good\ndescription: Fine"))
        bad = self.tmp / "src" / "bad"; bad.mkdir(parents=True)
        (bad / "SKILL.md").write_text("no front matter")
        rc = convert_main([str(self.tmp / "src"), "-o", str(self.tmp / "out"), "--batch"])
        self.assertEqual(rc, 0)
        self.assertTrue((self.tmp / "out" / "good" / "SKILL.md").exists())

    def test_support_files_copied(self):
        d = self.tmp / "sk"; d.mkdir()
        (d / "SKILL.md").write_text(_skill("name: sk\ndescription: d"))
        (d / "scripts").mkdir(); (d / "scripts" / "helper.py").write_text("print('hi')")
        convert_main([str(d), "-o", str(self.tmp / "out")])
        self.assertTrue((self.tmp / "out" / "sk" / "scripts" / "helper.py").exists())

    def test_evals_not_copied(self):
        d = self.tmp / "sk"; d.mkdir()
        (d / "SKILL.md").write_text(_skill("name: sk\ndescription: d"))
        (d / "evals").mkdir(); (d / "evals" / "t.json").write_text("{}")
        convert_main([str(d), "-o", str(self.tmp / "out")])
        self.assertFalse((self.tmp / "out" / "sk" / "evals").exists())

    def test_missing_input_returns_1(self):
        rc = convert_main([str(self.tmp / "nope"), "-o", str(self.tmp / "out")])
        self.assertEqual(rc, 1)


PROC_BODY = textwrap.dedent("""\
    ## Workflow

    1. Build the artifact.
    2. Run the tests.
    3. Push to registry.

    ## Notes

    Keep things tidy.
""")


class TestRestepMarkdown(unittest.TestCase):
    def test_converts_proc_list(self):
        out, report = restep_markdown(PROC_BODY)
        self.assertIn("<Steps>", out)
        self.assertIn("<Step>", out)
        self.assertIn("Build the artifact.", out)
        self.assertEqual(len(report), 1)
        self.assertIn("Workflow", report[0])

    def test_leaves_non_proc_heading(self):
        out, report = restep_markdown("## Design principles\n\n1. Keep it simple.\n2. Fail loud.\n")
        self.assertNotIn("<Steps>", out)
        self.assertEqual(report, [])

    def test_no_table_conversion(self):
        out, _ = restep_markdown("## Workflow\n\n| A | B |\n|---|---|\n| 1 | 2 |\n")
        self.assertNotIn("<Steps>", out)

    def test_no_fenced_code_conversion(self):
        out, _ = restep_markdown("## Workflow\n\n```bash\n1. fake\n2. also fake\n```\n")
        self.assertNotIn("<Steps>", out)

    def test_no_blockquote_conversion(self):
        out, _ = restep_markdown("## Workflow\n\n> 1. note\n> 2. another\n")
        self.assertNotIn("<Steps>", out)

    def test_front_matter_preserved(self):
        text = _skill("name: n\ndescription: d", PROC_BODY)
        out, _ = restep_skill_md(text)
        self.assertTrue(out.startswith("---\n"))
        self.assertIn("<Steps>", out)

    def test_aggressive_converts_imperative_paras(self):
        body = "## Setup steps\n\nInstall the dependencies.\n\nConfigure the database.\n\nRun the migration.\n"
        out, report = restep_markdown(body, aggressive=True)
        self.assertIn("<Steps>", out)
        self.assertTrue(any("aggressive" in r for r in report))

    def test_aggressive_off_by_default(self):
        body = "## Setup steps\n\nInstall the dependencies.\n\nConfigure the database.\n"
        out, _ = restep_markdown(body, aggressive=False)
        self.assertNotIn("<Steps>", out)

    def test_no_triple_blank_lines(self):
        out, _ = restep_markdown(PROC_BODY)
        self.assertNotIn("\n\n\n", out)


if __name__ == "__main__":
    unittest.main()
