"""Generic source/scope and native runtime boundaries; fake tools are not measurements."""

import json
import os
from pathlib import Path
import subprocess
import sys
import time
from unittest.mock import patch

import pytest

from nanochip.laboratory.physical import run_physical_design
from nanochip.laboratory.physical.flow import _coverage_libraries, _execute, collect_checks


def design(tmp_path):
    source = tmp_path / "source.v"
    source.write_text("module other_top(input clk, input d, output reg q); always @(posedge clk) q <= d; endmodule\n")
    return {"rtl/top.v": source}, {"DESIGN_NAME": "other_top", "VERILOG_FILES": ["dir::rtl/top.v"], "CLOCK_PORT": "clk", "CLOCK_PERIOD": 100, "VERILOG_INCLUDE_DIRS": ["dir::rtl"]}


def test_generic_design_retains_source_manifest_and_explicit_scope(tmp_path):
    sources, config = design(tmp_path)
    with patch("nanochip.laboratory.physical.flow.shutil.which", return_value=None):
        result = run_physical_design(sources, tmp_path / "out", config=config,
                                     scope="core:other_top", boundary="test only", mode="docker")
    assert result["status"] == "unavailable"
    assert result["design_name"] == "other_top"
    assert result["candidate_hash_kind"] == "source-manifest"
    assert result["scope"] == "core:other_top"
    assert result["source_manifest"][0]["path"] == "rtl/top.v"
    assert (tmp_path / "out/rtl/top.v").read_bytes() == next(iter(sources.values())).read_bytes()
    assert json.loads((tmp_path / "out/config.json").read_text()) == config
    assert all(c["scope"] == "core:other_top" for c in collect_checks(tmp_path / "out", scope="core:other_top")[0])


@pytest.mark.parametrize("name", ["../escape.v", "/escape.v", "config.json", "runs/physical/a.v"])
def test_manifest_rejects_unsafe_or_reserved_destination_before_output(tmp_path, name):
    sources, config = design(tmp_path)
    with pytest.raises(ValueError, match="safe run-relative"):
        run_physical_design({name: next(iter(sources.values()))}, tmp_path / "out", config=config,
                            scope="core:other_top", boundary="test")
    assert not (tmp_path / "out").exists()


def test_config_cannot_read_unmanifested_host_input(tmp_path):
    sources, config = design(tmp_path)
    config["VERILOG_FILES"] = ["dir::missing.v"]
    with pytest.raises(ValueError, match="unmanifested"):
        run_physical_design(sources, tmp_path / "out", config=config, scope="core:other_top", boundary="test")
    assert not (tmp_path / "out").exists()


def test_native_mode_requires_exact_image_identity_and_never_calls_docker(tmp_path):
    sources, config = design(tmp_path)
    with patch.dict(os.environ, {"NANOCHIP_PHYSICAL_IMAGE": "incorrect"}), patch("nanochip.laboratory.physical.flow._execute") as execute:
        result = run_physical_design(sources, tmp_path / "out", config=config,
                                     scope="core:other_top", boundary="test", mode="native")
    assert result["status"] == "unavailable"
    assert "pinned" in result["details"]
    assert result["runtime_mode"] == "native"
    execute.assert_not_called()


@pytest.mark.parametrize("new_session", [False, True])
def test_native_timeout_kills_subprocess_descendants(tmp_path, new_session):
    pidfile = tmp_path / "child.pid"
    code = "import pathlib,subprocess,sys,time; p=subprocess.Popen([sys.executable,'-c','import time; time.sleep(60)'],start_new_session=bool(int(sys.argv[2]))); pathlib.Path(sys.argv[1]).write_text(str(p.pid)); time.sleep(60)"
    with (tmp_path / "process.log").open("w") as stream, pytest.raises(subprocess.TimeoutExpired):
        _execute([sys.executable, "-c", code, str(pidfile), str(int(new_session))], stream, 1)
    pid = int(pidfile.read_text())
    # A killed child may briefly remain a zombie until its adopter reaps it.
    for _ in range(20):
        status = subprocess.run(["ps", "-o", "stat=", "-p", str(pid)], capture_output=True, text=True).stdout.strip()
        if not status or status.startswith("Z"):
            break
        time.sleep(0.05)
    assert not status or status.startswith("Z")


def test_macro_coverage_requires_matching_timing_model_at_every_corner():
    config = {"LIB": {"*": ["standard.lib"]}, "EXTRA_LIBS": ["extra.lib"],
              "MACROS": {"sram": {"lib": {"*_ss_*": ["sram-slow.lib"]}}}}
    assert _coverage_libraries(config, "nom_ss_100C_1v60") == (["standard.lib", "extra.lib", "sram-slow.lib"], [])
    assert _coverage_libraries(config, "nom_ff_n40C_1v95") == (["standard.lib", "extra.lib"], ["sram"])
