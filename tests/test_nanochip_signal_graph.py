"""Independent connectivity checks for bounded physical signal repair."""
import json
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest

from nanochip.laboratory.physical.signal_graph import (
    SignalGraphError,
    check_signal_reachability,
)


BUF = "sky130_fd_sc_hd__buf_4"
BUF8 = "sky130_fd_sc_hd__buf_8"
DIODE = "sky130_fd_sc_hd__diode_2"
CLKBUF = "sky130_fd_sc_hd__clkbuf_4"
CLKBUF8 = "sky130_fd_sc_hd__clkbuf_8"


def design(components, nets, *, port_direction="INPUT"):
    component_text = "\n".join(
        f"- {name} {master} + PLACED ( 0 0 ) N ;" for name, master in components
    )
    net_text = "\n".join(
        f"- {name} "
        + " ".join(f"( {inst} {pin} )" for inst, pin in pins)
        + f" + USE {kind} ;"
        for name, kind, pins in nets
    )
    return f"""VERSION 5.8 ;
COMPONENTS {len(components)} ;
{component_text}
END COMPONENTS
PINS 2 ;
- in + NET n0 + DIRECTION {port_direction} + USE SIGNAL ;
- out + NET n2 + DIRECTION OUTPUT + USE SIGNAL ;
END PINS
NETS {len(nets)} ;
{net_text}
END NETS
END DESIGN
"""


BASE_COMPONENTS = [("u", "logic_1"), ("s", "sink_1")]
BASE_NETS = [
    ("n0", "SIGNAL", [("PIN", "in"), ("u", "A")]),
    ("n1", "SIGNAL", [("u", "X"), ("s", "A")]),
    ("n2", "SIGNAL", [("s", "X"), ("PIN", "out")]),
]
BRANCH_NETS = [
    BASE_NETS[0],
    ("n1", "SIGNAL", [("u", "X"), ("b", "A")]),
    BASE_NETS[2],
    ("n3", "SIGNAL", [("b", "X"), ("s", "A")]),
]


def declarations():
    functions = {
        "logic_1": "!A",
        "logic_2": "!A",
        "bad_logic": "A",
        "sink_1": "A",
        BUF: "(A)",
        BUF8: "(A)",
        CLKBUF: "A",
        CLKBUF8: "A",
        "inverter": "!A",
    }
    liberty = "library(test) {\n"
    lef = ""
    for name, function in functions.items():
        liberty += f'cell({name}) {{ pg_pin(VPWR) {{ pg_type: primary_power; }} pin(A) {{ direction: input; }} pin(X) {{ direction: output; function: "{function}"; }} }}\n'
        lef += f"MACRO {name}\n  PIN A\n    DIRECTION INPUT ;\n    USE SIGNAL ;\n  END A\n  PIN X\n    DIRECTION OUTPUT ;\n    USE SIGNAL ;\n  END X\n  PIN VPWR\n    DIRECTION INOUT ;\n    USE POWER ;\n  END VPWR\nEND {name}\n"
    liberty += f"cell({DIODE}) {{\n"
    lef += f"MACRO {DIODE}\n  CLASS CORE ANTENNACELL ;\n"
    for name, use, pg_type in [
        ("VPWR", "POWER", "primary_power"),
        ("VGND", "GROUND", "primary_ground"),
        ("VPB", "POWER", "nwell"),
        ("VNB", "GROUND", "pwell"),
    ]:
        liberty += f"pg_pin({name}) {{ pg_type: {pg_type}; }}\n"
        lef += f"  PIN {name}\n    DIRECTION INOUT ;\n    USE {use} ;\n  END {name}\n"
    liberty += "pin(DIODE) { direction: input; }\n}\n"
    lef += f"  PIN DIODE\n    DIRECTION INPUT ;\n    USE SIGNAL ;\n  END DIODE\nEND {DIODE}\n"
    return liberty + "}\n", lef


