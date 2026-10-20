"""A small, replaceable retrieval component with explicit source boundaries."""

import hashlib
import json
from pathlib import Path
import re
from typing import Mapping, Sequence

from .contracts import ContractError, Observation, Task, file_sha256


def specification_sources() -> tuple[dict, ...]:
    """Index local upstream specification paragraphs without copying them into code."""
    root = Path(__file__).resolve().parents[1] / "kpu/docs"
    result = []
    for name in ("interface.md", "quantization.md"):
        path = root / name
        for index, text in enumerate(re.split(r"\n\s*\n", path.read_text(encoding="utf-8"))):
            if not text.strip():
                continue
            result.append(dict(
                source_id=f"{name}:paragraph-{index}", text=text.strip(),
                partition="specification", kind="specification", source=str(path),
                file_sha256=file_sha256(path),
                text_sha256=hashlib.sha256(text.strip().encode()).hexdigest(),
                license="Apache-2.0; see nanochip/kpu/LICENSE",
            ))
    return tuple(result)


def _terms(text: str) -> set[str]:
    return set(re.findall(r"[a-z][a-z0-9_]+", text.lower()))


class KeywordContext:
    """Rank allowed paragraphs and return a bounded amount of sourced text.

    Budget is whitespace-separated words, not model tokens. This baseline
    demonstrates the interface; it makes no retrieval-quality claim.
    """

    def retrieve(self, query: str, allowed_sources: Sequence[Mapping], *, max_words: int = 80):
        if type(max_words) is not int or max_words < 0:
            raise ContractError("Context word budget must be a nonnegative integer")
        ranked = []
        seen = set()
        for item in allowed_sources:
            if item.get("partition") not in ("train", "dev", "specification"):
                raise ContractError("Retrieval cannot consume final-test or undeclared sources")
            if not all(isinstance(item.get(key), str) and item[key] for key in
                       ("source_id", "text", "text_sha256", "source")):
                raise ContractError("Context records need text, source identity, and content hash")
            if item["source_id"] in seen:
                raise ContractError("Duplicate knowledge-source identity")
            seen.add(item["source_id"])
            if hashlib.sha256(item["text"].encode()).hexdigest() != item["text_sha256"]:
                raise ContractError("Knowledge text no longer matches its source hash")
            score = len(_terms(query) & _terms(item["text"]))
            if score:
                ranked.append((score, item["source_id"], dict(item)))
        remaining = max_words
        output = []
        for score, _, item in sorted(ranked, key=lambda value: (-value[0], value[1])):
            if remaining <= 0:
                break
            words = item["text"].split()
            excerpt = words[:remaining]
            excerpt_text = " ".join(excerpt)
            output.append(dict(item, text=excerpt_text, retrieved_words=len(excerpt),
                               text_sha256=hashlib.sha256(excerpt_text.encode()).hexdigest(),
                               truncated=len(excerpt) < len(words), score=score,
                               full_text_sha256=item["text_sha256"]))
            remaining -= len(excerpt)
        return tuple(output)

    def build(self, task: Task, history: tuple[Observation, ...],
              allowed_sources: Sequence[Mapping], budget: int):
        query = json.dumps(dict(task.specification), sort_keys=True)
        if history:
            query += " " + history[-1].details
        return self.retrieve(query, allowed_sources, max_words=budget)


def with_context(observation_text: str, context: Sequence[Mapping]) -> str:
    """Put optional reference material before the unchanged observed evidence."""
    if not context:
        return observation_text
    excerpts = "\n".join(f"[{item['source_id']}] {item['text']}" for item in context)
    return "REFERENCE MATERIAL\n" + excerpts + "\nOBSERVATION\n" + observation_text
