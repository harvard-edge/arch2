"""Negative tests: each check must fail on the shortcut it exists to stop."""
import ast
import hashlib
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"data/{name}.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


claims = load("validate_claims")
runs = load("validate_runs")
scan = load("scan_shortcuts")


def kinds(code):
    return {kind for _, kind in scan.scan_tree(ast.parse(code))}


def claim(**extra):
    base = {
        "claim_id": "C1",
        "description": "d",
        "verbatim_quote": "gain of 3x",
        "label": "measured",
        "origin": "third-party-reported",
        "headline": False,
        "citations": ["K"],
    }
    return {**base, **extra}


def errors_for(item, chapter="a gain of 3x here"):
    errors = []
    claims.check_claim(item, chapter, {"K"}, errors, "w")
    return errors


def test_valid_claim_passes():
    assert errors_for(claim()) == []


def test_claim_without_evidence_fails():
    assert any("no evidence" in e for e in errors_for(claim(citations=[])))


def test_bad_label_fails():
    assert any("label" in e for e in errors_for(claim(label="verified")))


def test_unknown_citation_fails():
    assert any("not in references" in e for e in errors_for(claim(citations=["Nope"])))


def test_quote_gone_from_chapter_fails():
    assert any("no longer appears" in e for e in errors_for(claim(), "different text"))


def test_changed_evidence_fails():
    item = claim(source_files=[{"path": "data/validate_runs.py", "sha256": "0" * 64}])
    assert any("changed since" in e for e in errors_for(item))


def test_own_run_without_results_fails():
    assert any("own-run" in e for e in errors_for(claim(origin="own-run")))


def test_modeled_without_assumptions_fails():
    assert any("assumptions" in e for e in errors_for(claim(label="modeled")))


def test_formula_mismatch_fails():
    item = claim(
        formula="a / b", raw_inputs={"a": 3, "b": 2}, stated_value=2.0, tolerance=0.01
    )
    assert any("formula gives" in e for e in errors_for(item))


def test_formula_match_passes():
    item = claim(
        formula="a / b", raw_inputs={"a": 3, "b": 2}, stated_value=1.5, tolerance=0.01
    )
    assert errors_for(item) == []


def test_quantity_pattern_finds_multiplier_and_inline():
    assert claims.QUANTITY.search("a 17× gap")
    assert claims.QUANTITY.search("value `{python} x` here")
    assert not claims.QUANTITY.search("three chapters in 2021")


def test_scanner_flags_hidden_failure():
    assert "hidden-failure" in kinds("try:\n    f()\nexcept Exception:\n    pass\n")
    assert "hidden-failure" in kinds("try:\n    f()\nexcept:\n    raise\n")


def test_scanner_passes_reraised_failure():
    assert "hidden-failure" not in kinds(
        "try:\n    f()\nexcept ValueError:\n    raise SystemExit(1)\n"
    )


def test_scanner_flags_fallback_default():
    assert "fallback-default" in kinds("x = row.get('gain', 1.0)\n")
    assert "fallback-default" in kinds("x = gain or 1.0\n")


def test_scanner_flags_typed_series_inline():
    assert "hardcoded-values" in kinds("ax.bar(x, [1.1, 2.2, 3.3, 4.4])\n")


def test_scanner_flags_hardcoded_result_and_random():
    assert "hardcoded-result" in kinds("total_errata = 1234\n")
    assert "random-data" in kinds("y = np.random.normal(size=3)\n")


def test_scanner_flags_dropped_items_and_mock():
    assert "dropped-items" in kinds(
        "for p in ps:\n    if not p.exists():\n        continue\n"
    )
    assert "mock-data" in kinds("dummy_scores = load()\n")


