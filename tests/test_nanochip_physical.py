"""Evidence boundary tests; fixture reports are never physical measurements."""

from dataclasses import replace
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from nanochip.laboratory.adapters import DequantMaterializer, starter_task
from nanochip.laboratory.contracts import Action, ContractError, file_sha256
from nanochip.laboratory.physical import IMAGE, OpenRoadBackend, run_physical
from nanochip.laboratory.physical.flow import collect_checks


class PhysicalEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def state(self, name, metrics):
        p = self.root / 'runs' / 'physical' / name / 'state_out.json'
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps({'metrics': metrics}))

    def checks(self):
        return {c['name']: c['status'] for c in collect_checks(self.root)[0]}

    def test_pre_route_zero_slack_does_not_prove_routed_timing(self):
        self.state('23-openroad-globalplacement', {'timing__setup_vio__count': 0, 'timing__hold_vio__count': 0})
        self.assertEqual(self.checks()['routed_timing'], 'unresolved')

    def test_pre_route_antenna_check_cannot_hide_postroute_violations(self):
        self.state('35-openroad-checkantennas', {'route__antenna_violation__count': 0})
        self.state('39-openroad-detailedrouting', {'route__drc_errors': 0})
        self.assertEqual(self.checks()['postroute_antenna'], 'unresolved')
        self.state('41-openroad-checkantennas-1', {'route__antenna_violation__count': 11})
        self.assertEqual(self.checks()['postroute_antenna'], 'fail')

    def test_clean_setup_hold_does_not_hide_electrical_violations(self):
        self.state('54-openroad-stapostpnr', {'timing__setup_vio__count': 0, 'timing__hold_vio__count': 0,
                   'design__max_slew_violation__count': 22, 'design__max_cap_violation__count': 1,
                   'design__max_fanout_violation__count': 0})
        self.assertEqual(self.checks()['electrical_constraints'], 'fail')

    def test_route_zero_drc_does_not_prove_layout_decks(self):
        self.state('40-openroad-detailedrouting', {'route__drc_errors': 0})
        checks = self.checks()
        self.assertEqual(checks['detailed_route_drc'], 'pass')
        self.assertEqual(checks['physical_drc'], 'unresolved')
        self.assertEqual(checks['physical_lvs'], 'unresolved')

    def test_layout_violation_and_missing_metric_are_not_success(self):
        self.state('62-magic-drc', {'magic__drc_error__count': 3})
        self.state('63-klayout-drc', {})
        self.assertEqual(self.checks()['physical_drc'], 'fail')
        self.assertEqual(self.checks()['klayout_drc'], 'unresolved')

    def test_nonfinite_or_boolean_metric_cannot_pass(self):
        for bad in (float('nan'), False, '0', -1):
            with self.subTest(bad=bad):
                p = self.root / 'runs/physical/62-magic-drc/state_out.json'
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(json.dumps({'metrics': {'magic__drc_error__count': bad}}))
                self.assertEqual(self.checks()['magic_drc'], 'unresolved')

    def test_unconstrained_coverage_is_required_for_timing_pass(self):
        self.state('54-openroad-stapostpnr', {'timing__setup_vio__count': 0, 'timing__hold_vio__count': 0})
        self.assertEqual(self.checks()['routed_timing'], 'unresolved')

    def coverage_fixture(self, *, native_unconstrained=None):
        metrics = {'timing__setup_vio__count': 0, 'timing__hold_vio__count': 0}
        if native_unconstrained is not None:
            metrics['timing__unconstrained__count'] = native_unconstrained
        self.state('54-openroad-stapostpnr', metrics)
        stage = self.root / 'runs/physical/54-openroad-stapostpnr'
        (stage / 'config.json').write_text(json.dumps({'STA_CORNERS': ['slow', 'fast']}))
        (self.root / 'coverage.tcl').write_text('fixture script')
        (self.root / 'netlist.v').write_text('fixture netlist')
        corners = []
        for name in ('slow', 'fast'):
            (self.root / (name + '.log')).write_text('fixture check return')
            (self.root / (name + '.tcl')).write_text('fixture environment')
            corners.append(dict(corner=name, status='pass', log=name+'.log',
                                log_sha256=file_sha256(self.root / (name + '.log')),
                                environment=name+'.tcl', environment_sha256=file_sha256(self.root / (name + '.tcl'))))
        receipt = dict(status='pass', image=IMAGE, expected_corners=['slow','fast'], corners=corners,
                       postroute_state_sha256=file_sha256(stage / 'state_out.json'),
                       script_sha256=file_sha256(self.root / 'coverage.tcl'),
                       input_artifacts=[dict(path='netlist.v', sha256=file_sha256(self.root / 'netlist.v'))])
        (self.root / 'coverage-receipt.json').write_text(json.dumps(receipt))
        return receipt

    def test_explicit_bound_coverage_can_resolve_timing(self):
        for native_unconstrained in (None, 0):
            with self.subTest(native_unconstrained=native_unconstrained):
                self.coverage_fixture(native_unconstrained=native_unconstrained)
                self.assertEqual(self.checks()['routed_timing'], 'pass')
                (self.root / 'slow.log').write_text('changed')
                self.assertEqual(self.checks()['routed_timing'], 'unresolved')

    def test_omitted_corner_does_not_resolve_timing(self):
        receipt = self.coverage_fixture(native_unconstrained=0)
        receipt['corners'] = receipt['corners'][:1]
        receipt['expected_corners'] = ['slow']
        (self.root / 'coverage-receipt.json').write_text(json.dumps(receipt))
        self.assertEqual(self.checks()['routed_timing'], 'unresolved')

    def test_native_zero_cannot_replace_missing_explicit_coverage(self):
        self.state('54-openroad-stapostpnr', {'timing__setup_vio__count': 0,
                   'timing__hold_vio__count': 0, 'timing__unconstrained__count': 0})
        self.assertEqual(self.checks()['routed_timing'], 'unresolved')

    def test_native_zero_cannot_override_failed_explicit_coverage(self):
        receipt = self.coverage_fixture(native_unconstrained=0)
        receipt['status'] = 'fail'
        receipt['corners'][0]['status'] = 'fail'
        (self.root / 'coverage-receipt.json').write_text(json.dumps(receipt))
        self.assertEqual(self.checks()['routed_timing'], 'unresolved')

    def test_unavailable_engine_retains_input_and_receipt(self):
        rtl = self.root / 'source.v'
        rtl.write_text('module msh_deq; endmodule\n')
        with patch('nanochip.laboratory.physical.flow.shutil.which', return_value=None):
            result = run_physical(rtl, self.root / 'out')
        self.assertEqual(result['status'], 'unavailable')
        self.assertFalse(result['ok'])
        self.assertTrue((self.root / 'out/receipt.json').is_file())
        self.assertEqual((self.root / 'out/msh_deq.v').read_bytes(), rtl.read_bytes())
        with self.assertRaises(FileExistsError):
            run_physical(rtl, self.root / 'out')

    def test_generated_gds_does_not_imply_drc_or_lvs(self):
        p = self.root / 'runs/physical/56-magic-streamout/msh_deq.gds'
        p.parent.mkdir(parents=True)
        p.write_bytes(b'fixture-nonempty-bytes')
        checks = self.checks()
        self.assertEqual(checks['gds_generated'], 'pass')
        self.assertEqual(checks['physical_drc'], 'unresolved')
        self.assertEqual(checks['physical_lvs'], 'unresolved')

    def test_infinite_noncheck_metrics_do_not_break_receipt_serialization(self):
        self.state('40-openroad-detailedrouting', {'route__drc_errors': 0, 'timing__setup__ws': float('inf')})
        checks, stages = collect_checks(self.root)
        json.dumps(stages, allow_nan=False)
        self.assertEqual(stages['openroad-detailedrouting']['metrics']['timing__setup__ws'], 'Infinity')

    def test_truncated_partial_stage_is_retained_without_promoting_success(self):
        p = self.root / 'runs/physical/54-openroad-stapostpnr/state_out.json'
        p.parent.mkdir(parents=True)
        p.write_text('{"metrics":')
        self.assertEqual(self.checks()['routed_timing'], 'unresolved')
        self.assertEqual(p.read_text(), '{"metrics":')

    def test_backend_rejects_task_change_before_tool_invocation(self):
        task = starter_task()
        work = self.root / 'candidate-work'
        work.mkdir()
        candidate = DequantMaterializer().materialize(task, Action('reference'), work)
        with self.assertRaisesRegex(ContractError, 'different task'):
            OpenRoadBackend().evaluate(replace(task, specification={}), candidate)


if __name__ == '__main__':
    unittest.main()
