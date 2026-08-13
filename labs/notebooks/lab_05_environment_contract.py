import marimo

__generated_with = "0.23.13"
app = marimo.App(width="medium")


@app.cell
def _():
    import hashlib
    import json
    import subprocess
    import sys
    import tempfile
    from pathlib import Path
    from textwrap import dedent

    import marimo as mo

    _source = Path(__file__).resolve()
    for _candidate_root in [_source.parent, *_source.parents]:
        if (_candidate_root / "arch2_labs").is_dir():
            if str(_candidate_root) not in sys.path:
                sys.path.insert(0, str(_candidate_root))
            break

    from arch2_labs.environment import (
        load_environment_contract,
        rejection_threshold,
        validate_action,
    )
    from arch2_labs.scale_env import assess_candidate, example_dir, run_scalesim
    from arch2_labs.schemas import Candidate, load_candidates

    return (
        Candidate,
        Path,
        assess_candidate,
        dedent,
        example_dir,
        hashlib,
        json,
        load_candidates,
        load_environment_contract,
        mo,
        rejection_threshold,
        run_scalesim,
        subprocess,
        tempfile,
        validate_action,
    )


@app.cell
def _(dedent, mo):
    mo.md(
        dedent(
            r"""
        # Lab 05 | The Environment Contract | Chapter 6

        **You can, after this lab:** submit a frozen action to the checked-in SCALE-Sim
        environment contract, distinguish an environment refusal from a tool failure and a
        candidate rejection, and inspect the provenance returned by an actual tool run.

        > **Recap.** A tool becomes an environment when it declares legal actions,
        > observations, invalid-action semantics, cost, provenance, and rejection authority.
        > Refusing an undeclared action protects the action boundary. A tool failure is an
        > environment trace to diagnose. A candidate rejection requires a declared check that
        > applies to the candidate and its observations.
        """
        ).strip()
    )
    return


@app.cell
def _(mo):
    warmup = mo.ui.radio(
        options={
            "Any program a method can call.": "wrong",
            "A tool with declared actions, observations, refusal semantics, provenance, and rejection authority.": "right",
            "A simulator with a short runtime.": "wrong2",
        },
        label="**Warm-up (unlocks the lab).** What makes a tool an environment?",
    )
    warmup
    return (warmup,)


@app.cell
def _(mo, warmup):
    mo.stop(warmup.value != "right", mo.md("Locked. Match the recap to continue."))
    mo.md("The contract owns the boundary. Load it before proposing an action.")
    warmup_unlocked = True
    return (warmup_unlocked,)


@app.cell
def _(
    example_dir,
    hashlib,
    load_candidates,
    load_environment_contract,
    mo,
    warmup_unlocked,
):
    assert warmup_unlocked
    example_root = example_dir("scale_proxy_mirage")
    environment_path = example_root / "starter_receipt" / "environment.yaml"
    environment_contract = load_environment_contract(environment_path)
    example_spec = load_candidates(
        example_root / "configs" / "candidates.yaml", example_root
    )
    contract_topology = (
        example_root / environment_contract["provenance"]["topology"]
    ).resolve()
    contract_layout = (
        example_root / environment_contract["provenance"]["layout"]
    ).resolve()
    if example_spec.topology.resolve() != contract_topology:
        raise ValueError(
            "candidate specification and environment contract disagree on topology"
        )
    if example_spec.layout.resolve() != contract_layout:
        raise ValueError(
            "candidate specification and environment contract disagree on layout"
        )
    contract_sha256 = hashlib.sha256(environment_path.read_bytes()).hexdigest()
    action_rows = "\n".join(
        f"- `{field}`: {', '.join(str(value) for value in values)}"
        for field, values in environment_contract["legal_actions"].items()
    )
    observation_rows = "\n".join(
        f"- **{stage}:** {', '.join(values)}"
        for stage, values in environment_contract["observations"].items()
    )
    check_rows = "\n".join(
        f"- `{entry['gate']}` at `{entry['threshold']}`"
        for entry in environment_contract["rejection_authority"]
    )
    mo.md(
        f"""
        ## Loaded contract

        Source: `{environment_path}`
        SHA-256: `{contract_sha256}`

        **Legal action fields**

        {action_rows}

        **Observations**

        {observation_rows}

        **Candidate rejection authority**

        {check_rows}

        The action validator below reads this object. The notebook does not maintain a
        second copy of the legal sets or rejection thresholds.
        """
    )
    contract_ready = True
    return (
        contract_ready,
        contract_layout,
        contract_sha256,
        contract_topology,
        environment_contract,
        environment_path,
        example_spec,
    )


