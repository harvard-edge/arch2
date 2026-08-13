import marimo

__generated_with = "0.23.13"
app = marimo.App(width="medium")


@app.cell
def _():
    import hashlib
    import json
    from pathlib import Path
    from textwrap import dedent

    import marimo as mo

    return Path, dedent, hashlib, json, mo


@app.cell
def _(dedent, mo):
    mo.md(
        dedent(
            """
        # Lab 10 · Own the Commitment: Audit a Public Record · Chapter 11

        **You can, after this lab:** inspect all twelve canonical design-loop card
        fields for a fixed public-record snapshot, locate the fields that limit public
        adjudication, and set a commitment boundary without treating missing disclosure
        as proof that internal work did not exist.

        > **Recap.** The design-loop card localizes what a claim packet carries. It
        > does not force proprietary disclosure and does not decide whether a result is
        > true or false. The architect owns the boundary between what the disclosed
        > evidence supports and what remains outside public audit.
        """
        ).strip()
    )
    return


@app.cell
def _(mo):
    warmup = mo.ui.radio(
        options={
            "A field marked absent proves the original team never had that process internally.": "absence",
            "A field status describes what traveled in the cited public record, not everything the team did internally.": "right",
            "A public card automatically settles a disputed technical claim.": "settles",
        },
        label="**Warm-up.** What does an absent field mean in this audit?",
    )
    warmup
    return (warmup,)


@app.cell
def _(mo, warmup):
    mo.stop(
        warmup.value != "right",
        mo.md(
            "*Distinguish the public claim packet from the team's internal process.*"
        ),
    )
    mo.md(
        "This activity audits a fixed, cited Chapter 8 snapshot. It does not perform "
        "a new reassessment of AlphaChip."
    )
    warmup_unlocked = True
    return (warmup_unlocked,)


@app.cell
def _(mo, warmup_unlocked):
    assert warmup_unlocked

    def validate_prediction(value):
        if value is None or value.get("choice") is None:
            return "Choose the field cluster you expect to limit public adjudication."
        if value.get("confidence") is None:
            return "Record your confidence."
        if not str(value.get("reason", "")).strip():
            return "Explain why that cluster is load-bearing."
        return None

    prediction_form = mo.ui.dictionary(
        {
            "choice": mo.ui.dropdown(
                options={
                    "Intent, task, representation, and method role": "generation_side",
                    "Environment, feedback budget, evidence, and shared rejection authority": "public_adjudication",
                    "The project title and publication venue": "metadata",
                },
                label="**Predict.** Which field cluster most limits public adjudication in the Chapter 8 snapshot?",
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
                placeholder="Why would this cluster prevent an outside reviewer from settling the strongest claim?",
                rows=2,
            ),
        }
    ).form(
        submit_button_label="Lock my prediction",
        clear_on_submit=False,
        validate=validate_prediction,
    )
    prediction_form
    return (prediction_form,)


@app.cell
def _(mo, prediction_form):
    mo.stop(
        prediction_form.value is None,
        mo.md(
            "*Submit a prediction, confidence, and reason to reveal the sourced card.*"
        ),
    )
    prediction_snapshot = dict(prediction_form.value)
    mo.md(
        f"Prediction locked at **{prediction_snapshot['confidence']}% confidence**. "
        "Now inspect every canonical field in the fixed source fixture."
    )
    return (prediction_snapshot,)


@app.cell
def _(Path, hashlib, json, prediction_snapshot):
    assert prediction_snapshot
    fixture_path = (
        Path(__file__).resolve().parents[1]
        / "fixtures"
        / "alphachip_public_record_card.json"
    )
    fixture_bytes = fixture_path.read_bytes()
    source_fixture = json.loads(fixture_bytes)
    fixture_sha256 = hashlib.sha256(fixture_bytes).hexdigest()
    expected_fields = [
        "Intent",
        "Task",
        "Design space",
        "Representation",
        "Environment",
        "Method role",
        "Feedback budget",
        "Evidence",
        "Failed runs / rejected alternatives",
        "Rejection authority",
        "Commitment boundary / would overturn",
        "Decision and owner",
    ]
    actual_fields = [row["field"] for row in source_fixture["card_fields"]]
    if actual_fields != expected_fields:
        raise ValueError(
            "AlphaChip fixture does not contain the canonical twelve fields"
        )
    fixture_loaded = True
    return fixture_loaded, fixture_sha256, source_fixture


