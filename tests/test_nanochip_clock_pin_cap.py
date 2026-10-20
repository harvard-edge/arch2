"""Execute the production Tcl selector on a small mutable graph, without EDA."""
from decimal import Decimal
from pathlib import Path
import shutil
import subprocess

import pytest

from nanochip.laboratory.physical.clock_flow import validate_clock_repair_config


MOCK = r'''
namespace eval mock {}
namespace eval ord {}
namespace eval sta {}
set ::N [dict create]
set ::P [dict create]
set ::I [dict create]
set ::insertions 0
set ::queries 0
set ::unit_changes 0
set ::corners {tt ss ff}
proc handle {kind id} {
    set name ::mock.$kind.$id
    if {![llength [info commands $name]]} {interp alias {} $name {} dispatch $kind $id}
    return $name
}
proc addpin {instance port direction net caps} {
    set id $instance/$port
    dict set ::P $id [dict create inst $instance port $port direction $direction net $net caps $caps]
    set pins [dict get $::N $net pins]
    lappend pins $id
    dict set ::N $net pins $pins
}
proc dispatch {kind id method args} {
    switch $kind {
        db {
            if {$method eq "getChip"} {return [handle chip 0]}
            if {$method eq "getTech"} {return [handle tech 0]}
            if {$method eq "findMaster"} {return [handle master [lindex $args 0]]}
        }
        chip {if {$method eq "getBlock"} {return [handle block 0]}}
        tech {if {$method eq "getDbUnitsPerMicron"} {return 1000}}
        block {
            if {$method eq "getNets"} {return [lmap net [dict keys $::N] {handle net $net}]}
            set name [lindex $args 0]
            if {$method eq "findITerm"} {
                if {![dict exists $::P $name]} {return NULL}
                return [handle pin $name]
            }
            if {$method eq "findInst"} {
                if {![dict exists $::I $name]} {return NULL}
                return [handle inst $name]
            }
            if {$method eq "findNet"} {
                if {![dict exists $::N $name]} {return NULL}
                return [handle net $name]
            }
        }
        net {
            if {$method eq "getName"} {return $id}
            if {$method eq "getSigType"} {return [dict get $::N $id type]}
            if {$method eq "setSigType"} {dict set ::N $id type [lindex $args 0]; return}
            if {$method eq "getBTerms"} {return {}}
            if {$method eq "getITerms"} {return [lmap p [dict get $::N $id pins] {handle pin $p}]}
        }
        pin {
            if {$method eq "getInst"} {return [handle inst [dict get $::P $id inst]]}
            if {$method eq "getMTerm"} {return [handle mterm $id]}
            if {$method eq "getNet"} {return [handle net [dict get $::P $id net]]}
        }
        mterm {
            if {$method eq "getIoType"} {return [dict get $::P $id direction]}
            if {$method eq "getName"} {return [dict get $::P $id port]}
        }
        inst {
            if {$method eq "getName"} {return $id}
            if {$method eq "getMaster"} {return [handle master [dict get $::I $id master]]}
            if {$method eq "getLocation"} {return [dict get $::I $id location]}
            if {$method eq "getITerms"} {
                set pins [list]
                dict for {p data} $::P {if {[dict get $data inst] eq $id} {lappend pins [handle pin $p]}}
                return $pins
            }
        }
        master {if {$method eq "getName"} {return $id}}
        corner {if {$method eq "name"} {return $id}}
        sta_net {
            if {$method eq "pin_capacitance"} {
                incr ::queries
                lassign $args corner minmax
                if {$minmax ne "max"} {error "Expected explicit max capacitance"}
                set index [lsearch -exact $::corners [$corner name]]
                set total 0.0
                foreach p [dict get $::N $id pins] {
                    if {[dict get $::P $p direction] eq "INPUT"} {
                        set total [expr {$total+[lindex [dict get $::P $p caps] $index]*1e-12}]
                    }
                }
                return $total
            }
        }
    }
    error "Unsupported mock operation: $kind $id $method $args"
}
proc ord::get_db {} {return [handle db 0]}
proc sta::find_net {name} {return [handle sta_net $name]}
proc sta::corners {} {return [lmap c $::corners {handle corner $c}]}
proc sta::capacitance_ui_sta {value} {return [expr {$value*1e-12}]}
proc sta::capacitance_sta_ui {value} {return [expr {$value*1e12}]}
proc set_cmd_units {args} {
    if {$args ne {-capacitance pF}} {error "Unexpected unit setting"}
    incr ::unit_changes
}
proc insert_buffer {args} {
    array set opt $args
    set original [dict get $::P [lindex $opt(-load_pins) 0] net]
    set name $opt(-buffer_name)actual
    set branch $opt(-net_name)actual
    dict set ::I $name [dict create master $opt(-buffer_cell) location {0 0}]
    dict set ::N $branch [dict create type SIGNAL pins {}]
    foreach pin $opt(-load_pins) {
        if {[dict get $::P $pin net] ne $original} {error "Selected pins span nets"}
        set old [dict get $::N $original pins]
        dict set ::N $original pins [lsearch -all -inline -not -exact $old $pin]
        dict set ::P $pin net $branch
        set new [dict get $::N $branch pins]; lappend new $pin
        dict set ::N $branch pins $new
    }
    addpin $name A INPUT $original $::new_caps
    addpin $name X OUTPUT $branch {0 0 0}
    incr ::insertions
}
dict set ::N clk [dict create type CLOCK pins {}]
dict set ::I driver [dict create master source location {0 0}]
addpin driver X OUTPUT clk {0 0 0}
for {set i 0} {$i<$::load_count} {incr i} {
    dict set ::I sink$i [dict create master sink location [list [expr {$i*1000}] 0]]
    addpin sink$i A INPUT clk $::sink_caps
}
'''


