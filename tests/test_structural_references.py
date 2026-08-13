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


if __name__ == "__main__":
    unittest.main()
