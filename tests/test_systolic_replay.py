"""Regression checks for the frozen systolic study's standalone replay."""
from __future__ import annotations

import importlib.metadata
import importlib.util
import json
import shutil
from pathlib import Path

import pytest

STUDY = Path(__file__).resolve().parents[1] / "data/studies/ai_systolic_array_study"
SPEC = importlib.util.spec_from_file_location("systolic_replay", STUDY / "replay.py")
assert SPEC and SPEC.loader
REPLAY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(REPLAY)


@pytest.fixture
def fixture(tmp_path):
    root = tmp_path / "study"
    shutil.copytree(STUDY, root, ignore=shutil.ignore_patterns("__pycache__"))
    return root


def _reference(root):
    return root / "recorded/reference"


def _reports(root):
    return REPLAY.report_dir(_reference(root), "model_baseline_32x32")


def _refresh_manifest(root, paths):
    """Refresh test-copy hashes to exercise checks beyond the manifest."""
    reference = _reference(root)
    manifest_path = reference / "reference_manifest.json"
    manifest = json.loads(manifest_path.read_text())
    for entry in manifest["files"]:
        if entry["path"] in paths:
            path = reference / entry["path"]
            entry.update(sha256=REPLAY.sha256(path), size_bytes=path.stat().st_size)
    manifest_path.write_text(json.dumps(manifest))


def _change_results(root, change):
    reference = _reference(root)
    path = reference / "study_results.json"
    result = json.loads(path.read_text())
    change(result)
    path.write_text(json.dumps(result))
    (reference / "evaluations.jsonl").write_text(
        "\n".join(json.dumps(r) for r in result["evaluations"]) + "\n"
    )
    _refresh_manifest(root, {"study_results.json", "evaluations.jsonl"})


def test_verify_archived_fixture_is_read_only(fixture):
    files = [path for path in fixture.rglob("*") if path.is_file()]
    before = {path: REPLAY.sha256(path) for path in files}
    result = REPLAY.verify(fixture)
    assert len(result["evaluations"]) == 12
    assert result["ai_contribution_claim"]["status"] == "tie"
    assert before == {path: REPLAY.sha256(path) for path in files}


def test_tampered_record_fails_hash_check(fixture):
    path = _reference(fixture) / "study_results.json"
    path.write_text(
        path.read_text().replace(
            '"decision_score": 33782.', '"decision_score": 43782.', 1
        )
    )
    with pytest.raises(REPLAY.ReplayError, match="SHA256"):
        REPLAY.verify(fixture)


def test_missing_report_fails_verification(fixture):
    (_reports(fixture) / "COMPUTE_REPORT.csv").unlink()
    with pytest.raises(REPLAY.ReplayError, match="missing or external file"):
        REPLAY.verify(fixture)


def test_metric_mismatch_fails_even_with_refreshed_manifest(fixture):
    _change_results(
        fixture,
        lambda result: result["evaluations"][0]["metrics"].update(total_cycles=13918),
    )
    with pytest.raises(REPLAY.ReplayError, match="recomputed metrics.total_cycles"):
        REPLAY.verify(fixture)


def test_score_mismatch_fails_even_with_refreshed_manifest(fixture):
    _change_results(
        fixture, lambda result: result["evaluations"][0].update(decision_score=33783.0)
    )
    with pytest.raises(REPLAY.ReplayError, match="recomputed decision score"):
        REPLAY.verify(fixture)


def test_missing_run_is_not_silently_zipped_away(fixture):
    _change_results(fixture, lambda result: result["evaluations"].pop())
    with pytest.raises(REPLAY.ReplayError, match="twelve evaluations"):
        REPLAY.verify(fixture)


def test_recommendation_shape_must_match_selected_candidate(fixture):
    _change_results(
        fixture, lambda result: result["recommendation"].update(shape=[64, 16])
    )
    with pytest.raises(REPLAY.ReplayError, match="recommendation.shape"):
        REPLAY.verify(fixture)


