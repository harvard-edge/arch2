"""Attributed text and explicit architecture trajectory views for the byte LM.

Documentation is language pretraining data, not a measured architecture trace.
Constructed action labels and checked tool-outcome preferences remain separately
identified. These small related sources do not establish language competence or
independent workload transfer.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil

from .contracts import Artifact, ContractError, canonical_json, file_sha256

SCHEMA = "nanochip-language-corpus/v1"
DOCUMENT_SPLITS = {
    "architecture.md": "train",
    "interface.md": "train",
    "quantization.md": "train",
    "memory_map.md": "dev",
    "TASK_SPEC.md": "test",
}
ATTRIBUTION = "MoonshotAI/nano-kpu documentation, retained upstream snapshot"
SOURCE_URL = "https://github.com/MoonshotAI/nano-kpu"


def _chunks(text: str, max_bytes: int):
    """Declared corpus segmentation, preserving every original Unicode character."""
    chunk = []
    count = 0
    for character in text:
        width = len(character.encode("utf-8"))
        if width > max_bytes:
            raise ContractError("Corpus byte bound cannot hold one Unicode character")
        if chunk and count + width > max_bytes:
            yield "".join(chunk)
            chunk, count = [], 0
        chunk.append(character)
        count += width
    if chunk:
        yield "".join(chunk)


def _document_rows(root: Path, max_text_bytes: int):
    rows = []
    for name, split in DOCUMENT_SPLITS.items():
        relative = f"sources/{name}"
        path = root / relative
        digest = file_sha256(path)
        for index, text in enumerate(
            _chunks(path.read_text(encoding="utf-8"), max_text_bytes)
        ):
            if not text.strip():
                continue
            rows.append(
                dict(
                    record_id=f"document:{name}:{index}",
                    group_id=f"document:{name}",
                    split=split,
                    original_split=split,
                    input_text=text,
                    input_text_sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
                    source_sha256=digest,
                    source_receipt=dict(path=relative, sha256=digest),
                    source_root=str(root),
                    data_origin="repository_documentation",
                    label_origin="unlabeled repository text; next-byte prediction",
                    attribution=ATTRIBUTION,
                    source_url=SOURCE_URL,
                    license="Apache-2.0",
                )
            )
    return rows


def collect_language_corpus(
    output_dir: str | Path, *, max_text_bytes: int = 384
) -> dict:
    """Snapshot attributed docs and split whole documents before segmenting text.

    No tools, downloads, or model training run here. Segmentation is explicit
    dataset construction; inference still rejects oversized inputs.
    """
    if type(max_text_bytes) is not int or not 32 <= max_text_bytes <= 8192:
        raise ContractError(
            "Language corpus segment size must be 32 through 8192 UTF-8 bytes"
        )
    root = Path(output_dir).resolve()
    if root.exists():
        raise ContractError("Language corpus output must be a new directory")
    source = Path(__file__).resolve().parents[1] / "kpu"
    root.mkdir(parents=True)
    (root / "sources").mkdir()
    for name in DOCUMENT_SPLITS:
        shutil.copyfile(source / "docs" / name, root / "sources" / name)
    shutil.copyfile(source / "LICENSE", root / "sources/LICENSE")
    rows = _document_rows(root, max_text_bytes)
    manifest = dict(
        schema=SCHEMA,
        max_text_bytes=max_text_bytes,
        split_policy="whole documents assigned before UTF-8 segmentation",
        document_splits=DOCUMENT_SPLITS,
        source_files=[
            dict(path=f"sources/{name}", sha256=file_sha256(root / "sources" / name))
            for name in (*DOCUMENT_SPLITS, "LICENSE")
        ],
        attribution=ATTRIBUTION,
        source_url=SOURCE_URL,
        license="Apache-2.0",
        records=rows,
        records_sha256=hashlib.sha256(canonical_json(rows).encode()).hexdigest(),
        generator_sha256=file_sha256(__file__),
        manifest_path=str(root / "manifest.json"),
        limits=[
            "related documentation of one upstream design, not independent workloads",
            "text chunks retain documentation context but can end within a sentence",
            "documentation pretraining contains no measured trajectory or optimal-action labels",
        ],
    )
    (root / "manifest.json").write_text(
        json.dumps(manifest, indent=2, allow_nan=False) + "\n"
    )
    return manifest


def load_language_corpus(manifest: str | Path | dict) -> list[dict]:
    path = Path(
        manifest["manifest_path"] if isinstance(manifest, dict) else manifest
    ).resolve()
    data = json.loads(path.read_text())
    root = path.parent
    if (
        data.get("schema") != SCHEMA
        or data.get("document_splits") != DOCUMENT_SPLITS
        or data.get("generator_sha256") != file_sha256(__file__)
        or type(data.get("max_text_bytes")) is not int
        or not 32 <= data["max_text_bytes"] <= 8192
    ):
        raise ContractError(
            "Unsupported language corpus schema, split policy, generator, or byte envelope"
        )
    expected_names = {f"sources/{name}" for name in (*DOCUMENT_SPLITS, "LICENSE")}
    if {item["path"] for item in data["source_files"]} != expected_names:
        raise ContractError("Language corpus source manifest is incomplete")
    for item in data["source_files"]:
        Artifact(**item).validate(root)
    expected = _document_rows(root, data["max_text_bytes"])
    # Compare content/provenance independently of the directory's current location.
    saved = [dict(row, source_root=str(root)) for row in data["records"]]
    if (
        expected != saved
        or data.get("records_sha256")
        != hashlib.sha256(canonical_json(data["records"]).encode()).hexdigest()
    ):
        raise ContractError(
            "Language records differ from attributed source bytes or frozen partitions"
        )
    partition_text = {}
    for row in expected:
        digest = row["input_text_sha256"]
        if digest in partition_text and partition_text[digest] != row["split"]:
            raise ContractError("Exact documentation text crosses language partitions")
        partition_text[digest] = row["split"]
    return expected


def architecture_examples(manifest: str | Path | dict) -> list[dict]:
    """Verified constructed packed-row prompts, retaining disclosed heuristic labels."""
    from .design_learning import _load_manifest

    corpus, path = _load_manifest(manifest)
    return [
        dict(row, data_origin="constructed", source_root=str(path.parent))
        for row in corpus["records"]
    ]


def measured_feedback_examples(manifest: str | Path) -> list[dict]:
    """Load checked measured preferences, with no acceptance or optimal-PPA upgrade.

    The strict existing loader validates original execution bundles and recomputes
    the label. This is explicitly a designated development-to-training view.
    """
    from .design_feedback_data import load_feedback

    path = Path(manifest).resolve()
    corpus = load_feedback(path)
    return [
        dict(row, data_origin="measured", source_root=str(path.parent))
        for row in corpus["records"]
    ]
