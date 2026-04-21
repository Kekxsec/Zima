# backend/app/email_accounts/interpretation.py
"""
AccountInterpretationService — enriches ambiguous DiscoveredAccountDrafts
using a three-tier resolution pipeline:

  1. Domain lookup table  — instant, zero-inference, covers ~80% of senders.
  2. Fastembed similarity — optional CPU-only fallback (OLLAMA_EMBED_ENABLED).
  3. Ollama batch inference — remaining ambiguous accounts sent in one call.

Behaviour is controlled by ollama_mode in settings:
  off      — skip entirely, return drafts unchanged
  shadow   — resolve via all tiers, log suggestions, do NOT apply
  assist   — apply when model confidence >= ollama_min_confidence
  enforce  — apply all structurally-valid outputs

Fails open: any error in any tier leaves the draft unchanged.
No raw email bodies are passed to the model — only sender_domain,
subject lines (text only), current best-guess name, and email count.
"""

from __future__ import annotations

import asyncio
import re
from collections import defaultdict
from typing import TypedDict

from backend.app.core.config import settings
from backend.app.core.logging import get_logger
from backend.app.email_accounts.schemas import DiscoveredAccountDraft
from backend.app.providers.ai.ollama import lookup_table
from backend.app.providers.ai.ollama.client import OllamaProvider
from backend.app.providers.ai.ollama.schemas import (
    OllamaAccountContext,
    OllamaAccountInterpretation,
)
from backend.app.providers.base.exceptions import ProviderError
from backend.app.providers.tools.mbox_parser.models import ParsedEmail

# Cap concurrent Ollama calls across all background tasks. With batch
# inference we make far fewer calls, but the semaphore guards against
# concurrent scans queuing up on a serial Ollama instance.
_OLLAMA_SEMAPHORE = asyncio.Semaphore(2)

logger = get_logger(__name__)

_DOMAIN_TOKEN_RE = re.compile(r"[a-z0-9]+")
_COMPOUND_CC_TLD_HINTS = {"co", "com", "net", "org", "gov", "ac"}
_GENERIC_SERVICE_TOKENS = {
    "service",
    "services",
    "account",
    "accounts",
    "bank",
    "banking",
    "portal",
    "platform",
    "security",
    "cybersecurity",
    "payment",
    "payments",
}


class InterpretationStats(TypedDict):
    total_drafts: int
    candidates_attempted: int
    lookup_resolved: int
    embedding_resolved: int
    ollama_queued: int
    ollama_batches: int
    ollama_succeeded: int
    ollama_failed: int


def build_subjects_map(emails: list[ParsedEmail]) -> dict[str, list[str]]:
    """
    Build a mapping of raw sender_domain → subject lines from the parsed email
    list. Used to supply sample subjects to Ollama without sending email bodies.
    """
    result: dict[str, list[str]] = defaultdict(list)
    for msg in emails:
        if msg.sender_domain and msg.subject:
            result[msg.sender_domain].append(msg.subject)
    return dict(result)


def _is_ambiguous(draft: DiscoveredAccountDraft) -> bool:
    """
    True when the draft's service_name was derived from the raw domain rather
    than a curated ServiceRegistry match, making it a candidate for enrichment.
    """
    domain = draft.sender_domain or ""
    name = (draft.service_name or "").lower()
    domain_lower = domain.lower()
    root_label = domain_lower.split(".")[0]
    name_is_domain_derived = name in (domain_lower, root_label)
    return name_is_domain_derived or draft.confidence_score < 50


def _normalized_service_token(service_name: str) -> str:
    return "".join(ch for ch in service_name.lower() if ch.isalnum())


def _domain_tokens(sender_domain: str) -> set[str]:
    domain = sender_domain.strip().lower()
    if not domain:
        return set()

    labels = [label for label in domain.split(".") if label]
    if not labels:
        return set()

    # Approximate the registrable root label (e.g. lloydsbank.co.uk -> lloydsbank).
    if (
        len(labels) >= 3
        and len(labels[-1]) == 2
        and labels[-2] in _COMPOUND_CC_TLD_HINTS
    ):
        root_label = labels[-3]
    elif len(labels) >= 2:
        root_label = labels[-2]
    else:
        root_label = labels[0]

    tokens: set[str] = set()
    for label in labels:
        for token in _DOMAIN_TOKEN_RE.findall(label):
            if len(token) >= 2:
                tokens.add(token)

    for token in _DOMAIN_TOKEN_RE.findall(root_label):
        if len(token) >= 2:
            tokens.add(token)

    return tokens