@app.cell
def _(contract_ready, environment_contract, mo):
    assert contract_ready
    legal_actions = environment_contract["legal_actions"]
    row_options = [*legal_actions["array_rows"], max(legal_actions["array_rows"]) * 2]
    col_options = [*legal_actions["array_cols"], max(legal_actions["array_cols"]) * 2]
    dataflow_options = [*legal_actions["dataflow"], "os"]

    def _validate_prediction(value):
        if value is None or value.get("prediction") is None:
            return "Predict whether the configured action will be accepted."
        if value.get("confidence") is None:
            return "Record your confidence before locking the action."
        if not str(value.get("reason", "")).strip():
            return "Give one reason tied to the loaded contract."
        return None

    action_prediction_form = mo.ui.dictionary(
        {
            "array_rows": mo.ui.dropdown(
                options=row_options,
                value=32,
                label="**array_rows**",
            ),
            "array_cols": mo.ui.dropdown(
                options=col_options,
                value=32,
                label="**array_cols**",
            ),
            "dataflow": mo.ui.dropdown(
                options=dataflow_options,
                value=legal_actions["dataflow"][0],
                label="**dataflow**",
            ),
            "prediction": mo.ui.radio(
                options={
                    "The environment accepts the action.": "accepted",
                    "The environment refuses the action before running the tool.": "refused",
                },
                label="**Predict.** What will the loaded action contract do?",
            ),
            "confidence": mo.ui.dropdown(
                options={
                    "Low (25%)": 25,
                    "Medium (50%)": 50,
                    "High (75%)": 75,
                    "Very high (100%)": 100,
                },
                label="**Confidence** (required)",
            ),
            "reason": mo.ui.text_area(
                label="**Reason** (required)",
                rows=2,
                placeholder="Name the contract field that decides acceptance.",
            ),
        }
    ).form(
        submit_button_label="Lock action and prediction",
        clear_on_submit=False,
        validate=_validate_prediction,
    )
    action_prediction_form
    return (action_prediction_form,)


@app.cell
def _(action_prediction_form, environment_contract, mo):
    mo.stop(
        action_prediction_form.value is None,
        mo.md("Submit one frozen action, prediction, confidence, and reason."),
    )
    submitted = dict(action_prediction_form.value)
    prediction_snapshot = {
        "prediction": submitted["prediction"],
        "confidence": submitted["confidence"],
        "reason": submitted["reason"].strip(),
        "action": {
            "array_rows": submitted["array_rows"],
            "array_cols": submitted["array_cols"],
            "dataflow": submitted["dataflow"],
            "sram_kb_each": environment_contract["legal_actions"]["sram_kb_each"][0],
            "dram_bandwidth_words_per_cycle": environment_contract["legal_actions"][
                "dram_bandwidth_words_per_cycle"
            ][0],
        },
    }
    mo.md(
        f"Action and prediction locked at **{prediction_snapshot['confidence']}% confidence**."
    )
    return (prediction_snapshot,)


@app.cell
def _(environment_contract, mo, prediction_snapshot, validate_action):
    action_violations = validate_action(
        environment_contract, prediction_snapshot["action"]
    )
    action_legal = not action_violations
    predicted_legal = prediction_snapshot["prediction"] == "accepted"
    if action_legal:
        response = "Accepted. The action is inside every declared legal set."
    else:
        response = "Refused before tool execution: " + "; ".join(action_violations)
    calibration = (
        "Your prediction matched the contract."
        if predicted_legal == action_legal
        else "Compare your prediction with the loaded legal-action sets."
    )
    mo.md(
        f"""
        ### Environment response

        **{response}**

        {calibration}

        An environment refusal says the proposed action is outside the action contract. It
        is not a simulator failure and not a candidate rejection.
        """
    )
    assessment_revealed = True
    return action_legal, action_violations, assessment_revealed


@app.cell
def _(action_legal, assessment_revealed, mo):
    assert assessment_revealed
    execute_action = mo.ui.run_button(
        label=(
            "Run the accepted action in SCALE-Sim"
            if action_legal
            else "Record the environment refusal"
        )
    )
    execute_action
    return (execute_action,)


