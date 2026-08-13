import marimo

__generated_with = "0.23.13"
app = marimo.App(width="medium")


@app.cell
def _():
    import io
    import json
    import sys
    import tempfile
    import zipfile
    from datetime import datetime, timezone
    from pathlib import Path
    from textwrap import dedent

    import marimo as mo

    # Make arch2_labs importable when run from anywhere.
    LABS_ROOT = Path(__file__).resolve().parents[2]
    if str(LABS_ROOT) not in sys.path:
        sys.path.insert(0, str(LABS_ROOT))

    from arch2_labs.scale_env import run_example
    from arch2_labs.decisions import record_human_decision
    from arch2_labs.presentation import (
        render_objective_summary,
        render_receipt_validation,
    )
    from arch2_labs.validators import validate_receipt

    return (
        Path,
        datetime,
        dedent,
        io,
        json,
        mo,
        record_human_decision,
        render_objective_summary,
        render_receipt_validation,
        run_example,
        tempfile,
        timezone,
        validate_receipt,
        zipfile,
    )


@app.cell
def _(dedent, mo):
    mo.md(
        dedent(
            """
    # Lab 06 · Proxy vs Evidence  ·  Chapter 5 (Method Roles)

    **You can, after this lab:** predict what a cheap proxy will say, run a real
    simulator, measure how far the proxy *overstated* the winner, inspect the
    evidence and rejection records, and record a decision that states its
    governing objective and owner.

    > **Architecture 2.0 recap.** A method's job inside the loop is a *role*:
    > generate, **predict**, optimize, critique. A cheap predictor (proxy) can
    > rank candidates fast, but its score is only a proxy. Stronger review can
    > become rejection-bound only when comparable admitted proposals arrive faster
    > than trusted dispositions. This four-candidate exercise does not measure
    > those rates; it tests whether stronger evidence changes what may advance.
    """
        ).strip()
    )
    return


@app.cell
def _(mo):
    retrieval = mo.ui.radio(
        options={
            "It is the final evidence; if it ranks a design first, ship it.": "wrong1",
            "It is a fast estimate whose ranking must be checked by stronger evidence before anyone acts on it.": "right",
            "It is only useful for energy, never for latency.": "wrong2",
        },
        label="**Warm-up (unlocks the lab).** What is a cheap proxy in an Architecture 2.0 loop?",
    )
    retrieval
    return (retrieval,)


@app.cell
def _(mo, retrieval):
    mo.stop(
        retrieval.value != "right",
        mo.md("🔒 *Pick the answer that matches the recap to continue.*"),
    )
    mo.md("✅ Right. A proxy ranks; it does not commit. Keep going.")
    warmup_unlocked = True
    return (warmup_unlocked,)


@app.cell
def _(dedent, mo, warmup_unlocked):
    assert warmup_unlocked
    mo.md(
        dedent(
            """
    ## The Study Brief

    - **Claim.** One accelerator configuration is worth advancing to a stronger
      study for this XR-like GEMM slice.
    - **Design space.** A systolic array of 8×8, 16×16, 32×32, or 64×64 PEs.
    - **Cheap proxy.** total MACs ÷ PE count (nominal throughput). It ranks the
      **64×64** first and implies it is **16× faster** than the 16×16.
    - **Stronger evidence.** SCALE-Sim: real cycles, utilization, memory traffic.
    - **Authorized next step.** Advance to a next-fidelity study only. No RTL,
      signoff, or product claim.
    """
        ).strip()
    )
    brief_ready = True
    return (brief_ready,)


