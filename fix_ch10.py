import re

with open("book/contents/chapters/10-evaluation/10-evaluation.qmd", "r") as f:
    text = f.read()

target1 = r"If different engineering teams are deployed, their experience is matched and remaining skill gaps are reported. Both arms receive a declared familiarization period and stable operating procedure, separating setup time from measured task duration. If exposure to the first arm reveals critical design insights that would advantage the second, fresh tasks, a washout period, or carryover modeling must be applied. When generated artifacts reveal their origin through distinct coding styles or structural quirks, the study records leaked cues, unblinded judgments, reviewer agreement rates, and final adjudication procedures."
replacement1 = r"If different engineering teams are deployed, their experience is matched through equal domain expertise and identical initial design specifications. Both arms receive a declared stabilization period, separating environment setup from measured task duration. Evaluator-blinded RTL inspections and held-out benchmark task suites prevent design insights from advantaging subsequent runs. When generated artifacts reveal their origin through distinct coding styles, the study logs leaked cues and final reviewer adjudication."
text = text.replace(target1, replacement1)

target2 = r"Tracking these measurements reveals whether AI integrations reduced raw engineering work, shifted that burden into review and repair phases, or amplified the effectiveness of expert intervention."
replacement2 = r"Tracking these measurements reveals whether AI integrations reduced raw engineering work, or simply shifted the burden into developing prompts, resolving SVA violations, manually drafting ECOs, and correcting unroutable pin placements."
text = text.replace(target2, replacement2)

target3 = r"The true economic cost often shifts to unmeasured human friction: prompt reengineering, constraint repair, triage of hallucinated netlists, and data pipeline maintenance. Whether nonintrusive developer telemetry can quantify the cognitive overhead of reviewing automated proposals honestly remains an open engineering management challenge."
replacement3 = r"The true economic cost often shifts to unmeasured human intervention: prompt reengineering, resolving SVA violations, triage of hallucinated netlists, and data pipeline maintenance. Whether telemetry can accurately quantify the engineering hours spent manually correcting automated proposals remains an open evaluation challenge."
text = text.replace(target3, replacement3)

with open("book/contents/chapters/10-evaluation/10-evaluation.qmd", "w") as f:
    f.write(text)
