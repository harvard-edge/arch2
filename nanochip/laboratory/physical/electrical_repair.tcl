# Owned bounded routed-repair helpers. Final extracted checks remain mandatory.
# Pinned EST global recomputation replaces every RC annotation but does not
# clear its invalid-net bookkeeping. Placement recomputes all nets and clears
# that set. Immediately replace its annotations with full retained-route RC;
# no decisions or reports may consume the transient placement estimate.
proc nanochip_refresh_global_rc {} {
    estimate_parasitics -placement
    estimate_parasitics -global_routing
}

proc nanochip_checkpoint {tag} {
    set clean 1
    write_db $::nanochip_dir/$tag.odb
    write_def $::nanochip_dir/$tag.def
    write_guides $::nanochip_dir/$tag.guides
    foreach corner [sta::corners] {
        set name [$corner name]
        sta::set_cmd_corner $corner
        report_net -digits 9 $::env(CLOCK_PORT) > $::nanochip_dir/$tag.$name.clock-cap.rpt
        puts "NANOCHIP_STATUS=$tag $name"
        puts "NANOCHIP_SETUP_WS=[worst_slack -corner $name -max]"
        puts "NANOCHIP_HOLD_WS=[worst_slack -corner $name -min]"
        puts "NANOCHIP_FANOUT_COUNT=[sta::max_fanout_violation_count]"
        puts "NANOCHIP_SLEW_COUNT=[llength [sta::check_slew_limits NULL 1 $corner max]]"
        puts "NANOCHIP_CAP_COUNT=[llength [sta::check_capacitance_limits NULL 1 $corner max]]"
        puts "%OL_CREATE_REPORT $tag.$name.electrical.rpt"
        sta::report_slew_limits NULL $corner max 1 0 1
        sta::report_capacitance_limits NULL $corner max 1 0 1
        sta::report_fanout_limits NULL max 1 0 1
        puts "%OL_END_REPORT"
        set row [list $tag $name [worst_slack -corner $name -max] [worst_slack -corner $name -min] [sta::max_fanout_violation_count] [llength [sta::check_slew_limits NULL 1 $corner max]] [llength [sta::check_capacitance_limits NULL 1 $corner max]]]
        set stream [open $::nanochip_dir/checks.tsv a]
        puts $stream [join $row "\t"]
        close $stream
        if {[lindex $row 2] < 0 || [lindex $row 3] < 0 || [lindex $row 4] || [lindex $row 5] || [lindex $row 6]} {set clean 0}
    }
    return $clean
}

proc nanochip_resolve_electrical_net {path} {
    set term [$::block findITerm $path]
    if {$term eq "NULL"} {
        set term [$::block findBTerm $path]
        if {$term eq "NULL" || [$term getIoType] ne "OUTPUT" || [$term getSigType] ne "SIGNAL"} {
            error "Electrical port must be an internally driven SIGNAL output: $path"
        }
    }
    set net [$term getNet]
    if {$net eq "NULL"} {error "Electrical endpoint is unconnected: $path"}
    foreach port [$net getBTerms] {
        if {[$port getIoType] ne "OUTPUT"} {error "Electrical net has an external or bidirectional driver: $path"}
    }
    return $net
}

