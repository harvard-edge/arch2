fconfigure stdout -buffering line
set_thread_count 1
source $::env(SCRIPTS_DIR)/openroad/common/io.tcl
source $::env(SCRIPTS_DIR)/openroad/common/resizer.tcl
load_rsz_corners
read_current_odb
source [file join [file dirname [info script]] clock_repair.tcl]
set ::nanochip_clock_signal_dump_prefix [file join [file dirname $::env(SAVE_ODB)] clock-signals]
set initial_instances [dict create]
foreach inst [$::block getInsts] {dict set initial_instances [$inst getName] 1}
set initial_signals [nanochip_signal_connectivity]
if {$::env(NANOCHIP_CLOCK_BUFFER_INPUTS)} {
    # Measured SS slew closure; input capacitance remains explicitly checked.
    nanochip_buffer_clock_inputs sky130_fd_sc_hd__clkbuf_8
}

set working_pin_cap {}
if {[info exists ::env(NANOCHIP_CLOCK_WORKING_PIN_CAPACITANCE)]} {
    set working_pin_cap $::env(NANOCHIP_CLOCK_WORKING_PIN_CAPACITANCE)
}
set branch_cell sky130_fd_sc_hd__clkbuf_4
if {[info exists ::env(NANOCHIP_CLOCK_BRANCH_CELL)]} {set branch_cell $::env(NANOCHIP_CLOCK_BRANCH_CELL)}
if {[catch {set added [nanochip_repair_clock_fanout $::env(MAX_FANOUT_CONSTRAINT) \
    $::env(NANOCHIP_CLOCK_BRANCH_SIZE) $branch_cell $working_pin_cap]} message options]} {
    puts stderr [dict get $options -errorinfo]
    error $message
}

# The optional repair uses all timing models loaded by load_rsz_corners. The
# measured setup margin is broad; hold/electrical repair remains necessary.
set_propagated_clock [all_clocks]
source $::env(SCRIPTS_DIR)/openroad/common/set_rc.tcl
estimate_parasitics -placement
if {$::env(NANOCHIP_POST_CTS_HOLD_REPAIR)} {
    puts "NANOCHIP_ELECTRICAL_REPAIR_BEGIN"
    repair_design -verbose
    estimate_parasitics -placement
    puts "NANOCHIP_HOLD_REPAIR_BEGIN"
    repair_timing -hold -verbose -setup_margin $::env(PL_RESIZER_SETUP_SLACK_MARGIN) \
        -hold_margin $::env(PL_RESIZER_HOLD_SLACK_MARGIN) \
        -max_buffer_percent $::env(PL_RESIZER_HOLD_MAX_BUFFER_PCT)
    puts "NANOCHIP_HOLD_REPAIR_END"
}

# Apply the actual supply mapping to both added clock and data repair buffers.
source $::env(SCRIPTS_DIR)/openroad/common/set_power_nets.tcl
if {[llength $::env(VDD_NETS)] != 1 || [llength $::env(GND_NETS)] != 1} {
    error "Clock repair profile requires one explicit power domain"
}
set_global_connections
source $::env(SCRIPTS_DIR)/openroad/common/dpl.tcl
set all_added [list]
foreach inst [$::block getInsts] {
    if {![dict exists $initial_instances [$inst getName]]} {lappend all_added [$inst getName]}
}
nanochip_check_clock_power $all_added $::env(VDD_NET) $::env(GND_NET)
set maximum [nanochip_clock_max_fanout]
puts "NANOCHIP_FINAL_CLOCK_MAX_SINK_COUNT=$maximum"
if {$maximum > $::env(MAX_FANOUT_CONSTRAINT)} {error "Final custom operation violates the clock sink-count bound"}
set final_signals [nanochip_signal_connectivity]
set stream [open [file join [file dirname $::env(SAVE_ODB)] post-repair-signals.tcl] w]
puts $stream $final_signals
close $stream
puts "NANOCHIP_DATA_REPAIR_CONNECTIVITY_CHANGED=[expr {$initial_signals ne $final_signals}]"
puts "NANOCHIP_ALL_ADDED_INSTANCE_COUNT=[llength $all_added]"
source $::env(SCRIPTS_DIR)/openroad/common/set_rc.tcl
estimate_parasitics -placement
if {$working_pin_cap ne ""} {nanochip_check_all_clock_pin_caps $working_pin_cap}
write_views
