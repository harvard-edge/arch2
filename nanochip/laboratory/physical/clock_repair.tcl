# Connectivity-preserving clock branching. Caller owns legalization, power,
# extracted timing, routing, and all acceptance checks after this operation.
proc nanochip_signal_connectivity {} {
    set block [[[ord::get_db] getChip] getBlock]
    set rows [list]
    foreach net [$block getNets] {
        if {[$net getSigType] ne "SIGNAL"} {continue}
        set pins [list]
        foreach pin [$net getITerms] {
            lappend pins "I:[[$pin getInst] getName]/[[$pin getMTerm] getName]"
        }
        foreach pin [$net getBTerms] {lappend pins "B:[$pin getName]"}
        lappend rows [list [$net getName] [lsort $pins]]
    }
    return [lsort -index 0 $rows]
}

proc nanochip_assert_signal_connectivity {original} {
    if {[nanochip_signal_connectivity] ne $original} {
        error "Clock repair altered a nonclock signal connection"
    }
    puts "NANOCHIP_DATA_CONNECTIVITY_CHECK=pass"
}

proc nanochip_clock_max_fanout {} {
    set block [[[ord::get_db] getChip] getBlock]
    set maximum 0
    foreach net [$block getNets] {
        if {[$net getSigType] ne "CLOCK"} {continue}
        set count 0
        foreach pin [$net getITerms] {
            if {[[$pin getMTerm] getIoType] eq "INPUT"} {incr count}
        }
        if {$count > $maximum} {set maximum $count}
    }
    return $maximum
}

proc nanochip_buffer_clock_inputs {buffer_cell} {
    set db [ord::get_db]
    set block [[$db getChip] getBlock]
    set dbu [[$db getTech] getDbUnitsPerMicron]
    set original_signals [nanochip_signal_connectivity]
    set ports [list]
    foreach net [$block getNets] {
        if {[$net getSigType] ne "CLOCK"} {continue}
        foreach port [$net getBTerms] {
            if {[$port getIoType] eq "INPUT"} {lappend ports [$port getName]}
        }
    }
    set added [list]; set index 0
    foreach name [lsort $ports] {
        set port [$block findBTerm $name]
        set net [$port getNet]
        set pins [list]
        foreach pin [$net getITerms] {
            if {[[$pin getMTerm] getIoType] eq "OUTPUT"} {error "Clock input has an internal competing driver"}
            if {[[$pin getMTerm] getIoType] ne "INPUT"} {continue}
            lappend pins "[[$pin getInst] getName]/[[$pin getMTerm] getName]"
        }
        if {![llength $pins]} {error "Clock input has no actual CTS loads"}
        set boxes [list]
        foreach bpin [$port getBPins] {
            foreach box [$bpin getBoxes] {lappend boxes $box}
        }
        if {![llength $boxes]} {error "Clock input has no placed BPin geometry"}
        set box [lindex $boxes 0]
        set xmin [$box xMin]; set xmax [$box xMax]
        set ymin [$box yMin]; set ymax [$box yMax]
        foreach box [lrange $boxes 1 end] {
            set xmin [expr {min($xmin,[$box xMin])}]; set xmax [expr {max($xmax,[$box xMax])}]
            set ymin [expr {min($ymin,[$box yMin])}]; set ymax [expr {max($ymax,[$box yMax])}]
        }
        # Put the first buffer beside the actual input metal. Legalization
        # moves it onto the nearest legal row, keeping long RC after buffering.
        set x [expr {double($xmin+$xmax)/2/$dbu}]
        set y [expr {double($ymin+$ymax)/2/$dbu}]
        puts "NANOCHIP_CLOCK_INPUT_TARGET=$name $x $y"
        insert_buffer -buffer_cell $buffer_cell -load_pins $pins -location [list $x $y] \
            -buffer_name nanochip_clock_input_${index}_ -net_name nanochip_clock_input_net_${index}_
        set actual_net [[$block findITerm [lindex $pins 0]] getNet]
        if {$actual_net eq "NULL" || $actual_net eq $net || [$port getNet] ne $net} {
            error "Clock input insertion altered its source connection"
        }
        set drivers [list]
        foreach pin [$actual_net getITerms] {
            if {[[$pin getMTerm] getIoType] eq "OUTPUT"} {lappend drivers $pin}
        }
        if {[llength $drivers] != 1} {error "Clock input branch has no unique driver"}
        set inst [[lindex $drivers 0] getInst]
        if {[[$inst getMaster] getName] ne $buffer_cell} {error "Clock input branch has an unexpected master"}
        set inputs 0
        foreach pin [$inst getITerms] {
            if {[[$pin getMTerm] getIoType] ne "INPUT"} {continue}
            incr inputs
            if {[$pin getNet] ne $net} {error "Clock input buffer lost its primary input source"}
        }
        if {$inputs != 1} {error "Clock input buffer is not a single-input noninverting branch"}
        foreach pin_name $pins {
            if {[[$block findITerm $pin_name] getNet] ne $actual_net} {error "Clock input buffer lost a selected sink"}
        }
        $actual_net setSigType CLOCK
        lappend added [$inst getName]
        incr index
    }
    nanochip_assert_signal_connectivity $original_signals
    puts "NANOCHIP_CLOCK_INPUT_BUFFER_COUNT=[llength $added]"
    return $added
}