proc nanochip_unique_signal_driver {pin} {
    set path [get_full_name $pin]
    set term [$::block findITerm $path]
    if {$term eq "NULL"} {set term [$::block findBTerm $path]}
    if {$term eq "NULL" || [$term getNet] eq "NULL"} {error "Unknown/unconnected electrical endpoint"}
    set net [$term getNet]
    if {[$net getSigType] eq "CLOCK"} {return [list]}
    set net [nanochip_resolve_electrical_net $path]
    if {[$net getSigType] ne "SIGNAL" || [$net isDoNotTouch]} {error "Unsupported/protected slew net"}
    set drivers [list]
    foreach term [$net getITerms] {
        set direction [[$term getMTerm] getIoType]
        if {$direction eq "INOUT"} {error "Bidirectional slew endpoint"}
        if {$direction eq "OUTPUT"} {lappend drivers $term}
    }
    if {[llength $drivers]!=1} {error "Slew violation lacks unique internal driver"}
    set driver [lindex $drivers 0];set inst [$driver getInst]
    if {[$inst isDoNotTouch]} {error "Protected slew driver"}
    return [list [$inst getName] [[$inst getMaster] getName] [$net getName] [[$driver getMTerm] getName]]
}
proc nanochip_resize_fresh_drivers {} {
set cap [dict create];set slew [dict create]
foreach corner [sta::corners] {
    foreach pin [sta::check_capacitance_limits NULL 1 $corner max] {
        set row [nanochip_unique_signal_driver $pin]
        if {[llength $row]} {dict set cap [lindex $row 0] $row}
    }
    foreach pin [sta::check_slew_limits NULL 1 $corner max] {
        set row [nanochip_unique_signal_driver $pin]
        if {[llength $row]} {dict set slew [lindex $row 0] $row}
    }
}
set cap_record [open $::nanochip_dir/$::nanochip_phase.cap-targets-excluded.tsv w]
puts $cap_record "instance\tmaster\tnet\toutput_pin"
foreach name [lsort [dict keys $cap]] {puts $cap_record [join [dict get $cap $name] "\t"]}
close $cap_record
set planned [dict create];set unsupported 0;set cap_skipped [dict size $cap]
set record [open $::nanochip_dir/$::nanochip_phase.preflight.tsv w]
puts $record "instance\tmaster_before\tmaster_proposed\tnet\toutput_pin\tclassification"
foreach name [lsort [dict keys $slew]] {
    lassign [dict get $slew $name] instance master net pin
    set new "";set status unsupported_working_slew
    if {[dict exists $cap $name]} {set status cap_net_excluded} elseif {[dict exists $::nanochip_stronger_cells $master]} {
        set new [dict get $::nanochip_stronger_cells $master]
        set status supported_slew_only
        dict set planned $name [list $master $new $net $pin]
    } else {incr unsupported}
    puts $record "$name\t$master\t$new\t$net\t$pin\t$status"
}
close $record
puts "NANOCHIP_SUPPORTED_SLEW_PREFLIGHT=[dict size $planned]"
puts "NANOCHIP_UNSUPPORTED_WORKING_SLEW=$unsupported"
puts "NANOCHIP_CAP_NETS_EXCLUDED=$cap_skipped"
if {[dict size $planned]>5000} {error "Over-bound supported batch"}
# Complete preflight is retained before the first equivalent replacement.
set record [open $::nanochip_dir/$::nanochip_phase.resizes.tsv w]
puts $record "instance\tbefore\tafter\treturn"
foreach name [lsort [dict keys $planned]] {
    lassign [dict get $planned $name] old new net_name pin
    set inst [$::block findInst $name];set term [$::block findITerm "$name/$pin"]
    if {$inst eq "NULL" || [[$inst getMaster] getName] ne $old || [$inst isDoNotTouch] || $term eq "NULL"} {error "Preflighted instance changed"}
    set net [$term getNet]
    if {$net eq "NULL" || [$net getName] ne $net_name || [$net getSigType] ne "SIGNAL" || [$net isDoNotTouch]} {error "Preflighted slew net changed"}
    set result [replace_cell $name $new]
    if {$result!=1 || [[$inst getMaster] getName] ne $new} {error "Verified batch replacement failed"}
    puts $record "$name\t$old\t$new\t$result";flush $record
}
close $record

}


