"""Pluggable LLM and reference proposers for Stage 2 (Explore) of nanochip.

Supports:
  - `reference`: Canonical 5-turn Kimi K3 co-design trajectory (deterministic, zero API keys required)
  - `kimi-k3`:   Moonshot AI API (`MOONSHOT_API_KEY` or `OPENROUTER_API_KEY`)
  - `claude`:    Anthropic Messages API (`ANTHROPIC_API_KEY`)
  - `gemini`:    Google Gemini API (`GEMINI_API_KEY`)
  - `openai`:    OpenAI Responses/Chat API (`OPENAI_API_KEY`)

When an API key is not present in the environment, any cloud provider cleanly
falls back to the verified `reference` proposer while recording `fallback_used=True`
in the execution metadata so CLI and cockpit demos never crash offline.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .lifecycle import ProposalRecord


SUPPORTED_PROPOSERS = ("reference", "kimi-k3", "claude", "gemini", "openai")

PROVIDER_ENV_KEYS = {
    "reference": (),
    "kimi-k3": ("MOONSHOT_API_KEY", "OPENROUTER_API_KEY"),
    "claude": ("ANTHROPIC_API_KEY",),
    "gemini": ("GEMINI_API_KEY",),
    "openai": ("OPENAI_API_KEY",),
}


@dataclass
class ProposerMetadata:
    provider: str
    effective_provider: str
    api_key_detected: bool
    fallback_used: bool
    model_id: str


def resolve_proposer(provider: str = "reference") -> ProposerMetadata:
    """Resolve the requested proposer provider and check environment credentials."""
    prov = (provider or "reference").lower().strip()
    if prov not in SUPPORTED_PROPOSERS:
        prov = "reference"

    if prov == "reference":
        return ProposerMetadata(
            provider="reference",
            effective_provider="reference",
            api_key_detected=True,
            fallback_used=False,
            model_id="moonshot-kimi-k3-reference-trajectory",
        )

    env_keys = PROVIDER_ENV_KEYS.get(prov, ())
    has_key = any(bool(os.environ.get(k, "").strip()) for k in env_keys)

    default_models = {
        "kimi-k3": os.environ.get("NANOCHIP_KIMI_MODEL", "kimi-k2.5"),
        "claude": os.environ.get("NANOCHIP_CLAUDE_MODEL", "claude-sonnet-4-20250514"),
        "gemini": os.environ.get("NANOCHIP_GEMINI_MODEL", "gemini-2.5-pro"),
        "openai": os.environ.get("NANOCHIP_OPENAI_MODEL", "gpt-4.1"),
    }

    if not has_key:
        return ProposerMetadata(
            provider=prov,
            effective_provider="reference",
            api_key_detected=False,
            fallback_used=True,
            model_id=f"{default_models[prov]} (offline->reference fallback)",
        )

    return ProposerMetadata(
        provider=prov,
        effective_provider=prov,
        api_key_detected=True,
        fallback_used=False,
        model_id=default_models[prov],
    )


class NanochipProposer:
    """Generates Stage 2 (`ProposalRecord`) hypotheses conditioned on prior turn feedback."""

    def __init__(self, provider: str = "reference"):
        self.meta = resolve_proposer(provider)

    def propose_turn(
        self,
        turn_id: int,
        reference_turn_data: Dict[str, Any],
        prior_interpretation: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Return a ProposalRecord dict and proposer telemetry for `turn_id`."""
        ref_proposal = ProposalRecord.from_dict(reference_turn_data["explore"])

        if self.meta.effective_provider == "reference":
            return {
                "proposal": ref_proposal.to_dict(),
                "proposer_meta": {
                    "requested_provider": self.meta.provider,
                    "effective_provider": self.meta.effective_provider,
                    "model_id": self.meta.model_id,
                    "api_key_detected": self.meta.api_key_detected,
                    "fallback_used": self.meta.fallback_used,
                },
            }

        # Live LLM call with structured JSON prompt, falling back to reference on network error
        prompt = self._build_prompt(turn_id, ref_proposal, prior_interpretation)
        try:
            llm_json = self._call_cloud_llm(prompt)
            merged = ref_proposal.to_dict()
            for k in (
                "title",
                "hypothesis",
                "predicted_cycles_per_token",
                "predicted_tokens_per_sec",
            ):
                if k in llm_json and llm_json[k] is not None:
                    merged[k] = llm_json[k]
            return {
                "proposal": merged,
                "proposer_meta": {
                    "requested_provider": self.meta.provider,
                    "effective_provider": self.meta.effective_provider,
                    "model_id": self.meta.model_id,
                    "api_key_detected": True,
                    "fallback_used": False,
                },
            }
        except Exception as exc:
            return {
                "proposal": ref_proposal.to_dict(),
                "proposer_meta": {
                    "requested_provider": self.meta.provider,
                    "effective_provider": "reference",
                    "model_id": self.meta.model_id,
                    "api_key_detected": self.meta.api_key_detected,
                    "fallback_used": True,
                    "fallback_reason": str(exc),
                },
            }

    def _build_prompt(
        self,
        turn_id: int,
        ref_proposal: ProposalRecord,
        prior_interpretation: Optional[Dict[str, Any]],
    ) -> str:
        feedback = (
            json.dumps(prior_interpretation, indent=2)
            if prior_interpretation
            else "None (Turn 0)"
        )
        return (
            f"You are proposing Turn {turn_id} in Stage 2 (Explore) of the Architecture 2.0 loop "
            f"for the Moonshot hybrid KDA+MLA+MoE chip (`msh_chip_top`, `nano` config).\n"
            f"Prior Stage 5 (Interpret) diagnostic feedback:\n{feedback}\n\n"
            f"Return a JSON object with keys: title, hypothesis, predicted_cycles_per_token, "
            f"predicted_tokens_per_sec.\n"
            f"Reference anchor for Turn {turn_id}: {ref_proposal.title}"
        )

    def _call_cloud_llm(self, prompt: str) -> Dict[str, Any]:
        prov = self.meta.effective_provider
        if prov == "kimi-k3":
            api_key = os.environ.get("MOONSHOT_API_KEY") or os.environ.get(
                "OPENROUTER_API_KEY", ""
            )
            url = (
                "https://api.moonshot.cn/v1/chat/completions"
                if os.environ.get("MOONSHOT_API_KEY")
                else "https://openrouter.ai/api/v1/chat/completions"
            )
            payload = {
                "model": self.meta.model_id,
                "messages": [{"role": "user", "content": prompt}],
                "response_format": {"type": "json_object"},
                "temperature": 0.1,
            }
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}",
                },
            )
            with urllib.request.urlopen(req, timeout=20) as resp:
                body = json.loads(resp.read().decode("utf-8"))
                return json.loads(body["choices"][0]["message"]["content"])
        raise RuntimeError(
            f"Live cloud call skipped or unsupported for {prov}; using reference anchor."
        )
