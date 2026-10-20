"""Guard the composed routed-repair evidence, including negative controls."""
import json
from decimal import Decimal
import fnmatch
from pathlib import Path
import re
import tempfile
import unittest

from nanochip.laboratory.physical.repair_flow import (audit_repair_phases, merge_cell_lefs,
    repair_libraries, validate_repair_config, working_repair_settings,
    configure_working_environment, WORKING_KEYS)

BUF = 'sky130_fd_sc_hd__buf_4'
CORNERS = ['nom_tt_025C_1v80', 'nom_ss_100C_1v60', 'nom_ff_n40C_1v95']


def design(branch=False):
    components = [('u', BUF), ('s', BUF)] + ([('b', BUF)] if branch else [])
    nets = [('n0', [('PIN', 'in'), ('u', 'A')]),
            ('n1', [('u', 'X'), ('b' if branch else 's', 'A')]),
            ('n2', [('s', 'X'), ('PIN', 'out')])]
    if branch: nets.append(('n3', [('b', 'X'), ('s', 'A')]))
    return ('COMPONENTS ' + str(len(components)) + ' ;\n' +
            '\n'.join(f'- {n} {m} + PLACED ( 0 0 ) N ;' for n, m in components) +
            '\nEND COMPONENTS\nPINS 2 ;\n- in + NET n0 + DIRECTION INPUT + USE SIGNAL ;\n- out + NET n2 + DIRECTION OUTPUT + USE SIGNAL ;\nEND PINS\nNETS ' + str(len(nets)) + ' ;\n' +
            '\n'.join('- ' + n + ' ' + ' '.join(f'( {i} {p} )' for i, p in pins) + ' + USE SIGNAL ;' for n, pins in nets) + '\nEND NETS\n')


def fixture(root):
    lib = f'library(test) {{ cell({BUF}) {{ pg_pin(VPWR) {{ pg_type: primary_power; }} pin(A) {{ direction: input; }} pin(X) {{ direction: output; function: "A"; }} }} }}'
    lef = f'MACRO {BUF}\n PIN A\n DIRECTION INPUT ;\n USE SIGNAL ;\n END A\n PIN X\n DIRECTION OUTPUT ;\n USE SIGNAL ;\n END X\n PIN VPWR\n DIRECTION INOUT ;\n USE POWER ;\n END VPWR\nEND {BUF}\n'
    diode = 'sky130_fd_sc_hd__diode_2'
    pins = [('VPWR', 'POWER', 'primary_power'), ('VGND', 'GROUND', 'primary_ground'),
            ('VPB', 'POWER', 'nwell'), ('VNB', 'GROUND', 'pwell')]
    diode_lib = f'cell({diode}) {{' + ''.join(f'pg_pin({n}) {{ pg_type: {t}; }}' for n, _, t in pins) + 'pin(DIODE) { direction: input; } }'
    lib = lib.removesuffix('}') + diode_lib + '}'
    lef += f'MACRO {diode}\n CLASS CORE ANTENNACELL ;\n' + ''.join(f' PIN {n}\n DIRECTION INOUT ;\n USE {u} ;\n END {n}\n' for n, u, _ in pins) + f' PIN DIODE\n DIRECTION INPUT ;\n USE SIGNAL ;\n END DIODE\nEND {diode}\n'
    (root / 'cells.lef').write_text(lef)
    libraries = []
    for corner in CORNERS:
        p = root / (corner + '.lib');p.write_text(lib);libraries.append(p)
    for tag in ['native.before', 'native.after', 'electrical0.before']:
        (root / (tag + '.def')).write_text(design())
    for tag in ['electrical0.after', 'antenna0.before', 'antenna0.after', 'core']:
        (root / (tag + '.def')).write_text(design(True))
    (root / 'phases.tsv').write_text('phase\tkind\tbefore\tafter\nnative\tnative\tnative.before\tnative.after\nelectrical0\telectrical\telectrical0.before\telectrical0.after\nantenna0\tantenna\tantenna0.before\tantenna0.after\n')
    (root / 'electrical0.resizes.tsv').write_text('instance\tbefore\tafter\treturn\n')
    (root / 'electrical0.preflight.tsv').write_text('instance\tmaster_before\tmaster_proposed\tnet\toutput_pin\tclassification\n')
    (root / 'checks.tsv').write_text(''.join(f'antenna0.after\t{c}\t20\t.1\t0\t0\t0\n' for c in CORNERS))
    for c in CORNERS: (root / ('antenna0.after.' + c + '.clock-cap.rpt')).write_text('Total capacitance: 0.005-0.006\n')
    (root / 'antenna0.strict-antenna.rpt').write_text('')
    (root / 'verified-drive-choices.json').write_text('{}')
    return {'CELL_LEFS': [root / 'cells.lef'], 'DESIGN_NAME': 'core', 'STA_CORNERS': CORNERS,
            'MAX_CAPACITANCE_CONSTRAINT': .2}, libraries