# Bounded noninverting electrical fanout repair. All endpoint decisions use
# actual ODB SIGNAL connectivity; diode loads count exactly like other loads.
proc nanochip_repair_signal_fanout {limit group_size buffer_cell} {
    set block [[[ord::get_db] getChip] getBlock]
    set dbu [$block getDbUnitsPerMicron]
    if {$limit != 10 || $group_size != 8 || $buffer_cell ne "sky130_fd_sc_hd__buf_4"} {
        error "Unexpected bounded signal-branch prototype parameters"
    }
    set targets [list]
    foreach net [$block getNets] {
        if {[$net getSigType] ne "SIGNAL"} {continue}
        set loads [list];set drivers [list]
        foreach pin [$net getITerms] {
            if {[$pin getSigType] in {POWER GROUND}} {continue}
            set direction [[$pin getMTerm] getIoType]
            if {$direction eq "INPUT"} {lappend loads $pin}
            if {$direction eq "OUTPUT"} {lappend drivers $pin}
            if {$direction eq "INOUT"} {error "Unsupported bidirectional signal fanout endpoint"}
        }
        if {[llength $loads] <= $limit} {continue}
        if {[llength $drivers] != 1 || [llength [$net getBTerms]]} {
            error "Signal branch needs exactly one internal driver and no top ports: [$net getName]"
        }
        set driver [lindex $drivers 0]
        lappend targets "[[$driver getInst] getName]/[[$driver getMTerm] getName]"
    }
    set index 0
    set record [open $::nanochip_dir/$::nanochip_phase.branches.tsv w]
    puts $record "driver\tinput_net\toutput_net\tbuffer\tmaster\tselected_load_pins\tselected_locations_dbu\tinput_loads_after"
    foreach driver_name [lsort $targets] {
        set driver [$block findITerm $driver_name]
        set depth 0
        while {1} {
            set net [$driver getNet]
            if {[$net getSigType] ne "SIGNAL"} {error "Signal branch crossed a clock or supply net"}
            set loads [list]
            foreach pin [$net getITerms] {
                if {[$pin getSigType] in {POWER GROUND} || [[$pin getMTerm] getIoType] ne "INPUT"} {continue}
                lassign [$pin getAvgXY] ok x y
                if {!$ok} {lassign [[$pin getInst] getLocation] x y}
                lappend loads [list $x $y "[[$pin getInst] getName]/[[$pin getMTerm] getName]"]
            }
            if {[llength $loads] <= $limit} {break}
            if {[incr depth] > 16} {error "Signal tree depth bound exceeded"}
            set loads [lsort -integer -index 0 [lsort -integer -index 1 $loads]]
            # Preserve protective diodes when a small functional-only split
            # can reserve two root slots, as measured in the final ECO probe.
            set functional [list]
            foreach row $loads {
                set pin [$block findITerm [lindex $row 2]]
                if {[[[$pin getInst] getMaster] getName] ne "sky130_fd_sc_hd__diode_2"} {lappend functional $row}
            }
            set move [expr {[llength $loads]-8+1}]
            set groups [list]
            if {$move <= $group_size && [llength $functional] >= $move} {
                set best [list];set best_span Inf
                for {set n 0} {$n <= [llength $functional]-$move} {incr n} {
                    set candidate [lrange $functional $n [expr {$n+$move-1}]]
                    set xs [list];set ys [list]
                    foreach row $candidate {lappend xs [lindex $row 0];lappend ys [lindex $row 1]}
                    set xs [lsort -integer $xs];set ys [lsort -integer $ys]
                    set span [expr {[lindex $xs end]-[lindex $xs 0]+[lindex $ys end]-[lindex $ys 0]}]
                    if {$span < $best_span} {set best $candidate;set best_span $span}
                }
                lappend groups $best
            } else {
                for {set n 0} {$n < [llength $loads]} {incr n $group_size} {
                    lappend groups [lrange $loads $n [expr {$n+$group_size-1}]]
                }
            }
            foreach group $groups {
                set pins [list];set x 0;set y 0
                foreach row $group {
                    lassign $row px py pin
                    lappend pins $pin
                    set x [expr {$x+$px}];set y [expr {$y+$py}]
                }
                set x [expr {double($x)/[llength $group]/$dbu}]
                set y [expr {double($y)/[llength $group]/$dbu}]
                set name nanochip_signal_branch_${::nanochip_phase}_${index}_
                set branch nanochip_signal_branch_net_${::nanochip_phase}_${index}_
                if {[$block findInst $name] ne "NULL" || [$block findNet $branch] ne "NULL"} {
                    error "Signal branch output name collision"
                }
                insert_buffer -buffer_cell $buffer_cell -load_pins $pins -location [list $x $y] \
                    -buffer_name $name -net_name $branch
                set actual_net [[$block findITerm [lindex $pins 0]] getNet]
                if {$actual_net eq "NULL" || $actual_net eq $net} {error "Signal buffer did not split its input net"}
                set outputs [list]
                foreach pin [$actual_net getITerms] {
                    if {[[$pin getMTerm] getIoType] eq "OUTPUT"} {lappend outputs $pin}
                }
                if {[llength $outputs] != 1} {error "Signal branch has no unique output"}
                set inst [[lindex $outputs 0] getInst]
                if {[[$inst getMaster] getName] ne $buffer_cell} {error "Unexpected noninverting buffer master"}
                set inputs 0
                foreach pin [$inst getITerms] {
                    if {[[$pin getMTerm] getIoType] ne "INPUT"} {continue}
                    incr inputs
                    if {[$pin getNet] ne $net} {error "Signal buffer input is disconnected from its original driver"}
                }
                if {$inputs != 1} {error "Signal buffer has an unexpected logical interface"}
                foreach pin_name $pins {
                    if {[[$block findITerm $pin_name] getNet] ne $actual_net} {error "Signal branch lost an original sink"}
                }
                $actual_net setSigType SIGNAL
                set remaining 0
                foreach pin [$net getITerms] {
                    if {[$pin getSigType] ni {POWER GROUND} && [[$pin getMTerm] getIoType] eq "INPUT"} {incr remaining}
                }
                puts $record "$driver_name\t[$net getName]\t[$actual_net getName]\t[$inst getName]\t$buffer_cell\t$pins\t$group\t$remaining"
                incr index
                if {$index > 10000} {error "Signal insertion bound exceeded"}
            }
        }
    }
    close $record
    puts "NANOCHIP_SIGNAL_BRANCH_TARGETS=[llength $targets]"
    puts "NANOCHIP_SIGNAL_BRANCH_BUFFERS=$index"
}

