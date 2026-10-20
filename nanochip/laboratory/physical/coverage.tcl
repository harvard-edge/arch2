# Reload retained post-route views and the configured corner's library.
set_cmd_units -time ns -capacitance pF -current mA -voltage V -resistance kOhm -distance um
set corner $::env(NANOCHIP_CORNER)
define_corners $corner
foreach lib $::env(NANOCHIP_LIBS) {read_liberty -corner $corner $lib}
read_verilog $::env(NANOCHIP_NETLIST)
link_design $::env(NANOCHIP_TOP)
read_sdc $::env(NANOCHIP_SDC)
read_spef -corner $corner $::env(NANOCHIP_SPEF)
set clocks [llength [all_clocks]]
set registers [llength [all_registers]]
puts "NANOCHIP_CLOCK_COUNT=$clocks"
puts "NANOCHIP_REGISTER_COUNT=$registers"
set valid [check_setup -verbose -unconstrained_endpoints -no_input_delay -no_output_delay -multiple_clock -no_clock -loops -generated_clocks]
puts "NANOCHIP_CONSTRAINT_COVERAGE=$valid"
if {$valid != 1 || $clocks < 1 || $registers < 1} {exit 1}
exit 0