@app.cell
def _(brief_ready, mo):
    assert brief_ready

    def _validate_prediction(value):
        if value is None or value.get("prediction") is None:
            return "Select a predicted SCALE-Sim speedup."
        if value.get("confidence") is None:
            return "Record your confidence before locking the prediction."
        if not str(value.get("reason", "")).strip():
            return "Name a mechanism that could make the proxy wrong."
        return None

    prediction_form = mo.ui.dictionary(
        {
            "prediction": mo.ui.dropdown(
                options=[
                    "About 16× (the proxy is right)",
                    "About 10–13× (a little less)",
                    "About 6–8× (much less than promised)",
                    "Under 2× (the proxy is badly wrong)",
                ],
                label="**Predict.** The proxy says the 64×64 is 16× faster than the 16×16. What will SCALE-Sim measure?",
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
                placeholder="One sentence: what mechanism might make the real speedup differ from 16×?",
                label="**Reason** (required)",
                rows=2,
            ),
        }
    ).form(
        submit_button_label="Lock my prediction",
        clear_on_submit=False,
        validate=_validate_prediction,
    )
    prediction_form
    return (prediction_form,)


@app.cell
def _(mo, prediction_form):
    mo.stop(
        prediction_form.value is None,
        mo.md("*Submit a prediction, confidence, and reason to continue.*"),
    )
    prediction_snapshot = dict(prediction_form.value)
    prediction_locked = True
    mo.md(
        f"Prediction locked at **{prediction_snapshot['confidence']}% confidence**. "
        "Now run the real simulator."
    )
    return prediction_locked, prediction_snapshot


@app.cell
def _(mo, prediction_locked, prediction_snapshot):
    assert prediction_locked and prediction_snapshot
    run = mo.ui.run_button(label="Run SCALE-Sim on all four arrays")
    run
    return (run,)


@app.cell
def _(Path, json, mo, prediction_snapshot, run, run_example, tempfile):
    assert prediction_snapshot
    mo.stop(not run.value, mo.md("*Click **Run** to execute the simulator.*"))

    _out = Path(tempfile.mkdtemp(prefix="arch2_proxy_")) / "run"
    summary = run_example("scale_proxy_mirage", _out, force=True)

    runs = [
        json.loads(line)
        for line in (_out / "runs.jsonl").read_text().splitlines()
        if line.strip()
    ]
    proxy_rows = {
        record["candidate_id"]: record
        for record in runs
        if record.get("stage") == "proxy"
    }
    sim_rows = {
        record["candidate_id"]: record
        for record in runs
        if record.get("stage") == "scalesim" and record.get("status") == "ok"
    }
    evidence_text = (_out / "evidence_record.json").read_text()
    evidence = json.loads(evidence_text)
    negative_traces = [
        json.loads(line)
        for line in (_out / "negative_traces.jsonl").read_text().splitlines()
        if line.strip()
    ]
    provenance_rows = []
    for record in runs:
        if record.get("stage") != "scalesim":
            continue
        tool = record.get("tool", {})
        inputs = record.get("inputs", {})
        outputs = record.get("outputs", {})
        provenance_rows.append(
            {
                "candidate": record["candidate_id"],
                "tool": f"{tool.get('name', 'unknown')} {tool.get('version', 'unknown')}",
                "status": record.get("status"),
                "command": " ".join(record.get("command", [])),
                "config_sha256": inputs.get("config_sha256", ""),
                "raw_files": len(outputs.get("raw_files", [])),
            }
        )

    card_text = (_out / "card.yaml").read_text()
    environment_text = (_out / "environment.yaml").read_text()
    manifest_text = (_out / "manifest.yaml").read_text()
    run_dir = _out
    run_complete = True
    mo.md(
        f"Ran **{len(sim_rows)} candidates**. Draft status: `{summary['status']}`. "
        f"Local run archive: `{run_dir}`."
    )
    return (
        card_text,
        environment_text,
        evidence,
        evidence_text,
        manifest_text,
        negative_traces,
        provenance_rows,
        proxy_rows,
        run_dir,
        run_complete,
        sim_rows,
    )