def run_tcl(tmp_path, *, loads=8, caps=(.004, .008, .005), new_caps=(.004, .004, .004),
            target="0.06", group=4, cell="sky130_fd_sc_hd__clkbuf_8", extra="", after=""):
    executable = None
    for candidate in ("/opt/homebrew/opt/tcl-tk/bin/tclsh", "/usr/local/opt/tcl-tk/bin/tclsh", shutil.which("tclsh")):
        if candidate and Path(candidate).is_file():
            probe = subprocess.run([candidate], input="if {[info commands lmap] eq {}} {exit 1}\n", text=True, capture_output=True)
            if probe.returncode == 0:
                executable = candidate
                break
    if executable is None:
        pytest.skip("Tcl 8.6+ interpreter (lmap) unavailable; native reproduction remains required")
    source = Path(__file__).resolve().parents[1] / "nanochip/laboratory/physical/clock_repair.tcl"
    script = tmp_path / "check.tcl"
    initial = (f"set ::load_count {loads}\nset ::sink_caps {{{' '.join(map(str, caps))}}}\n"
               f"set ::new_caps {{{' '.join(map(str, new_caps))}}}\n")
    args = f"10 {group} {cell}" + (f" {{{target}}}" if target is not None else "")
    script.write_text(initial + MOCK + f"\nsource {{{source}}}\n" + extra + f'''
if {{[catch {{set added [nanochip_repair_clock_fanout {args}]
{after}
}} error]}} {{puts stderr $error; exit 1}}
puts "MOCK_RESULT=$::insertions,$::queries,$::unit_changes,[nanochip_clock_max_fanout]"
''')
    return subprocess.run([executable, str(script)], text=True, capture_output=True, timeout=5)


def test_cap_only_trigger_checks_every_corner_and_branches_below_original_fanout_limit(tmp_path):
    result = run_tcl(tmp_path)
    assert result.returncode == 0, result.stderr
    assert "NANOCHIP_CLOCK_TARGET_COUNT=1" in result.stdout
    assert "NANOCHIP_CLOCK_BUFFER_COUNT=2" in result.stdout
    assert "NANOCHIP_CLOCK_FANOUT_LIMIT=10" in result.stdout
    assert "ss 0.064" in result.stdout
    assert "NANOCHIP_CLOCK_MAX_SINK_COUNT=4" in result.stdout


def test_disabled_option_preserves_legacy_fanout_only_behavior_and_does_not_query_sta(tmp_path):
    result = run_tcl(tmp_path, target=None)
    assert result.returncode == 0, result.stderr
    assert "MOCK_RESULT=0,0,0,8" in result.stdout
    result = run_tcl(tmp_path, loads=11, target=None)
    assert result.returncode == 0, result.stderr
    assert "MOCK_RESULT=3,0,0,4" in result.stdout


