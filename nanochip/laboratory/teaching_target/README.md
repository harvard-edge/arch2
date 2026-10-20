# Inspect the teaching target's memory boundary

This component moves the complete-core path forward by extracting the actual
upstream `nano` memory requirements and making one memory-interface mapping
editable and executable. It does not create a smaller core or realize physical
memories. The first Nanochip design demo continues to use the dequantizer.

Run from the repository root in the prepared environment:

```bash
python3 -m nanochip.laboratory.teaching_target inspect
python3 -m nanochip.laboratory.teaching_target validate
python3 -m nanochip.laboratory.teaching_target check \
  --output output/nanochip/teaching-memory-001 --timeout-s 60
python3 -m unittest discover -s tests -p test_nanochip_teaching_target.py -v
```

`inspect` prints the checked-in `target.json` snapshot without invoking tools.
It is source-derived inventory, not a fresh validation receipt. `validate`
requires local Yosys and compares the snapshot's design fields with a fresh
elaboration. `derive --output /tmp/new-target.json` writes a new snapshot to a
previously nonexistent file; it does not overwrite the checked-in snapshot.
No command installs tools, pulls images, or invokes a physical flow.

The inventory reads the frozen RTL compile manifest and macro blackboxes,
resolves parameters and hierarchy with Yosys, and records each instantiated
SRAM/ROM geometry. Replicated memories remain separate instances. Every ROM
file is hashed and checked for the declared number and width of words. The
upstream Python and JSON configurations must agree. The snapshot records
source hashes, memory contracts, totals computed from the instantiated
geometries, and unresolved physical views. An absent memory or altered geometry
cannot pass by adjusting the summary totals. The derivation runs frontend and
hierarchy passes, not synthesis or timing analysis.

## Build and check a mapping

`mapping.py` is the student-editable component. Implement the conversion from
XBUF's logical address to its packed SRAM word address, and from its int32 lane
mask to SRAM byte enables. `reference.py` expresses the instructor mapping
using individual bit selections. The contract follows `msh_xbuf` in frozen
`kpu/rtl/msh_mem.v`.

Try replacing the sparse address mapping with a contiguous low-bit slice, or
returning the lane mask directly as the byte mask. Run the check and interpret
the first counterexample. Restore the implementation, then explain why
discarded address bits alias and why the two read copies need synchronized
masked writes. Mapping all input bit patterns does not establish that a
workload is allowed to use an aliased address.

`check` first compares every address input and lane mask against the instructor
mapping. It then copies the exact mapper, reference, testbench, upstream XBUF
wrapper, and upstream SRAM model into a new directory. It loads the copied
Python components, generates deterministic vectors, and uses local Verilator
to execute those copied RTL sources. Every physical storage location is
explicitly written before its output is compared. The test exercises both read
copies, sparse-address aliases, all lane masks, and simultaneous read/write
behavior. A separate small generic SRAM fixture checks old-data collisions,
disabled-read output retention, byte writes, and zero write masks.

The receipt binds copied inputs, vectors, logs, commands, tool revision, and
the runner identity. A pass requires zero command errors and an exact pass
marker with the expected comparison counts. Missing tools, timeouts, missing
markers, and failures remain distinct. The CLI requires a new output directory
so evidence is retained. The Python API `run_memory_check(output=None,
timeout_s=60)` also supports temporary execution, embedding logs in its returned
receipt and labeling artifacts as unretained. `check_mapping()` runs only the
Python mapping comparison. `derive_target()` and `validate_target(target)`
provide the inventory API.

## What remains before a complete core

The supplied SRAM model has a synchronous read port, a write port, per-byte
write enables, old-data read/write collisions, and unspecified initial storage.
The ROM model has two asynchronous read ports and loads its constant contents
at simulation time zero. Physical SRAM mapping must preserve those contracts
or introduce checked scheduling changes. ROM realization must implement its
contents and read behavior; a simulation `readmemh` is not a physical ROM.

The current complete-core RTL fixes buffer depths, packed address slices,
accumulator organization, and ROM table dimensions. Reducing the workload's
sequence length does not shrink these structures. A smaller derivative needs
coordinated changes to configuration, packing, RTL dimensions/addressing,
reference outputs, and workload checks. This component makes no claim that a
minimum derivative has been found or that such changes are simple.

No compatible SRAM/ROM physical view set is selected here. Full-workload
correctness with actual wrappers, initialization, functional correspondence,
macro-aware constraints and timing coverage, floorplanning, routing, LVS,
connectivity, DRC, antenna, and electrical closure remain open. The existing
physical adapter is specific to the dequantizer and its supplementary timing
coverage path rejects macro configurations. Its block results cannot establish
complete-core acceptance.
