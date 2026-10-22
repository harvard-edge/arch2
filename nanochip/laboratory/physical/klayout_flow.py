"""Forward native DRC options to the exact pinned SKY130 KLayout deck.

LibreLane and this deck use different names for three arguments. Translate
only those names, retaining the deck, values, native report conversion, and
acceptance checks. This does not change rule coverage or enable tiling.
"""

import hashlib
import json
from pathlib import Path
import re


DRC_DECK_SHA256 = "caf4a6b08cb12f78d6bb2d120737424c786b3bae8d6489234b9b269e91107bfc"
ARGUMENT_NAMES = {
    "topcell": "top_cell",
    "floating_metal": "floating_met",
    "threads": "thr",
}
NATIVE_ARGUMENTS = {
    "input",
    "topcell",
    "report",
    "feol",
    "beol",
    "floating_metal",
    "offgrid",
    "seal",
    "threads",
}


def adapt_sky130_drc_command(command, *, runset, top):
    """Return a copied native command with the pinned deck's argument names."""
    if (
        not isinstance(command, (list, tuple))
        or len(command) < 5
        or list(command[:4]) != ["klayout", "-b", "-zz", "-r"]
    ):
        raise ValueError("Unexpected pinned KLayout DRC command")
    script = Path(runset)
    if Path(command[4]).resolve() != script.resolve():
        raise ValueError("KLayout command does not use its configured DRC deck")
    if hashlib.sha256(script.read_bytes()).hexdigest() != DRC_DECK_SHA256:
        raise ValueError("Pinned KLayout DRC deck identity differs")
    if (len(command) - 5) % 2:
        raise ValueError("Incomplete KLayout DRC argument pair")
    arguments = {}
    adapted = list(command[:5])
    for index in range(5, len(command), 2):
        option = command[index + 1]
        if command[index] != "-rd" or not isinstance(option, str) or "=" not in option:
            raise ValueError("Unexpected KLayout DRC argument pair")
        name, value = option.split("=", 1)
        if name not in NATIVE_ARGUMENTS or name in arguments or not value:
            raise ValueError("Unknown, duplicate, or empty KLayout DRC argument")
        arguments[name] = value
        adapted.extend(["-rd", ARGUMENT_NAMES.get(name, name) + "=" + value])
    if set(arguments) != NATIVE_ARGUMENTS:
        raise ValueError("Pinned KLayout DRC arguments are incomplete")
    if arguments["topcell"] != top:
        raise ValueError("KLayout DRC top does not match the design")
    if not re.fullmatch(r"[1-9][0-9]*", arguments["threads"]):
        raise ValueError("KLayout DRC thread count must be a positive integer")
    return adapted, {
        "schema": "nanochip-klayout-drc-arguments/v1",
        "scope": "Argument compatibility only; native DRC results and checks remain required",
        "deck_path": str(script),
        "deck_sha256": DRC_DECK_SHA256,
        "original_command": [str(part) for part in command],
        "adapted_command": [str(part) for part in adapted],
        "renamed_arguments": ARGUMENT_NAMES,
        "threads": int(arguments["threads"]),
        "top": top,
        "rule_values": {
            key: arguments[key]
            for key in ("feol", "beol", "floating_metal", "offgrid", "seal")
        },
    }


def build_klayout_drc_step(base, *, step_error):
    """Wrap the installed DRC producer without importing EDA tools on the host."""

    class CompatibleKLayoutDRC(base):
        def run_sky130(self, state_in, **kwargs):
            self._nanochip_drc_invocations = 0
            metrics = super().run_sky130(state_in, **kwargs)
            if self._nanochip_drc_invocations != 1:
                raise step_error("KLayout DRC requires exactly one deck invocation")
            return metrics

        def run_subprocess(self, command, *args, **kwargs):
            self._nanochip_drc_invocations += 1
            if self._nanochip_drc_invocations != 1:
                raise step_error("Unexpected additional KLayout DRC subprocess")
            try:
                adapted, receipt = adapt_sky130_drc_command(
                    command,
                    runset=self.config["KLAYOUT_DRC_RUNSET"],
                    top=self.config["DESIGN_NAME"],
                )
            except (OSError, TypeError, ValueError) as exc:
                raise step_error(str(exc)) from exc
            receipt["status"] = "prepared"
            path = Path(self.step_dir) / "nanochip-klayout-drc-arguments.json"
            path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")
            try:
                kwargs["check"] = True
                result = super().run_subprocess(adapted, *args, **kwargs)
                if (
                    type(result.get("returncode")) is not int
                    or result["returncode"] != 0
                ):
                    raise step_error(
                        "KLayout DRC subprocess did not report a successful exit"
                    )
                receipt.update(status="subprocess_completed", returncode=0)
                return result
            except Exception as exc:
                receipt.update(
                    status="error",
                    error=str(exc),
                    returncode=getattr(exc, "returncode", None),
                )
                raise
            finally:
                path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n")

    return CompatibleKLayoutDRC