def test_enabled_target_preserves_fanout_only_trigger_and_multilevel_progress(tmp_path):
    result = run_tcl(tmp_path, loads=11, caps=(.001, .001, .001))
    assert result.returncode == 0, result.stderr
    assert "NANOCHIP_CLOCK_BUFFER_COUNT=3" in result.stdout
    assert "NANOCHIP_CLOCK_PIN_CAP_TARGET=" not in result.stdout
    result = run_tcl(tmp_path, loads=21, caps=(.004, .004, .004))
    assert result.returncode == 0, result.stderr
    assert "NANOCHIP_CLOCK_BUFFER_COUNT=8" in result.stdout
    assert "NANOCHIP_CLOCK_MAX_SINK_COUNT=4" in result.stdout


def test_final_network_recheck_catches_later_load_change_and_checks_new_children(tmp_path):
    result = run_tcl(tmp_path, after="nanochip_check_all_clock_pin_caps 0.06")
    assert result.returncode == 0, result.stderr
    assert "NANOCHIP_CLOCK_PIN_CAP_FINAL_CHECKED=3" in result.stdout
    result = run_tcl(tmp_path, after="dict set ::P sink0/A caps {.1 .1 .1}\nnanochip_check_all_clock_pin_caps 0.06")
    assert result.returncode != 0
    assert "Unsupported CLOCK pin-cap target (final)" in result.stderr
    assert "sink0/A" in result.stderr


def test_selector_ignores_signal_loads_and_rejects_competing_clock_drivers(tmp_path):
    extra = """
dict set ::N data [dict create type SIGNAL pins {}]
dict set ::I data_source [dict create master source location {0 0}]
dict set ::I data_sink [dict create master sink location {0 0}]
addpin data_source X OUTPUT data {0 0 0}
addpin data_sink A INPUT data {1 1 1}
"""
    result = run_tcl(tmp_path, caps=(.001, .001, .001), extra=extra)
    assert result.returncode == 0, result.stderr
    assert "NANOCHIP_CLOCK_TARGET_COUNT=0" in result.stdout
    result = run_tcl(tmp_path, extra="dict set ::I second [dict create master source location {0 0}]\naddpin second X OUTPUT clk {0 0 0}")
    assert result.returncode != 0 and "one internal output" in result.stderr


@pytest.mark.parametrize("target", ["0", "-0.1", "Inf", "-Inf", "NaN", "not-a-number", "1e-1000"])
def test_bad_tcl_cap_targets_fail_before_mutation(tmp_path, target):
    result = run_tcl(tmp_path, target=target)
    assert result.returncode != 0
    assert "capacitance" in result.stderr


@pytest.mark.parametrize("kwargs,phase", [
    ({"caps": (.02, .02, .02)}, "child"),
    ({"new_caps": (.04, .04, .04)}, "root"),
    ({"loads": 4, "caps": (.02, .02, .02)}, "<=group"),
])
def test_unmet_child_root_and_unsplittable_targets_fail_explicitly(tmp_path, kwargs, phase):
    result = run_tcl(tmp_path, **kwargs)
    assert result.returncode != 0
    assert f"Unsupported CLOCK pin-cap target ({phase}" in result.stderr
    assert "corners_pf=" in result.stderr and "inputs=" in result.stderr


def test_missing_corner_and_arbitrary_branch_cell_reject(tmp_path):
    result = run_tcl(tmp_path, extra="set ::corners {}\n")
    assert result.returncode != 0 and "requires loaded timing corners" in result.stderr
    result = run_tcl(tmp_path, cell="sky130_fd_sc_hd__inv_8")
    assert result.returncode != 0 and "verified noninverting" in result.stderr


@pytest.mark.parametrize("value", [None, Decimal(".06"), .06, 1])
def test_valid_optional_config_preserves_default_or_positive_pf(value):
    validate_clock_repair_config({"NANOCHIP_CLOCK_WORKING_PIN_CAPACITANCE": value})


@pytest.mark.parametrize("value", [True, False, "0.06", 0, -.1, float("inf"), float("nan"),
                                    Decimal("Infinity"), Decimal("sNaN"), 10**1000])
def test_invalid_optional_config_rejects(value):
    with pytest.raises(ValueError, match="positive finite"):
        validate_clock_repair_config({"NANOCHIP_CLOCK_WORKING_PIN_CAPACITANCE": value})


def test_config_restricts_branch_master_to_verified_clock_family():
    with pytest.raises(ValueError, match="verified noninverting"):
        validate_clock_repair_config({"NANOCHIP_CLOCK_BRANCH_CELL": "sky130_fd_sc_hd__inv_8"})
