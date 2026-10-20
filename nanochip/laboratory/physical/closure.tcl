# Bounded exploratory repair helpers for the pinned SKY130 HD flow.
# Caller loads the immutable routed input; all writes go to a new run directory.
# These transformations never change an STA constraint or grant acceptance.
proc nanochip_split_clock_branches {driver_pins group_size} {
    if {$group_size < 2 || $group_size > 8} {error "Use clock branch groups of 2..8 loads"}
    set db [ord::get_db]
    set block [[$db getChip] getBlock]
    set dbu [[$db getTech] getDbUnitsPerMicron]
    set index 0
    foreach name $driver_pins {
        set driver [$block findITerm $name]
        if {$driver eq "NULL" || [[$driver getMTerm] getIoType] ne "OUTPUT"} {
            error "Missing clock driver output $name"
        }
        set net [$driver getNet]
        set loads [list]
        foreach pin [$net getITerms] {
            if {[[$pin getMTerm] getIoType] eq "INPUT"} {lappend loads $pin}
        }
        if {[llength $loads] <= $group_size} {continue}
        # A common extra buffer level preserves the phase of the clock.
        # Final extracted skew, hold, fanout, capacitance and slew must be checked.
        for {set n 0} {$n < [llength $loads]} {incr n $group_size} {
            set group [lrange $loads $n [expr {$n+$group_size-1}]]
            set pins [list]; set x 0; set y 0
            foreach pin $group {
                lappend pins "[[$pin getInst] getName]/[[$pin getMTerm] getName]"
                lassign [[$pin getInst] getLocation] px py
                set x [expr {$x+$px}]; set y [expr {$y+$py}]
            }
            set x [expr {double($x)/[llength $group]/$dbu}]
            set y [expr {double($y)/[llength $group]/$dbu}]
            insert_buffer -buffer_cell sky130_fd_sc_hd__clkbuf_4 -load_pins $pins \
                -location [list $x $y] -buffer_name nanochip_branch_$index \
                -net_name nanochip_clock_$index
            incr index
        }
    }
    puts "NANOCHIP_CLOCK_BRANCH_BUFFERS=$index"
}

proc nanochip_place_sink_diodes {sink_pins} {
    set db [ord::get_db]
    set block [[$db getChip] getBlock]
    set master [$db findMaster sky130_fd_sc_hd__diode_2]
    if {$master eq "NULL"} {error "Pinned SKY130 antenna diode master is missing"}
    set index 0
    foreach name $sink_pins {
        set pin [$block findITerm $name]
        if {$pin eq "NULL" || [[$pin getMTerm] getIoType] ne "INPUT"} {
            error "Missing antenna sink input $name"
        }
        set inst [odb::dbInst_create $block $master nanochip_diode_$index]
        lassign [[$pin getInst] getLocation] x y
        $inst setLocation [expr {$x-[$master getWidth]}] $y
        $inst setPlacementStatus PLACED
        [$inst findITerm DIODE] connect [$pin getNet]
        incr index
    }
    puts "NANOCHIP_SINK_DIODES=$index"
}
