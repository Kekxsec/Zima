# tests/unit/email_accounts/test_interpretation.py
from datetime import UTC, datetime
from unittest.mock import AsyncMock, patch

import pytest

from backend.app.email_accounts.interpretation import (
    _is_ambiguous,
    _is_service_domain_aligned,
    interpret_accounts,
    interpret_accounts_with_stats,
)
from backend.app.email_accounts.schemas import DiscoveredAccountDraft
from backend.app.providers.base.exceptions import ProviderError


def _draft(
    service_name: str = "someservice.com",
    display_name: str = "someservice.com",
    sender_domain: str = "someservice.com",
    confidence_score: int = 30,
    email_count: int = 5,
) -> DiscoveredAccountDraft:
    return DiscoveredAccountDraft(
        service_name=service_name,
        display_name=display_name,
        email_used="user@example.com",
        source_type="inbox",
        sender_domain=sender_domain,
        login_url=None,
        password_reset_url=None,
        first_seen_at=datetime.now(UTC),
        last_seen_at=datetime.now(UTC),
        email_count=email_count,
        confidence_score=confidence_score,
    )


def _apply_settings(
    mock,
    *,
    mode: str = "enforce",
    max_candidates: int = 10,
    min_confidence: int = 70,
) -> None:
    """Apply a standard settings block to a MagicMock."""
    mock.ollama_enabled = True
    mock.ollama_mode = mode
    mock.ollama_base_url = "http://localhost:11434"
    mock.ollama_model = "gemma2:2b"
    mock.ollama_timeout_seconds = 30
    mock.ollama_max_candidates_per_batch = max_candidates
    mock.ollama_min_confidence = min_confidence
    mock.ollama_embed_enabled = False
    mock.ollama_require_domain_alignment = False


# ---------------------------------------------------------------------------
# _is_ambiguous
# ---------------------------------------------------------------------------


def test_is_ambiguous_domain_derived() -> None:
    draft = _draft(
        service_name="someservice.com",
        sender_domain="someservice.com",
        confidence_score=80,
    )
    assert _is_ambiguous(draft) is True


def test_is_ambiguous_root_label_match() -> None:
    draft = _draft(
        service_name="someservice", sender_domain="someservice.com", confidence_score=80
    )
    assert _is_ambiguous(draft) is True


def test_is_ambiguous_low_confidence() -> None:
    draft = _draft(
        service_name="netflix", sender_domain="netflix.com", confidence_score=40
    )
    assert _is_ambiguous(draft) is True


def test_is_not_ambiguous_curated() -> None:
    # service_name differs from domain root AND confidence is high → not ambiguous
    draft = _draft(
        service_name="streaming-service", sender_domain="nflx.com", confidence_score=90
    )
    assert _is_ambiguous(draft) is False


def test_is_service_domain_aligned_exact_match() -> None:
    assert _is_service_domain_aligned("receipts.charlestyrwhitt.com", "charlestyrwhitt")


def test_is_service_domain_aligned_prefix_wrapped_domain() -> None:
    assert _is_service_domain_aligned("myworkday.com", "workday")


def test_is_service_domain_aligned_mismatch() -> None:
    assert not _is_service_domain_aligned("vitamojo.com", "vimeo")


def test_is_service_domain_aligned_blocks_generic_relabel() -> None:
    assert not _is_service_domain_aligned("lloydsbank.co.uk", "banking")


# ---------------------------------------------------------------------------
# interpret_accounts — mode/enabled guards
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_mode_off_skips_ollama() -> None:
    drafts = [_draft()]
    with patch("backend.app.email_accounts.interpretation.settings") as mock_settings:
        mock_settings.ollama_enabled = True
        mock_settings.ollama_mode = "off"
        result = await interpret_accounts(drafts, {})
    assert result is drafts


@pytest.mark.asyncio
async def test_not_enabled_skips_ollama() -> None:
    drafts = [_draft()]
    with patch("backend.app.email_accounts.interpretation.settings") as mock_settings:
        mock_settings.ollama_enabled = False
        mock_settings.ollama_mode = "assist"
        result = await interpret_accounts(drafts, {})
    assert result is drafts


