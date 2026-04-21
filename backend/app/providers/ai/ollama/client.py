# backend/app/providers/ai/ollama/client.py
"""
OllamaProvider — local inference client for structured JSON tasks.

Constraints:
- No raw email bodies sent — only domain, subjects (subject lines only), and
  the current best-guess name are passed to the model.
- Uses /api/chat with format:"json" and temperature 0 for determinism.
- Fails closed: any parse or schema error raises ProviderSchemaError so
  callers can fall back to the existing classification result.
"""

from __future__ import annotations

import json
import re
from typing import Any

from backend.app.providers.ai.ollama.schemas import (
    OllamaAccountContext,
    OllamaAccountInterpretation,
    OllamaBatchContext,
    OllamaBatchInterpretation,
)
from backend.app.providers.base.client import BaseProviderClient
from backend.app.providers.base.exceptions import ProviderSchemaError

_SYSTEM_PROMPT = (
    "You are a service identification assistant. "
    "Given metadata about emails from a sender, identify the real service. "
    "Never include PII, email addresses, or raw email content in your output. "
    "Respond ONLY with a JSON object with exactly these keys: "
    "service_name (lowercase slug, e.g. 'netflix'), "
    "display_name (human-readable, e.g. 'Netflix'), "
    "confidence (integer 0-100), "
    "reason (one sentence explaining your decision)."
)

_USER_TEMPLATE = (
    "Sender domain: {sender_domain}\n"
    "Email count: {email_count}\n"
    "Sample subject lines (up to 5):\n{subjects}\n"
    "Current best guess: {current_guess}\n"
    "{url_hints}"
    "Identify the service. Reply with JSON only."
)

_BATCH_SYSTEM_PROMPT = (
    "You are a service identification assistant. "
    "Given metadata about emails from multiple senders, identify the real service for each. "
    "Never include PII, email addresses, or raw email content in your output. "
    "Respond ONLY with a JSON object: "
    '{"results": [{"index": <int>, "service_name": <slug>, '
    '"display_name": <name>, "confidence": <0-100>, "reason": <optional str>}, ...]}. '
    'service_name must be a lowercase ASCII slug (e.g. "netflix"). '
    "Include exactly one result per account, matched by index."
)

# Input sanitization limits
_MAX_SUBJECTS = 5
_MAX_SUBJECT_LENGTH = 120
_HTML_TAG_RE = re.compile(r"<[^>]{0,200}>")
_SERVICE_SLUG_RE = re.compile(r"[a-z0-9][a-z0-9-]{0,63}")

# Output validation limits
_MAX_SERVICE_NAME_LEN = 64
_MAX_DISPLAY_NAME_LEN = 128
_MAX_REASON_LEN = 512


