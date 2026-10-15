# Moonshot hybrid chip-design evaluation — task Makefile.
# This file is part of the frozen harness. Do not modify.

PY ?= python3

.PHONY: help setup selftest lint audit quick evaluate synth clean

help:
	@echo "targets:"
	@echo "  setup          check/install tools + fetch cell library"
	@echo "  selftest       reference determinism + harness self-checks + ROM check"
	@echo "  lint           verilator --lint-only -Wall on rtl/filelist.f"
	@echo "  audit          machine-checkable R1 scan (also run by evaluate)"
	@echo "  quick          fast loop: nano short prompt, no synth"
	@echo "  evaluate       nano quantitative evaluation (2 prompts + synth/gates)"
	@echo "  synth          yosys area/timing metrics only"
	@echo "  clean          remove build/ artifacts (keeps golden cache)"
	@echo "variables: SEEDS=<seeds.json> to use an alternate seed set"

setup:
	bash scripts/setup_env.sh

selftest:
	$(PY) reference/selftest.py --configs nano --stats
	$(PY) harness/selfcheck.py
	bash scripts/check_roms.sh

lint:
	verilator --lint-only -Wall -Wno-fatal --top-module msh_chip_top \
	    harness/macros/msh_sram.v harness/macros/msh_rom.v -f rtl/filelist.f

audit:
	@$(PY) harness/audit.py

quick:
	$(PY) harness/evaluate.py --quick $(if $(SEEDS),--seeds-file $(SEEDS),)

evaluate:
	$(PY) harness/evaluate.py $(if $(SEEDS),--seeds-file $(SEEDS),)

synth:
	@mkdir -p build
	$(PY) -c "import sys; sys.path.insert(0,'.'); \
	from harness.evaluate import do_synth, do_tech, load_budgets; \
	import json; \
	print(json.dumps(do_synth(), indent=2)); \
	print(json.dumps(do_tech(load_budgets()), indent=2))"

clean:
	rm -rf build
