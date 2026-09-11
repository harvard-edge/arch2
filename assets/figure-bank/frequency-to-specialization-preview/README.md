# Frequency-to-specialization preview

A standalone proposal; the manuscript and its historical CPU values are unchanged.

## Scope

CPU curves reproduce the current Chapter 2 figure at dev commit 2d0dca23. They are the existing four-year interval maxima through 2021, not newly audited or extended CPU data. GPU points are selected NVIDIA generations, not cross-vendor market maxima. All GPU transistor counts exclude HBM; Blackwell totals two logic dies. Dotted lines connect observed specification points, not projections or fits. Era boundaries remain approximate.

The lower panel plots vendor peak dense FP16 Tensor throughput per SXM GPU, not measured workload performance, energy efficiency, CPU SPEC performance, or proof that gains come from specialization alone. It does not mix FP8/FP4 or sparse throughput into FP16. Announcement/introduction years index product generations; current specifications were accessed 2026-09-11. No Rubin preliminary specification is included.

## Primary sources and arithmetic

- V100 transistor count and Tensor operation definition: https://www.nvidia.com/content/dam/en-zz/Solutions/Data-Center/tesla-product-literature/volta-architecture-whitepaper.pdf
- V100 and A100 dense FP16 peaks, and A100 54.2 billion transistors: https://developer.nvidia.com/blog/nvidia-ampere-architecture-in-depth/
- A100 dense 312 TFLOP/s independently explicit in vendor guidance: https://docs.nvidia.com/deeplearning/performance/dl-performance-gpu-background/index.html
- H100 80 billion transistors: https://developer.nvidia.com/blog/nvidia-hopper-architecture-in-depth/
- H100 SXM published 1,979 sparse FP16 TFLOP/s: https://www.nvidia.com/en-us/data-center/h100/ . Divide by two to obtain 989.5, displayed approximately 990 because the published specification is rounded.
- Blackwell 208 billion transistors across two logic dies: https://www.nvidia.com/en-us/data-center/technologies/blackwell-architecture/
- Blackwell Ultra two-die organization: https://developer.nvidia.com/blog/inside-nvidia-blackwell-ultra-the-chip-powering-the-ai-factory-era/
- B200/B300 HGX each list 36 sparse FP16 PFLOP/s across eight GPUs; dense is half: https://www.nvidia.com/en-us/data-center/hgx/ . 36,000 / 8 / 2 = 2,250 dense TFLOP/s per GPU.

## Proposed caption

**Frequency scaling stalls while specialized compute keeps expanding.** (a) Historical CPU interval maxima retain the original units and colors; purple dotted diamonds add selected GPU transistor counts through 2025. Blackwell counts combine two logic dies. (b) Published dense FP16 Tensor throughput for selected NVIDIA SXM GPUs, shown separately from CPU SPEC performance. These are peak specifications, not measured application speedups.

## Reproduction

Run make_preview.py. The local cpu-series.py snapshot preserves the historical points; accelerators.csv records each new value, derivation, and source. SVG, vector PDF, and 300 dpi PNG are emitted together. This preview has been visually inspected; it is not integrated into the book.