proc nanochip_clock_cap_target {value} {
    if {![string is double -strict $value] ||
        [catch {expr {$value > 0.0 && $value < Inf}} valid] || !$valid} {
        error "Clock working pin capacitance must be positive finite pF"
    }
    set native [sta::capacitance_ui_sta $value]
    if {[catch {expr {$native > 0.0 && $native < Inf}} valid] || !$valid} {
        error "Clock working pin capacitance is not representable in native units"
    }
    return $native
}

proc nanochip_clock_pin_capacitance {net} {
    set sn [sta::find_net [$net getName]]
    if {$sn eq "NULL"} {error "CLOCK net missing from STA: [$net getName]"}
    set corners [sta::corners]
    if {![llength $corners]} {error "Clock pin-cap selection requires loaded timing corners"}
    set maximum 0.0; set values [dict create]
    foreach corner $corners {
        set name [$corner name]
        if {[dict exists $values $name]} {error "Duplicate clock pin-cap timing corner: $name"}
        # Exact pinned report_net Pin-capacitance path, with an explicit
        # corner object rather than the aggregate command-corner default.
        set cap [$sn pin_capacitance $corner max]
        if {[catch {expr {$cap >= 0.0 && $cap < Inf}} valid] || !$valid} {
            error "Invalid clock pin capacitance: [$net getName]/$name"
        }
        dict set values $name [sta::capacitance_sta_ui $cap]
        set maximum [expr {max($maximum,$cap)}]
    }
    return [dict create maximum $maximum corners_pf $values]
}

proc nanochip_check_clock_pin_cap {net target phase} {
    set info [nanochip_clock_pin_capacitance $net]
    if {[dict get $info maximum] > $target} {
        set loads [list]
        foreach pin [$net getITerms] {
            if {[[$pin getMTerm] getIoType] eq "INPUT"} {
                lappend loads "[[$pin getInst] getName]/[[$pin getMTerm] getName]"
            }
        }
        error "Unsupported CLOCK pin-cap target ($phase): [$net getName] target_pf=[sta::capacitance_sta_ui $target] corners_pf=[dict get $info corners_pf] inputs=[lsort $loads]"
    }
}

proc nanochip_check_all_clock_pin_caps {working_pin_cap_pf} {
    set_cmd_units -capacitance pF
    set target [nanochip_clock_cap_target $working_pin_cap_pf]
    set block [[[ord::get_db] getChip] getBlock]
    set count 0
    foreach net [$block getNets] {
        if {[$net getSigType] ne "CLOCK"} {continue}
        nanochip_check_clock_pin_cap $net $target final
        incr count
    }
    puts "NANOCHIP_CLOCK_PIN_CAP_FINAL_CHECKED=$count"
}