@app.cell
def _(mo, proxy_rows, run_complete, sim_rows):
    assert run_complete

    def _format_evidence():
        order = ["proxy_hero_64x64", "throughput_32x32", "balanced_16x16", "tiny_8x8"]
        rows = []
        for candidate_id in order:
            if candidate_id not in sim_rows:
                continue
            metrics = sim_rows[candidate_id]["metrics"]
            estimates = sim_rows[candidate_id]["estimates"]
            rows.append(
                {
                    "candidate": candidate_id,
                    "proxy_cycles": proxy_rows[candidate_id]["proxy_cycles"],
                    "sim_cycles": metrics["total_cycles"],
                    "min_util_%": round(metrics["min_layer_util_pct"], 1),
                    "energy_uJ": estimates["energy"]["e_total_uj"],
                    "roofline": estimates["roofline"]["bound"],
                }
            )
        return rows

    evidence_rows = _format_evidence()
    big = next(row for row in evidence_rows if row["candidate"] == "proxy_hero_64x64")
    small = next(row for row in evidence_rows if row["candidate"] == "balanced_16x16")
    proxy_ratio = round(small["proxy_cycles"] / big["proxy_cycles"], 1)
    real_ratio = round(small["sim_cycles"] / big["sim_cycles"], 1)

    mo.vstack(
        [
            mo.md("### The evidence"),
            mo.ui.table(evidence_rows, selection=None),
            mo.md(
                f"**Proxy promised {proxy_ratio}× speedup for the 64×64. "
                f"SCALE-Sim measured {real_ratio}×.** The proxy overstated by "
                f"about {round(proxy_ratio / real_ratio, 1)}×."
            ),
        ]
    )
    evidence_revealed = True
    return evidence_revealed, real_ratio


@app.cell
def _(evidence_revealed, mo, prediction_snapshot, real_ratio):
    assert evidence_revealed
    picked = prediction_snapshot["prediction"]
    close = "6–8×" in picked
    mo.md(
        f"""
        ### Compare Your Prediction With the Result

        You predicted **{picked}** at **{prediction_snapshot['confidence']}% confidence**.
        Your submitted mechanism was: *{prediction_snapshot['reason']}*

        SCALE-Sim measured about **{real_ratio}×**.
        {"Your predicted range matched the measured result." if close else "The realized speedup is far below the proxy's promise."}

        **The measured mechanism.** The proxy divides by PE *count*, which silently
        assumes every PE does useful work. A 64×64 array on a workload with a 32-row
        layer leaves rows idle, so mapping and utilization make the measured speedup a
        fraction of the proxy's promise. The roofline label is a separate analytic
        warning derived from access counts and declared bandwidth. SCALE-Sim 3.0.0 does
        not model bandwidth stalls in this configuration, so the label is not evidence
        that memory stalls caused the measured cycle gap.
        """
    )
    reconciliation_complete = True
    return (reconciliation_complete,)


@app.cell
def _(
    card_text,
    environment_text,
    evidence_text,
    manifest_text,
    mo,
    negative_traces,
    provenance_rows,
    reconciliation_complete,
):
    assert reconciliation_complete
    artifact_browser = mo.accordion(
        {
            "Design-loop card (v2 draft)": mo.md("```yaml\n" + card_text + "```"),
            "Environment contract": mo.md("```yaml\n" + environment_text + "```"),
            "Supporting evidence record": mo.md("```json\n" + evidence_text + "```"),
            "Rejected candidates and rejection checks": mo.ui.table(
                negative_traces, selection=None
            ),
            "Run provenance": mo.ui.table(provenance_rows, selection=None),
            "Hash-sealed draft manifest": mo.md("```yaml\n" + manifest_text + "```"),
        },
        multiple=False,
    )
    mo.vstack(
        [
            mo.md(
                "### Inspect the Run Archive Before Deciding\n\n"
                "Open each record. The card summarizes the claim, the evidence record states "
                "what each stage supports and omits, rejected-alternative records preserve "
                "declared rejections, provenance binds runs to inputs and outputs, and "
                "the manifest seals the draft."
            ),
            artifact_browser,
        ]
    )
    artifacts_revealed = True
    return (artifacts_revealed,)