@app.cell
def _(
    Candidate,
    Path,
    action_legal,
    action_violations,
    assess_candidate,
    contract_layout,
    contract_topology,
    environment_contract,
    example_spec,
    execute_action,
    mo,
    prediction_snapshot,
    rejection_threshold,
    run_scalesim,
    subprocess,
    tempfile,
):
    mo.stop(not execute_action.value, mo.md("Execute or record the submitted action."))
    if not action_legal:
        outcome_record = {
            "kind": "environment_refusal",
            "status": "refused",
            "action": prediction_snapshot["action"],
            "violations": action_violations,
            "tool_invoked": False,
            "provenance": None,
            "candidate_rejection": None,
        }
    else:
        baseline = next(
            candidate
            for candidate in example_spec.candidates
            if candidate.candidate_id == example_spec.baseline_id
        )
        submitted_action = prediction_snapshot["action"]
        candidate = Candidate(
            candidate_id=(
                f"lab05_{submitted_action['array_rows']}x{submitted_action['array_cols']}_"
                f"{submitted_action['dataflow']}"
            ),
            label="Lab 05 submitted action",
            source="learner-submitted environment action",
            array_rows=int(submitted_action["array_rows"]),
            array_cols=int(submitted_action["array_cols"]),
            dataflow=str(submitted_action["dataflow"]),
            sram_kb=int(submitted_action["sram_kb_each"]),
            dram_bandwidth_words_per_cycle=int(
                submitted_action["dram_bandwidth_words_per_cycle"]
            ),
            clock_mhz=baseline.clock_mhz,
            area_budget_pes=int(
                rejection_threshold(environment_contract, "area_budget_pes")
            ),
            deadline_cycles=int(
                rejection_threshold(environment_contract, "deadline_cycles")
            ),
            min_layer_util_pct=baseline.min_layer_util_pct,
        )
        run_dir = (
            Path(tempfile.mkdtemp(prefix="arch2_environment_")) / candidate.candidate_id
        )
        try:
            tool_record = run_scalesim(
                candidate,
                contract_topology,
                contract_layout,
                run_dir,
            )
            _provenance_record = {
                "command": tool_record["command"],
                "tool": tool_record["tool"],
                "runtime": tool_record["runtime"],
                "inputs": tool_record["inputs"],
                "outputs": tool_record["outputs"],
            }
            if tool_record["status"] != "ok":
                outcome_record = {
                    "kind": "tool_failure",
                    "status": tool_record["status"],
                    "action": submitted_action,
                    "tool_invoked": True,
                    "returncode": tool_record["returncode"],
                    "stderr_tail": tool_record["stderr_tail"],
                    "provenance": _provenance_record,
                    "candidate_rejection": None,
                }
            else:
                accepted, _candidate_rejection = assess_candidate(
                    candidate, tool_record["metrics"]
                )
                outcome_record = {
                    "kind": (
                        "accepted_observation" if accepted else "candidate_rejection"
                    ),
                    "status": "ok",
                    "action": submitted_action,
                    "tool_invoked": True,
                    "metrics": tool_record["metrics"],
                    "provenance": _provenance_record,
                    "candidate_rejection": _candidate_rejection,
                }
        except (OSError, subprocess.TimeoutExpired) as error:
            outcome_record = {
                "kind": "tool_failure",
                "status": "exception",
                "action": submitted_action,
                "tool_invoked": True,
                "error": f"{type(error).__name__}: {error}",
                "provenance": None,
                "candidate_rejection": None,
            }
    mo.md(f"Outcome recorded as **`{outcome_record['kind']}`**.")
    return (outcome_record,)


@app.cell
def _(mo, outcome_record):
    outcome_kind = outcome_record["kind"]
    if outcome_kind == "environment_refusal":
        detail = (
            "The tool was not invoked. The refusal is an invalid-action record: "
            + "; ".join(outcome_record["violations"])
        )
        provenance_text = "No tool provenance exists because execution was refused."
    elif outcome_kind == "tool_failure":
        detail = (
            "The action was legal, but the tool did not return a usable observation. "
            "Diagnose the environment before assigning candidate blame."
        )
        provenance_text = (
            "A partial provenance record is preserved below."
            if outcome_record.get("provenance")
            else "The failure occurred before a complete provenance record was available."
        )
    elif outcome_kind == "candidate_rejection":
        _rejection_detail = outcome_record["candidate_rejection"]
        detail = (
            f"The tool returned observations, then the `{_rejection_detail['gate']}` check rejected the "
            f"candidate at {_rejection_detail['observed']} versus threshold {_rejection_detail['threshold']}."
        )
        provenance_text = "The complete tool provenance is preserved below."
    else:
        detail = "The legal action produced observations and passed the declared rejection checks."
        provenance_text = "The complete tool provenance is preserved below."

    _display_provenance = outcome_record.get("provenance")
    if _display_provenance:
        input_hashes = "\n".join(
            f"- `{field}`: `{value}`"
            for field, value in _display_provenance["inputs"].items()
            if field.endswith("_sha256")
        )
        raw_files = _display_provenance["outputs"].get("raw_files", [])
        actual_provenance = f"""
        - **Tool:** `{_display_provenance['tool']['name']} {_display_provenance['tool']['version']}`
        - **Runtime:** Python `{_display_provenance['runtime']['python']}` at `{_display_provenance['runtime']['executable']}`
        - **Command:** `{' '.join(str(part) for part in _display_provenance['command'])}`
        - **Raw output files with hashes:** {len(raw_files)}

        **Input hashes**

        {input_hashes}
        """
    else:
        actual_provenance = "- No tool record."

    mo.md(
        f"""
        ### Outcome and actual provenance

        {detail}

        {provenance_text}

        {actual_provenance}

        | **Disposition** | **Meaning** |
        | --- | --- |
        | Environment refusal | Proposed action is outside the declared action contract; tool not invoked. |
        | Tool failure | Legal action did not yield a usable observation; diagnose the environment. |
        | Candidate rejection | A declared rejection check excludes the candidate using applicable state or observations. |
        """
    )
    outcome_revealed = True
    return (outcome_revealed,)