proc nanochip_repair_clock_fanout {limit group_size buffer_cell {working_pin_cap_pf {}}} {
    if {$limit < 2 || $group_size < 2 || $group_size > 8 || $group_size > $limit} {
        error "Invalid clock fanout/branch bounds"
    }
    if {$buffer_cell ni {sky130_fd_sc_hd__clkbuf_2 sky130_fd_sc_hd__clkbuf_4 sky130_fd_sc_hd__clkbuf_8 sky130_fd_sc_hd__clkbuf_16}} {
        error "Clock branch master is not in the verified noninverting clkbuf family"
    }
    set cap_enabled [expr {$working_pin_cap_pf ne ""}]
    if {$cap_enabled} {
        set_cmd_units -capacitance pF
        set target_cap [nanochip_clock_cap_target $working_pin_cap_pf]
    }
    set db [ord::get_db]
    set block [[$db getChip] getBlock]
    set original_signals [nanochip_signal_connectivity]
    set dbu [[$db getTech] getDbUnitsPerMicron]
    if {[$db findMaster $buffer_cell] eq "NULL"} {error "Clock buffer master missing"}
    set targets [list]
    # CLOCK is actual ODB signal classification populated by CTS. No instance
    # or net name prefix is used to infer clock membership.
    foreach net [$block getNets] {
        if {[$net getSigType] ne "CLOCK"} {continue}
        set drivers [list]; set count 0
        foreach pin [$net getITerms] {
            set direction [[$pin getMTerm] getIoType]
            if {$direction eq "INPUT"} {incr count}
            if {$direction eq "OUTPUT"} {lappend drivers $pin}
        }
        set cap_trigger 0
        if {$cap_enabled} {
            set cap_info [nanochip_clock_pin_capacitance $net]
            set cap_trigger [expr {[dict get $cap_info maximum] > $target_cap}]
        }
        if {$count <= $limit && !$cap_trigger} {continue}
        if {[llength $drivers] != 1 || [llength [$net getBTerms]]} {
            error "Clock branch is not driven by one internal output: [$net getName]"
        }
        set driver [lindex $drivers 0]
        if {$cap_trigger && $count <= $group_size} {
            nanochip_check_clock_pin_cap $net $target_cap "<=group sinks=$count"
        }
        if {$cap_trigger} {
            puts "NANOCHIP_CLOCK_PIN_CAP_TARGET=[$net getName] sinks=$count corners_pf=[dict get $cap_info corners_pf]"
        }
        lappend targets [list "[[$driver getInst] getName]/[[$driver getMTerm] getName]" \
            [expr {$cap_trigger ? $group_size : $limit}]]
    }
    set index 0; set new_instances [list]
    foreach target [lsort -index 0 $targets] {
        lassign $target name working_limit
        set driver [$block findITerm $name]
        set depth 0
        while {1} {
            set net [$driver getNet]
            set loads [list]
            foreach pin [$net getITerms] {
                if {[[$pin getMTerm] getIoType] ne "INPUT"} {continue}
                lassign [[$pin getInst] getLocation] x y
                lappend loads [list $x $y "[[$pin getInst] getName]/[[$pin getMTerm] getName]"]
            }
            if {[llength $loads] <= $working_limit} {break}
            if {[incr depth] > 16} {error "Clock repair depth bound exceeded"}
            set loads [lsort -integer -index 0 [lsort -integer -index 1 $loads]]
            for {set n 0} {$n < [llength $loads]} {incr n $group_size} {
                set pins [list]; set x 0; set y 0
                set group [lrange $loads $n [expr {$n+$group_size-1}]]
                foreach row $group {
                    lassign $row px py pin
                    lappend pins $pin
                    set x [expr {$x+$px}]; set y [expr {$y+$py}]
                }
                set x [expr {double($x)/[llength $group]/$dbu}]
                set y [expr {double($y)/[llength $group]/$dbu}]
                set instance nanochip_clock_branch_${index}_
                set branch nanochip_clock_branch_net_${index}_
                if {[$block findInst $instance] ne "NULL" || [$block findNet $branch] ne "NULL"} {
                    error "Clock repair output name already exists"
                }
                insert_buffer -buffer_cell $buffer_cell -load_pins $pins -location [list $x $y] \
                    -buffer_name $instance -net_name $branch
                # The pinned API treats supplied names as bases and adds its
                # own unique suffix. Recover actual objects from connectivity.
                set actual_net [[$block findITerm [lindex $pins 0]] getNet]
                if {$actual_net eq "NULL" || $actual_net eq $net} {error "Clock buffer insertion did not split its input net"}
                foreach pin_name $pins {
                    if {[[$block findITerm $pin_name] getNet] ne $actual_net} {error "Clock branch lost a selected sink"}
                }
                set actual_drivers [list]
                foreach pin [$actual_net getITerms] {
                    if {[[$pin getMTerm] getIoType] eq "OUTPUT"} {lappend actual_drivers $pin}
                }
                if {[llength $actual_drivers] != 1} {error "Inserted clock branch has no unique driver"}
                set actual_inst [[lindex $actual_drivers 0] getInst]
                if {[[$actual_inst getMaster] getName] ne $buffer_cell} {error "Unexpected clock branch buffer master"}
                set inputs 0
                foreach pin [$actual_inst getITerms] {
                    if {[[$pin getMTerm] getIoType] ne "INPUT"} {continue}
                    incr inputs
                    if {[$pin getNet] ne $net} {error "Inserted clock buffer has an incorrect input"}
                }
                if {$inputs != 1} {error "Added clock buffer is not a single-input noninverting branch"}
                $actual_net setSigType CLOCK
                if {$cap_enabled} {nanochip_check_clock_pin_cap $actual_net $target_cap child}
                lappend new_instances [$actual_inst getName]
                incr index
            }
            set remaining 0
            foreach pin [[$driver getNet] getITerms] {
                if {[[$pin getMTerm] getIoType] eq "INPUT"} {incr remaining}
            }
            if {$remaining >= [llength $loads]} {error "Clock repair did not reduce the root sink count"}
        }
        if {$cap_enabled} {nanochip_check_clock_pin_cap [$driver getNet] $target_cap root}
    }
    puts "NANOCHIP_CLOCK_TARGET_COUNT=[llength $targets]"
    puts "NANOCHIP_CLOCK_BUFFER_COUNT=$index"
    puts "NANOCHIP_CLOCK_FANOUT_LIMIT=$limit"
    puts "NANOCHIP_CLOCK_BRANCH_SIZE=$group_size"
    set maximum [nanochip_clock_max_fanout]
    puts "NANOCHIP_CLOCK_MAX_SINK_COUNT=$maximum"
    if {$maximum > $limit} {error "Clock repair did not satisfy its actual sink-count bound"}
    nanochip_assert_signal_connectivity $original_signals
    if {[info exists ::nanochip_clock_signal_dump_prefix]} {
        foreach {suffix data} [list before $original_signals after [nanochip_signal_connectivity]] {
            set stream [open "$::nanochip_clock_signal_dump_prefix.$suffix.tcl" w]
            puts $stream $data
            close $stream
        }
    }
    return $new_instances
}

proc nanochip_check_clock_power {instances vdd gnd} {
    set block [[[ord::get_db] getChip] getBlock]
    foreach name $instances {
        set inst [$block findInst $name]
        set power_count 0; set ground_count 0
        foreach pin [$inst getITerms] {
            set kind [[$pin getMTerm] getSigType]
            if {$kind ni {POWER GROUND}} {continue}
            if {$kind eq "POWER"} {incr power_count} else {incr ground_count}
            set rail [expr {$kind eq "POWER" ? $vdd : $gnd}]
            if {[$pin getNet] eq "NULL" || [[$pin getNet] getName] ne $rail} {
                error "Added clock buffer has an incorrect supply: $name/[[$pin getMTerm] getName]"
            }
        }
        if {!$power_count || !$ground_count} {error "Added clock buffer has no explicit power/ground terminals: $name"}
    }
    puts "NANOCHIP_CLOCK_POWER_CHECK=pass"
}
