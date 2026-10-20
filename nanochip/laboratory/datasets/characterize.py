"""Inspectable data distributions and descriptive training-input support.

These functions inspect supplied records. Source receipt validation belongs to
the corpus loader: a hash string here is an identity to count, not proof that a
file exists or that a tool measured it. Observed ranges/categories are neither
calibrated OOD confidence nor permission to accept a design or skip checks.
"""

from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import math
import statistics
from typing import Any, Mapping, Sequence

from ..contracts import ContractError, canonical_json

PROFILE_SCHEMA = "nanochip-data-profile/v1"
SUPPORT_SCHEMA = "nanochip-observed-input-support/v1"
LIMITATIONS = [
    "Descriptive observed training ranges and categories; not calibrated OOD confidence.",
    "Numeric ranges ignore gaps, feature correlations, and semantic similarity.",
    "Within these bounds does not establish typicality, correctness, model usefulness, or design approval.",
    "Source receipt validation remains the caller's corpus-loader responsibility.",
]


def _sha(value):
    try:
        return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()
    except (TypeError, ValueError) as exc:
        raise ContractError("Characterization records/support must contain finite JSON values") from exc


def _text(value):
    if not isinstance(value, str):
        raise ContractError("Characterization input_text must be text")
    try:
        return value.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ContractError("Characterization input_text must be valid UTF-8") from exc


def _rows(records, text_key):
    rows = []
    for record in records:
        if not isinstance(record, Mapping):
            raise ContractError("Characterization records must be mappings")
        row = dict(record)
        for key in ("record_id", "group_id", "split"):
            if not isinstance(row.get(key), str) or not row[key].strip():
                raise ContractError("Characterization records need nonempty record_id, group_id, and split")
        _text(row.get(text_key))
        rows.append(row)
    return rows


def _distribution(values):
    ordered = sorted(values)
    if not ordered:
        return dict(count=0, min=None, max=None, mean=None, median=None, p90=None, total=0,
                    percentile_method="nearest rank")
    return dict(count=len(ordered), min=ordered[0], max=ordered[-1],
                mean=statistics.fmean(ordered), median=statistics.median(ordered),
                p90=ordered[math.ceil(.9 * len(ordered)) - 1], total=sum(ordered),
                percentile_method="nearest rank")


def _count(values):
    return dict(sorted(Counter(values).items()))


def _identity(value):
    return value if isinstance(value, str) and value.strip() else "undeclared"


def _clusters(rows, key, *, cross_partition=False):
    groups = defaultdict(list)
    for row in rows:
        value = key(row)
        if value is not None:
            groups[value].append(row)
    result = []
    for value, members in sorted(groups.items()):
        splits = sorted({row["split"] for row in members})
        if (len(splits) > 1 if cross_partition else len(members) > 1):
            result.append(dict(identity=value, count=len(members), splits=splits,
                               record_ids=[row["record_id"] for row in members]))
    return result