proc nanochip_connect_power {} {
    source $::env(SCRIPTS_DIR)/openroad/common/set_power_nets.tcl
    if {[llength $::env(VDD_NETS)] != 1 || [llength $::env(GND_NETS)] != 1} {error "Routed repair requires one explicit power domain"}
    set_global_connections
    set names [list]
    foreach inst [$::block getInsts] {lappend names [$inst getName]}
    nanochip_check_clock_power $names $::env(VDD_NET) $::env(GND_NET)
}

proc nanochip_legalize_incrementally {} {
    global_route -start_incremental
    nanochip_connect_power
    set prior $::env(PL_OPTIMIZE_MIRRORING)
    set ::env(PL_OPTIMIZE_MIRRORING) 0
    source $::env(SCRIPTS_DIR)/openroad/common/dpl.tcl
    set ::env(PL_OPTIMIZE_MIRRORING) $prior
    global_route -end_incremental -congestion_iterations $::env(GRT_OVERFLOW_ITERS) -verbose
    nanochip_refresh_global_rc
}

proc nanochip_electrical_phase {phase} {
    set ::nanochip_phase $phase
    nanochip_checkpoint $phase.before
    # Native insert_buffer owns its own EST/GRT guard. External sizing and
    # legalization have separate routing observers, with full RC replacement.
    global_route -start_incremental
    nanochip_resize_fresh_drivers
    global_route -end_incremental -congestion_iterations $::env(GRT_OVERFLOW_ITERS) -verbose
    nanochip_refresh_global_rc
    nanochip_repair_signal_fanout 10 8 sky130_fd_sc_hd__buf_4
    nanochip_legalize_incrementally
    return [nanochip_checkpoint $phase.after]
}


