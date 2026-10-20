"""Declared semantics shared by a training representation and its inference adapter.

Students can replace a serializer by declaring a new schema/version or serializer
identity. This record checks compatibility; it cannot prove that arbitrary Python
serializer code implements the declared meaning. Keep exact-byte examples beside
each serializer. No registration or automatic discovery is involved.
"""

from dataclasses import asdict, dataclass
import hashlib
from typing import Any, Mapping

from .contracts import ContractError, canonical_json


@dataclass(frozen=True)
class ModelIOContract:
    """A checkpoint's input meaning, finite output grammar, and byte envelope.

    ``serializer_id`` identifies the implementation/conventions, rather than an
    import path. Change it when serialization semantics change. Action ordering
    matters because the sequence decoder assigns tokens in this order. The byte
    budget covers serialized UTF-8 text, before model BOS/separator tokens.
    """

    schema_id: str
    schema_version: int
    serializer_id: str
    actions: tuple[str, ...]
    max_input_bytes: int
    overflow: str = "reject"
    encoding: str = "utf-8"

    def __post_init__(self) -> None:
        if any(not isinstance(value, str) or not value.strip()
               for value in (self.schema_id, self.serializer_id)):
            raise ContractError("Model input schema and serializer identities must be nonempty strings")
        if type(self.schema_version) is not int or self.schema_version < 1:
            raise ContractError("Model input schema version must be a positive integer")
        if (not isinstance(self.actions, tuple) or not self.actions
                or any(not isinstance(action, str) or not action.strip() for action in self.actions)
                or len(set(self.actions)) != len(self.actions)):
            raise ContractError("Model input contract actions must be distinct nonempty strings in a tuple")
        if type(self.max_input_bytes) is not int or not 1 <= self.max_input_bytes <= 8192:
            raise ContractError("Model input byte limit must be an integer from 1 through 8192")
        if self.overflow != "reject" or self.encoding != "utf-8":
            raise ContractError("Model input contracts support UTF-8 and reject overflow; no truncation")

    def to_dict(self) -> dict[str, Any]:
        result = asdict(self)
        result["actions"] = list(self.actions)
        return result

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ModelIOContract":
        if not isinstance(value, Mapping):
            raise ContractError("Model input contract must be a mapping")
        required = {"schema_id", "schema_version", "serializer_id", "actions",
                    "max_input_bytes", "overflow", "encoding"}
        if set(value) != required or not isinstance(value["actions"], (list, tuple)):
            raise ContractError("Malformed model input contract fields")
        return cls(**(dict(value) | {"actions": tuple(value["actions"])}))

    @property
    def digest(self) -> str:
        return hashlib.sha256(canonical_json(self.to_dict()).encode("utf-8")).hexdigest()

    def require_match(self, supplied: "ModelIOContract | None") -> None:
        if not isinstance(supplied, ModelIOContract) or supplied != self:
            raise ContractError("Model input contract mismatch: declare the checkpoint's schema, serializer, actions, and byte limit")

    def validate_text(self, text: str) -> bytes:
        if not isinstance(text, str):
            raise ContractError("Model input serializer must return text")
        try:
            data = text.encode(self.encoding)
        except UnicodeEncodeError as exc:
            raise ContractError("Model input must encode as valid UTF-8") from exc
        if len(data) > self.max_input_bytes:
            raise ContractError(f"Input has {len(data)} UTF-8 bytes; configured maximum is {self.max_input_bytes}; no truncation applied")
        return data