def profile_records(records: Sequence[Mapping[str, Any]], *, text_key: str = "input_text",
                    label_key: str | None = "target_action") -> dict:
    """Report input lengths, provenance counts, baselines, duplicates, and leakage.

    Content leakage means exact UTF-8 model-input equality, not a claim to detect
    paraphrases or semantic duplicates. A label is used only if it is a nonempty
    string. The majority action is chosen using designated train labels only.
    """
    rows = _rows(records, text_key)
    text_hash = lambda row: hashlib.sha256(_text(row[text_key])).hexdigest()
    split_names = sorted({row["split"] for row in rows})
    labels = lambda items: Counter(row[label_key] for row in items
        if label_key is not None and isinstance(row.get(label_key), str) and row[label_key].strip())
    training_labels = labels(row for row in rows if row["split"] == "train" and row.get("original_split") != "test")
    majority = min(training_labels, key=lambda value: (-training_labels[value], value)) if training_labels else None
    baseline = {}
    for split in split_names:
        counts = labels(row for row in rows if row["split"] == split)
        total = sum(counts.values())
        baseline[split] = dict(labeled_records=total, label_counts=dict(sorted(counts.items())),
                              constant_action_accuracy=counts[majority] / total if majority is not None and total else None)
    receipts = lambda row: (row["source_receipt"].get("sha256")
        if isinstance(row.get("source_receipt"), Mapping) and isinstance(row["source_receipt"].get("sha256"), str) else None)
    sources = lambda row: row.get("source_sha256") if isinstance(row.get("source_sha256"), str) else None
    conflicting = []
    by_text = defaultdict(list)
    for row in rows:
        by_text[text_hash(row)].append(row)
    for digest, members in sorted(by_text.items()):
        distinct = sorted(labels(members))
        if len(distinct) > 1:
            conflicting.append(dict(input_sha256=digest, labels=distinct,
                                     record_ids=[row["record_id"] for row in members]))
    return dict(schema=PROFILE_SCHEMA, record_count=len(rows),
        dataset_sha256=_sha(rows), text_key=text_key, label_key=label_key,
        input_bytes=_distribution([len(_text(row[text_key])) for row in rows]),
        by_split={split: dict(record_count=sum(row["split"] == split for row in rows),
            input_bytes=_distribution([len(_text(row[text_key])) for row in rows if row["split"] == split]),
            groups=len({row["group_id"] for row in rows if row["split"] == split}),
            sources=len({sources(row) for row in rows if row["split"] == split and sources(row) is not None}))
            for split in split_names},
        split_counts=_count(row["split"] for row in rows),
        original_split_counts=_count(_identity(row.get("original_split")) for row in rows),
        group_counts=_count(row["group_id"] for row in rows),
        source_counts=_count(sources(row) or "undeclared" for row in rows),
        data_origin_counts=_count(_identity(row.get("data_origin")) for row in rows),
        label_counts=dict(sorted(labels(rows).items())),
        missing_label_count=len(rows) - sum(labels(rows).values()),
        training_majority_baseline=dict(action=majority, selection="train labels only; lexical tie break", by_split=baseline),
        retagged_final_test_record_ids=[row["record_id"] for row in rows
                                      if row["split"] == "train" and row.get("original_split") == "test"],
        duplicate_record_ids=_clusters(rows, lambda row: row["record_id"]),
        exact_record_duplicates=_clusters(rows, _sha),
        exact_input_duplicates=_clusters(rows, text_hash), conflicting_input_labels=conflicting,
        cross_partition_leakage=dict(groups=_clusters(rows, lambda row: row["group_id"], cross_partition=True),
            sources=_clusters(rows, sources, cross_partition=True),
            source_receipts=_clusters(rows, receipts, cross_partition=True),
            exact_inputs=_clusters(rows, text_hash, cross_partition=True)),
        validation="Counts supplied identities only; source receipts are not opened or validated.",
        limitations=LIMITATIONS + ["Exact input checks do not detect semantic duplicates or related task families."])


def _numeric(value):
    return type(value) is int or type(value) is float and math.isfinite(value)


def _category(value):
    if value is not None and type(value) not in (str, bool, int, float):
        raise ContractError("Categorical support accepts JSON scalar values only")
    if type(value) is float and not math.isfinite(value):
        raise ContractError("Categorical support requires finite values")
    return canonical_json(dict(type=type(value).__name__, value=value))