class RepairFlowTests(unittest.TestCase):
    def test_optional_targets_are_atomic_finite_and_stricter(self):
        config = dict(zip(WORKING_KEYS, ['.25', '.06', '50']))
        config.update(MAX_TRANSITION_CONSTRAINT='.75', MAX_CAPACITANCE_CONSTRAINT='.2',
                      GRT_DESIGN_REPAIR_MAX_WIRE_LENGTH=100)
        self.assertEqual(str(working_repair_settings(config)[WORKING_KEYS[2]]), '50')
        for key in WORKING_KEYS:
            for value in (None, 0, -1, True, 'NaN', 'Infinity'):
                with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                    working_repair_settings({**config, key: value})
        for key, value in zip(WORKING_KEYS, ['.75', '.2', 100]):
            with self.subTest(key=key), self.assertRaises(ValueError):
                working_repair_settings({**config, key: value})
        ambient = {**dict.fromkeys(WORKING_KEYS, 'invalid ambient target'), 'NANOCHIP_PHYSICAL_CORES': '2'}
        self.assertEqual(configure_working_environment({}, ambient), {'NANOCHIP_PHYSICAL_CORES': '2'})
        self.assertEqual(Decimal(configure_working_environment(config, ambient)[WORKING_KEYS[0]]), Decimal('.25'))

    def test_enabled_policy_requires_exact_declared_fresh_prefix(self):
        for mutation in ('none', 'failed_initial', 'omit_cap', 'swap', 'gap', 'disabled', 'wrong_units', 'missing_original', 'invalid_initial', 'failed_optimized', 'failed_final'):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp);config, libraries = fixture(root)
                config.update(dict(zip(WORKING_KEYS, ['.25', '.06', '50'])))
                config.update(MAX_TRANSITION_CONSTRAINT='.75', GRT_DESIGN_REPAIR_MAX_WIRE_LENGTH=100)
                for phase in ('cap', 'slew'):
                    for side in ('before', 'after'): (root / f'{phase}.{side}.def').write_text(design())
                (root / 'slew.resizes.tsv').write_text('instance\tbefore\tafter\treturn\n')
                (root / 'slew.preflight.tsv').write_text('instance\tmaster_before\tmaster_proposed\tnet\toutput_pin\tclassification\n')
                (root / 'cap.targets.tsv').write_text('net\tdriver\tmaster_before\toutput_pin\tmax_length_meters\tcomputed_logic\n')
                for tag in ('original.initial', 'original.optimized', 'original.final'):
                    (root / (tag + '.def')).write_text(design(True) if tag == 'original.final' else design())
                    with (root / 'checks.tsv').open('a') as stream:
                        stream.write(''.join(f'{tag}\t{corner}\t20\t.1\t0\t0\t0\n' for corner in CORNERS))
                text = (root / 'phases.tsv').read_text().replace('electrical0\telectrical',
                    'cap\tcap\tcap.before\tcap.after\nslew\tslew\tslew.before\tslew.after\nelectrical0\telectrical', 1)
                if mutation == 'omit_cap': text = text.replace('cap\tcap\tcap.before\tcap.after\n', '')
                if mutation == 'swap': text = text.replace('cap\tcap\tcap.before\tcap.after\nslew\tslew\tslew.before\tslew.after', 'slew\tslew\tslew.before\tslew.after\ncap\tcap\tcap.before\tcap.after')
                if mutation == 'gap': (root / 'slew.before.def').write_text(design(True))
                if mutation == 'disabled':
                    for key in WORKING_KEYS: config.pop(key)
                if mutation == 'wrong_units':
                    (root / 'cap.targets.tsv').write_text('net\tdriver\tmaster_before\toutput_pin\tmax_length_meters\tcomputed_logic\nn1\tu\t' + BUF + '\tX\t50\tX\n')
                if mutation == 'missing_original':
                    (root / 'checks.tsv').write_text('\n'.join(line for line in (root / 'checks.tsv').read_text().splitlines() if not line.startswith('original.initial\t')) + '\n')
                if mutation in ('failed_initial', 'invalid_initial'):
                    text_checks = (root / 'checks.tsv').read_text()
                    text_checks = text_checks.replace('original.initial\t' + CORNERS[0] + '\t20\t.1\t0\t0\t0',
                        'original.initial\t' + CORNERS[0] + ('\t-2\t-.1\t3\t4\t5' if mutation == 'failed_initial' else '\tNaN\t.1\t0\t0\t0'))
                    (root / 'checks.tsv').write_text(text_checks)
                if mutation in ('failed_optimized', 'failed_final'):
                    tag = 'original.optimized' if mutation == 'failed_optimized' else 'original.final'
                    (root / 'checks.tsv').write_text((root / 'checks.tsv').read_text().replace(tag + '\t' + CORNERS[0] + '\t20\t.1\t0\t0\t0', tag + '\t' + CORNERS[0] + '\t20\t-.1\t0\t0\t0'))
                (root / 'phases.tsv').write_text(text)
                if mutation in ('none', 'failed_initial'): self.assertEqual(len(audit_repair_phases(root, config, libraries)['phase_receipts']), 5)
                else:
                    with self.assertRaises(ValueError): audit_repair_phases(root, config, libraries)

    def test_all_configured_lefs_are_consumed_and_hash_bound(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp);config, libraries = fixture(root)
            first = root / 'cells.lef'
            text = first.read_text()
            boundary = text.index('MACRO sky130_fd_sc_hd__diode_2')
            first.write_text(text[:boundary])
            second = root / 'antenna.lef';second.write_text(text[boundary:])
            config['CELL_LEFS'].append(second)
            result = audit_repair_phases(root, config, libraries)
            self.assertEqual([r['path'] for r in result['configured_lefs']], [str(first), str(second)])
            self.assertEqual(len(result['configured_lefs']), 2)
            # The diode schema is in the second view; omitting it must fail.
            config['CELL_LEFS'].pop()
            (root / 'configured-cells.merged.lef').unlink()
            with self.assertRaises(ValueError): audit_repair_phases(root, config, libraries)

    def test_conflicting_repeated_or_redirected_lefs_reject(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp);config, _ = fixture(root)
            first = config['CELL_LEFS'][0]
            duplicate = root / 'duplicate.lef';duplicate.write_bytes(first.read_bytes())
            link = root / 'link.lef';link.symlink_to(first)
            for paths in ([], [first, first], [first, duplicate], [link], [root]):
                with self.subTest(paths=paths), self.assertRaises(ValueError):
                    merge_cell_lefs(paths, root / 'merged.lef')
            original = first.read_bytes()
            for output in (first, duplicate, link):
                with self.subTest(output=output), self.assertRaises(ValueError):
                    merge_cell_lefs([first], output)
            self.assertEqual(first.read_bytes(), original)
            dangling = root / 'dangling.lef';dangling.symlink_to(root / 'absent.lef')
            with self.assertRaises(ValueError): merge_cell_lefs([first], dangling)

    def test_native_candidate_policy_matches_verified_new_buffer_families(self):
        script = (Path(__file__).parents[1] / 'nanochip/laboratory/physical/antenna_electrical_step.tcl').read_text()
        patterns = re.search(r'foreach pattern \{([^}]+)\}', script).group(1).split()
        # These ordinary candidates appear in the retained pinned findBuffers
        # report. In particular, removing buf_2 can change bufbuf_8 pruning.
        reported = ['bufbuf_16', 'buf_12', 'buf_8', 'bufbuf_8', 'buf_6', 'buf_4', 'buf_2', 'buf_1']
        candidates = reported + ['clkdlybuf4s25_1', 'dlygate4sd3_1', 'dlymetal6s2s_1', 'clkbuf_1', 'clkbuf_2', 'clkbuf_4', 'clkbuf_8', 'clkbuf_16']
        remaining = [name for name in candidates if not any(fnmatch.fnmatchcase('sky130_fd_sc_hd__' + name, pattern) for pattern in patterns)]
        self.assertEqual(set(remaining), {'buf_4', 'buf_6', 'buf_8', 'buf_12', 'clkbuf_4', 'clkbuf_8', 'clkbuf_16'})
        self.assertTrue(all(re.fullmatch(r'(?:buf|clkbuf)_(?:4|6|8|12|16)', name) for name in remaining))
        self.assertLess(script.index('read_current_odb'), script.index('foreach pattern'))
        self.assertLess(script.index('foreach pattern'), script.index('repair_design -verbose'))

    def test_unimplemented_protection_cannot_be_silently_ignored(self):
        validate_repair_config({'RSZ_DONT_TOUCH_RX': '$^', 'RSZ_DONT_TOUCH_LIST': None})
        validate_repair_config({'RSZ_DONT_TOUCH_RX': None, 'RSZ_DONT_TOUCH_LIST': []})
        for config in ({'RSZ_DONT_TOUCH_RX': '^keep_'},
                       {'RSZ_DONT_TOUCH_RX': '$^', 'RSZ_DONT_TOUCH_LIST': ['u/A']},
                       {'RSZ_DONT_TOUCH_LIST': 'u/A'}):
            with self.subTest(config=config), self.assertRaisesRegex(ValueError, 'protection'):
                validate_repair_config(config)

    def test_phase_proofs_compose_with_bound_reports(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp);config, libraries = fixture(root)
            result = audit_repair_phases(root, config, libraries)
            self.assertEqual(result['status'], 'pass')
            self.assertFalse(result['eligible'])
            self.assertFalse(result['direct_oldest_to_final_comparator_passed'])
            self.assertEqual(len(result['phase_receipts']), 3)
            self.assertEqual(result['clock_cap'][0]['margin_pf'], '0.194')

    def test_phase_gap_stale_final_and_failed_measurement_rejected(self):
        changes = {
            'preflight_skip_mutation': ('electrical0.preflight.tsv', 'instance\tmaster_before\tmaster_proposed\tnet\toutput_pin\tclassification\nu\t' + BUF + '\t' + BUF + '\tn1\tX\tunsupported_working_slew\n'),
            'preflight_duplicate': ('electrical0.preflight.tsv', 'instance\tmaster_before\tmaster_proposed\tnet\toutput_pin\tclassification\n' + ('u\t' + BUF + '\t\tn1\tX\tunsupported_working_slew\n') * 2),
            'gap': ('antenna0.before.def', design()),
            'final': ('core.def', design()),
            'fanout': ('checks.tsv', ''.join(f'antenna0.after\t{c}\t20\t.1\t1\t0\t0\n' for c in CORNERS)),
            'hold': ('checks.tsv', ''.join(f'antenna0.after\t{c}\t20\t-.1\t0\t0\t0\n' for c in CORNERS)),
            'cap': ('antenna0.after.' + CORNERS[0] + '.clock-cap.rpt', 'Total capacitance: 0.3\n'),
            'phase': ('phases.tsv', 'phase\tkind\tbefore\tafter\nnative\tnative\tnative.before\tnative.after\nantenna0\tantenna\tantenna0.before\tantenna0.after\n'),
            'missing_corner': ('checks.tsv', f'antenna0.after\t{CORNERS[0]}\t20\t.1\t0\t0\t0\n'),
        }
        for label, (name, value) in changes.items():
            with self.subTest(label=label), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp);config, libraries = fixture(root);(root / name).write_text(value)
                with self.assertRaises(ValueError): audit_repair_phases(root, config, libraries)

    def test_matched_libraries_require_all_three_actual_pvts(self):
        config = {'STA_CORNERS': CORNERS + ['min_tt_025C_1v80'], 'LIB': {'*_tt*': ['tt.lib'], '*_ss*': ['ss.lib'], '*_ff*': ['ff.lib']}}
        self.assertEqual(repair_libraries(config), ['tt.lib', 'ss.lib', 'ff.lib'])
        config['LIB']['*_ss*'] = ['ss.lib', 'macro.lib']
        with self.assertRaises(ValueError): repair_libraries(config)


if __name__ == '__main__': unittest.main()
