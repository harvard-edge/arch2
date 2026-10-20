"""Power-aware pin preservation and rejection gates for digital cell models."""
import hashlib
import json
import re
from pathlib import Path
import shutil
import subprocess
from tempfile import TemporaryDirectory
import unittest

from nanochip.laboratory.physical.cell_models import inspect_liberty, validate_model_audit, write_model_script

PG='''pg_pin(VPWR) { pg_type: primary_power; }
pg_pin(VGND) { pg_type: primary_ground; }
pg_pin(VPB) { pg_type: nwell; }
pg_pin(VNB) { pg_type: pwell; }'''
LIB='''library(test) {
 cell(sky130_fd_sc_hd__dfxtp_1) {
 %s
 ff(IQ, IQ_N) { clocked_on: "CLK"; next_state: "D"; }
 pin(CLK) { direction: input; }
 pin(D) { direction: input; }
 pin(Q) { direction: output; function: "IQ"; }
 }
 cell(sky130_fd_sc_hd__inv_1) {
 %s
 pin(A) { direction: input; }
 pin(Y) { direction: output; function: "!A"; }
 }
 cell(sky130_fd_sc_hd__broken_1) {
 %s
 pin(A) { direction: input; }
 pin(Y) { direction: output; }
 }
}''' % (PG,PG,PG)
GATE='''module dut(input clk, input d, output q, inout VPWR, VGND, VPB, VNB);
 sky130_fd_sc_hd__dfxtp_1 ff(.CLK(clk),.D(d),.Q(q),.VPWR(VPWR),.VGND(VGND),.VPB(VPB),.VNB(VNB));
 sky130_fd_sc_hd__fill_1 fill(.VPWR(VPWR),.VGND(VGND),.VPB(VPB),.VNB(VNB));
endmodule'''

