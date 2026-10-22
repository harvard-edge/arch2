import hashlib

import pytest

from nanochip.laboratory.context import KeywordContext, with_context
from nanochip.laboratory.contracts import ContractError


def source(text="weights scale zero point", partition="train"):
    return dict(
        source_id="example",
        text=text,
        partition=partition,
        source="test-fixture",
        text_sha256=hashlib.sha256(text.encode()).hexdigest(),
    )


def test_retrieval_preserves_source_and_budget():
    result = KeywordContext().retrieve("weights", [source()], max_words=2)
    assert result[0]["text"] == "weights scale"
    assert result[0]["source_id"] == "example"
    assert result[0]["truncated"] and result[0]["retrieved_words"] == 2
    assert (
        result[0]["text_sha256"]
        == hashlib.sha256(result[0]["text"].encode()).hexdigest()
    )
    assert result[0]["full_text_sha256"] == source()["text_sha256"]
    assert with_context("observed", result).endswith("OBSERVATION\nobserved")


def test_test_sources_are_rejected_even_when_not_relevant():
    with pytest.raises(ContractError):
        KeywordContext().retrieve("unrelated", [source(partition="test")])


def test_modified_knowledge_is_rejected():
    item = source()
    item["text"] += " changed"
    with pytest.raises(ContractError):
        KeywordContext().retrieve("weights", [item])


def test_empty_context_does_not_change_model_input():
    assert with_context("exact input", []) == "exact input"
