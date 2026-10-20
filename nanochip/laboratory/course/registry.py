"""The nine ordered construction exercises and their durable outputs."""

from dataclasses import dataclass


@dataclass(frozen=True)
class LabSpec:
    number: int
    title: str
    component: str
    student_file: str
    upstream: tuple[int, ...]
    artifact: str
    integration_check: str


LABS = (
    LabSpec(1, "Workload and data", "grouped data and split construction", "lab01_data.py", (),
            "data/split-manifest.json", "grouped_split_preserves_records"),
    LabSpec(2, "Representations and numerical checks", "packed int4 conversion and oracle", "lab02_representation.py", (1,),
            "representation/int4-vectors.json", "int4_pack_unpack_matches_oracle"),
    LabSpec(3, "Experiment harness", "receipt adapter and fail-closed eligibility", "lab03_harness.py", (1, 2),
            "harness/receipt-contract-check.json", "receipt_identity_and_fail_closed_states"),
    LabSpec(4, "Train a small model", "language model and training record", "lab04_train.py", (1, 2, 3),
            "learning/training-check.json", "checkpoint_reloads_with_declared_contract"),
    LabSpec(5, "Adapt and use the model", "adaptation, action parser, and context provider", "lab05_inference.py", (3, 4),
            "inference/inference-check.json", "legal_action_reaches_shared_harness"),
    LabSpec(6, "Predict and search", "predictor and budgeted search policy", "lab06_search.py", (1, 3, 5),
            "search/campaign.json", "feedback_changes_next_legal_action"),
    LabSpec(7, "Change the architecture", "student RTL transformation", "lab07_architecture.py", (2, 3, 5, 6),
            "design/candidate/", "full_core_numerical_and_differential_checks"),
    LabSpec(8, "Close the physical path", "physical adapter and receipt interpreter", "lab08_physical.py", (3, 7),
            "physical/receipt-summary.json", "physical_receipt_binds_checked_source"),
    LabSpec(9, "Evaluate and improve the system", "feedback curation and independent comparison", "lab09_evaluate.py", (1, 3, 4, 5, 6, 7, 8),
            "evaluation/decision.json", "heldout_comparison_and_cost_report"),
)

BY_NUMBER = {lab.number: lab for lab in LABS}


def get_lab(number: int) -> LabSpec:
    if type(number) is not int or number not in BY_NUMBER:
        raise ValueError("Lab number must be an integer from 1 through 9")
    return BY_NUMBER[number]