def fit_training_support(records: Sequence[Mapping[str, Any]], *,
                         numeric_features: Sequence[str] = (), categorical_features: Sequence[str] = (),
                         feature_key: str = "features", text_key: str = "input_text") -> dict:
    """Fit simple observed support using split='train' only, before held-out use.

    Callers explicitly choose features; this function does not mine labels, infer
    task semantics, or fit thresholds on dev/test. A declared development training
    view is allowed; original_split='test' cannot be reassigned to train.
    """
    numeric_features, categorical_features = tuple(numeric_features), tuple(categorical_features)
    names = numeric_features + categorical_features
    if (len(set(names)) != len(names) or any(not isinstance(name, str) or not name.strip() for name in names)):
        raise ContractError("Support features must be distinct nonempty names with one declared type each")
    train = []
    for row in records:
        if not isinstance(row, Mapping):
            raise ContractError("Support records must be mappings")
        if row.get("split") == "train":
            if row.get("original_split") == "test":
                raise ContractError("Final-test records cannot fit training support through reassignment")
            train.append(row)
    train = _rows(train, text_key)
    if not train:
        raise ContractError("Observed support requires designated training records")
    values = defaultdict(list)
    for row in train:
        features = row.get(feature_key, {})
        if not isinstance(features, Mapping):
            raise ContractError("Declared support features require a mapping")
        for name in names:
            if name not in features:
                raise ContractError(f"Training record lacks declared feature: {name}")
            value = features[name]
            if name in numeric_features and not _numeric(value):
                raise ContractError(f"Training numeric feature must be finite and nonboolean: {name}")
            if name in categorical_features:
                _category(value)
            values[name].append(value)
    support = dict(schema=SUPPORT_SCHEMA, text_key=text_key, feature_key=feature_key,
        training_record_count=len(train), training_record_ids=[row["record_id"] for row in train],
        training_dataset_sha256=_sha(train),
        training_group_ids=sorted({row["group_id"] for row in train}),
        original_split_counts=_count(_identity(row.get("original_split")) for row in train),
        input_bytes=_distribution([len(_text(row[text_key])) for row in train]),
        numeric_features={name: dict(min=min(values[name]), max=max(values[name])) for name in numeric_features},
        categorical_features={name: [value for _, value in sorted({_category(v): v for v in values[name]}.items())]
                              for name in categorical_features},
        limitations=LIMITATIONS)
    support["support_sha256"] = _sha(support)
    return support


def assess_input_support(input_text: str, features: Mapping[str, Any], support: Mapping[str, Any]) -> dict:
    """Explain departures from training ranges/categories; never authorize a run."""
    if not isinstance(support, Mapping) or support.get("schema") != SUPPORT_SCHEMA:
        raise ContractError("Unsupported observed-input support schema")
    if support.get("support_sha256") != _sha({k: v for k, v in support.items() if k != "support_sha256"}):
        raise ContractError("Observed-input support content changed")
    if not isinstance(features, Mapping):
        raise ContractError("Input support assessment requires an explicit feature mapping")
    length = len(_text(input_text))
    reasons = []
    bounds = support["input_bytes"]
    if length < bounds["min"] or length > bounds["max"]:
        reasons.append(dict(code="byte_length_outside_training_range", observed=length,
                            training_min=bounds["min"], training_max=bounds["max"]))
    declared = set(support["numeric_features"]) | set(support["categorical_features"])
    for name in sorted(declared):
        if name not in features:
            reasons.append(dict(code="missing_declared_feature", feature=name))
            continue
        value = features[name]
        if name in support["numeric_features"]:
            limits = support["numeric_features"][name]
            if not _numeric(value):
                reasons.append(dict(code="invalid_numeric_feature", feature=name))
            elif value < limits["min"] or value > limits["max"]:
                reasons.append(dict(code="numeric_outside_training_range", feature=name, observed=value,
                                    training_min=limits["min"], training_max=limits["max"]))
        else:
            categories = support["categorical_features"][name]
            try:
                observed = _category(value)
            except ContractError:
                reasons.append(dict(code="invalid_categorical_feature", feature=name))
                continue
            if observed not in {_category(category) for category in categories}:
                reasons.append(dict(code="unseen_category", feature=name, observed=value,
                                    training_categories=categories))
    return dict(schema=SUPPORT_SCHEMA, support_sha256=support["support_sha256"],
                within_observed_support=not reasons, input_bytes=length, reasons=reasons,
                unchecked_feature_names=sorted(set(features) - declared),
                interpretation="Observed training ranges/categories only; not confidence, correctness, or approval.",
                limitations=LIMITATIONS)