@app.cell
def _(artifacts_revealed, evidence, mo, render_objective_summary):
    assert artifacts_revealed
    mo.md(render_objective_summary(evidence))
    decision_ready = True
    return (decision_ready,)


@app.cell
def _(decision_ready, evidence, mo):
    assert decision_ready
    eligible = [
        outcome["candidate_id"]
        for outcome in evidence["candidate_outcomes"]
        if outcome["accepted"]
    ]

    def _validate_decision(value):
        if value is None:
            return "Complete the decision record."
        required = [
            value.get("objective"),
            value.get("choice"),
            value.get("level"),
            str(value.get("human_owner", "")).strip(),
            str(value.get("rationale", "")).strip(),
            str(value.get("residual_risk", "")).strip(),
            str(value.get("would_overturn", "")).strip(),
        ]
        if not all(required):
            return "Complete every required decision field."
        expected_candidate = (
            evidence["objective_rankings"]
            .get(value["objective"], {})
            .get("candidate_id")
        )
        if value["level"] != "next_fidelity_study":
            return (
                "Proxy-plus-one-simulator evidence licenses only a next-fidelity study."
            )
        if value["choice"] != expected_candidate and not value["objective_override"]:
            return "Choose the objective winner among candidates that passed the checks, or state why you chose another one."
        if value["choice"] == expected_candidate and value["objective_override"]:
            return "An override is unnecessary when the choice already matches the objective winner."
        if (
            value["objective_override"]
            and not str(value.get("override_reason", "")).strip()
        ):
            return "Explain the human objective override."
        return None

    decision_form = mo.ui.dictionary(
        {
            "objective": mo.ui.dropdown(
                options={
                    "Minimize latency (take the fastest that fits the budget)": "latency_under_declared_gates",
                    "Minimize energy per inference": "energy_under_declared_gates",
                    "Maximize area efficiency (TOPS/mm²)": "area_efficiency_under_declared_gates",
                },
                label="**Decide.** Which objective governs this decision?",
            ),
            "choice": mo.ui.dropdown(
                options=eligible,
                label="**Human choice.** Which candidate that passed both checks do you select?",
            ),
            "level": mo.ui.dropdown(
                options={
                    "Advance to a next-fidelity study only": "next_fidelity_study",
                    "Advance to RTL": "advance_to_rtl",
                    "Ready for signoff / product": "ready_for_signoff",
                },
                label="**Authorized next step**",
            ),
            "human_owner": mo.ui.text(
                placeholder="Your name or review role",
                label="**Decision owner** (required)",
            ),
            "rationale": mo.ui.text_area(
                placeholder="Why does this candidate fit the governing objective and evidence?",
                label="**Rationale** (required)",
                rows=2,
            ),
            "objective_override": mo.ui.checkbox(
                value=False,
                label="**Override objective winner**",
            ),
            "override_reason": mo.ui.text_area(
                placeholder="Why does another check-passing candidate better serve the stated objective?",
                label="**Override reason** (required only for an override)",
                rows=2,
            ),
            "residual_risk": mo.ui.text_area(
                placeholder="What material uncertainty remains after this simulator run?",
                label="**Residual risk** (required)",
                rows=2,
            ),
            "would_overturn": mo.ui.text_area(
                placeholder="What new evidence would change your decision?",
                label="**Would overturn** (required)",
                rows=2,
            ),
        }
    ).form(
        submit_button_label="Record my decision",
        clear_on_submit=False,
        validate=_validate_decision,
    )
    decision_form
    return (decision_form,)


