"""Constructed comparison fixtures; no measured physical results in these tests."""

from copy import deepcopy

import pytest

from nanochip.laboratory.contracts import ContractError
from nanochip.laboratory.design_feedback import compare_outcomes, _selected_physical_metrics


def outcome(source, area):
    return dict(source_sha256=source, complete_design_eligible=False,
        metrics=dict(cell_area_um2=area), config_sha256="fixture", image="fixture",
        pdk_revision="fixture", cores=1, runner_sha256="fixture", coverage_script_sha256="fixture",
        checks=[dict(name=name, scope="block:msh_deq", status=status) for name,status in (
            ("dequant_vectors", "pass"), ("sequential_rtl_differential", "pass"),
            ("routed_timing", "pass"), ("electrical_constraints", "fail"),
            ("postroute_antenna", "fail"), ("gds_generated", "pass"),
            ("detailed_route_drc", "pass"), ("magic_drc", "pass"), ("klayout_drc", "pass"),
            ("physical_drc", "pass"), ("physical_lvs", "pass"))])


def test_area_preference_never_turns_failed_checks_into_acceptance():
    result = compare_outcomes(outcome("one", 120), outcome("two", 100))
    assert result["exploration_area_improved"]
    assert not result["accepted_design_improvement"]
    assert result["area_change_percent"] == pytest.approx(-100 / 6)


def test_same_design_with_rerun_area_variation_is_not_learning_improvement():
    result = compare_outcomes(outcome("same", 120), outcome("same", 100))
    assert result["same_design"]
    assert result["area_change_percent"] < 0
    assert not result["exploration_area_improved"]
    assert not result["accepted_design_improvement"]


@pytest.mark.parametrize("name", ["dequant_vectors", "sequential_rtl_differential", "routed_timing", "physical_lvs", "magic_drc", "electrical_constraints"])
def test_area_is_not_rewarded_without_functional_and_timing_checks(name):
    control, adapted = outcome("one", 120), outcome("two", 100)
    for row in (control, adapted):
        next(check for check in row["checks"] if check["name"] == name)["status"] = "unresolved"
    assert not compare_outcomes(control, adapted)["exploration_area_improved"]


def test_different_failed_families_cannot_earn_area_preference():
    adapted = outcome("two", 100)
    adapted["checks"].append(dict(name="physical_lvs", scope="block:msh_deq", status="fail"))
    assert not compare_outcomes(outcome("one", 120), adapted)["exploration_area_improved"]


def test_partial_run_does_not_produce_numeric_improvement():
    adapted = outcome("two", 100)
    adapted["metrics"] = None
    result = compare_outcomes(outcome("one", 120), adapted)
    assert result["area_change_percent"] is None
    assert not result["exploration_area_improved"]


def test_unmatched_physical_settings_are_rejected():
    control = outcome("one", 120)
    adapted = deepcopy(control)
    adapted["config_sha256"] = "other"
    with pytest.raises(ContractError, match="different physical settings"):
        compare_outcomes(control, adapted)


def test_feedback_metrics_follow_stages_after_flow_inserts_repairs(tmp_path):
    import json
    from nanochip.laboratory.physical.flow import collect_checks

    stages = {
        "32-openroad-checkantennas": {"route__antenna_violation__count": 0},
        "40-openroad-detailedrouting": {"route__drc_errors": 0},
        "42-openroad-checkantennas-1": {"route__antenna_violation__count": 7},
        "51-openroad-stapostpnr": {
            "design__instance__area": 123.0, "design__instance__count": 40,
            "timing__setup__ws": 2.0, "timing__hold__ws": 0.1,
            "timing__setup_vio__count": 0, "timing__hold_vio__count": 0,
            "timing__unconstrained__count": 0,
            "design__max_slew_violation__count": 98,
            "design__max_cap_violation__count": 1,
            "design__max_fanout_violation__count": 38,
        },
    }
    for name, metrics in stages.items():
        directory = tmp_path / "runs/physical" / name
        directory.mkdir(parents=True)
        (directory / "state_out.json").write_text(json.dumps({"metrics": metrics}))
    _, selected = collect_checks(tmp_path)
    result = _selected_physical_metrics(selected)
    assert result["antenna_violations"] == 7
    assert result["slew_violations"] == 98
    assert result["cell_area_um2"] == 123.0


def test_missing_postroute_measurements_cannot_label_feedback():
    with pytest.raises(ContractError, match="postroute antenna"):
        _selected_physical_metrics({})
