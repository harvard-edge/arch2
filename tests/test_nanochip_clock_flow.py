"""Clock-branch planning/identity checks; these are not closure evidence."""

from pathlib import Path
import hashlib
import json

import pytest

from nanochip.laboratory.physical.clock_flow import FLOW_FILES, branch_counts


@pytest.mark.parametrize("loads", [0, 1, 10, 11, 18, 81, 8193, 19118])
def test_planned_levels_cover_all_loads_and_end_within_unchanged_limit(loads):
    previous = loads
    levels = branch_counts(loads)
    for count in levels:
        assert count * 8 >= previous
        assert (count - 1) * 8 < previous
        assert count < previous
        previous = count
    assert previous <= 10
    assert bool(levels) == (loads > 10)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"loads": -1},
        {"loads": True},
        {"loads": 12, "group_size": 1},
        {"loads": 12, "group_size": 9},
        {"loads": 12, "limit": 1},
    ],
)
def test_invalid_clock_branch_plans_are_rejected(kwargs):
    with pytest.raises(ValueError):
        branch_counts(**kwargs)


def test_profile_files_are_present_and_profile_preserves_actual_clock_membership_guard():
    from nanochip.laboratory.physical import clock_flow

    root = Path(clock_flow.__file__).parent
    assert all((root / name).is_file() for name in FLOW_FILES)
    source = (root / "clock_repair.tcl").read_text()
    assert '[$net getSigType] ne "CLOCK"' in source
    assert "setSigType CLOCK" in source
    assert "nanochip_check_clock_power" in source


def test_midpnr_compatibility_changes_only_the_pinned_parasitic_branch(
    tmp_path, monkeypatch
):
    from nanochip.laboratory.physical import clock_flow

    block = (
        clock_flow.SKEW_BLOCK_START
        + "\nworst_clock_skew -hold\nreport_clock_skew -hold\n\n"
    )
    original = (
        "source set_rc.tcl\nif {[grt::have_routes]} {\n    estimate_parasitics -global_routing\n"
        + clock_flow.MIDPNR_OLD_BRANCH
        + "\nreport_checks\nreport_check_types\n"
        + block
        + clock_flow.SKEW_BLOCK_END
        + "\nworst_slack\n"
    )
    source, target = tmp_path / "original.tcl", tmp_path / "derived.tcl"
    source.write_text(original)
    monkeypatch.setattr(
        clock_flow,
        "MIDPNR_SCRIPT_SHA256",
        hashlib.sha256(source.read_bytes()).hexdigest(),
    )
    monkeypatch.setattr(
        clock_flow, "SKEW_BLOCK_SHA256", hashlib.sha256(block.encode()).hexdigest()
    )
    clock_flow.derive_midpnr_script(source, target)
    restored = target.read_text().replace(
        'puts "NANOCHIP_CLOCK_SKEW_DIAGNOSTICS=not_computed"\n\n', block
    )
    assert (
        restored.replace(clock_flow.MIDPNR_NEW_BRANCH, clock_flow.MIDPNR_OLD_BRANCH)
        == original
    )
    metadata = json.loads(target.with_suffix(".json").read_text())
    assert metadata["derived_sha256"] == hashlib.sha256(target.read_bytes()).hexdigest()
    assert metadata["clock_skew_diagnostics"]["status"] == "not_computed"
    source.write_text(original + "changed\n")
    with pytest.raises(ValueError, match="identity differs"):
        clock_flow.derive_midpnr_script(source, target)


def test_skew_invalidation_preserves_every_other_metric_and_never_invents_zero():
    from nanochip.laboratory.physical.clock_flow import invalidate_inherited_skew

    inherited = {
        "clock__skew__worst_hold": 1.5,
        "clock__skew__worst_hold__corner:old": 2,
        "timing__hold__ws": -0.2,
    }
    updates = {
        "timing__hold__ws": 0.1,
        "design__max_fanout_violation__count": 0,
        "clock__skew__unexpected": 9,
    }
    result = invalidate_inherited_skew(inherited, updates)
    assert result == {
        **updates,
        "clock__skew__worst_hold": None,
        "clock__skew__worst_hold__corner:old": None,
        "clock__skew__unexpected": None,
    }
    assert inherited["clock__skew__worst_hold"] == 1.5


def test_repeated_step_subclasses_receive_the_profile_and_keep_their_ids():
    from nanochip.laboratory.physical.clock_flow import replace_step_family

    class Original:
        id = "Original"

        @classmethod
        def with_id(cls, name):
            return type(cls.__name__, (cls,), {"id": name})

    class Replacement(Original):
        pass

    repeated = Original.with_id("Original-1")
    selected = replace_step_family(repeated, ((Original, Replacement),))
    assert issubclass(selected, Replacement)
    assert selected.id == repeated.id
    assert replace_step_family(str, ((Original, Replacement),)) is str


def test_drt_compatibility_preserves_resolved_layers_and_every_other_argument(
    tmp_path, monkeypatch
):
    from nanochip.laboratory.physical import clock_flow

    original = (
        "set min_layer met1\nset max_layer met5\n"
        + clock_flow.DRT_OLD_COMMAND
        + "    -or_seed 42\\\n    -droute_end_iter $::env(DRT_OPT_ITERS)\nwrite_views\n"
    )
    source, target = tmp_path / "drt.tcl", tmp_path / "derived.tcl"
    source.write_text(original)
    monkeypatch.setattr(
        clock_flow, "DRT_SCRIPT_SHA256", hashlib.sha256(source.read_bytes()).hexdigest()
    )
    clock_flow.derive_drt_script(source, target)
    assert (
        target.read_text().replace(
            clock_flow.DRT_NEW_COMMAND, clock_flow.DRT_OLD_COMMAND
        )
        == original
    )
    assert (
        '-signal "$min_layer-$max_layer" -clock "$min_layer-$max_layer"'
        in target.read_text()
    )
    source.write_text(original + "changed\n")
    with pytest.raises(ValueError, match="identity"):
        clock_flow.derive_drt_script(source, target)


@pytest.mark.parametrize(
    "configured,budget,expected", [(None, "2", 2), (8, "2", 2), (1, "2", 1)]
)
def test_router_threads_honor_the_declared_cpu_budget(configured, budget, expected):
    from nanochip.laboratory.physical.clock_flow import bounded_drt_threads

    assert bounded_drt_threads(configured, budget) == expected


@pytest.mark.parametrize(
    "configured,budget", [(None, None), (None, "0"), (None, "9"), (True, "2")]
)
def test_router_threads_reject_missing_or_invalid_resource_identity(configured, budget):
    from nanochip.laboratory.physical.clock_flow import bounded_drt_threads

    with pytest.raises(ValueError):
        bounded_drt_threads(configured, budget)