# ---------------------------------------------------------------------------
# interpret_accounts — shadow mode
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_shadow_does_not_apply_changes() -> None:
    draft = _draft(
        service_name="someservice.com",
        sender_domain="someservice.com",
        confidence_score=20,
    )
    interpretation = {
        "service_name": "netflix",
        "display_name": "Netflix",
        "confidence": 95,
    }
    mock_batch = AsyncMock(return_value={"results": [interpretation]})

    with (
        patch("backend.app.email_accounts.interpretation.settings") as mock_settings,
        patch(
            "backend.app.email_accounts.interpretation.OllamaProvider.interpret_accounts_batch",
            new=mock_batch,
        ),
    ):
        _apply_settings(mock_settings, mode="shadow")
        result = await interpret_accounts([draft], {})

    assert result[0].service_name == "someservice.com"


# ---------------------------------------------------------------------------
# interpret_accounts — assist mode
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_assist_high_confidence_applies() -> None:
    draft = _draft(
        service_name="someservice.com",
        sender_domain="someservice.com",
        confidence_score=20,
    )
    interpretation = {
        "service_name": "netflix",
        "display_name": "Netflix",
        "confidence": 85,
    }
    mock_batch = AsyncMock(return_value={"results": [interpretation]})

    with (
        patch("backend.app.email_accounts.interpretation.settings") as mock_settings,
        patch(
            "backend.app.email_accounts.interpretation.OllamaProvider.interpret_accounts_batch",
            new=mock_batch,
        ),
    ):
        _apply_settings(mock_settings, mode="assist", min_confidence=70)
        result = await interpret_accounts([draft], {})

    assert result[0].service_name == "netflix"
    assert result[0].display_name == "Netflix"


@pytest.mark.asyncio
async def test_assist_high_confidence_alignment_required_blocks_mismatch() -> None:
    draft = _draft(
        service_name="vitamojo",
        display_name="Vitamojo",
        sender_domain="vitamojo.com",
        confidence_score=20,
    )
    interpretation = {
        "service_name": "vimeo",
        "display_name": "Vimeo",
        "confidence": 95,
    }
    mock_batch = AsyncMock(return_value={"results": [interpretation]})

    with (
        patch("backend.app.email_accounts.interpretation.settings") as mock_settings,
        patch(
            "backend.app.email_accounts.interpretation.OllamaProvider.interpret_accounts_batch",
            new=mock_batch,
        ),
    ):
        _apply_settings(mock_settings, mode="assist", min_confidence=70)
        mock_settings.ollama_require_domain_alignment = True
        result = await interpret_accounts([draft], {})

    # Blocked by domain alignment guard despite high confidence.
    assert result[0].service_name == "vitamojo"
    assert result[0].display_name == "Vitamojo"


@pytest.mark.asyncio
async def test_assist_low_confidence_no_apply() -> None:
    draft = _draft(
        service_name="someservice.com",
        sender_domain="someservice.com",
        confidence_score=20,
    )
    interpretation = {
        "service_name": "netflix",
        "display_name": "Netflix",
        "confidence": 55,
    }
    mock_batch = AsyncMock(return_value={"results": [interpretation]})

    with (
        patch("backend.app.email_accounts.interpretation.settings") as mock_settings,
        patch(
            "backend.app.email_accounts.interpretation.OllamaProvider.interpret_accounts_batch",
            new=mock_batch,
        ),
    ):
        _apply_settings(mock_settings, mode="assist", min_confidence=70)
        result = await interpret_accounts([draft], {})

    assert result[0].service_name == "someservice.com"


# ---------------------------------------------------------------------------
# interpret_accounts — enforce mode
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_enforce_always_applies() -> None:
    draft = _draft(
        service_name="someservice.com",
        sender_domain="someservice.com",
        confidence_score=20,
    )
    interpretation = {
        "service_name": "netflix",
        "display_name": "Netflix",
        "confidence": 30,
    }
    mock_batch = AsyncMock(return_value={"results": [interpretation]})

    with (
        patch("backend.app.email_accounts.interpretation.settings") as mock_settings,
        patch(
            "backend.app.email_accounts.interpretation.OllamaProvider.interpret_accounts_batch",
            new=mock_batch,
        ),
    ):
        _apply_settings(mock_settings, mode="enforce")
        result = await interpret_accounts([draft], {})

    assert result[0].service_name == "netflix"