def _is_service_domain_aligned(sender_domain: str, suggested_service: str) -> bool:
    """
    Return True when the suggested service appears plausibly tied to sender domain.

    This is a lightweight heuristic to block obvious mismatches such as:
    - vitamojo.com -> vimeo
    - lloydsbank.co.uk -> banking
    """
    if not sender_domain:
        return True

    domain_tokens = _domain_tokens(sender_domain)
    if not domain_tokens:
        return True

    service_token = _normalized_service_token(suggested_service)
    if len(service_token) < 2:
        return True

    if service_token in domain_tokens:
        return True

    for domain_token in domain_tokens:
        # Permit common prefix/suffix wrapping (e.g. myworkday -> workday).
        if len(service_token) >= 4 and (
            service_token in domain_token or domain_token in service_token
        ):
            return True

    # Avoid overly generic service relabels when there is no domain overlap.
    if service_token in _GENERIC_SERVICE_TOKENS:
        return False

    return False


def _apply_interpretation(
    draft: DiscoveredAccountDraft,
    interpretation: OllamaAccountInterpretation,
    mode: str,
    require_domain_alignment: bool,
    source: str,
) -> DiscoveredAccountDraft:
    """Apply an interpretation to a draft according to current mode settings."""
    model_confidence = interpretation["confidence"]
    confidence_allows_apply = mode == "enforce" or (
        mode == "assist" and model_confidence >= settings.ollama_min_confidence
    )
    alignment_ok = _is_service_domain_aligned(
        draft.sender_domain or "",
        interpretation["service_name"],
    )
    should_apply = confidence_allows_apply and (
        not require_domain_alignment or alignment_ok
    )

    logger.info(
        "ollama.interpret_account.result",
        sender_domain=draft.sender_domain,
        current_guess=draft.service_name,
        suggested_service=interpretation["service_name"],
        suggested_display=interpretation["display_name"],
        model_confidence=model_confidence,
        mode=mode,
        source=source,
        alignment_required=require_domain_alignment,
        alignment_ok=alignment_ok,
        blocked_by_alignment=(
            confidence_allows_apply and require_domain_alignment and not alignment_ok
        ),
        applied=should_apply,
    )

    if should_apply:
        return DiscoveredAccountDraft(
            **{
                **draft.model_dump(),
                "service_name": interpretation["service_name"],
                "display_name": interpretation["display_name"],
            }
        )
    return draft


def _build_context(
    draft: DiscoveredAccountDraft,
    subjects_map: dict[str, list[str]],
) -> OllamaAccountContext:
    ctx: OllamaAccountContext = {
        "sender_domain": draft.sender_domain or "",
        "sample_subjects": subjects_map.get(draft.sender_domain or "", []),
        "current_guess": draft.service_name or "",
        "email_count": draft.email_count,
    }
    if draft.login_url:
        ctx["login_url"] = draft.login_url
    if draft.unsubscribe_url:
        ctx["unsubscribe_url"] = draft.unsubscribe_url
    return ctx


