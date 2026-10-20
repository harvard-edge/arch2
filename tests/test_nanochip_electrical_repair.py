"""Execute the production output-port resolver with mutable Tcl endpoints."""
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


SCRIPT = Path(__file__).parents[1] / "nanochip/laboratory/physical/electrical_repair.tcl"
MOCK = r'''
set ::block block
set ::direction OUTPUT
set ::sigtype SIGNAL
set ::drivers 1
set ::inout 0
set ::connected 1
set ::master OLD
set ::replacements 0
set ::nanochip_phase test
set ::nanochip_stronger_cells [dict create OLD NEW]
proc get_full_name {pin} {return $pin}
proc block {op path} {
 if {$op eq "findInst" && $path eq "u"} {return inst}
 if {$op eq "findITerm"} {if {$path eq "u/X"} {return driver};return NULL}
 if {$path eq "out"} {return port}
 return NULL
}
proc port {op} {
 switch $op {
  getIoType {return $::direction}
  getSigType {return $::sigtype}
  getNet {if {$::connected} {return net};return NULL}
 }
 error "Unexpected port API"
}
proc net {op} {
 switch $op {
  getName {return n}
  isDoNotTouch {return 0}
  getBTerms {return [list port]}
  getSigType {return $::sigtype}
  getITerms {
   set result [list]
   for {set i 0} {$i<$::drivers} {incr i} {lappend result driver}
   if {$::inout} {lappend result bidir}
   return $result
  }
 }
 error "Unexpected net API"
}
proc driver {op} {if {$op eq "getMTerm"} {return output_mterm};if {$op eq "getInst"} {return inst};if {$op eq "getNet"} {return net};error "Unexpected driver API"}
proc bidir {op} {return inout_mterm}
proc output_mterm {op} {if {$op eq "getName"} {return X};return OUTPUT}
proc inout_mterm {op} {return INOUT}
proc inst {op} {if {$op eq "isDoNotTouch"} {return 0};if {$op eq "getName"} {return u};if {$op eq "getMaster"} {return master};error "Unexpected instance API"}
proc master {op} {return $::master}
proc replace_cell {name cell} {incr ::replacements;set ::master $cell;return 1}
namespace eval sta {
 proc corners {} {return [list corner]}
 proc check_slew_limits {args} {return [list out]}
 proc check_capacitance_limits {args} {return [list]}
}
'''


@unittest.skipUnless(shutil.which("tclsh"), "Tcl interpreter required")
class ElectricalOutputTests(unittest.TestCase):
    def run_case(self, setup, *, accepted):
        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp) / "case.tcl"
            script.write_text('source {' + str(SCRIPT) + '}\n' + MOCK +
                              '\nset ::nanochip_dir {' + tmp + '}\n' + setup + r'''
set code [catch {nanochip_resize_fresh_drivers} message]
puts "RESULT=$code,$::replacements,$::master"
puts $message
''')
            result = subprocess.run(["tclsh", str(script)], capture_output=True, text=True, timeout=5)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("RESULT=0,1,NEW" if accepted else "RESULT=1,0,OLD", result.stdout)

    def test_output_port_resolves_its_internal_driver(self):
        self.run_case("", accepted=True)

    def test_external_or_invalid_ports_cannot_be_resized(self):
        for setup in ("set ::direction INPUT", "set ::direction INOUT", "set ::sigtype POWER",
                      "set ::connected 0", "set ::drivers 0", "set ::drivers 2", "set ::inout 1"):
            with self.subTest(setup=setup):
                self.run_case(setup, accepted=False)


if __name__ == "__main__":
    unittest.main()