# ---------------------------------------------------------------------------
# interpret_accounts — review_all mode
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_review_all_applies_to_non_ambiguous_accounts() -> None:
    draft = _draft(
        service_name="netflix", sender_domain="nflx.com", confidence_score=95
    )
    interpretation = {
        "service_name": "netflix",
        "display_name": "Netflix, Inc.",
        "confidence": 99,
    }
    mock_batch = AsyncMock(return_value={"results": [interpretation]})

    with (
        patch("backend.app.email_accounts.interpretation.settings") as mock_settings,
        patch(
            "backend.app.email_accounts.interpretation.OllamaProvider.interpret_accounts_batch",
            new=mock_batch,
        ),
    ):
        _apply_settings(mock_settings, mode="enforce", max_candidates=1)
        result = await interpret_accounts([draft], {}, review_all=True)

    assert result[0].display_name == "Netflix, Inc."


@pytest.mark.asyncio
async def test_max_candidates_override_bypasses_default_cap() -> None:
    drafts = [
        _draft(
            service_name=f"service{i}.com",
            sender_domain=f"service{i}.com",
            confidence_score=10,
        )
        for i in range(3)
    ]
    mock_batch = AsyncMock(
        return_value={
            "results": [
                {
                    "service_name": "netflix",
                    "display_name": "Netflix",
                    "confidence": 90,
                },
                {
                    "service_name": "netflix",
                    "display_name": "Netflix",
                    "confidence": 90,
                },
                {
                    "service_name": "netflix",
                    "display_name": "Netflix",
                    "confidence": 90,
                },
            ]
        }
    )

    with (
        patch("backend.app.email_accounts.interpretation.settings") as mock_settings,
        patch(
            "backend.app.email_accounts.interpretation.OllamaProvider.interpret_accounts_batch",
            new=mock_batch,
        ),
    ):
        # default cap=1 is overridden by max_candidates=0 (unlimited)
        _apply_settings(mock_settings, mode="enforce", max_candidates=1)
        result = await interpret_accounts(drafts, {}, review_all=True, max_candidates=0)

    # All 3 were updated despite the per-settings cap of 1
    assert all(d.service_name == "netflix" for d in result)


@pytest.mark.asyncio
async def test_force_ollama_reviews_all_candidates_in_chunks() -> None:
    drafts = [
        _draft(
            service_name=f"service{i}.com",
            sender_domain=f"service{i}.com",
            confidence_score=10,
        )
        for i in range(3)
    ]
    mock_batch = AsyncMock(
        side_effect=[
            {
                "results": [
                    {
                        "service_name": "netflix",
                        "display_name": "Netflix",
                        "confidence": 90,
                    },
                    {
                        "service_name": "netflix",
                        "display_name": "Netflix",
                        "confidence": 90,
                    },
                ]
            },
            {
                "results": [
                    {
                        "service_name": "netflix",
                        "display_name": "Netflix",
                        "confidence": 90,
                    },
                ]
            },
        ]
    )

    with (
        patch("backend.app.email_accounts.interpretation.settings") as mock_settings,
        patch(
            "backend.app.email_accounts.interpretation.OllamaProvider.interpret_accounts_batch",
            new=mock_batch,
        ),
    ):
        _apply_settings(mock_settings, mode="enforce", max_candidates=1)
        result, stats = await interpret_accounts_with_stats(
            drafts,
            {},
            review_all=True,
            max_candidates=0,
            force_ollama=True,
            batch_size=2,
        )

    assert all(d.service_name == "netflix" for d in result)
    assert stats["candidates_attempted"] == 3
    assert stats["lookup_resolved"] == 0
    assert stats["embedding_resolved"] == 0
    assert stats["ollama_queued"] == 3
    assert stats["ollama_batches"] == 2
    assert stats["ollama_succeeded"] == 3
    assert stats["ollama_failed"] == 0


# ---------------------------------------------------------------------------
# interpret_accounts — lookup table tier (Tier 1)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_lookup_table_bypasses_batch() -> None:
    """Domain in lookup table should be resolved immediately; batch must not be called."""
    draft = _draft(
        service_name="amazon.com",
        display_name="amazon.com",
        sender_domain="amazon.com",
        confidence_score=20,
    )
    mock_batch = AsyncMock()

    with (
        patch("backend.app.email_accounts.interpretation.settings") as mock_settings,
        patch(
            "backend.app.email_accounts.interpretation.OllamaProvider.interpret_accounts_batch",
            new=mock_batch,
        ),
    ):
        _apply_settings(mock_settings, mode="enforce")
        result = await interpret_accounts([draft], {})

    mock_batch.assert_not_called()
    assert result[0].service_name == "amazon"
    assert result[0].display_name == "Amazon"


