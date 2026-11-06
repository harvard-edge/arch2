"""The audit gate must reject the ways a result could avoid independent review."""
import importlib.util
import json
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parent.parent
spec = importlib.util.spec_from_file_location(
    "gate", ROOT / "data/validate_evidence_audit.py"
)
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


CAPTION = '![**Claim.** Body.](images/x){#fig-x fig-alt="Chart."}'


def good_record(digest, caption=None):
    return {
        "figure": "fig-x",
        "producer": "session-a",
        "auditor": "session-b",
        "audited_on": "2026-11-02",
        "inputs": {
            "data/x.csv": digest,
            "caption": caption or gate.hashlib.sha256(CAPTION.encode()).hexdigest(),
        },
        "source_check": "reread the source table",
        "rerun": {"command": "python3 x.py", "result": "values match"},
        "attempts": [
            {"attack": f"attack {i}", "outcome": "survived"} for i in range(3)
        ],
        "negative_control": "a shuffled input changed the output",
        "limits": "one machine",
        "verdict": "PASS",
    }


@pytest.fixture
def repo(tmp_path):
    (tmp_path / "data/datasets").mkdir(parents=True)
    (tmp_path / "data/audits").mkdir()
    (tmp_path / "data/x.csv").write_text("a\n1\n")
    (tmp_path / "book/contents").mkdir(parents=True)
    (tmp_path / "book/contents/c.qmd").write_text(CAPTION + "\n")
    manifest = {
        "figure_evidence": {
            "fig-x": {"evidence_class": "measured", "data": ["data/x.csv"]},
            "fig-c": {"evidence_class": "conceptual"},
        }
    }
    (tmp_path / "data/datasets/provenance.yml").write_text(yaml.safe_dump(manifest))
    return tmp_path


def write(repo, record):
    (repo / "data/audits/fig-x.yml").write_text(yaml.safe_dump(record))


def digest(repo):
    return gate.sha256(repo / "data/x.csv")


def test_unaudited_figure_fails(repo):
    assert any("no independent audit" in f for f in gate.check(repo)[0])


def test_conceptual_figure_is_not_gated(repo):
    write(repo, good_record(digest(repo)))
    assert gate.check(repo) == ([], {"audited": 1, "baseline": 0})


def test_self_audit_fails(repo):
    write(repo, good_record(digest(repo)) | {"auditor": "session-a"})
    assert any("auditor is the producer" in f for f in gate.check(repo)[0])


def test_changed_input_makes_audit_stale(repo):
    write(repo, good_record(digest(repo)))
    (repo / "data/x.csv").write_text("a\n2\n")
    assert any("stale audit" in f for f in gate.check(repo)[0])


def test_changed_caption_makes_audit_stale(repo):
    write(repo, good_record(digest(repo)))
    (repo / "book/contents/c.qmd").write_text(
        CAPTION.replace("Claim", "Stronger claim") + "\n"
    )
    assert any("stale audit" in f and "caption" in f for f in gate.check(repo)[0])


def test_code_cell_caption_is_found(repo):
    (repo / "book/contents/c.qmd").write_text(
        "```{python}\n#| label: fig-x\n#| fig-cap: |\n#|   **Claim.**\nimport csv\n```\n"
    )
    assert "**Claim.**" in gate.figure_text(
        repo, "fig-x"
    ) and "import" not in gate.figure_text(repo, "fig-x")


def test_fail_verdict_fails(repo):
    write(repo, good_record(digest(repo)) | {"verdict": "FAIL"})
    assert any("verdict is FAIL" in f for f in gate.check(repo)[0])


def test_broken_attempt_cannot_pass(repo):
    record = good_record(digest(repo))
    record["attempts"][0]["outcome"] = "broken"
    write(repo, record)
    assert any("broken attempt" in f for f in gate.check(repo)[0])


def test_too_few_attempts_fail(repo):
    record = good_record(digest(repo))
    record["attempts"] = record["attempts"][:2]
    write(repo, record)
    assert any("at least 3" in f for f in gate.check(repo)[0])


@pytest.mark.parametrize("field", gate.REQUIRED_FIELDS)
def test_every_required_field_is_enforced(repo, field):
    record = good_record(digest(repo))
    del record[field]
    write(repo, record)
    assert any(field in f for f in gate.check(repo)[0])


def frozen(repo):
    return gate.bound_hashes(repo, "fig-x", ["data/x.csv"])


def test_unchanged_baseline_figure_passes(repo):
    (repo / "data/audits/BASELINE.json").write_text(json.dumps({"fig-x": frozen(repo)}))
    assert gate.check(repo) == ([], {"audited": 0, "baseline": 1})


def test_changed_baseline_input_fails(repo):
    (repo / "data/audits/BASELINE.json").write_text(json.dumps({"fig-x": frozen(repo)}))
    (repo / "data/x.csv").write_text("a\n2\n")
    assert any("changed since the baseline" in f for f in gate.check(repo)[0])


def test_changed_baseline_caption_fails(repo):
    (repo / "data/audits/BASELINE.json").write_text(json.dumps({"fig-x": frozen(repo)}))
    (repo / "book/contents/c.qmd").write_text(
        CAPTION.replace("Claim", "Stronger claim") + "\n"
    )
    assert any("changed since the baseline" in f for f in gate.check(repo)[0])


@pytest.mark.parametrize("label", ["mined", "modeled", "derived", "unknown"])
def test_only_conceptual_escapes_the_gate(repo, label):
    path = repo / "data/datasets/provenance.yml"
    manifest = yaml.safe_load(path.read_text())
    manifest["figure_evidence"]["fig-x"]["evidence_class"] = label
    path.write_text(yaml.safe_dump(manifest))
    assert any("no independent audit" in f for f in gate.check(repo)[0])


def test_baseline_cannot_grow_or_be_rewritten(repo):
    subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
    base = repo / "data/audits/BASELINE.json"
    base.write_text(json.dumps({"fig-other": {"p": "h"}}))
    subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
    subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@t", "commit", "-qm", "x"],
        cwd=repo,
        check=True,
    )
    base.write_text(
        json.dumps({"fig-other": {"p": "h2"}, "fig-x": {"data/x.csv": digest(repo)}})
    )
    failures = gate.check(repo)[0]
    assert any("added to the baseline" in f for f in failures)
    assert any("baseline hashes rewritten" in f for f in failures)