async def interpret_accounts_with_stats(
    drafts: list[DiscoveredAccountDraft],
    subjects_map: dict[str, list[str]],
    *,
    review_all: bool = False,
    max_candidates: int | None = None,
    force_ollama: bool = False,
    batch_size: int | None = None,
) -> tuple[list[DiscoveredAccountDraft], InterpretationStats]:
    """
    Enrich drafts via lookup/embed/Ollama and return detailed execution stats.

    force_ollama:
      - False (default): use lookup + embed short-circuit before Ollama.
      - True: skip lookup/embed and send every candidate directly to Ollama.

    batch_size:
      - None: falls back to settings.ollama_max_candidates_per_batch.
      - >0: explicit per-request batch size for Ollama calls.
      - <=0: treated as 1.
    """
    stats: InterpretationStats = {
        "total_drafts": len(drafts),
        "candidates_attempted": 0,
        "lookup_resolved": 0,
        "embedding_resolved": 0,
        "ollama_queued": 0,
        "ollama_batches": 0,
        "ollama_succeeded": 0,
        "ollama_failed": 0,
    }

    mode = settings.ollama_mode
    if not settings.ollama_enabled or mode == "off":
        return drafts, stats

    require_domain_alignment = (
        getattr(settings, "ollama_require_domain_alignment", False) is True
    )
    candidate_limit = (
        settings.ollama_max_candidates_per_batch
        if max_candidates is None
        else max_candidates
    )
    resolved_batch_size = (
        settings.ollama_max_candidates_per_batch if batch_size is None else batch_size
    )
    if resolved_batch_size <= 0:
        resolved_batch_size = 1

    # result_map holds the resolved draft for each position; starts as the
    # original draft and is overwritten when a tier resolves it.
    result_map: dict[int, DiscoveredAccountDraft] = dict(enumerate(drafts))
    # ollama_queue: positions that still need Ollama after lookup/embed tiers
    ollama_queue: list[tuple[int, DiscoveredAccountDraft]] = []

    # ------------------------------------------------------------------
    # Tier 1/2 candidate selection
    # ------------------------------------------------------------------
    for idx, draft in enumerate(drafts):
        if not review_all and not _is_ambiguous(draft):
            continue

        if candidate_limit > 0 and stats["candidates_attempted"] >= candidate_limit:
            break

        stats["candidates_attempted"] += 1

        if force_ollama:
            ollama_queue.append((idx, draft))
            continue

        # ------------------------------------------------------------------
        # Tier 1: domain lookup table
        # ------------------------------------------------------------------
        interpretation = lookup_table.lookup(draft.sender_domain or "")
        if interpretation is not None:
            result_map[idx] = _apply_interpretation(
                draft, interpretation, mode, require_domain_alignment, "lookup"
            )
            stats["lookup_resolved"] += 1
            continue

        # ------------------------------------------------------------------
        # Tier 2: fastembed similarity (optional)
        # ------------------------------------------------------------------
        if getattr(settings, "ollama_embed_enabled", False):
            try:
                from backend.app.providers.ai.ollama.embeddings import (
                    query_embedding,  # noqa: PLC0415
                )

                embed_result = query_embedding(draft.sender_domain or "")
                if embed_result is not None:
                    result_map[idx] = _apply_interpretation(
                        draft, embed_result, mode, require_domain_alignment, "embedding"
                    )
                    stats["embedding_resolved"] += 1
                    continue
            except ImportError:
                pass  # fastembed not installed — skip silently

        # Queue for Ollama batch
        ollama_queue.append((idx, draft))

    # ------------------------------------------------------------------
    # Tier 3: Ollama batch inference
    # ------------------------------------------------------------------
    stats["ollama_queued"] = len(ollama_queue)
    if ollama_queue:
        provider = OllamaProvider(
            base_url=settings.ollama_base_url,
            model=settings.ollama_model,
            timeout_seconds=settings.ollama_timeout_seconds,
        )
        for start in range(0, len(ollama_queue), resolved_batch_size):
            chunk = ollama_queue[start : start + resolved_batch_size]
            contexts = [_build_context(d, subjects_map) for _, d in chunk]
            stats["ollama_batches"] += 1

            # Items still needing resolution after the batch attempt
            pending: list[tuple[int, DiscoveredAccountDraft, OllamaAccountContext]] = [
                (idx, draft, ctx)
                for (idx, draft), ctx in zip(chunk, contexts, strict=True)
            ]

            try:
                async with _OLLAMA_SEMAPHORE:
                    batch_result = await provider.interpret_accounts_batch(
                        {"accounts": contexts}
                    )
                raw_results = batch_result["results"]
                still_pending = []
                for position, (idx, draft, ctx) in enumerate(pending):
                    interpretation = (
                        raw_results[position] if position < len(raw_results) else None
                    )
                    if interpretation is not None:
                        stats["ollama_succeeded"] += 1
                        result_map[idx] = _apply_interpretation(
                            draft,
                            interpretation,
                            mode,
                            require_domain_alignment,
                            "ollama",
                        )
                    else:
                        still_pending.append((idx, draft, ctx))
                pending = still_pending
            except ProviderError as exc:
                logger.warning(
                    "ollama.batch.failed",
                    queued=len(chunk),
                    error=str(exc),
                )
                # All items remain pending for per-item retry below

            # Per-item retry for anything the batch did not resolve.
            # gemma2:2b often omits the index field in batch responses; the
            # single-account prompt has no index requirement and succeeds more
            # reliably.
            for idx, draft, item_ctx in pending:
                try:
                    async with _OLLAMA_SEMAPHORE:
                        interp = await provider.interpret_account(item_ctx)
                    stats["ollama_succeeded"] += 1
                    result_map[idx] = _apply_interpretation(
                        draft, interp, mode, require_domain_alignment, "ollama_retry"
                    )
                except ProviderError as exc:
                    stats["ollama_failed"] += 1
                    logger.debug(
                        "ollama.single_retry.failed",
                        domain=draft.sender_domain,
                        error=str(exc),
                    )

    return [result_map[i] for i in range(len(drafts))], stats


async def interpret_accounts(
    drafts: list[DiscoveredAccountDraft],
    subjects_map: dict[str, list[str]],
    *,
    review_all: bool = False,
    max_candidates: int | None = None,
) -> list[DiscoveredAccountDraft]:
    """
    Backward-compatible wrapper that returns only interpreted drafts.
    """
    interpreted, _ = await interpret_accounts_with_stats(
        drafts,
        subjects_map,
        review_all=review_all,
        max_candidates=max_candidates,
    )
    return interpreted