@app.cell
def _(fixture_loaded, mo, prediction_snapshot, source_fixture):
    assert fixture_loaded
    audit_rows = [
        {
            "card_field": row["field"],
            "public_record_2021": row["public_record_2021"],
            "after_2024_addendum": row["public_record_after_2024_addendum"],
            "citation_keys": ", ".join(row["citations"]),
        }
        for row in source_fixture["card_fields"]
    ]
    hit = prediction_snapshot["choice"] == "public_adjudication"
    mo.vstack(
        [
            mo.md(
                f"""
                ### The Twelve-Field Public-Record Audit

                Source: `{source_fixture['source']['book_section']}`,
                table `{source_fixture['source']['table_label']}`.

                {source_fixture['interpretation_boundary']}
                """
            ),
            mo.ui.table(audit_rows, selection=None, pagination=True),
            mo.md(
                f"""
                ### Compare With the Public Record

                You selected the **{prediction_snapshot['choice']}** cluster at
                **{prediction_snapshot['confidence']}% confidence** and wrote:
                *{prediction_snapshot['reason']}*

                {"Your prediction matches the Chapter 8 audit." if hit else "The Chapter 8 audit places the public-adjudication limit elsewhere."}
                The generation-side fields were substantially present. The public dispute
                concentrated in the environment, feedback budget, evidence packet, and
                lack of a rejection authority both sides accepted. The card localizes
                that mismatch. It does not resolve it by itself.
                """
            ),
        ]
    )
    audit_revealed = True
    return (audit_revealed,)


@app.cell
def _(audit_revealed, mo):
    assert audit_revealed

    def validate_commitment(value):
        if value is None or value.get("boundary") is None:
            return "Choose the public commitment boundary."
        if value["boundary"] != "context_only":
            return "The fixed public packet does not license that conclusion."
        if not str(value.get("human_owner", "")).strip():
            return "Name the owner of the audit judgment."
        if not str(value.get("rationale", "")).strip():
            return "Explain why the boundary follows from the twelve fields."
        if not str(value.get("would_strengthen", "")).strip():
            return "Name evidence that would strengthen public adjudication."
        return None

    commitment_form = mo.ui.dictionary(
        {
            "boundary": mo.ui.dropdown(
                options={
                    "Treat the strongest public claim as context-only in this snapshot; do not infer that the underlying work is false.": "context_only",
                    "Accept every deployment claim because a production team reported it.": "accept_all",
                    "Conclude that the underlying method is false because public fields are missing.": "reject_false",
                },
                label="**Commit.** Where does the outside reviewer's boundary sit?",
            ),
            "human_owner": mo.ui.text(
                label="**Human audit owner** (required)",
                placeholder="Your name or review role",
            ),
            "rationale": mo.ui.text_area(
                label="**Rationale** (required)",
                placeholder="Which card fields cap the public claim, and why does absence not prove falsity?",
                rows=2,
            ),
            "would_strengthen": mo.ui.text_area(
                label="**Would strengthen public adjudication** (required)",
                placeholder="Name a shared environment, matched budget, evidence packet, or agreed rejection check.",
                rows=2,
            ),
        }
    ).form(
        submit_button_label="Record public-audit boundary",
        clear_on_submit=False,
        validate=validate_commitment,
    )
    commitment_form
    return (commitment_form,)


@app.cell
def _(
    commitment_form,
    fixture_sha256,
    json,
    mo,
    prediction_snapshot,
    source_fixture,
):
    mo.stop(
        commitment_form.value is None,
        mo.md("*Submit the audit boundary to produce the chapter record.*"),
    )
    commitment_snapshot = dict(commitment_form.value)
    chapter_record = {
        "schema_version": "arch2-learning-record/v1",
        "activity_id": "lab_10_own_the_commitment",
        "record_type": "sourced_public_record_audit",
        "card_conformance_claim": "none; this is a learning record around the canonical twelve-field fixture",
        "source_fixture_sha256": fixture_sha256,
        "source": source_fixture["source"],
        "interpretation_boundary": source_fixture["interpretation_boundary"],
        "canonical_card_fields": source_fixture["card_fields"],
        "prediction": prediction_snapshot,
        "human_audit_commitment": commitment_snapshot,
    }
    record_text = json.dumps(chapter_record, indent=2, sort_keys=True) + "\n"
    mo.vstack(
        [
            mo.md(
                "### Sourced Audit Record\n\n"
                "The JSON contains all twelve fixture rows with citation keys, the "
                "fixture hash, your submitted prediction, and your bounded audit "
                "judgment. It does not claim card conformance or replayability."
            ),
            mo.download(
                data=record_text.encode(),
                filename="arch2-lab10-public-record-audit.json",
                mimetype="application/json",
                label="Download Lab 10 audit record",
            ),
        ]
    )
    artifact_ready = True
    return (artifact_ready,)


@app.cell
def _(artifact_ready, mo):
    assert artifact_ready
    reflection_form = mo.ui.text_area(
        label="**Reflect.** Which one shared artifact or rejection check would most improve this public audit, and what claim would it still not settle?",
        placeholder="Name both the improvement and its remaining scope limit.",
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
        mo.md("*Submit the reflection to finish the activity.*"),
    )
    mo.md(
        "**Activity complete.** You audited the full card, preserved its sources, and "
        "kept the public commitment inside the disclosed evidence boundary."
    )
    return


if __name__ == "__main__":
    app.run()