@app.cell
def _(
    datetime,
    decision_form,
    mo,
    run_dir,
    record_human_decision,
    render_receipt_validation,
    timezone,
    validate_receipt,
):
    mo.stop(
        decision_form.value is None,
        mo.md("*Complete and submit the decision record to continue.*"),
    )
    decision_snapshot = dict(decision_form.value)
    try:
        record_human_decision(
            run_dir,
            {
                "schema_version": "arch2-human-decision/v0.2",
                "lab_id": "scale_proxy_mirage",
                "human_owner": str(decision_snapshot["human_owner"]).strip(),
                "authored_at": datetime.now(timezone.utc).isoformat(),
                "selected_candidate_id": decision_snapshot["choice"],
                "governing_objective": decision_snapshot["objective"],
                "objective_override": decision_snapshot["objective_override"],
                "override_reason": str(
                    decision_snapshot.get("override_reason", "")
                ).strip()
                or None,
                "commitment_level": decision_snapshot["level"],
                "rationale": str(decision_snapshot["rationale"]).strip(),
                "residual_risk": str(decision_snapshot["residual_risk"]).strip(),
                "would_overturn": str(decision_snapshot["would_overturn"]).strip(),
            },
        )
        errors = validate_receipt(run_dir)
    except ValueError as exc:
        errors = [str(exc)]
    mo.stop(errors, mo.md(render_receipt_validation(errors)))
    mo.md(render_receipt_validation([]))
    decision_complete = True
    return (decision_complete,)


@app.cell
def _(decision_complete, io, mo, run_dir, validate_receipt, zipfile):
    assert decision_complete
    final_errors = validate_receipt(run_dir)
    mo.stop(final_errors, mo.md("The completed run archive no longer validates."))

    archive_buffer = io.BytesIO()
    with zipfile.ZipFile(archive_buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(run_dir.rglob("*")):
            if path.is_file() and not path.is_symlink():
                archive.write(
                    path,
                    arcname=(
                        "arch2-proxy-mirage-run/" + path.relative_to(run_dir).as_posix()
                    ),
                )
    run_archive = archive_buffer.getvalue()
    archive_download = mo.download(
        data=run_archive,
        filename="arch2-proxy-mirage-run.zip",
        mimetype="application/zip",
        label="Download complete run archive",
    )
    mo.vstack(
        [
            mo.md(
                "### Complete Run Archive\n\n"
                "The ZIP contains the card, environment contract, supporting evidence "
                "record, failed-run and rejected-alternative records, raw simulator "
                "reports, provenance, machine recommendation, decision record, "
                "and final hash-sealed manifest."
            ),
            archive_download,
        ]
    )
    archive_ready = True
    return (archive_ready,)


@app.cell
def _(archive_ready, dedent, mo):
    assert archive_ready
    reflection_form = mo.ui.text_area(
        label="**Reflect.** What is the smallest brief or evidence change that would flip your decision?",
        placeholder="Name the workload, budget, objective, or higher-fidelity result and how it changes the decision.",
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
    mo.vstack(
        [
            mo.md(
                dedent(
                    """
                ### Reflect

                The workload had a 32-row layer. If every layer were 64 rows or larger,
                would the 64×64's utilization gap close, and would the proxy's
                overstatement shrink?

                *SCALE-Sim 3.0.0 does not model bandwidth stalls in this configuration.
                This lab therefore teaches proxy overstatement through
                mapping/utilization and objective conflict. The roofline result is a
                separate analytic warning, not a causal explanation of the simulator's
                measured cycles.*
                """
                ).strip()
            ),
            reflection_form,
        ]
    )
    return (reflection_form,)


@app.cell
def _(mo, reflection_form):
    mo.stop(
        reflection_form.value is None,
        mo.md("*Submit the reflection to finish the activity.*"),
    )
    mo.md(
        "**Activity complete.** You submitted a prediction, inspected the evidence, recorded a decision, validated the run archive, and reflected on what could change the result."
    )
    return


if __name__ == "__main__":
    app.run()