class CellModelContractTests(unittest.TestCase):
    def prepare(self,root,gate=GATE,lib_text=LIB,**kwargs):
        (root/'cells.lib').write_text(lib_text);(root/'gate.v').write_text(gate)
        return write_model_script(root/'cells.lib',root/'gate.v',root/'models',top='dut',physical_only_cells={'sky130_fd_sc_hd__fill_1':[]},**kwargs)

    def test_extracts_actual_pg_and_ff_declarations(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp);p=self.prepare(root);data=inspect_liberty(root/'cells.lib')
            self.assertEqual(set(data['sky130_fd_sc_hd__dfxtp_1']['pg_pins']),{'VPWR','VGND','VPB','VNB'})
            self.assertEqual(data['sky130_fd_sc_hd__dfxtp_1']['sequential'][0]['next_state'],'D')
            script=Path(p['script_path']).read_text()
            self.assertIn('read_liberty -ignore_miss_func ',script)
            self.assertNotIn('read_liberty -lib ',script)
            self.assertIn('add -inout VPWR 1 sky130_fd_sc_hd__dfxtp_1',script)
            self.assertIn('read_verilog -noblackbox -overwrite',script)
            self.assertLess(script.index('write_json '),script.index('opt_clean -purge'))
            self.assertIn('flatten\nopt_clean -purge\ncheck -assert',script)

    def test_rejects_unrecognized_physical_override(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'cells.lib').write_text(LIB);(root/'gate.v').write_text(GATE)
            with self.assertRaisesRegex(ValueError,'Unrecognized'):
                write_model_script(root/'cells.lib',root/'gate.v',root/'models',top='dut',physical_only_cells={'sky130_fd_sc_hd__inv_1':[]})

    @unittest.skipUnless(shutil.which('yosys'),'Yosys required')
    def test_exact_two_pin_lef_tap_keeps_other_four_pin_rails_required(self):
        powered=GATE.replace('inout VPWR, VGND, VPB, VNB','inout VPWR, VGND').replace('.VPB(VPB)','.VPB(VPWR)').replace('.VNB(VNB)','.VNB(VGND)')
        tap='sky130_fd_sc_hd__tapvpwrvgnd_1 tap(.VPWR(VPWR),.VGND(VGND));'
        positive=powered.replace('endmodule',tap+'\nendmodule')
        variants={'positive':positive,
                  'missing_tap':positive.replace(tap,tap.replace('.VPWR(VPWR),','')),
                  'crossed_tap':positive.replace(tap,tap.replace('.VPWR(VPWR)','.VPWR(VGND)')),
                  'unknown_tap':positive.replace(tap,tap.replace('.VPWR(VPWR)','.VPWR(d)')),
                  'extra_tap':positive.replace(tap,tap.replace('));','),.VPB(VPWR));')),
                  'missing_four_rail_body':positive.replace('.VPB(VPWR),','',1)}
        for label,gate in variants.items():
            with self.subTest(label=label),TemporaryDirectory() as tmp:
                root=Path(tmp);(root/'cells.lib').write_text(LIB);(root/'gate.v').write_text(gate)
                plan=write_model_script(root/'cells.lib',root/'gate.v',root/'models',top='dut',physical_only_cells={'sky130_fd_sc_hd__fill_1':[], 'sky130_fd_sc_hd__tapvpwrvgnd_1':[]},power_ports={'VPWR':1,'VGND':0})
                run=subprocess.run(['yosys','-Q','-T','-s',plan['script_path']],capture_output=True,text=True,timeout=20)
                if run.returncode:
                    self.assertNotEqual(label,'positive',run.stdout+run.stderr)
                    continue
                if label!='positive':
                    with self.assertRaises(ValueError):validate_model_audit(plan)
                    continue
                audit=validate_model_audit(plan)
                schema=audit['physical_only_pg_sources']['sky130_fd_sc_hd__tapvpwrvgnd_1']
                self.assertEqual(schema['pin_uses'],{'VGND':'GROUND','VPWR':'POWER'})
                self.assertEqual(schema['sha256'],'3a3ea4e9d0973402702764d897659e52fe3d413eb48c306cd811de40a75264fa')
                self.assertEqual(audit['power_rail_audit']['checked_connections'],{'power':5,'ground':5})
                # Rehashing metadata cannot replace the declared master schema.
                metadata_path=Path(plan['model_metadata_path']);metadata=json.loads(metadata_path.read_text())
                metadata['physical_only_pg_sources']['sky130_fd_sc_hd__tapvpwrvgnd_1']['pin_uses'].pop('VGND')
                metadata_path.write_text(json.dumps(metadata));plan['model_metadata_sha256']=hashlib.sha256(metadata_path.read_bytes()).hexdigest()
                with self.assertRaisesRegex(ValueError,'pinned master declaration'):validate_model_audit(plan)

    @unittest.skipUnless(shutil.which('yosys'),'Yosys required')
    def test_rejects_used_missing_function_and_missing_pg_connection(self):
        for mutation in ('broken','pg'):
            with self.subTest(mutation=mutation),TemporaryDirectory() as tmp:
                root=Path(tmp)
                gate=GATE.replace('sky130_fd_sc_hd__dfxtp_1 ff(.CLK(clk),.D(d),.Q(q)', 'sky130_fd_sc_hd__broken_1 ff(.A(d),.Y(q)') if mutation=='broken' else GATE
                if mutation=='pg': gate=GATE.replace('.VPWR(VPWR),','',1)
                plan=self.prepare(root,gate)
                result=subprocess.run(['yosys','-Q','-T','-s',plan['script_path']],capture_output=True,text=True,timeout=20)
                if mutation=='broken': self.assertNotEqual(result.returncode,0)
                else:
                    # Either hierarchy/check or independent connection audit rejects.
                    if result.returncode==0:
                        with self.assertRaisesRegex(ValueError,'PG port'):validate_model_audit(plan)

    @unittest.skipUnless(shutil.which('yosys'),'Yosys required')
    def test_nominal_supply_wrapper_and_crossed_or_unknown_rails(self):
        powered=GATE.replace('inout VPWR, VGND, VPB, VNB','inout VPWR, VGND').replace('.VPB(VPB)','.VPB(VPWR)').replace('.VNB(VNB)','.VNB(VGND)')
        variants={
            'positive':powered,
            'crossed':powered.replace('.VPB(VPWR)','.VPB(VGND)',1),
            'unknown':powered.replace('.VPWR(VPWR)','.VPWR(d)',1),
            'unconnected':powered.replace('.VPWR(VPWR)','.VPWR()',1),
            'extra_top':powered.replace('inout VPWR, VGND','inout VPWR, VGND, EXTRA'),
            'unknown_type':powered,
            'shorted':powered.replace('endmodule','assign VGND=VPWR; endmodule'),
        }
        for label,gate in variants.items():
            with self.subTest(label=label),TemporaryDirectory() as tmp:
                root=Path(tmp);plan=self.prepare(root,gate,lib_text=LIB.replace('pg_type: primary_power','pg_type: unsupported_power') if label=='unknown_type' else LIB,power_ports={'VPWR':1,'VGND':0})
                run=subprocess.run(['yosys','-Q','-T','-s',plan['script_path']],capture_output=True,text=True,timeout=20)
                if run.returncode:
                    self.assertNotEqual(label,'positive',run.stdout+run.stderr)
                    continue
                normalized_sha=hashlib.sha256(Path(plan['normalized_path']).read_bytes()).hexdigest()
                if label!='positive':
                    with self.assertRaises(ValueError):validate_model_audit(plan)
                    self.assertFalse(Path(plan['simulation_source_path']).exists())
                    continue
                audit=validate_model_audit(plan)
                self.assertEqual(audit['power_rail_audit']['status'],'pass')
                self.assertEqual(audit['power_rail_audit']['unknown_or_crossed_rails'],0)
                self.assertEqual(audit['power_rail_audit']['checked_connections'],{'power':4,'ground':4})
                self.assertNotEqual(plan['simulation_source_path'],plan['normalized_path'])
                self.assertEqual(hashlib.sha256(Path(plan['normalized_path']).read_bytes()).hexdigest(),normalized_sha)
                text=Path(plan['simulation_source_path']).read_text()
                self.assertIn("supply1 __nanochip_nominal_VPWR;",text)
                self.assertIn("supply0 __nanochip_nominal_VGND;",text)
                self.assertIn('module dut__nominal_powered',text)
                self.assertEqual(audit['simulation_source_sha256'],hashlib.sha256(text.encode()).hexdigest())
                if shutil.which('verilator'):
                    bench=root/'tb.v'
                    bench.write_text("""module tb;
reg clk=0,d=0;wire q;dut u(clk,d,q);
initial begin #1;clk=1;#1;if(q!==0)$fatal(1,"d0");
clk=0;d=1;#1;clk=1;#1;if(q!==1)$fatal(1,"d1");
$display("POWER_WRAPPER_PASS");$finish;end
endmodule""")
                    build=subprocess.run(['verilator','--binary','--timing','-Wno-fatal','--top-module','tb','--Mdir',str(root/'obj'),plan['simulation_source_path'],str(bench)],capture_output=True,text=True,timeout=40)
                    self.assertEqual(build.returncode,0,build.stdout+build.stderr)
                    run=subprocess.run([str(root/'obj/Vtb')],capture_output=True,text=True,timeout=10)
                    self.assertEqual(run.returncode,0,run.stdout+run.stderr)
                    self.assertIn('POWER_WRAPPER_PASS',run.stdout)

    @unittest.skipUnless(shutil.which('yosys') and shutil.which('verilator'),'Local Yosys/Verilator required')
    def test_clocked_positive_and_inverted_negative_control(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp);plan=self.prepare(root)
            y=subprocess.run(['yosys','-Q','-T','-s',plan['script_path']],capture_output=True,text=True,timeout=20)
            self.assertEqual(y.returncode,0,y.stdout+y.stderr)
            audit=validate_model_audit(plan)
            self.assertEqual(audit['functional_blackboxes'],0)
            self.assertIn('sky130_fd_sc_hd__dfxtp_1',audit['sequential_models'])
            # The same mapped FF is checked against q<=d and q<=~d. The inverted
            # reference MUST fail; this guards formal/model false positives.
            bench=root/'tb.v'
            bench.write_text('''module tb;
 reg clk=0,d=0; wire q; supply1 VPWR,VPB; supply0 VGND,VNB;
 dut u(clk,d,q,VPWR,VGND,VPB,VNB);
 initial begin
 #1; clk=1; #1; if(q!==d) $fatal(1,"positive d0 failed");
 clk=0; d=1; #1; clk=1; #1; if(q!==d) $fatal(1,"positive d1 failed");
 if(q===~d) $fatal(1,"inverted negative falsely accepted");
 $display("CELL_MODEL_POSITIVE_PASS NEGATIVE_REJECTED"); $finish;
 end
 endmodule''')
            command=['verilator','--binary','--timing','-Wno-fatal','--top-module','tb','--Mdir',str(root/'obj'),plan['normalized_path'],str(bench)]
            build=subprocess.run(command,capture_output=True,text=True,timeout=40)
            self.assertEqual(build.returncode,0,build.stdout+build.stderr)
            run=subprocess.run([str(root/'obj/Vtb')],capture_output=True,text=True,timeout=10)
            self.assertEqual(run.returncode,0,run.stdout+run.stderr)
            self.assertIn('CELL_MODEL_POSITIVE_PASS NEGATIVE_REJECTED',run.stdout)
            normalized=Path(plan['normalized_path'])
            positive_sha=hashlib.sha256(normalized.read_bytes()).hexdigest()
            # Change the actual mapped FF input, then normalize/audit it anew.
            # Internal alias names can legitimately vanish during opt_clean.
            negative_gate=root/'negative-gate.v'
            changed,count=re.subn(r"\.D\(d\)",'.D(~d)',GATE)
            self.assertEqual(count,1);negative_gate.write_text(changed)
            negative_plan=write_model_script(root/'cells.lib',negative_gate,root/'models-negative',top='dut',physical_only_cells={'sky130_fd_sc_hd__fill_1':[]})
            run=subprocess.run(['yosys','-Q','-T','-s',negative_plan['script_path']],capture_output=True,text=True,timeout=20)
            self.assertEqual(run.returncode,0,run.stdout+run.stderr)
            validate_model_audit(negative_plan)
            negative=Path(negative_plan['normalized_path'])
            negative_sha=hashlib.sha256(negative.read_bytes()).hexdigest()
            self.assertNotEqual(positive_sha,negative_sha)
            negative_command=command.copy()
            negative_command[negative_command.index(plan['normalized_path'])]=str(negative)
            negative_command[negative_command.index(str(root/'obj'))]=str(root/'obj-negative')
            build=subprocess.run(negative_command,capture_output=True,text=True,timeout=40)
            self.assertEqual(build.returncode,0,build.stdout+build.stderr)
            self.assertIn(str(negative),(root/'obj-negative/Vtb__verFiles.dat').read_text())
            run=subprocess.run([str(root/'obj-negative/Vtb')],capture_output=True,text=True,timeout=10)
            self.assertNotEqual(run.returncode,0,run.stdout+run.stderr)
            self.assertIn('positive d0 failed',run.stdout+run.stderr)
            self.assertEqual(hashlib.sha256(negative.read_bytes()).hexdigest(),negative_sha)
            # A changed original input cannot reuse prior model-audit acceptance.
            (root/'gate.v').write_text(GATE+'\n//changed\n')
            with self.assertRaisesRegex(ValueError,'input changed'):validate_model_audit(plan)

if __name__=='__main__':unittest.main()