def test_gate_result_cannot_pass_after_recomputed_deadline_failure(fixture):
    candidate = "ai_extreme_8x128"
    report_dir = REPLAY.report_dir(_reference(fixture), candidate)
    report = report_dir / "COMPUTE_REPORT.csv"
    first_layer_cycles = int(REPLAY.report_rows(report)[0]["Total Cycles"])
    _alter_report(report, "Total Cycles", str(first_layer_cycles + 100000))
    relative_report = report.relative_to(_reference(fixture)).as_posix()
    _refresh_manifest(fixture, {relative_report})

    def change(result):
        record = next(
            r for r in result["evaluations"] if r["candidate_id"] == candidate
        )
        computed = REPLAY.metrics(report_dir)
        record["metrics"] = computed
        record["decision_score"] = computed["total_cycles"] / (
            computed["avg_layer_util_pct"] / 100
        )
        record["gates"]["deadline"].update(
            observed=computed["total_cycles"], passed=False
        )
        for entry in record["raw_outputs"]:
            if entry["path"] == relative_report:
                entry["sha256"] = REPLAY.sha256(report)
        # Leave gate_result='pass': internally consistent report/metric hashes
        # must not conceal this contradiction in the declared disposition.

    _change_results(fixture, change)
    with pytest.raises(
        REPLAY.ReplayError, match="gate_result is pass but a recomputed gate fails"
    ):
        REPLAY.verify(fixture)


@pytest.mark.parametrize("output_kind", ["existing", "inside_study", "symlink"])
def test_replay_refuses_destructive_output(fixture, tmp_path, output_kind):
    sentinel = fixture / "keep.txt"
    sentinel.write_text("preserve me")
    if output_kind == "existing":
        output = tmp_path / "existing"
        output.mkdir()
        (output / "keep.txt").write_text("existing output")
    elif output_kind == "symlink":
        output = tmp_path / "linked"
        output.symlink_to(fixture, target_is_directory=True)
    else:
        output = fixture / "new-output"
    with pytest.raises(REPLAY.ReplayError, match="output must"):
        REPLAY.replay(fixture, output)
    assert sentinel.read_text() == "preserve me"
    if output_kind == "existing":
        assert (output / "keep.txt").read_text() == "existing output"
    elif output_kind == "inside_study":
        assert not output.exists()


def _alter_report(path, column, replacement):
    rows = path.read_text().splitlines()
    headers = [field.strip() for field in rows[0].split(",")]
    fields = rows[1].split(",")
    fields[headers.index(column)] = " " + replacement
    rows[1] = ",".join(fields)
    path.write_text("\n".join(rows) + "\n")


@pytest.mark.parametrize(
    "column,value",
    [
        ("Total Cycles", "7104"),
        ("Total Cycles", "7103.00000000001"),
        ("Overall Util %", "57.66577502463748"),
        ("Compute Util %", "50.5928853755"),
        ("Compute Util %", "NaN"),
    ],
)
def test_replay_comparison_rejects_real_or_nonfinite_differences(
    tmp_path, column, value
):
    observed = tmp_path / "observed"
    shutil.copytree(_reports(STUDY), observed)
    _alter_report(observed / "COMPUTE_REPORT.csv", column, value)
    with pytest.raises(REPLAY.ReplayError):
        REPLAY.compare_reports(_reports(STUDY), observed)


def test_replay_comparison_allows_only_documented_diagnostic_roundoff(tmp_path):
    observed = tmp_path / "observed"
    shutil.copytree(_reports(STUDY), observed)
    _alter_report(
        observed / "COMPUTE_REPORT.csv", "Compute Util %", "50.59288537549407"
    )
    assert REPLAY.compare_reports(_reports(STUDY), observed) == 1


@pytest.mark.parametrize("change", ["missing_layer", "extra_column", "wrong_header"])
def test_replay_comparison_rejects_report_schema_changes(tmp_path, change):
    observed = tmp_path / "observed"
    shutil.copytree(_reports(STUDY), observed)
    path = observed / "COMPUTE_REPORT.csv"
    rows = path.read_text().splitlines()
    if change == "missing_layer":
        rows.pop()
    elif change == "extra_column":
        rows = [row + "1," for row in rows]
    else:
        rows[0] = rows[0].replace("Total Cycles,", "Different Cycles,")
    path.write_text("\n".join(rows) + "\n")
    with pytest.raises(REPLAY.ReplayError):
        REPLAY.compare_reports(_reports(STUDY), observed)


def test_full_replay_matches_twelve_runs_without_modifying_reference(tmp_path):
    pytest.importorskip("scalesim")
    if importlib.metadata.version("scalesim") != "3.0.0":
        pytest.skip("full replay requires SCALE-Sim 3.0.0")
    files = [path for path in (STUDY / "recorded").rglob("*") if path.is_file()]
    before = {path: REPLAY.sha256(path) for path in files}
    output = tmp_path / "fresh-replay"
    summary = REPLAY.replay(STUDY, output)
    assert summary["status"] == "matched"
    assert len(summary["runs"]) == 12
    assert json.loads((output / "replay_summary.json").read_text()) == summary
    assert before == {path: REPLAY.sha256(path) for path in files}