@app.cell
def _(mo, outcome_record, outcome_revealed):
    assert outcome_revealed
    expected_commitment = {
        "environment_refusal": "Record an environment refusal; revise the action or contract before any tool run.",
        "tool_failure": "Record a tool failure; diagnose the environment before judging the candidate.",
        "candidate_rejection": "Record a candidate rejection under the named check; do not promote the candidate.",
        "accepted_observation": "Record an accepted observation; it supports this bounded simulation result, not RTL or product commitment.",
    }[outcome_record["kind"]]

    def _validate_commitment(value):
        if value is None:
            return "Choose the disposition supported by this outcome."
        return None

    commitment_form = mo.ui.dropdown(
        options=[
            expected_commitment,
            "Treat every failed execution as a candidate rejection.",
            "Advance to RTL because the environment returned or refused a number.",
        ],
        label="**Commit.** What may this outcome authorize?",
    ).form(
        submit_button_label="Record disposition",
        clear_on_submit=False,
        validate=_validate_commitment,
    )
    commitment_form
    return commitment_form, expected_commitment


@app.cell
def _(commitment_form, expected_commitment, mo):
    mo.stop(
        commitment_form.value is None,
        mo.md("Choose and submit a disposition."),
    )
    mo.stop(
        commitment_form.value != expected_commitment,
        mo.md(
            "That disposition collapses action refusal, tool health, candidate validity, "
            "or commitment. Keep those judgments separate."
        ),
    )
    commitment_snapshot = commitment_form.value
    mo.md("Disposition recorded at the boundary supported by the actual outcome.")
    return (commitment_snapshot,)


@app.cell
def _(
    commitment_snapshot,
    contract_sha256,
    environment_contract,
    environment_path,
    json,
    mo,
    outcome_record,
    prediction_snapshot,
):
    environment_record = {
        "schema_version": "arch2-environment-action-audit/v0.1",
        "lab_id": "lab_05_environment_contract",
        "environment_contract": {
            "source": environment_path.name,
            "sha256": contract_sha256,
            "schema_version": environment_contract["schema_version"],
        },
        "prediction": prediction_snapshot,
        "outcome": outcome_record,
        "human_disposition": commitment_snapshot,
    }
    record_bytes = (
        json.dumps(environment_record, indent=2, sort_keys=True) + "\n"
    ).encode()
    mo.vstack(
        [
            mo.md(
                "### Environment action record\n\nThe download binds the submitted action and prediction to the canonical contract, actual outcome, provenance, and disposition."
            ),
            mo.download(
                data=record_bytes,
                filename="lab_05_environment_action_record.json",
                mimetype="application/json",
                label="Download environment action record",
            ),
        ]
    )
    artifact_ready = True
    return (artifact_ready,)


@app.cell
def _(artifact_ready, mo):
    assert artifact_ready
    reflection_form = mo.ui.text_area(
        label="**Reflect.** Which outcome boundary is easiest to blur in your own tool wrapper, and what record would keep it explicit?",
        placeholder="Choose refusal, tool failure, or candidate rejection and name the required record.",
        rows=3,
    ).form(
        submit_button_label="Record reflection",
        clear_on_submit=False,
        validate=lambda value: (
            None
            if value is not None and str(value).strip()
            else "Write one reflection."
        ),
    )
    reflection_form
    return (reflection_form,)


@app.cell
def _(mo, reflection_form):
    mo.stop(
        reflection_form.value is None,
        mo.md("Submit the reflection to finish the activity."),
    )
    mo.md(
        "Activity complete. The environment boundary and the candidate decision remained separately auditable."
    )
    return


if __name__ == "__main__":
    app.run()