@pytest.mark.asyncio
async def test_lookup_table_miss_falls_through_to_batch() -> None:
    """Unknown domain should miss Tier 1 and be processed by Tier 3 batch."""
    draft = _draft(
        service_name="unknownxyz.com",
        sender_domain="unknownxyz.com",
        confidence_score=20,
    )
    interpretation = {
        "service_name": "unknown-xyz",
        "display_name": "Unknown XYZ",
        "confidence": 80,
    }
    mock_batch = AsyncMock(return_value={"results": [interpretation]})

    with (
        patch("backend.app.email_accounts.interpretation.settings") as mock_settings,
        patch(
            "backend.app.email_accounts.interpretation.OllamaProvider.interpret_accounts_batch",
            new=mock_batch,
        ),
    ):
        _apply_settings(mock_settings, mode="enforce")
        result = await interpret_accounts([draft], {})

    mock_batch.assert_called_once()
    assert result[0].service_name == "unknown-xyz"


# ---------------------------------------------------------------------------
# interpret_accounts — error handling + batch cap
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_provider_error_fails_open() -> None:
    draft = _draft(
        service_name="someservice.com",
        sender_domain="someservice.com",
        confidence_score=20,
    )
    mock_batch = AsyncMock(side_effect=ProviderError("connection refused"))

    with (
        patch("backend.app.email_accounts.interpretation.settings") as mock_settings,
        patch(
            "backend.app.email_accounts.interpretation.OllamaProvider.interpret_accounts_batch",
            new=mock_batch,
        ),
    ):
        _apply_settings(mock_settings, mode="enforce")
        result = await interpret_accounts([draft], {})

    assert result[0].service_name == "someservice.com"


@pytest.mark.asyncio
async def test_batch_cap_respected() -> None:
    drafts = [
        _draft(
            service_name=f"service{i}.com",
            sender_domain=f"service{i}.com",
            confidence_score=10,
        )
        for i in range(5)
    ]
    mock_batch = AsyncMock(
        return_value={
            "results": [
                {
                    "service_name": "netflix",
                    "display_name": "Netflix",
                    "confidence": 90,
                },
                {
                    "service_name": "netflix",
                    "display_name": "Netflix",
                    "confidence": 90,
                },
                {
                    "service_name": "netflix",
                    "display_name": "Netflix",
                    "confidence": 90,
                },
            ]
        }
    )

    with (
        patch("backend.app.email_accounts.interpretation.settings") as mock_settings,
        patch(
            "backend.app.email_accounts.interpretation.OllamaProvider.interpret_accounts_batch",
            new=mock_batch,
        ),
    ):
        _apply_settings(mock_settings, mode="enforce", max_candidates=3)
        result = await interpret_accounts(drafts, {})

    mock_batch.assert_called_once()
    # First 3 updated, last 2 are beyond the cap and remain unchanged
    assert result[0].service_name == "netflix"
    assert result[1].service_name == "netflix"
    assert result[2].service_name == "netflix"
    assert result[3].service_name == "service3.com"
    assert result[4].service_name == "service4.com"


@pytest.mark.asyncio
async def test_batch_cap_respected_when_provider_errors() -> None:
    drafts = [
        _draft(
            service_name=f"service{i}.com",
            sender_domain=f"service{i}.com",
            confidence_score=10,
        )
        for i in range(5)
    ]
    mock_batch = AsyncMock(side_effect=ProviderError("connection refused"))

    with (
        patch("backend.app.email_accounts.interpretation.settings") as mock_settings,
        patch(
            "backend.app.email_accounts.interpretation.OllamaProvider.interpret_accounts_batch",
            new=mock_batch,
        ),
    ):
        _apply_settings(mock_settings, mode="enforce", max_candidates=3)
        result = await interpret_accounts(drafts, {})

    assert [d.service_name for d in result] == [f"service{i}.com" for i in range(5)]