def make_log(tmp_path, elapsed=5.0, timing="within_expected", note=False):
    study = tmp_path / "data/studies/x"
    (study / "runs").mkdir(parents=True)
    console = study / "runs/a.log"
    console.write_text("ok")
    record = {
        "type": "run",
        "run_id": "a",
        "started_utc": "t",
        "reason": "r",
        "command": ["c"],
        "exit_code": 0,
        "elapsed_s": elapsed,
        "expected_s": [1, 10],
        "timing": timing,
        "code_sha": "s",
        "dirty": False,
        "host": {},
        "changed_outputs": {},
        "log": "runs/a.log",
        "log_sha256": hashlib.sha256(b"ok").hexdigest(),
    }
    rows = [json.dumps(record)]
    if note:
        rows.append(json.dumps({"type": "timing_note", "run_id": "a", "text": "why"}))
    (study / "runs.jsonl").write_text("\n".join(rows) + "\n")
    return study


def check(study, monkeypatch):
    monkeypatch.setattr(runs, "committed", lambda path: "")
    errors = []
    runs.check_log(study, errors)
    return errors


def test_run_log_passes(tmp_path, monkeypatch):
    assert check(make_log(tmp_path), monkeypatch) == []


def test_too_fast_run_fails_until_explained(tmp_path, monkeypatch):
    errors = check(make_log(tmp_path, 0.1, "outside_expected"), monkeypatch)
    assert any("unexplained" in e for e in errors)


def test_explained_timing_passes(tmp_path, monkeypatch):
    assert (
        check(make_log(tmp_path, 0.1, "outside_expected", note=True), monkeypatch) == []
    )


def test_false_timing_field_fails(tmp_path, monkeypatch):
    errors = check(make_log(tmp_path, 0.1, "within_expected"), monkeypatch)
    assert any("contradicts" in e for e in errors)


def test_edited_console_log_fails(tmp_path, monkeypatch):
    study = make_log(tmp_path)
    (study / "runs/a.log").write_text("edited")
    assert any("was changed" in e for e in check(study, monkeypatch))


def test_rewritten_history_fails(tmp_path, monkeypatch):
    study = make_log(tmp_path)
    monkeypatch.setattr(runs, "committed", lambda path: "older line that was deleted\n")
    errors = []
    runs.check_log(study, errors)
    assert any("rewrites committed history" in e for e in errors)


def test_run_wrapper_logs_a_failing_attempt():
    import shutil
    import subprocess

    study = ROOT / "data/studies/zz-wrapper-test"
    study.mkdir()
    try:
        done = subprocess.run(
            [
                sys.executable,
                "data/run_study.py",
                "zz-wrapper-test",
                "--expected",
                "0",
                "60",
                "--reason",
                "test",
                "--",
                sys.executable,
                "-c",
                "raise SystemExit(3)",
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        assert done.returncode == 3, done.stderr
        record = json.loads((study / "runs.jsonl").read_text().splitlines()[0])
        assert (
            record["exit_code"] == 3
            and record["reason"] == "test"
            and record["timing"] == "within_expected"
        )
    finally:
        shutil.rmtree(study)


def test_constructed_claim_without_a_stated_basis_fails():
    item = claim(label="constructed", origin="author-example", citations=[])
    assert any("assumptions" in e for e in errors_for(item))


def test_constructed_claim_with_a_stated_basis_passes():
    item = claim(
        label="constructed",
        origin="author-example",
        citations=[],
        assumptions="worked example, values chosen",
    )
    assert errors_for(item) == []


def test_same_second_runs_keep_separate_logs():
    import shutil
    import subprocess

    study = ROOT / "data/studies/zz-wrapper-test"
    study.mkdir()
    try:
        for _ in range(4):
            subprocess.run(
                [
                    sys.executable,
                    "data/run_study.py",
                    "zz-wrapper-test",
                    "--expected",
                    "0",
                    "60",
                    "--reason",
                    "t",
                    "--",
                    sys.executable,
                    "-c",
                    "pass",
                ],
                cwd=ROOT,
                capture_output=True,
            )
        ids = [
            json.loads(line)["run_id"]
            for line in (study / "runs.jsonl").read_text().splitlines()
        ]
        assert len(set(ids)) == 4
        assert len(list((study / "runs").glob("*.log"))) == 4
    finally:
        shutil.rmtree(study)