class OllamaProvider(BaseProviderClient):
    name = "ollama"

    def __init__(
        self,
        *,
        base_url: str = "http://localhost:11434",
        model: str = "gemma2:2b",
        timeout_seconds: int = 30,
    ) -> None:
        super().__init__(timeout_seconds=timeout_seconds)
        self._base_url = base_url.rstrip("/")
        self._model = model

    # ------------------------------------------------------------------
    # Input sanitization
    # ------------------------------------------------------------------

    @staticmethod
    def _sanitize_subjects(subjects: list[str]) -> list[str]:
        """Strip HTML, control characters, and truncate before sending to model."""
        sanitized = []
        for raw in subjects[:_MAX_SUBJECTS]:
            clean = _HTML_TAG_RE.sub("", raw)
            clean = clean.replace("\r", " ").replace("\n", " ").strip()
            if clean:
                sanitized.append(clean[:_MAX_SUBJECT_LENGTH])
        return sanitized

    # ------------------------------------------------------------------
    # Utility methods
    # ------------------------------------------------------------------

    async def health_check(self) -> bool:
        """Return True if Ollama is reachable. Never raises."""
        try:
            await self._get(f"{self._base_url}/api/tags", label="Ollama")
            return True
        except Exception:  # noqa: BLE001
            return False

    async def list_models(self) -> list[str]:
        """Return names of locally available models. Returns [] on any error."""
        try:
            raw = await self._get(f"{self._base_url}/api/tags", label="Ollama")
            if not isinstance(raw, dict):
                return []
            models = raw.get("models", [])
            if not isinstance(models, list):
                return []
            return [m["name"] for m in models if isinstance(m, dict) and "name" in m]
        except Exception:  # noqa: BLE001
            return []

    async def structured_query(
        self,
        task: str,
        context: dict[str, Any],
        schema_hint: str,
    ) -> dict[str, Any]:
        """
        Generic JSON inference endpoint for future callers.

        Sends `task` and `context` to the model with an instruction to
        respond as a JSON object matching `schema_hint`. Returns the parsed
        dict. Raises ProviderSchemaError if the response is not a JSON object.
        """
        system = (
            "You are a structured-output assistant. "
            "Respond ONLY with a valid JSON object. "
            f"The response must match this schema description: {schema_hint}"
        )
        user_msg = (
            f"Task: {task}\n\n"
            f"Context:\n{json.dumps(context, indent=2)}\n\n"
            "Respond with JSON only."
        )
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user_msg},
            ],
            "format": "json",
            "stream": False,
            "options": {"temperature": 0},
        }
        raw = await self._post(
            f"{self._base_url}/api/chat",
            json_data=payload,
            label="Ollama",
            timeout=self._timeout_seconds,
        )
        if not isinstance(raw, dict):
            raise ProviderSchemaError("Ollama: response is not a JSON object")
        message = raw.get("message", {})
        if not isinstance(message, dict):
            raise ProviderSchemaError("Ollama: 'message' missing or not an object")
        content = message.get("content", "")
        if not isinstance(content, str) or not content.strip():
            raise ProviderSchemaError("Ollama: empty content in response")
        try:
            result = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ProviderSchemaError(f"Ollama: JSON parse failed: {exc}") from exc
        if not isinstance(result, dict):
            raise ProviderSchemaError("Ollama: content is not a JSON object")
        return result

    # ------------------------------------------------------------------
    # Account interpretation — single
    # ------------------------------------------------------------------

    async def interpret_account(
        self, ctx: OllamaAccountContext
    ) -> OllamaAccountInterpretation:
        """
        Ask Ollama to identify the real service behind an ambiguous account.

        Raises ProviderError subclasses on network failure or schema mismatch.
        """
        clean_subjects = self._sanitize_subjects(ctx["sample_subjects"])
        subjects_text = (
            "\n".join(f"  - {s}" for s in clean_subjects) or "  (none available)"
        )

        url_parts: list[str] = []
        if ctx.get("login_url"):
            url_parts.append(f"Login URL: {ctx['login_url']}")
        if ctx.get("unsubscribe_url"):
            url_parts.append(f"Unsubscribe URL: {ctx['unsubscribe_url']}")
        url_hints = ("\n".join(url_parts) + "\n") if url_parts else ""

        user_msg = _USER_TEMPLATE.format(
            sender_domain=ctx["sender_domain"],
            email_count=ctx["email_count"],
            subjects=subjects_text,
            current_guess=ctx["current_guess"] or "(unknown)",
            url_hints=url_hints,
        )

        payload: dict[str, Any] = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            "format": "json",
            "stream": False,
            "options": {"temperature": 0},
        }

        raw = await self._post(
            f"{self._base_url}/api/chat",
            json_data=payload,
            label="Ollama",
            timeout=self._timeout_seconds,
        )
        return self._parse_account_response(raw)

    @staticmethod
    def _parse_account_response(raw: Any) -> OllamaAccountInterpretation:
        if not isinstance(raw, dict):
            raise ProviderSchemaError("Ollama: response is not a JSON object")

        message = raw.get("message", {})
        if not isinstance(message, dict):
            raise ProviderSchemaError("Ollama: 'message' missing or not an object")

        content = message.get("content", "")
        if not isinstance(content, str) or not content.strip():
            raise ProviderSchemaError("Ollama: empty content in response")

        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ProviderSchemaError(f"Ollama: JSON parse failed: {exc}") from exc

        if not isinstance(parsed, dict):
            raise ProviderSchemaError("Ollama: content is not a JSON object")

        return OllamaProvider._validate_interpretation_dict(parsed)

    # ------------------------------------------------------------------
    # Account interpretation — batch
    # ------------------------------------------------------------------

    async def interpret_accounts_batch(
        self, batch_ctx: OllamaBatchContext
    ) -> OllamaBatchInterpretation:
        """
        Identify services for multiple accounts in a single Ollama call.

        Returns OllamaBatchInterpretation whose results list has the same
        length as batch_ctx["accounts"]. Entries are None where the model
        returned a malformed or missing result for that index.
        """
        accounts = batch_ctx["accounts"]
        if not accounts:
            return {"results": []}

        lines: list[str] = []
        for i, ctx in enumerate(accounts):
            clean_subjects = self._sanitize_subjects(ctx["sample_subjects"])
            subj_str = (
                ", ".join(f'"{s}"' for s in clean_subjects)
                if clean_subjects
                else "(none)"
            )
            line = (
                f"[{i}] domain={ctx['sender_domain']}, "
                f"emails={ctx['email_count']}, "
                f"guess={ctx['current_guess'] or '(unknown)'}\n"
                f"    subjects: {subj_str}"
            )
            if ctx.get("login_url"):
                line += f"\n    login_url: {ctx['login_url']}"
            if ctx.get("unsubscribe_url"):
                line += f"\n    unsubscribe_url: {ctx['unsubscribe_url']}"
            lines.append(line)

        user_msg = (
            "Identify the service for each sender. Match your output index to the input index.\n\n"
            + "\n".join(lines)
            + '\n\nReply with JSON: {"results": [...]}'
        )

        payload: dict[str, Any] = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": _BATCH_SYSTEM_PROMPT},
                {"role": "user", "content": user_msg},
            ],
            "format": "json",
            "stream": False,
            "options": {"temperature": 0},
        }

        raw = await self._post(
            f"{self._base_url}/api/chat",
            json_data=payload,
            label="Ollama",
            timeout=self._timeout_seconds,
        )
        return self._parse_batch_response(raw, expected_count=len(accounts))

    @staticmethod
    def _parse_batch_response(
        raw: Any, expected_count: int
    ) -> OllamaBatchInterpretation:
        """
        Parse a batch Ollama response into a positional result list.

        Entries that are missing or malformed are set to None so the caller
        can fall open on individual failures without losing valid results.
        """
        if not isinstance(raw, dict):
            raise ProviderSchemaError("Ollama batch: response is not a JSON object")

        message = raw.get("message", {})
        if not isinstance(message, dict):
            raise ProviderSchemaError(
                "Ollama batch: 'message' missing or not an object"
            )

        content = message.get("content", "")
        if not isinstance(content, str) or not content.strip():
            raise ProviderSchemaError("Ollama batch: empty content in response")

        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as exc:
            raise ProviderSchemaError(
                f"Ollama batch: JSON parse failed: {exc}"
            ) from exc

        if not isinstance(parsed, dict):
            raise ProviderSchemaError("Ollama batch: content is not a JSON object")

        raw_results = parsed.get("results")
        if not isinstance(raw_results, list):
            raise ProviderSchemaError("Ollama batch: 'results' missing or not an array")

        slot: list[OllamaAccountInterpretation | None] = [None] * expected_count

        for item in raw_results:
            if not isinstance(item, dict):
                continue
            index = item.get("index")
            # bool is a subclass of int — reject it
            if isinstance(index, bool) or not isinstance(index, int):
                continue
            if not (0 <= index < expected_count):
                continue
            try:
                slot[index] = OllamaProvider._validate_interpretation_dict(item)
            except ProviderSchemaError:
                pass  # leave None, caller fails open

        return {"results": slot}

    # ------------------------------------------------------------------
    # Shared validation
    # ------------------------------------------------------------------

    @staticmethod
    def _validate_interpretation_dict(d: dict[str, Any]) -> OllamaAccountInterpretation:
        """Validate and normalise a raw interpretation dict (single or batch item)."""
        service_name = d.get("service_name")
        display_name = d.get("display_name")
        confidence = d.get("confidence")

        if not isinstance(service_name, str) or not service_name.strip():
            raise ProviderSchemaError("Ollama: 'service_name' missing or empty")
        if not isinstance(display_name, str) or not display_name.strip():
            raise ProviderSchemaError("Ollama: 'display_name' missing or empty")
        # bool is a subclass of int in Python — reject it explicitly
        if (
            isinstance(confidence, bool)
            or not isinstance(confidence, int)
            or not (0 <= confidence <= 100)
        ):
            raise ProviderSchemaError(
                "Ollama: 'confidence' must be an integer between 0 and 100"
            )

        service_name_clean = service_name.strip().lower()
        if len(service_name_clean) > _MAX_SERVICE_NAME_LEN:
            raise ProviderSchemaError(
                f"Ollama: 'service_name' exceeds {_MAX_SERVICE_NAME_LEN} characters"
            )
        if not service_name_clean.isascii() or not _SERVICE_SLUG_RE.fullmatch(
            service_name_clean
        ):
            raise ProviderSchemaError(
                "Ollama: 'service_name' must be a lowercase ASCII slug "
                "(letters, digits, hyphens)"
            )

        display_name_clean = display_name.strip()
        if len(display_name_clean) > _MAX_DISPLAY_NAME_LEN:
            raise ProviderSchemaError(
                f"Ollama: 'display_name' exceeds {_MAX_DISPLAY_NAME_LEN} characters"
            )
        if not display_name_clean.isprintable():
            raise ProviderSchemaError(
                "Ollama: 'display_name' contains invalid characters"
            )

        result: OllamaAccountInterpretation = {
            "service_name": service_name_clean,
            "display_name": display_name_clean,
            "confidence": confidence,
        }

        reason = d.get("reason")
        if isinstance(reason, str) and reason.strip():
            reason_clean = reason.strip().replace("\r", " ").replace("\n", " ")
            if reason_clean.isprintable():
                result["reason"] = reason_clean[:_MAX_REASON_LEN]

        return result


__all__ = ["OllamaProvider"]
