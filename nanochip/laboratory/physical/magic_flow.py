"""Reject failed Magic processes and incomplete output from its LEF producer.

These checks establish producer completion, not LEF semantics, antenna
closure, layout correctness, or manufacturing signoff. The downstream pin
property, DRC, LVS, and electrical checks remain required.
"""

import hashlib
import json
from pathlib import Path


LEF_SCRIPT_SHA256 = "223fefeb7b2242b818879ea3b8289931c2410429762dca37021e182a0fb18805"
LEF_COMPLETE = "[INFO] LEF Write Complete."


def _sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1048576), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _local_file(value, directory):
    path = Path(value)
    root = Path(directory).resolve(strict=True)
    if (
        path.is_symlink()
        or not path.is_file()
        or not path.resolve().is_relative_to(root)
    ):
        raise ValueError(
            "Magic output must be a regular file in its executing step: " + str(path)
        )
    return path


def validate_lef_completion(lef_path, log_path, top, directory):
    """Check the pinned writer's terminators and completion marker.

    This deliberately does not parse or approve pin geometry or antenna
    properties. The following native OpenDB check owns those semantics.
    """
    lef = _local_file(lef_path, directory)
    log = _local_file(log_path, directory)
    if not isinstance(top, str) or not top or any(char.isspace() for char in top):
        raise ValueError("A nonempty LEF top name is required")
    if lef.stat().st_size == 0:
        raise ValueError("Magic produced an empty LEF")
    macros, ends, library_ends = [], [], []
    last_tokens = None
    with lef.open(encoding="utf-8") as stream:
        for index, line in enumerate(stream):
            tokens = line.split("#", 1)[0].split()
            if not tokens:
                continue
            last_tokens = tokens
            if tokens[0] == "MACRO":
                macros.append((index, tokens))
            if tokens == ["END", top]:
                ends.append(index)
            if tokens == ["END", "LIBRARY"]:
                library_ends.append(index)
    if (
        len(macros) != 1
        or macros[0][1] != ["MACRO", top]
        or len(ends) != 1
        or len(library_ends) != 1
        or not macros[0][0] < ends[0] < library_ends[0]
        or last_tokens != ["END", "LIBRARY"]
    ):
        raise ValueError(
            "Magic LEF lacks one complete top macro and library terminator"
        )
    with log.open(encoding="utf-8") as stream:
        completions = sum(line.strip() == LEF_COMPLETE for line in stream)
    if completions != 1:
        raise ValueError("Magic LEF completion marker is missing or repeated")
    return {
        "lef": str(lef),
        "lef_sha256": _sha256(lef),
        "size_bytes": lef.stat().st_size,
        "top": top,
        "log": str(log),
        "log_sha256": _sha256(log),
        "completion_markers": completions,
    }


def build_magic_exit_step(base, *, step_error):
    """Enforce the installed subprocess contract without changing tool checks.

    The pinned MagicStep disables subprocess checking. A partial DRC report,
    netlist, or layout left by a failed process must not be admitted by native
    parsing of that output. Zero exit status does not replace those native
    checks: a completed process can still report DRC or LVS errors.
    """

    class CheckedMagicExit(base):
        def run_subprocess(self, *args, **kwargs):
            kwargs["check"] = True
            result = super().run_subprocess(*args, **kwargs)
            if type(result.get("returncode")) is not int or result["returncode"] != 0:
                raise step_error("Magic subprocess did not report a successful exit")
            return result

    return CheckedMagicExit


def build_write_lef_step(magic, *, step_error):
    """Add completion checks to the installed LEF producer and strict exit check.

    The caller supplies LibreLane's Magic namespace and StepError, so importing
    this helper does not require EDA dependencies on a student's host.
    """
    base = build_magic_exit_step(magic.WriteLEF, step_error=step_error)
    if len(base.outputs) != 1:
        raise ValueError("Unexpected pinned Magic.WriteLEF output contract")
    lef_format = base.outputs[0]

    class CheckedWriteLEF(base):
        def get_script_path(self):
            script = Path(super().get_script_path())
            if _sha256(script) != LEF_SCRIPT_SHA256:
                raise step_error("Pinned Magic LEF script identity differs")
            return str(script)

        def run_subprocess(self, *args, **kwargs):
            result = super().run_subprocess(*args, **kwargs)
            self._nanochip_magic_invocations.append(
                {"returncode": result["returncode"], "log_path": result["log_path"]}
            )
            return result

        def run(self, state_in, **kwargs):
            self._nanochip_magic_invocations = []
            receipt = {
                "schema": "nanochip-magic-lef-producer/v1",
                "status": "error",
                "scope": "LEF producer completion only; downstream physical checks remain required",
                "script_sha256": LEF_SCRIPT_SHA256,
            }
            try:
                views, metrics = super().run(state_in, **kwargs)
                if len(self._nanochip_magic_invocations) != 1:
                    raise step_error(
                        "Magic LEF requires exactly one recorded subprocess"
                    )
                if lef_format not in views:
                    raise step_error("Magic LEF producer returned no LEF view")
                invocation = self._nanochip_magic_invocations[0]
                receipt["output"] = validate_lef_completion(
                    views[lef_format],
                    invocation["log_path"],
                    self.config["DESIGN_NAME"],
                    self.step_dir,
                )
                receipt.update(status="pass", returncode=invocation["returncode"])
                return views, metrics
            except Exception as exc:
                receipt.update(
                    error=str(exc), returncode=getattr(exc, "returncode", None)
                )
                raise
            finally:
                receipt["invocations"] = self._nanochip_magic_invocations
                (Path(self.step_dir) / "nanochip-lef-producer.json").write_text(
                    json.dumps(receipt, indent=2, sort_keys=True) + "\n"
                )

    return CheckedWriteLEF