class SignalGraphTests(unittest.TestCase):
    def prepare(self, root, after=None, before=None):
        lib, lef = declarations()
        (root / "cells.lib").write_text(lib)
        (root / "cells.lef").write_text(lef)
        (root / "before.def").write_text(before or design(BASE_COMPONENTS, BASE_NETS))
        (root / "after.def").write_text(
            after or design(BASE_COMPONENTS + [("b", BUF)], BRANCH_NETS)
        )

    def check(self, root, **kwargs):
        return check_signal_reachability(
            root / "before.def",
            root / "after.def",
            lef_path=root / "cells.lef",
            liberty_path=root / "cells.lib",
            **kwargs,
        )

    def test_identity_branch_preserves_every_original_load_and_hashes_inputs(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.prepare(root)
            receipt = self.check(root, output=root / "receipt.json")
            self.assertEqual(receipt["original_signal_loads_checked"], 3)
            self.assertEqual(receipt["added_noninverting_buffers"], 1)
            self.assertEqual(receipt["status"], "pass")
            self.assertFalse(receipt["eligible"])
            self.assertEqual(json.loads((root / "receipt.json").read_text()), receipt)
            self.assertIn("SPECIALNETS", " ".join(receipt["limitations"]))
            self.assertEqual(len(receipt["inputs"]["checker"]["sha256"]), 64)

    def test_same_endpoint_set_cannot_hide_changed_original_driver(self):
        changed = [
            ("n0", "SIGNAL", [("PIN", "in"), ("u", "A"), ("s", "A")]),
            ("n1", "SIGNAL", [("u", "X")]),
            BASE_NETS[2],
        ]
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.prepare(root, after=design(BASE_COMPONENTS, changed))
            with self.assertRaisesRegex(SignalGraphError, "reachability changed"):
                self.check(root)

    def test_rejects_lost_sink_extra_driver_and_added_original_pin(self):
        mutations = {
            "lost": design(BASE_COMPONENTS, BASE_NETS).replace("( s A )", ""),
            "extra_driver": design(BASE_COMPONENTS, BASE_NETS)
            .replace("( s A )", "( s A ) ( s X )")
            .replace("( s X ) ( PIN out )", "( PIN out )"),
            "unknown_pin": design(BASE_COMPONENTS, BASE_NETS).replace(
                "( s A )", "( s A ) ( s UNKNOWN )"
            ),
        }
        for label, after in mutations.items():
            with self.subTest(label=label), TemporaryDirectory() as tmp:
                root = Path(tmp)
                self.prepare(root, after=after)
                with self.assertRaises(SignalGraphError):
                    self.check(root)

    def test_added_buffer_cycle_is_rejected(self):
        nets = [
            BASE_NETS[0],
            ("n1", "SIGNAL", [("u", "X")]),
            BASE_NETS[2],
            ("a", "SIGNAL", [("b", "X"), ("c", "A"), ("s", "A")]),
            ("b", "SIGNAL", [("c", "X"), ("b", "A")]),
        ]
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.prepare(
                root, after=design(BASE_COMPONENTS + [("b", BUF), ("c", BUF)], nets)
            )
            with self.assertRaisesRegex(SignalGraphError, "cycle"):
                self.check(root)

    def test_added_inverter_or_unlisted_master_cannot_be_contracted(self):
        for allowed in (False, True):
            with self.subTest(allowed=allowed), TemporaryDirectory() as tmp:
                root = Path(tmp)
                self.prepare(
                    root,
                    after=design(BASE_COMPONENTS + [("b", "inverter")], BRANCH_NETS),
                )
                with self.assertRaisesRegex(
                    SignalGraphError, "identity buffer" if allowed else "Unlisted added"
                ):
                    self.check(
                        root,
                        **({"added_buffer_masters": ("inverter",)} if allowed else {}),
                    )

    def test_exact_original_master_exception_checks_function_and_is_consumed(self):
        for target, allowed, passes in [
            ("logic_2", {}, False),
            ("logic_2", {"u": {"before": "logic_1", "after": "logic_2"}}, True),
            ("bad_logic", {"u": {"before": "logic_1", "after": "bad_logic"}}, False),
        ]:
            with self.subTest(
                target=target, allowed=allowed
            ), TemporaryDirectory() as tmp:
                root = Path(tmp)
                self.prepare(
                    root,
                    after=design(
                        [("u", target), ("s", "sink_1"), ("b", BUF)], BRANCH_NETS
                    ),
                )
                if passes:
                    self.assertEqual(
                        self.check(root, allowed_master_changes=allowed)[
                            "original_master_changes"
                        ],
                        allowed,
                    )
                else:
                    with self.assertRaises(SignalGraphError):
                        self.check(root, allowed_master_changes=allowed)
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.prepare(root)
            with self.assertRaisesRegex(SignalGraphError, "Unused"):
                self.check(
                    root,
                    allowed_master_changes={
                        "u": {"before": "logic_1", "after": "logic_2"}
                    },
                )

    def test_added_override_binds_exact_instance_and_identity_function(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.prepare(
                root, after=design(BASE_COMPONENTS + [("b", BUF8)], BRANCH_NETS)
            )
            with self.assertRaises(SignalGraphError):
                self.check(root)
            self.assertEqual(
                self.check(root, added_buffer_overrides={"b": BUF8})[
                    "added_buffer_overrides"
                ],
                {"b": BUF8},
            )
            with self.assertRaises(SignalGraphError):
                self.check(root, added_buffer_overrides={"c": BUF8})

    def test_clock_endpoints_are_preserved_directly(self):
        components = BASE_COMPONENTS + [("c", BUF), ("d", BUF)]
        before = design(
            components, BASE_NETS + [("clock", "CLOCK", [("c", "X"), ("d", "A")])]
        )
        after = design(
            components, BASE_NETS + [("clock", "CLOCK", [("c", "X"), ("d", "X")])]
        )
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.prepare(root, before=before, after=after)
            with self.assertRaisesRegex(SignalGraphError, "CLOCK connectivity"):
                self.check(root)

    def test_unchanged_clock_with_pg_or_unknown_component_pin_is_rejected(self):
        for pin in ("VPWR", "UNKNOWN"):
            with self.subTest(pin=pin), TemporaryDirectory() as tmp:
                root = Path(tmp)
                text = design(
                    BASE_COMPONENTS, BASE_NETS + [("clock", "CLOCK", [("u", pin)])]
                )
                self.prepare(root, before=text, after=text)
                with self.assertRaisesRegex(
                    SignalGraphError, "PG endpoint|unknown signal pin"
                ):
                    self.check(root)

    def test_pg_ports_are_declarations_only_and_cannot_enter_signal_graph(self):
        def pg_port(text):
            return text.replace("PINS 2 ;", "PINS 3 ;").replace(
                "END PINS",
                "- VPWR + NET VPWR + DIRECTION INOUT + USE POWER ;\nEND PINS",
            )

        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.prepare(
                root,
                before=pg_port(design(BASE_COMPONENTS, BASE_NETS)),
                after=pg_port(design(BASE_COMPONENTS + [("b", BUF)], BRANCH_NETS)),
            )
            self.assertEqual(self.check(root)["status"], "pass")
            bad = (
                (root / "after.def")
                .read_text()
                .replace("( PIN in )", "( PIN in ) ( PIN VPWR )")
            )
            (root / "after.def").write_text(bad)
            with self.assertRaisesRegex(SignalGraphError, "PG port"):
                self.check(root)

    def test_counts_duplicates_port_directions_and_routed_grammar_fail_closed(self):
        good = design(BASE_COMPONENTS, BASE_NETS)
        mutations = [
            good.replace("COMPONENTS 2", "COMPONENTS 3"),
            good.replace("PINS 2", "PINS 1"),
            good.replace("NETS 3", "NETS 4"),
            good.replace("- s sink_1", "- u sink_1"),
            good.replace("- out + NET n2", "- in + NET n2"),
            good.replace("- n2 ", "- n1 "),
            good.replace("DIRECTION INPUT", "DIRECTION INOUT"),
            good.replace("( PIN in )", "( PIN in ) + ROUTED met1 ( 0 0 )", 1),
            good.replace("( s A )", "( s A ) ( s A )"),
        ]
        for index, after in enumerate(mutations):
            with self.subTest(index=index), TemporaryDirectory() as tmp:
                root = Path(tmp)
                self.prepare(root, after=after)
                with self.assertRaises(SignalGraphError):
                    self.check(root)

    def test_rejection_remains_enabled_under_python_optimization(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.prepare(
                root,
                after=design(BASE_COMPONENTS, BASE_NETS).replace("NETS 3", "NETS 4"),
            )
            code = (
                "from nanochip.laboratory.physical.signal_graph import check_signal_reachability; import pathlib; p=pathlib.Path(%r); check_signal_reachability(p/'before.def',p/'after.def',lef_path=p/'cells.lef',liberty_path=p/'cells.lib')"
                % str(root)
            )
            result = subprocess.run(
                [sys.executable, "-O", "-c", code],
                capture_output=True,
                text=True,
                timeout=10,
                env=os.environ.copy(),
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("Declared NETS count mismatch", result.stderr)

    def test_declared_input_only_diode_is_counted_without_changing_reachability(self):
        nets = [
            *BRANCH_NETS[:-1],
            ("n3", "SIGNAL", [("b", "X"), ("s", "A"), ("d", "DIODE")]),
        ]
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.prepare(
                root, after=design(BASE_COMPONENTS + [("b", BUF), ("d", DIODE)], nets)
            )
            with self.assertRaisesRegex(SignalGraphError, "Unlisted added master"):
                self.check(root)
            receipt = self.check(root, added_physical_masters=(DIODE,))
            self.assertEqual(receipt["original_signal_loads_checked"], 3)
            self.assertEqual(receipt["added_physical_cells"], 1)
            self.assertEqual(receipt["added_physical_cell_counts"], {DIODE: 1})
            self.assertEqual(receipt["added_physical_masters"], [DIODE])
            self.assertIn(DIODE, receipt["verified_physical_schemas"])

    def test_diode_admission_rejects_functional_sequential_or_wrong_lef_schema(self):
        nets = [
            *BRANCH_NETS[:-1],
            ("n3", "SIGNAL", [("b", "X"), ("s", "A"), ("d", "DIODE")]),
        ]
        mutations = {
            "output": (
                "pin(DIODE) { direction: input; }",
                'pin(DIODE) { direction: output; function: "1"; }',
            ),
            "function": (
                "pin(DIODE) { direction: input; }",
                'pin(DIODE) { direction: input; function: "1"; }',
            ),
            "sequential": (
                "pin(DIODE) { direction: input; }",
                'pin(DIODE) { direction: input; } ff(IQ,IQ_N) { clocked_on: "DIODE"; next_state: "DIODE"; }',
            ),
        }
        for label, (old, new) in mutations.items():
            with self.subTest(label=label), TemporaryDirectory() as tmp:
                root = Path(tmp)
                self.prepare(
                    root,
                    after=design(BASE_COMPONENTS + [("b", BUF), ("d", DIODE)], nets),
                )
                path = root / "cells.lib"
                path.write_text(path.read_text().replace(old, new))
                with self.assertRaises(SignalGraphError):
                    self.check(root, added_physical_masters=(DIODE,))
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.prepare(
                root, after=design(BASE_COMPONENTS + [("b", BUF), ("d", DIODE)], nets)
            )
            path = root / "cells.lef"
            path.write_text(
                path.read_text().replace("CLASS CORE ANTENNACELL", "CLASS CORE")
            )
            with self.assertRaisesRegex(SignalGraphError, "LEF antenna cell"):
                self.check(root, added_physical_masters=(DIODE,))
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.prepare(root)
            with self.assertRaisesRegex(
                SignalGraphError, "Unrecognized added physical"
            ):
                self.check(root, added_physical_masters=("inverter",))

    def test_diode_admission_rejects_disconnected_input_clock_load_and_hidden_lost_sink(
        self,
    ):
        components = BASE_COMPONENTS + [("b", BUF), ("d", DIODE)]
        cases = {
            "disconnected": BRANCH_NETS,
            "clock": BRANCH_NETS + [("diodeclock", "CLOCK", [("d", "DIODE")])],
            "lost_sink": [
                *BRANCH_NETS[:-1],
                ("n3", "SIGNAL", [("b", "X"), ("d", "DIODE")]),
            ],
        }
        for label, nets in cases.items():
            with self.subTest(label=label), TemporaryDirectory() as tmp:
                root = Path(tmp)
                self.prepare(root, after=design(components, nets))
                with self.assertRaises(SignalGraphError):
                    self.check(root, added_physical_masters=(DIODE,))

    def clock_diode_case(self):
        components = BASE_COMPONENTS + [("c", BUF), ("d", BUF)]
        clock = ("clock", "CLOCK", [("c", "X"), ("d", "A")])
        after_clock = (
            "clock",
            "CLOCK",
            clock[2] + [("ant", "DIODE"), ("ant2", "DIODE")],
        )
        before = design(components, BASE_NETS + [clock])
        after = design(
            components + [("ant", DIODE), ("ant2", DIODE)], BASE_NETS + [after_clock]
        )
        return before, after

    def test_exact_clock_diode_allowance_preserves_original_graph_without_claiming_identity(
        self,
    ):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            before, after = self.clock_diode_case()
            self.prepare(root, before=before, after=after)
            receipt = self.check(
                root,
                added_physical_masters=(DIODE,),
                allowed_clock_diode_loads={"clock": ("ant2/DIODE", "ant/DIODE")},
            )
            self.assertFalse(receipt["clock_connectivity_identical"])
            self.assertTrue(receipt["original_clock_connectivity_preserved"])
            self.assertEqual(
                receipt["added_clock_diode_loads"],
                {"clock": ["ant/DIODE", "ant2/DIODE"]},
            )
            self.assertEqual(receipt["added_physical_cells"], 2)

    def test_clock_diode_allowance_is_exact_and_does_not_admit_arbitrary_clock_pins(
        self,
    ):
        maps = [
            {},
            {"clock": ("ant/DIODE",)},
            {"clock": ("ant/DIODE", "ant/DIODE")},
            {"clock": ("ant/DIODE", "ant2/DIODE", "s/A")},
            {"clock": ("ant/DIODE", "ant2/A")},
            {"notclock": ("ant/DIODE", "ant2/DIODE")},
            {"clock": ()},
        ]
        for allowance in maps:
            with self.subTest(allowance=allowance), TemporaryDirectory() as tmp:
                root = Path(tmp)
                before, after = self.clock_diode_case()
                self.prepare(root, before=before, after=after)
                with self.assertRaises(SignalGraphError):
                    self.check(
                        root,
                        added_physical_masters=(DIODE,),
                        allowed_clock_diode_loads=allowance,
                    )

    def test_clock_diode_allowance_cannot_hide_original_sink_removal_or_net_type_change(
        self,
    ):
        before, after = self.clock_diode_case()
        variants = [
            after.replace("( d A )", ""),
            after.replace("- clock ", "- different_clock "),
            after.replace("+ USE CLOCK", "+ USE SIGNAL"),
        ]
        for index, changed in enumerate(variants):
            with self.subTest(index=index), TemporaryDirectory() as tmp:
                root = Path(tmp)
                self.prepare(root, before=before, after=changed)
                with self.assertRaisesRegex(
                    SignalGraphError, "CLOCK connectivity changed"
                ):
                    self.check(
                        root,
                        added_physical_masters=(DIODE,),
                        allowed_clock_diode_loads={
                            "clock": ("ant/DIODE", "ant2/DIODE")
                        },
                    )

    def test_clock_buffer_addition_cannot_use_diode_allowance(self):
        components = BASE_COMPONENTS + [("c", BUF), ("d", BUF)]
        before = design(
            components, BASE_NETS + [("clock", "CLOCK", [("c", "X"), ("d", "A")])]
        )
        after = design(
            components + [("b", BUF)],
            BASE_NETS
            + [
                ("clock", "CLOCK", [("c", "X"), ("b", "A")]),
                ("clockbranch", "CLOCK", [("b", "X"), ("d", "A")]),
            ],
        )
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.prepare(root, before=before, after=after)
            with self.assertRaisesRegex(SignalGraphError, "verified diode input"):
                self.check(
                    root,
                    added_physical_masters=(DIODE,),
                    allowed_clock_diode_loads={"clock": ("b/A",)},
                )

    def cts_case(self):
        components = BASE_COMPONENTS + [("ff0", BUF), ("ff1", BUF)]
        before_clocks = [
            ("clkold", "CLOCK", [("PIN", "clka"), ("ff0", "A"), ("ff1", "A")]),
            ("clkbnet", "CLOCK", [("PIN", "clkb")]),
        ]
        after_clocks = [
            ("renamedclk", "CLOCK", [("PIN", "clka"), ("cts0", "A")]),
            ("branch", "CLOCK", [("cts0", "X"), ("ff0", "A"), ("cts1", "A")]),
            ("leaf", "CLOCK", [("cts1", "X"), ("ff1", "A")]),
            before_clocks[1],
        ]

        def ports(text, net):
            return text.replace("PINS 2 ;", "PINS 4 ;").replace(
                "END PINS",
                f"- clka + NET {net} + DIRECTION INPUT + USE SIGNAL ;\n- clkb + NET clkbnet + DIRECTION INPUT + USE SIGNAL ;\nEND PINS",
            )

        before = ports(design(components, BASE_NETS + before_clocks), "clkold")
        after = ports(
            design(
                components + [("cts0", CLKBUF), ("cts1", CLKBUF8)],
                BASE_NETS + after_clocks,
            ),
            "renamedclk",
        )
        return before, after

    def test_explicit_cts_mode_preserves_sources_and_sinks_across_renamed_multilevel_tree(
        self,
    ):
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            before, after = self.cts_case()
            self.prepare(root, before=before, after=after)
            with self.assertRaises(SignalGraphError):
                self.check(root)
            receipt = self.check(root, clock_tree_buffer_masters=(CLKBUF, CLKBUF8))
            self.assertEqual(
                receipt["clock_check_mode"], "new_noninverting_buffer_reachability"
            )
            self.assertFalse(receipt["clock_connectivity_identical"])
            self.assertTrue(receipt["original_clock_connectivity_preserved"])
            self.assertEqual(receipt["original_clock_loads_checked"], 2)
            self.assertEqual(
                receipt["original_clock_sources"], ["PIN/clka", "PIN/clkb"]
            )
            self.assertEqual(receipt["added_clock_buffers"], 2)
            self.assertEqual(
                receipt["added_clock_buffer_counts"], {CLKBUF: 1, CLKBUF8: 1}
            )
            self.assertEqual(receipt["original_signal_loads_checked"], 3)
            self.assertEqual(receipt["added_noninverting_buffers"], 0)

    def test_cts_mode_rejects_lost_sink_disconnection_changed_driver_and_extra_clock_endpoint(
        self,
    ):
        before, after = self.cts_case()
        variants = {
            "lost_sink": after.replace("( ff1 A )", ""),
            "disconnected_buffer": after.replace("( cts1 A )", ""),
            "wrong_source": after.replace("( cts1 A )", "").replace(
                "( PIN clkb )", "( PIN clkb ) ( cts1 A )"
            ),
            "extra_original_pin": after.replace("( ff1 A )", "( ff1 A ) ( ff0 X )"),
            "extra_driver": after.replace(
                "( cts1 X )", "( cts1 X ) ( cts0 X )"
            ).replace("( cts0 X ) ( ff0 A )", "( ff0 A )"),
            "clock_to_signal": after.replace(
                "- leaf ( cts1 X ) ( ff1 A ) + USE CLOCK",
                "- leaf ( cts1 X ) ( ff1 A ) + USE SIGNAL",
            ),
            "original_cell_removed": after.replace("COMPONENTS 6", "COMPONENTS 5")
            .replace(f"- ff1 {BUF} + PLACED ( 0 0 ) N ;\n", "")
            .replace("( ff1 A )", ""),
            "original_master_changed": after.replace(f"- ff0 {BUF} ", f"- ff0 {BUF8} "),
        }
        for name, changed in variants.items():
            with self.subTest(name=name), TemporaryDirectory() as tmp:
                root = Path(tmp)
                self.prepare(root, before=before, after=changed)
                with self.assertRaises(SignalGraphError):
                    self.check(root, clock_tree_buffer_masters=(CLKBUF, CLKBUF8))

    def test_cts_mode_rejects_inverting_unlisted_extra_functional_and_unused_clock_buffers(
        self,
    ):
        before, after = self.cts_case()
        variants = {
            "inverting": (after.replace(CLKBUF8, "inverter"), (CLKBUF, "inverter")),
            "unlisted": (after, (CLKBUF,)),
            "extra_functional": (
                after.replace("COMPONENTS 6", "COMPONENTS 7")
                .replace(
                    "END COMPONENTS",
                    "- extra sink_1 + PLACED ( 0 0 ) N ;\nEND COMPONENTS",
                )
                .replace("( ff1 A )", "( ff1 A ) ( extra A )"),
                (CLKBUF, CLKBUF8),
            ),
            "unused_buffer": (
                after.replace("( ff1 A )", "").replace(
                    "( ff0 A )", "( ff0 A ) ( ff1 A )"
                ),
                (CLKBUF, CLKBUF8),
            ),
            "cycle": (
                after.replace("( cts1 A )", "").replace(
                    "( ff1 A )", "( ff1 A ) ( cts1 A )"
                ),
                (CLKBUF, CLKBUF8),
            ),
        }
        for name, (changed, masters) in variants.items():
            with self.subTest(name=name), TemporaryDirectory() as tmp:
                root = Path(tmp)
                self.prepare(root, before=before, after=changed)
                with self.assertRaises(SignalGraphError):
                    self.check(root, clock_tree_buffer_masters=masters)

    def test_cts_mode_cannot_hide_changed_signal_reachability(self):
        before, after = self.cts_case()
        changed = after.replace("( s A )", "").replace(
            "( PIN in )", "( PIN in ) ( s A )"
        )
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.prepare(root, before=before, after=changed)
            with self.assertRaisesRegex(
                SignalGraphError, "Original driver-to-load reachability changed"
            ):
                self.check(root, clock_tree_buffer_masters=(CLKBUF, CLKBUF8))

    def test_cts_mode_rejects_swapped_sinks_between_two_live_clock_roots(self):
        before, after = self.cts_case()

        def extra_sink(text, count):
            return (
                text.replace(f"COMPONENTS {count}", f"COMPONENTS {count + 1}")
                .replace(
                    "END COMPONENTS",
                    f"- ff2 {BUF} + PLACED ( 0 0 ) N ;\nEND COMPONENTS",
                )
                .replace("( PIN clkb )", "( PIN clkb ) ( ff2 A )")
            )

        before, after = extra_sink(before, 4), extra_sink(after, 6)
        swapped = (
            after.replace("( ff1 A )", "( SWAP A )")
            .replace("( ff2 A )", "( ff1 A )")
            .replace("( SWAP A )", "( ff2 A )")
        )
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.prepare(root, before=before, after=after)
            receipt = self.check(root, clock_tree_buffer_masters=(CLKBUF, CLKBUF8))
            self.assertEqual(receipt["original_clock_loads_checked"], 3)
            (root / "after.def").write_text(swapped)
            with self.assertRaisesRegex(
                SignalGraphError, "Original CLOCK driver-to-load reachability changed"
            ):
                self.check(root, clock_tree_buffer_masters=(CLKBUF, CLKBUF8))

    def test_cts_mode_rejects_orphan_clock_tree_and_unreachable_cycle(self):
        before, after = self.cts_case()
        orphan = after.replace("COMPONENTS 6", "COMPONENTS 7").replace(
            "END COMPONENTS", f"- unused {CLKBUF} + PLACED ( 0 0 ) N ;\nEND COMPONENTS"
        )
        orphan = (
            orphan.replace("NETS 7", "NETS 8")
            .replace("( PIN clkb )", "( PIN clkb ) ( unused A )")
            .replace("END NETS", "- unusednet ( unused X ) + USE CLOCK ;\nEND NETS")
        )
        cycle = after.replace("COMPONENTS 6", "COMPONENTS 8").replace(
            "END COMPONENTS",
            f"- ca {CLKBUF} + PLACED ( 0 0 ) N ;\n- cb {CLKBUF} + PLACED ( 0 0 ) N ;\nEND COMPONENTS",
        )
        cycle = cycle.replace("NETS 7", "NETS 9").replace(
            "END NETS",
            "- cyclea ( ca X ) ( cb A ) + USE CLOCK ;\n- cycleb ( cb X ) ( ca A ) + USE CLOCK ;\nEND NETS",
        )
        for label, changed, error in [
            ("orphan", orphan, "reaches no original CLOCK load"),
            ("cycle", cycle, "CLOCK-buffer cycle"),
        ]:
            with self.subTest(label=label), TemporaryDirectory() as tmp:
                root = Path(tmp)
                self.prepare(root, before=before, after=changed)
                with self.assertRaisesRegex(SignalGraphError, error):
                    self.check(root, clock_tree_buffer_masters=(CLKBUF, CLKBUF8))

    def test_cts_mode_still_admits_separately_declared_signal_buffer_repair(self):
        before, after = self.cts_case()
        after = after.replace("COMPONENTS 6", "COMPONENTS 7").replace(
            "END COMPONENTS", f"- sig {BUF} + PLACED ( 0 0 ) N ;\nEND COMPONENTS"
        )
        after = after.replace("NETS 7", "NETS 8").replace(
            "( u X ) ( s A )", "( u X ) ( sig A )"
        )
        after = after.replace(
            "END NETS", "- sigbranch ( sig X ) ( s A ) + USE SIGNAL ;\nEND NETS"
        )
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.prepare(root, before=before, after=after)
            receipt = self.check(root, clock_tree_buffer_masters=(CLKBUF, CLKBUF8))
            self.assertEqual(receipt["added_clock_buffers"], 2)
            self.assertEqual(receipt["added_noninverting_buffers"], 1)

    def test_cts_driver_rejection_remains_active_with_python_optimization(self):
        before, after = self.cts_case()
        after = after.replace("( cts1 A )", "").replace(
            "( PIN clkb )", "( PIN clkb ) ( cts1 A )"
        )
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.prepare(root, before=before, after=after)
            code = (
                "from nanochip.laboratory.physical.signal_graph import check_signal_reachability; import pathlib; p=pathlib.Path(%r); check_signal_reachability(p/'before.def',p/'after.def',lef_path=p/'cells.lef',liberty_path=p/'cells.lib',clock_tree_buffer_masters=(%r,%r))"
                % (str(root), CLKBUF, CLKBUF8)
            )
            result = subprocess.run(
                [sys.executable, "-O", "-c", code],
                capture_output=True,
                text=True,
                timeout=10,
                env=os.environ.copy(),
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(
                "Original CLOCK driver-to-load reachability changed", result.stderr
            )

    def cts_dummy_case(self, master="inverter"):
        before, after = self.cts_case()
        after = after.replace("COMPONENTS 6", "COMPONENTS 7").replace(
            "END COMPONENTS", f"- dummy {master} + PLACED ( 0 0 ) N ;\nEND COMPONENTS"
        )
        after = after.replace("( ff1 A )", "( ff1 A ) ( dummy A )")
        allowance = {"dummy": {"master": master, "input_pin": "A", "net": "leaf"}}
        return before, after, allowance

    def test_exact_native_dummy_load_is_a_verified_load_not_a_transport_buffer(self):
        for master in ("inverter", CLKBUF):
            with self.subTest(master=master), TemporaryDirectory() as tmp:
                root = Path(tmp)
                before, after, allowance = self.cts_dummy_case(master)
                self.prepare(root, before=before, after=after)
                with self.assertRaises(SignalGraphError):
                    self.check(root, clock_tree_buffer_masters=(CLKBUF, CLKBUF8))
                receipt = self.check(
                    root,
                    clock_tree_buffer_masters=(CLKBUF, CLKBUF8),
                    clock_dummy_loads=allowance,
                )
                self.assertEqual(receipt["added_clock_buffers"], 2)
                self.assertEqual(receipt["original_clock_loads_checked"], 2)
                self.assertEqual(receipt["added_clock_dummy_loads"], 1)
                self.assertEqual(receipt["added_clock_dummy_counts"], {master: 1})
                self.assertEqual(receipt["clock_dummy_loads"], allowance)
                self.assertIn(master, receipt["verified_clock_dummy_schemas"])
                self.assertFalse(receipt["clock_connectivity_identical"])
                self.assertFalse(receipt["eligible"])

    def test_dummy_allowances_bind_every_instance_master_input_and_net_exactly(self):
        before, after, allowance = self.cts_dummy_case()
        maps = [
            {"not_added": allowance["dummy"]},
            {"ff0": allowance["dummy"]},
            {"dummy": {**allowance["dummy"], "master": CLKBUF}},
            {"dummy": {**allowance["dummy"], "input_pin": "X"}},
            {"dummy": {**allowance["dummy"], "net": "branch"}},
            {"dummy": {"master": "inverter", "net": "leaf"}},
            {"dummy": {**allowance["dummy"], "arbitrary": True}},
        ]
        for value in maps:
            with self.subTest(value=value), TemporaryDirectory() as tmp:
                root = Path(tmp)
                self.prepare(root, before=before, after=after)
                with self.assertRaises(SignalGraphError):
                    self.check(
                        root,
                        clock_tree_buffer_masters=(CLKBUF, CLKBUF8),
                        clock_dummy_loads=value,
                    )
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.prepare(root, before=before, after=after)
            with self.assertRaisesRegex(SignalGraphError, "require explicit CTS mode"):
                self.check(root, clock_dummy_loads=allowance)

    def test_dummy_output_connections_and_signal_input_connections_reject(self):
        before, after, allowance = self.cts_dummy_case()
        variants = [
            after.replace("( ff1 A )", "( ff1 A ) ( dummy X )"),
            after.replace("( u A )", "( u A ) ( dummy X )"),
            after.replace("( dummy A )", "").replace("( u A )", "( u A ) ( dummy A )"),
            after.replace("( dummy A )", ""),
        ]
        for index, changed in enumerate(variants):
            with self.subTest(index=index), TemporaryDirectory() as tmp:
                root = Path(tmp)
                self.prepare(root, before=before, after=changed)
                with self.assertRaisesRegex(SignalGraphError, "CLOCK dummy"):
                    self.check(
                        root,
                        clock_tree_buffer_masters=(CLKBUF, CLKBUF8),
                        clock_dummy_loads=allowance,
                    )

    def test_dummy_logical_specialnet_connections_and_incomplete_section_reject(self):
        before, after, allowance = self.cts_dummy_case()
        for pin, count in [("dummy X", 1), ("dummy A", 1), ("* X", 1), ("dummy X", 2)]:
            with self.subTest(pin=pin, count=count), TemporaryDirectory() as tmp:
                root = Path(tmp)
                text = after.replace(
                    "END DESIGN",
                    f"SPECIALNETS {count} ;\n- VPWR ( {pin} ) + USE POWER ;\nEND SPECIALNETS\nEND DESIGN",
                )
                self.prepare(root, before=before, after=text)
                with self.assertRaises(SignalGraphError):
                    self.check(
                        root,
                        clock_tree_buffer_masters=(CLKBUF, CLKBUF8),
                        clock_dummy_loads=allowance,
                    )
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            text = after.replace(
                "END DESIGN",
                "SPECIALNETS 1 ;\n- VPWR (dummy X) + USE POWER ;\nEND SPECIALNETS\nEND DESIGN",
            )
            self.prepare(root, before=before, after=text)
            with self.assertRaisesRegex(SignalGraphError, "SPECIALNETS"):
                self.check(
                    root,
                    clock_tree_buffer_masters=(CLKBUF, CLKBUF8),
                    clock_dummy_loads=allowance,
                )
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            text = after.replace(
                "END DESIGN",
                "SPECIALNETS 1 ;\n- VPWR ( dummy VPWR ) + USE POWER ;\nEND SPECIALNETS\nEND DESIGN",
            )
            self.prepare(root, before=before, after=text)
            self.assertEqual(
                self.check(
                    root,
                    clock_tree_buffer_masters=(CLKBUF, CLKBUF8),
                    clock_dummy_loads=allowance,
                )["status"],
                "pass",
            )

    def test_dummy_sequential_arbitrary_function_and_extra_output_schemas_reject(self):
        before, after, allowance = self.cts_dummy_case()
        mutations = {
            "sequential": (
                "cell(inverter) {",
                'cell(inverter) { ff(IQ,IQ_N) { clocked_on: "A"; next_state: "A"; }',
            ),
            "constant": ('function: "!A"', 'function: "1"'),
            "arbitrary": ('function: "!A"', 'function: "A&A"'),
        }
        for label, (old, new) in mutations.items():
            with self.subTest(label=label), TemporaryDirectory() as tmp:
                root = Path(tmp)
                self.prepare(root, before=before, after=after)
                path = root / "cells.lib"
                path.write_text(path.read_text().replace(old, new))
                with self.assertRaises(SignalGraphError):
                    self.check(
                        root,
                        clock_tree_buffer_masters=(CLKBUF, CLKBUF8),
                        clock_dummy_loads=allowance,
                    )
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.prepare(root, before=before, after=after)
            lib = root / "cells.lib"
            text = lib.read_text().replace(
                "cell(inverter) {",
                'cell(inverter) { pin(Y) { direction: output; function: "A"; }',
            )
            lib.write_text(text)
            lef = root / "cells.lef"
            lef.write_text(
                lef.read_text().replace(
                    "MACRO inverter\n",
                    "MACRO inverter\n  PIN Y\n    DIRECTION OUTPUT ;\n    USE SIGNAL ;\n  END Y\n",
                )
            )
            with self.assertRaisesRegex(SignalGraphError, "one input and one output"):
                self.check(
                    root,
                    clock_tree_buffer_masters=(CLKBUF, CLKBUF8),
                    clock_dummy_loads=allowance,
                )

    def with_clock_ndr(self, text, *, net="renamedclk"):
        declaration = "NONDEFAULTRULES 1 ;\n- CTS_NDR_0\n + LAYER met1 WIDTH 140 SPACING 280\n + LAYER met2 WIDTH 140 SPACING 280\n;\nEND NONDEFAULTRULES\n"
        text = text.replace("COMPONENTS ", declaration + "COMPONENTS ", 1)
        lines = text.splitlines()
        return (
            "\n".join(
                line.replace(
                    "+ USE CLOCK ;", "+ USE CLOCK + NONDEFAULTRULE CTS_NDR_0 ;"
                )
                if line.startswith("- " + net + " ")
                else line
                for line in lines
            )
            + "\n"
        )

    def test_declared_clock_ndr_is_bound_metadata_separate_from_cts_reachability(self):
        before, after = self.cts_case()
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.prepare(root, before=before, after=self.with_clock_ndr(after))
            first = self.check(root, clock_tree_buffer_masters=(CLKBUF, CLKBUF8))
            rule = first["routing_rule_metadata"]["after"]
            self.assertEqual(rule["clock_net_rules"], {"renamedclk": "CTS_NDR_0"})
            self.assertEqual(
                rule["declared_rules"]["CTS_NDR_0"]["met1"],
                {"width_dbu": 140, "spacing_dbu": 280},
            )
            self.assertEqual(first["original_clock_loads_checked"], 2)
            self.assertIn("no physical rule", first["routing_rule_metadata"]["scope"])
            path = root / "after.def"
            path.write_text(path.read_text().replace("WIDTH 140", "WIDTH 141"))
            second = self.check(root, clock_tree_buffer_masters=(CLKBUF, CLKBUF8))
            self.assertNotEqual(
                first["inputs"]["after_def"]["sha256"],
                second["inputs"]["after_def"]["sha256"],
            )
            self.assertEqual(
                second["routing_rule_metadata"]["after"]["declared_rules"]["CTS_NDR_0"][
                    "met1"
                ]["width_dbu"],
                141,
            )

    def test_clock_ndr_metadata_does_not_relax_strict_clock_graph_mode(self):
        before, _ = self.cts_case()
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.prepare(
                root, before=before, after=self.with_clock_ndr(before, net="clkold")
            )
            receipt = self.check(root)
            self.assertTrue(receipt["clock_connectivity_identical"])
            self.assertEqual(receipt["clock_check_mode"], "exact_original_nets")
            path = root / "after.def"
            path.write_text(path.read_text().replace("( ff1 A )", ""))
            with self.assertRaisesRegex(SignalGraphError, "CLOCK connectivity changed"):
                self.check(root)

    def test_clock_ndr_references_counts_duplicate_rules_and_unsupported_declarations_reject(
        self,
    ):
        before, after = self.cts_case()
        good = self.with_clock_ndr(after)
        declaration = good[
            good.index("NONDEFAULTRULES 1 ;") : good.index("END NONDEFAULTRULES")
            + len("END NONDEFAULTRULES\n")
        ]
        duplicate = declaration.replace(
            "NONDEFAULTRULES 1", "NONDEFAULTRULES 2"
        ).replace(
            "END NONDEFAULTRULES",
            "- CTS_NDR_0 + LAYER met1 WIDTH 140 SPACING 280 ;\nEND NONDEFAULTRULES",
        )
        variants = {
            "undeclared": good.replace(
                "+ NONDEFAULTRULE CTS_NDR_0", "+ NONDEFAULTRULE MISSING"
            ),
            "missing_declarations": good.replace(declaration, ""),
            "wrong_count": good.replace("NONDEFAULTRULES 1", "NONDEFAULTRULES 2"),
            "duplicate_rule": good.replace(declaration, duplicate),
            "duplicate_layer": good.replace("+ LAYER met2", "+ LAYER met1"),
            "nonpositive_width": good.replace("WIDTH 140", "WIDTH 0"),
            "nonpositive_spacing": good.replace("SPACING 280", "SPACING 0"),
            "negative_width": good.replace("WIDTH 140", "WIDTH -1"),
            "unknown_rule_attribute": good.replace(
                "+ LAYER met2", "+ HARDSPACING + LAYER met2"
            ),
            "signal_rule": good.replace(
                "( u X ) ( s A ) + USE SIGNAL ;",
                "( u X ) ( s A ) + USE SIGNAL + NONDEFAULTRULE CTS_NDR_0 ;",
            ),
            "unknown_net_attribute": good.replace(
                "+ NONDEFAULTRULE CTS_NDR_0 ;",
                "+ NONDEFAULTRULE CTS_NDR_0 + SOURCE DIST ;",
            ),
            "routed_net": good.replace(
                "+ NONDEFAULTRULE CTS_NDR_0 ;",
                "+ NONDEFAULTRULE CTS_NDR_0 + ROUTED met1 ( 0 0 ) ;",
            ),
            "duplicate_reference": good.replace(
                "+ NONDEFAULTRULE CTS_NDR_0 ;",
                "+ NONDEFAULTRULE CTS_NDR_0 + NONDEFAULTRULE CTS_NDR_0 ;",
            ),
        }
        for label, changed in variants.items():
            with self.subTest(label=label), TemporaryDirectory() as tmp:
                root = Path(tmp)
                self.prepare(root, before=before, after=changed)
                with self.assertRaises(SignalGraphError):
                    self.check(root, clock_tree_buffer_masters=(CLKBUF, CLKBUF8))


if __name__ == "__main__":
    unittest.main()
