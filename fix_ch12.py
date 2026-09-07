import re

with open("book/contents/chapters/12-ecosystem/12-ecosystem.qmd", "r") as f:
    text = f.read()

target1 = r"Because the natural commercial instinct in electronic design automation (EDA) is to construct proprietary tool wrappers, vendors will not adopt open schema governance out of altruism. Their participation depends on an incentive structure where the threat of exclusion from multi-vendor, AI-native integration platforms outweighs the revenue preserved by proprietary lock-in. This shift requires major silicon buyers and foundry ecosystems to mandate OAI compliance as a condition of procurement, forcing toolmakers to compete on physical closure quality and engine runtime rather than on data-silo friction."
replacement1 = r"Historical CAD standards demonstrate that proprietary data silos create parsing drift and toolchain lock-in. Open schemas succeed when Tier-1 semiconductor design houses mandate open interchange standards (e.g., LEF/DEF, UPF, and SystemC) to integrate heterogeneous CAD flows, forcing toolmakers to compete on physical closure quality and engine runtime."
text = text.replace(target1, replacement1)

# Add footnote
target2 = r"If published models cannot distinguish fundamental physical limits from arbitrary heuristic thresholds, the surrogate foundation for AI-native architecture collapses."
replacement2 = r"If published models cannot distinguish fundamental physical limits from arbitrary heuristic thresholds, the surrogate foundation for AI-native architecture collapses.[^fn-huggingface-privacy-c12]"
footnote = r"""
[^fn-huggingface-privacy-c12]: **Precompetitive metadata sharing and model cards (ML ecosystem parallel)**: The machine-learning ecosystem overcame a similar data-sharing deadlock when enterprises and healthcare providers refused to disclose proprietary training corpora or patient records. Rather than demanding raw data sharing, the community standardized open evaluation harnesses, federated parameter updates, and Hugging Face model and dataset cards [@MitchellEtAl2019ModelCards]. These frameworks allow models to train on distributed, privacy-preserving gradient updates and share benchmark lineage without exposing sensitive underlying training artifacts. In semiconductor design, safe disclosure filters apply the same principle, converting proprietary GDSII/DEF layouts into normalized spatial graph embeddings and dimensionless slack distributions that train surrogates on physical failure boundaries without leaking proprietary transistor topologies or cell coordinates.
"""
text = text.replace(target2, replacement2)
if "[^fn-huggingface-privacy-c12]" in text and footnote.strip() not in text:
    text += "\n" + footnote.strip() + "\n"

with open("book/contents/chapters/12-ecosystem/12-ecosystem.qmd", "w") as f:
    f.write(text)
