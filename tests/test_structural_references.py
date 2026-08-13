"""Contract tests for the hard-coded and deictic structure-reference gates.

Both rules run inside ``arch2 check precommit`` via ``run_refs_check``. They are
regex-driven, so the failure mode is silent erosion: a widened pattern that stops
matching, or a narrowed one that starts flagging correct prose. These tests pin
both edges.
"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "cli"))

import arch2  # noqa: E402


def codes_for(text: str) -> set[str]:
    """Run both structure-reference rules over one snippet of manuscript prose."""
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "sample.qmd"
        path.write_text(text, encoding="utf-8")
        findings = arch2.structural_reference_findings(
            path
        ) + arch2.deictic_reference_findings(path)
    return {finding.code for finding in findings}


class HardCodedStructureReferences(unittest.TestCase):
    def test_hard_coded_numbers_are_rejected(self) -> None:
        for prose in (
            "The target introduced in Chapter 1 sets the envelope.",
            "Chapters 4 and 5 both develop the argument.",
            "The sweep is summarized in Table 2.1 for reference.",
            "The loop is drawn in Figure 4.2 for reference.",
            "The harness is given in Listing 3.2 for reference.",
            "The harness is given in Lst. 3 for reference.",
            "The protocol is stated in Section 2.3 for reference.",
            "The derivation is Equation 3 in full.",
            "The ledger is reproduced in Appendix A in full.",
            r"The loop is drawn in \ref{fig-design-loop} for reference.",
            r"The protocol is stated in \ref{sec-moonshot} for reference.",
            "The target is introduced in @chap-moonshot for reference.",
        ):
            with self.subTest(prose=prose):
                self.assertIn("raw-structure-reference", codes_for(prose))

    def test_correct_cross_references_pass(self) -> None:
        for prose in (
            "The target introduced in @sec-moonshot sets the envelope.",
            "The loop is drawn in @fig-design-loop and @tbl-proxy-metrics.",
            "The harness is given in @lst-sweep-driver for reference.",
            r"The loop is drawn in \ref{fig:design-loop} for reference.",
        ):
            with self.subTest(prose=prose):
                self.assertEqual(set(), codes_for(prose))

    def test_named_parts_are_allowed(self) -> None:
        """Quarto emits no @part-* reference, so Part I has nothing to migrate to."""
        for prose in (
            "Synthesizing the core principles of Part I, we turn to practice.",
            "In Part II, we define four modular technical building blocks.",
        ):
            with self.subTest(prose=prose):
                self.assertEqual(set(), codes_for(prose))

    def test_citation_keys_are_not_structure_references(self) -> None:
        self.assertEqual(
            set(), codes_for("The result holds broadly [@Chapter2020Something].")
        )

    def test_fenced_code_is_exempt(self) -> None:
        self.assertEqual(set(), codes_for("```\nsee Figure 4.2\n```\n"))


class DeicticStructureReferences(unittest.TestCase):
    def test_positional_pointers_are_rejected(self) -> None:
        for prose in (
            "We develop the harness in the next chapter.",
            "We saw the failure in the previous section.",
            "We pivot to controlled replacements in the following section.",
            "The sweep is summarized in the table above.",
            "The loop appears in the figure below.",
        ):
            with self.subTest(prose=prose):
                self.assertIn("deictic-structure-reference", codes_for(prose))

    def test_an_anchored_line_is_exempt(self) -> None:
        """A named target survives a reorder, so the deictic phrase is only colour."""
        self.assertEqual(
            set(),
            codes_for(
                "In the next chapter (@sec-loop-patterns-across-stack), we ask "
                "which parts of the record can be reused."
            ),
        )

    def test_preceding_part_is_allowed(self) -> None:
        self.assertEqual(set(), codes_for("The preceding part closed our argument."))

    def test_ordinary_prose_passes(self) -> None:
        for prose in (
            "The next attempt records a rejected candidate.",
            "We take the previous estimate as the baseline.",
            "The measured value sits below the thermal ceiling.",
        ):
            with self.subTest(prose=prose):
                self.assertEqual(set(), codes_for(prose))


class MachineReadableFindings(unittest.TestCase):
    """The JSON contract that makes a finding repairable without re-derivation."""

    def test_a_fixable_finding_carries_an_exact_edit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.qmd"
            path.write_text("Cost is bounded[^fn-cost-c01].\n", encoding="utf-8")
            findings = arch2.footnote_punctuation_findings(path)
        self.assertEqual(1, len(findings))
        record = findings[0].as_record()
        self.assertTrue(record["fixable"])
        self.assertEqual("[^fn-cost-c01].", record["span"])
        self.assertEqual(".[^fn-cost-c01]", record["replacement"])
        self.assertEqual(path.name, Path(record["path"]).name)
        self.assertEqual(1, record["line"])
        # The span must be applicable to the context verbatim.
        self.assertIn(record["span"], record["context"])

    def test_footnote_definitions_are_not_markers(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.qmd"
            path.write_text(
                "[^fn-cost-c01]: **Cost**: the bounded figure.\n", encoding="utf-8"
            )
            self.assertEqual([], arch2.footnote_punctuation_findings(path))

    def test_a_judgment_finding_is_not_marked_fixable(self) -> None:
        finding = arch2.Finding("error", "x", "a.qmd:1", "msg")
        self.assertFalse(finding.fixable)
        self.assertNotIn("span", finding.as_record())

    def test_a_non_positional_location_yields_no_path(self) -> None:
        record = arch2.Finding("warning", "citation-reuse", "SomeKey", "m").as_record()
        self.assertNotIn("path", record)
        self.assertNotIn("line", record)


class LineEditApplication(unittest.TestCase):
    """Repairs must compose on one line regardless of the order they arrive in."""

    def test_two_identical_spans_on_one_line_are_each_repaired(self) -> None:
        out = arch2.apply_line_edits(
            "Budget is 3 W and the ceiling is 3 W overall.",
            [("3 W", r"3\ W"), ("3 W", r"3\ W")],
        )
        self.assertEqual(r"Budget is 3\ W and the ceiling is 3\ W overall.", out)

    def test_edits_out_of_document_order_still_apply(self) -> None:
        """Findings arrive grouped by rule, so a later span can be listed first."""
        line = "The budget is 3 W in practice[^fn-x]."
        out = arch2.apply_line_edits(line, [("[^fn-x].", ".[^fn-x]"), ("3 W", r"3\ W")])
        self.assertEqual(r"The budget is 3\ W in practice.[^fn-x]", out)

    def test_a_span_that_is_absent_is_an_error_not_a_silent_skip(self) -> None:
        with self.assertRaises(ValueError):
            arch2.apply_line_edits("nothing here", [("3 W", r"3\ W")])


class Suppression(unittest.TestCase):
    """A deliberate exception must be cheap to express and impossible to hide."""

    def _map(self, text: str) -> dict:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "s.qmd"
            path.write_text(text, encoding="utf-8")
            return arch2.suppression_map(path)

    def _hygiene(self, text: str) -> set:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "s.qmd"
            path.write_text(text, encoding="utf-8")
            return {f.code for f in arch2.suppression_hygiene_findings([path])}

    def test_trailing_directive_covers_its_own_line(self) -> None:
        self.assertEqual(
            {1: {"informal-idiom"}},
            self._map("Text. <!-- arch2-allow: informal-idiom defended in fn -->\n"),
        )

    def test_standalone_directive_covers_the_next_content_line(self) -> None:
        self.assertEqual(
            {3: {"em-dash"}},
            self._map("<!-- arch2-allow: em-dash quoted source -->\n\nThe line.\n"),
        )

    def test_a_directive_without_a_reason_grants_nothing(self) -> None:
        self.assertEqual({}, self._map("Text. <!-- arch2-allow: em-dash -->\n"))

    def test_a_directive_without_a_reason_is_itself_reported(self) -> None:
        self.assertEqual(
            {"arch2-allow-missing-reason"},
            self._hygiene("Text. <!-- arch2-allow: em-dash -->\n"),
        )

    def test_a_reasoned_directive_is_accepted(self) -> None:
        self.assertEqual(
            set(), self._hygiene("Text. <!-- arch2-allow: em-dash quoted -->\n")
        )


class OnlyChildSections(unittest.TestCase):
    """A subdivision needs at least two members to be a subdivision."""

    def _codes(self, text: str) -> set:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "s.qmd"
            path.write_text(text, encoding="utf-8")
            return {f.code for f in arch2.only_child_section_findings(path)}

    def test_a_lone_subsection_is_rejected(self) -> None:
        self.assertEqual(
            {"only-child-section"},
            self._codes("## Parent\n\nProse.\n\n### Only Child\n\nMore.\n"),
        )

    def test_two_subsections_are_fine(self) -> None:
        self.assertEqual(
            set(),
            self._codes("## Parent\n\n### First\n\na\n\n### Second\n\nb\n"),
        )

    def test_a_section_with_no_subsections_is_fine(self) -> None:
        self.assertEqual(
            set(), self._codes("## Parent\n\nProse only.\n\n## Next\n\nb\n")
        )

    def test_a_grandchild_does_not_count_as_a_sibling(self) -> None:
        self.assertEqual(
            {"only-child-section"},
            self._codes("## Parent\n\n### Child\n\n#### Grandchild\n\na\n"),
        )

    def test_the_next_parent_ends_the_search(self) -> None:
        """A subsection of the following section is not a sibling of this one."""
        self.assertEqual(
            set(),
            self._codes("## One\n\nProse.\n\n## Two\n\n### A\n\na\n\n### B\n\nb\n"),
        )


if __name__ == "__main__":
    unittest.main()


class InterpreterCompatibility(unittest.TestCase):
    """The CLI must parse on the oldest Python CI runs, not just the local one.

    A backslash inside an f-string expression is a SyntaxError before 3.12 and
    legal from 3.12 on. Developing on a newer interpreter therefore hides the
    fault until CI rejects it, which is how it reached main once already.
    ``ast.parse(feature_version=...)`` does not help: the change is in the
    tokenizer and is not gated by that flag. Only a real old interpreter is.
    """

    CI_VERSIONS = ("3.10", "3.11")

    def test_cli_parses_on_the_oldest_available_ci_interpreter(self) -> None:
        import shutil
        import subprocess

        target = str(ROOT / "cli" / "arch2.py")
        checked = []
        for version in self.CI_VERSIONS:
            binary = shutil.which(f"python{version}")
            if not binary:
                continue
            checked.append(version)
            result = subprocess.run(
                [binary, "-c", f"import ast;ast.parse(open({target!r}).read())"],
                capture_output=True,
                text=True,
            )
            self.assertEqual(
                0,
                result.returncode,
                f"python{version} rejects the CLI:\n{result.stderr}",
            )
        if not checked:
            self.skipTest(f"none of {self.CI_VERSIONS} installed locally")
