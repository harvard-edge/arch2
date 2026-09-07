import re

with open("book/contents/chapters/03-lifecycle/03-lifecycle.qmd", "r") as f:
    text = f.read()

target1 = r"Because each failure mode requires a different engineering repair, and defect remediation costs escalate by orders of magnitude when errors escape downstream into physical synthesis or mask fabrication, the AI-native design system must partition exploration into isolated failure domains \[\@NASA2017SystemsEngineeringHandbook\]\. Six life-cycle responsibilities carry that partition: \*Formulate\*, \*Explore\*, \*Implement\*, \*Evaluate\*, \*Interpret\*, and \*Commit\*\. Rather than marching through an inflexible waterfall pipeline, the life cycle supports error-isolated paths, including feedback-driven returns to the responsibility that owns an inadequate result\."
replacement1 = r"Because each failure mode requires a different engineering repair, and defect remediation costs escalate by orders of magnitude when errors escape downstream into physical synthesis or mask fabrication, the AI-native design system partitions exploration into isolated failure domains. Six life-cycle responsibilities carry that partition: *Formulate*, *Explore*, *Implement*, *Evaluate*, *Interpret*, and *Commit*. The life cycle explicitly supports error-isolated paths, including feedback-driven returns to the responsibility that owns an inadequate result."
text = text.replace(target1, replacement1)

target2 = r"A milestone check judges an artifact at a point in the schedule, whereas a stage boundary judges the reasoning that produced it, so a violation surfaced at timing signoff can be routed to the question, the candidate, the tool run, or the measurement that owns it rather than to the milestone that happened to expose it\."
replacement2 = r"A traditional milestone check merely inspects an artifact at a scheduled calendar date, whereas a life-cycle stage boundary diagnoses the root-cause parameter, constraint, or tool configuration that induced the defect. A violation surfaced at timing signoff can therefore be routed to the question, the candidate, the tool run, or the measurement that owns it rather than to the milestone that happened to expose it."
text = text.replace(target2, replacement2)

target3 = r"Four precise terms distinguish the complete discipline from the parts that repeat across iterations\.\n\n- \*\*Life cycle:\*\* The complete six-stage ontology connecting high-level specification to physical tapeout commitment\.\n- \*\*Scoped study:\*\* A bounded architectural question answered by executing the life cycle once across a defined set of candidate designs\.\n- \*\*Design loop:\*\* An adaptive execution of the study that mutates candidates in response to tool feedback rather than merely sweeping a static set\.\n- \*\*Study record:\*\* The structured history of candidates, runs, and decisions produced during a scoped study\."
replacement3 = r"A static architectural sweep systematically explores a bounded parameter space, while an adaptive, feedback-driven design loop actively mutates candidates in response to downstream verification failures. Both approaches depend on a structured study record to preserve provenance across iterations."
text = text.replace(target3, replacement3)

with open("book/contents/chapters/03-lifecycle/03-lifecycle.qmd", "w") as f:
    f.write(text)