proc nanochip_repair_signal_cap_nets {max_wire_um} {
# Exact pinned internal DEBUG primitive. No public repair_net API is claimed.
if {[llength [info commands rsz::repair_net_cmd]] != 1} {error "Pinned per-net primitive unavailable"}
set_cmd_units -distance um
set max_length [sta::distance_ui_sta $max_wire_um]
# Native unit scale uses float storage; require exact user-unit roundtrip
# and a conservative relative numeric tolerance well below one database unit.
if {abs([sta::distance_sta_ui $max_length]-$max_wire_um)>1e-6 || abs($max_length-$max_wire_um*1e-6)>$max_wire_um*1e-6*1e-7} {error "Distance SI conversion differs"}
puts "NANOCHIP_TARGET_LENGTH_METERS=$max_length"
est::check_parasitics
report_dont_touch
set targets [dict create]
foreach corner [sta::corners] {
    foreach pin [sta::check_capacitance_limits NULL 1 $corner max] {
        set path [get_full_name $pin]
        set term [$::block findITerm $path]
        if {$term eq "NULL"} {error "Cap target is not an internal endpoint: $path"}
        set net [$term getNet]
        if {$net eq "NULL"} {error "Unconnected cap endpoint"}
        if {[$net getSigType] eq "CLOCK"} {continue}
        if {[$net getSigType] ne "SIGNAL" || [llength [$net getBTerms]]} {error "Unsupported cap net kind/boundary"}
        set drivers [list]
        foreach iterm [$net getITerms] {
            set type [[$iterm getMTerm] getIoType]
            if {$type eq "INOUT"} {error "Bidirectional cap net"}
            if {$type eq "OUTPUT"} {lappend drivers $iterm}
        }
        if {[llength $drivers] != 1} {error "Cap net needs unique internal driver"}
        set driver [lindex $drivers 0];set inst [$driver getInst]
        if {[$inst isDoNotTouch] || [$net isDoNotTouch]} {error "Protected cap target"}
        set master [[$inst getMaster] getName]
        # This isolated diagnostic supports only stateless ordinary logic families.
        if {![regexp {^sky130_fd_sc_hd__(buf|clkbuf|inv|nand2)_[0-9]+$} $master]} {error "Unsupported cap driver family $master"}
        set sta_net [sta::find_net [$net getName]]
        if {$sta_net eq "NULL"} {error "No STA Net object"}
        set driver_path "[$inst getName]/[[$driver getMTerm] getName]"
        set sta_pin [list [sta::find_pin $driver_path]]
        if {[llength $sta_pin] != 1 || [lindex $sta_pin 0] eq "NULL"} {error "No unique STA driver pin"}
        set logic [sta::pin_sim_logic_value [lindex $sta_pin 0]]
        if {$logic ne "X"} {error "Constant or unsupported computed driver value: $driver_path=$logic"}
        dict set targets [$net getName] [list [$inst getName] $master [[$driver getMTerm] getName] $logic]
    }
}
if {[dict size $targets] > 100} {error "Over-bound cap target set"}
# All target connectivity/protection/family checks finish before first mutation.
set record [open $::nanochip_dir/$::nanochip_phase.targets.tsv w]
puts $record "net\tdriver\tmaster_before\toutput_pin\tmax_length_meters\tcomputed_logic"
foreach name [lsort [dict keys $targets]] {
    lassign [dict get $targets $name] instance master pin logic
    set net [$::block findNet $name]
    if {$net eq "NULL" || [$net getSigType] ne "SIGNAL" || [$net isDoNotTouch] || [llength [$net getBTerms]]} {error "Preflighted net changed"}
    set driver [$::block findITerm "$instance/$pin"]
    if {$driver eq "NULL" || [$driver getNet] ne $net || [[$driver getInst] isDoNotTouch]} {error "Preflighted driver changed"}
    if {[[[$driver getInst] getMaster] getName] ne $master} {error "Preflighted master changed"}
    set driver_count 0
    foreach endpoint [$net getITerms] {
        set type [[$endpoint getMTerm] getIoType]
        if {$type eq "INOUT"} {error "Preflighted net gained bidirectional endpoint"}
        if {$type eq "OUTPUT"} {incr driver_count}
    }
    if {$driver_count != 1} {error "Preflighted net driver count changed"}
    set sta_pin [list [sta::find_pin "$instance/$pin"]]
    if {[llength $sta_pin] != 1 || [lindex $sta_pin 0] eq "NULL" || [sta::pin_sim_logic_value [lindex $sta_pin 0]] ne "X"} {error "Computed driver value changed"}
    set sta_net [sta::find_net $name]
    if {$sta_net eq "NULL"} {error "Preflighted STA net disappeared"}
    puts $record "$name\t$instance\t$master\t$pin\t$max_length\t$logic";flush $record
    # sta::find_net returns the exact sta::Net pointer consumed by this SWIG command.
    # Each call owns/completes its native EST + incremental-GRT guard.
    rsz::repair_net_cmd $sta_net $max_length 0.0 0.0
}
close $record
puts "NANOCHIP_TARGETED_CAP_NET_COUNT=[dict size $targets]"

}

proc nanochip_record_repair_phase {phase kind} {
    set stream [open $::nanochip_dir/phases.tsv a]
    puts $stream "$phase\t$kind\t$phase.before\t$phase.after"
    close $stream
}

proc nanochip_working_cap_phase {} {
    set ::nanochip_phase cap
    nanochip_checkpoint cap.before
    nanochip_repair_signal_cap_nets $::env(NANOCHIP_SIGNAL_RESIDUAL_MAX_WIRE_LENGTH)
    nanochip_legalize_incrementally
    nanochip_checkpoint cap.after
    nanochip_record_repair_phase cap cap
}

proc nanochip_working_slew_phase {} {
    set ::nanochip_phase slew
    nanochip_checkpoint slew.before
    global_route -start_incremental
    nanochip_resize_fresh_drivers
    global_route -end_incremental -congestion_iterations $::env(GRT_OVERFLOW_ITERS) -verbose
    nanochip_refresh_global_rc
    nanochip_legalize_incrementally
    nanochip_checkpoint slew.after
    nanochip_record_repair_phase slew slew
}
