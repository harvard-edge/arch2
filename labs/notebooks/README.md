# Architecture 2.0 Chapter Activities

The sequence follows the book from the moonshot prompt to architect-owned
commitment. Each activity provides selected practice with one or more parts of
a bounded architecture study and can also run independently from its chapter
recap. The activities use a deterministic execution path. They do not form a
live-AI comparison or assess the whole Architecture 2.0 discipline.

## Activity Map

| **Lab** | **Chapter and activity** | **Form** | **Typical time** | **Learner artifact** |
| --- | --- | --- | ---: | --- |
| [01](lab_01_prompt_to_card.py) | Ch1, Prompt to Card | reasoning | 20 min | Four-field context sketch with an explicit commitment limit |
| [02](lab_02_scissors_gap.py) | Ch2, Scissors Gap | data | 20 min | Queue and disposition diagnosis with an intervention choice |
| [03](lab_03_score_a_claim.py) | Ch3, Score a Claim | audit | 20 min | Claim-review record naming missing evidence and rejection conditions |
| [04](lab_04_represent_and_replay.py) | Ch4, Represent and Replay | simulator audit | 25 min | Replayability audit of a generated draft run archive |
| [05](lab_05_environment_contract.py) | Ch6, Environment Contract | simulator | 25 min | Legal or refused action plus a provenance-bearing environment record |
| [06](../examples/scale_proxy_mirage/lab.py) | Ch5, Proxy Versus Evidence | simulator anchor | 45 min | Completed and validated run archive with a recorded decision |
| [07](lab_07_earned_trust.py) | Ch7, Earned Trust | simulator red team | 30 min | Orthogonal feasibility check for an environment blind spot |
| [08](lab_08_run_the_loop.py) | Ch8, Run the Loop | simulator integration study | 45 min | Completed run archive and limited decision |
| [09](lab_09_same_loop_different_costs.py) | Ch9, Same Loop at Different Costs | feedback-budget exercise | 25 min | Budget-allocation audit and cheap-first rejection decision |
| [10](lab_10_own_the_commitment.py) | Ch11, Own the Commitment | public-record audit | 30 min | Shareable Architecture 2.0 claim audit with a bounded conclusion |

The full sequence takes about four and three-quarters hours. Labs 01, 06, and 08
form a coherent two-hour introduction when time is limited.

## Backward-Design Capability Map

The six capabilities are longitudinal outcomes, not six stages or one lab per
verb. The map below identifies observable guided practice in the current suite.
It does not claim independent mastery.

| **Capability** | **Primary practice** | **Observable learner artifact** | **Current boundary** |
| --- | --- | --- | --- |
| **Formulate** | Lab 01, supported by the diagnostic audit in Lab 03 | Four-field study sketch and a claim-review record that identifies missing formulation evidence. | The learner does not independently bound a new end-to-end study. |
| **Explore** | Labs 05, 06, and 09 | Submitted legal action, comparison of declared candidates, rejected-candidate records, and feedback-budget allocation. | The candidate families and methods are supplied; the suite does not compare a live AI method with a conventional baseline. |
| **Implement** | Labs 04, 05, 06, and 08 | Replay bindings, executable configuration, tool-produced reports, and validated run archive. | The learner connects artifacts to an existing wrapper rather than building a new tool path, compiler change, or RTL artifact. |
| **Evaluate** | Labs 03 through 10, with process diagnosis in Lab 02 | Rate diagnosis, claim audit, evidence packet, rejection-check results, provenance, and scoped evaluation record. | Most tasks use one compact workload and one simulator, so broader workload and fidelity claims remain outside scope. |
| **Explain** | Labs 06 and 07 | Mechanism prediction, reconciliation with measured utilization, and a separate analytic feasibility check with shared inputs disclosed. | The mechanism tests are guided; the learner does not design a new sensitivity, intervention, or ablation. |
| **Defend** | Labs 01, 03, and 05 through 10 | Bounded disposition or decision with rationale, ownership, residual risk, and reversal conditions. | The record is self-authored but is not defended under independent challenge. |

The summative transfer capstone is the new-problem study defined in Chapter 11,
not Lab 08. It requires a study brief, meaningful alternatives, a method
rationale, a checkable artifact and tool path, an evaluation packet, a tested
mechanism explanation, and a bounded decision defended under independent
challenge. A future matched-budget role-swap activity could compare an AI
generator or critic with a deterministic or no-AI baseline under the same tool
contract. That comparison is not part of the current suite.

## Learning Contract

The activities use the same teaching structure so learners must predict before
they see a result:

1. Retrieve the chapter's key distinction.
2. Submit a prediction with confidence and a reason.
3. Run or audit externally inspectable evidence.
4. Compare the prediction with the result and explain any mismatch.
5. State a bounded rejection, escalation, or commitment.
6. Inspect or download the chapter-appropriate record.
7. Transfer the lesson to another architecture problem.

The downloadable record captures steps 2 through 6. The transfer reflection in
step 7 is required in the interactive session but is not yet included in the
download, so it is formative unless an instructor collects it separately.

Hard rejection criteria are declared constraints such as a silicon budget or
deadline. The machine card stores each pass/fail check under the schema key
`gates`; the term does not refer to a workflow stage or a general quality goal.
Utilization, roofline position, and similar signals remain diagnostics unless a
separate validated rule grants them rejection authority. A tool failure remains
an environment failure unless the declared contract says otherwise.

## Running Activities

From `labs/`:

```bash
../.venv/bin/marimo edit notebooks/lab_03_score_a_claim.py
../.venv/bin/marimo run notebooks/lab_03_score_a_claim.py
```

Use edit mode for self-paced work and run mode for a read-only classroom app.
The simulator-backed activities can take longer on the first run while Python
loads SCALE-Sim.
