# tests/unit/providers/ai/test_ollama_client.py
import json
from unittest.mock import AsyncMock, patch

import pytest

from backend.app.providers.ai.ollama import lookup_table
from backend.app.providers.ai.ollama.client import OllamaProvider
from backend.app.providers.base.exceptions import ProviderSchemaError


def _make_raw(content: str) -> dict:
    return {"message": {"content": content}}


@pytest.fixture
def provider() -> OllamaProvider:
    return OllamaProvider(base_url="http://localhost:11434", model="llama3.2")


# ---------------------------------------------------------------------------
# _parse_account_response
# ---------------------------------------------------------------------------


def test_parse_valid_response() -> None:
    raw = _make_raw(
        '{"service_name": "Netflix", "display_name": "Netflix", "confidence": 90, "reason": "Clear branding"}'
    )
    result = OllamaProvider._parse_account_response(raw)
    assert result["service_name"] == "netflix"
    assert result["display_name"] == "Netflix"
    assert result["confidence"] == 90
    assert result["reason"] == "Clear branding"


def test_parse_optional_reason_absent() -> None:
    raw = _make_raw(
        '{"service_name": "spotify", "display_name": "Spotify", "confidence": 80}'
    )
    result = OllamaProvider._parse_account_response(raw)
    assert "reason" not in result


def test_service_name_lowercased() -> None:
    raw = _make_raw(
        '{"service_name": "NETFLIX", "display_name": "Netflix", "confidence": 75}'
    )
    result = OllamaProvider._parse_account_response(raw)
    assert result["service_name"] == "netflix"


def test_parse_missing_service_name() -> None:
    raw = _make_raw('{"display_name": "Netflix", "confidence": 90}')
    with pytest.raises(ProviderSchemaError, match="service_name"):
        OllamaProvider._parse_account_response(raw)


def test_parse_empty_service_name() -> None:
    raw = _make_raw(
        '{"service_name": "  ", "display_name": "Netflix", "confidence": 90}'
    )
    with pytest.raises(ProviderSchemaError, match="service_name"):
        OllamaProvider._parse_account_response(raw)


def test_parse_missing_display_name() -> None:
    raw = _make_raw('{"service_name": "netflix", "confidence": 90}')
    with pytest.raises(ProviderSchemaError, match="display_name"):
        OllamaProvider._parse_account_response(raw)


def test_parse_confidence_out_of_range() -> None:
    raw = _make_raw(
        '{"service_name": "netflix", "display_name": "Netflix", "confidence": 150}'
    )
    with pytest.raises(ProviderSchemaError, match="confidence"):
        OllamaProvider._parse_account_response(raw)


def test_parse_confidence_wrong_type() -> None:
    raw = _make_raw(
        '{"service_name": "netflix", "display_name": "Netflix", "confidence": "high"}'
    )
    with pytest.raises(ProviderSchemaError, match="confidence"):
        OllamaProvider._parse_account_response(raw)


def test_parse_bad_json_in_content() -> None:
    raw = _make_raw("not json at all")
    with pytest.raises(ProviderSchemaError, match="JSON parse failed"):
        OllamaProvider._parse_account_response(raw)


def test_parse_content_not_object() -> None:
    raw = _make_raw("[1, 2, 3]")
    with pytest.raises(ProviderSchemaError, match="not a JSON object"):
        OllamaProvider._parse_account_response(raw)


# ---------------------------------------------------------------------------
# Hardening — output validation
# ---------------------------------------------------------------------------


def test_confidence_boolean_rejected() -> None:
    # bool is a subclass of int; True == 1 would previously pass the int check
    raw = _make_raw(
        '{"service_name": "netflix", "display_name": "Netflix", "confidence": true}'
    )
    with pytest.raises(ProviderSchemaError, match="confidence"):
        OllamaProvider._parse_account_response(raw)


def test_service_name_too_long() -> None:
    long_name = "a" * 65
    raw = _make_raw(
        f'{{"service_name": "{long_name}", "display_name": "X", "confidence": 80}}'
    )
    with pytest.raises(ProviderSchemaError, match="exceeds"):
        OllamaProvider._parse_account_response(raw)


def test_service_name_with_newline_rejected() -> None:
    raw = _make_raw(
        '{"service_name": "net\\nflix", "display_name": "Netflix", "confidence": 80}'
    )
    with pytest.raises(ProviderSchemaError, match="ASCII slug"):
        OllamaProvider._parse_account_response(raw)


def test_service_name_with_space_rejected() -> None:
    raw = _make_raw(
        '{"service_name": "acme corp", "display_name": "Acme Corp", "confidence": 80}'
    )
    with pytest.raises(ProviderSchemaError, match="ASCII slug"):
        OllamaProvider._parse_account_response(raw)


def test_service_name_non_ascii_rejected() -> None:
    raw = _make_raw(
        '{"service_name": "аcme", "display_name": "Acme", "confidence": 80}'
    )
    with pytest.raises(ProviderSchemaError, match="ASCII slug"):
        OllamaProvider._parse_account_response(raw)


def test_display_name_too_long() -> None:
    long_name = "A" * 129
    raw = _make_raw(
        f'{{"service_name": "netflix", "display_name": "{long_name}", "confidence": 80}}'
    )
    with pytest.raises(ProviderSchemaError, match="exceeds"):
        OllamaProvider._parse_account_response(raw)


def test_display_name_with_newline_rejected() -> None:
    raw = _make_raw(
        '{"service_name": "netflix", "display_name": "Net\\nflix", "confidence": 80}'
    )
    with pytest.raises(ProviderSchemaError, match="invalid characters"):
        OllamaProvider._parse_account_response(raw)


def test_reason_truncated_to_max_length() -> None:
    long_reason = "x" * 600
    raw = _make_raw(
        f'{{"service_name": "netflix", "display_name": "Netflix", "confidence": 80, "reason": "{long_reason}"}}'
    )
    result = OllamaProvider._parse_account_response(raw)
    assert len(result["reason"]) == 512  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Hardening — input sanitization
# ---------------------------------------------------------------------------


def test_sanitize_subjects_strips_html() -> None:
    subjects = ["<b>Your order</b>", "<a href='x'>Click here</a>"]
    result = OllamaProvider._sanitize_subjects(subjects)
    assert result == ["Your order", "Click here"]


def test_sanitize_subjects_truncates() -> None:
    long_subject = "A" * 200
    result = OllamaProvider._sanitize_subjects([long_subject])
    assert len(result[0]) == 120


def test_sanitize_subjects_caps_count() -> None:
    subjects = [f"subject {i}" for i in range(10)]
    result = OllamaProvider._sanitize_subjects(subjects)
    assert len(result) == 5


def test_sanitize_subjects_strips_newlines() -> None:
    result = OllamaProvider._sanitize_subjects(["line1\nline2\r\nline3"])
    assert "\n" not in result[0]
    assert "\r" not in result[0]


def test_sanitize_subjects_drops_empty_after_strip() -> None:
    result = OllamaProvider._sanitize_subjects(["<b></b>", "   ", "real subject"])
    assert result == ["real subject"]


# ---------------------------------------------------------------------------
# health_check
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_health_check_up(provider: OllamaProvider) -> None:
    with patch.object(provider, "_get", new=AsyncMock(return_value={"models": []})):
        assert await provider.health_check() is True


@pytest.mark.asyncio
async def test_health_check_down(provider: OllamaProvider) -> None:
    with patch.object(
        provider, "_get", new=AsyncMock(side_effect=Exception("refused"))
    ):
        assert await provider.health_check() is False


# ---------------------------------------------------------------------------
# list_models
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_models_returns_names(provider: OllamaProvider) -> None:
    payload = {"models": [{"name": "llama3.2"}, {"name": "mistral"}]}
    with patch.object(provider, "_get", new=AsyncMock(return_value=payload)):
        models = await provider.list_models()
    assert models == ["llama3.2", "mistral"]


@pytest.mark.asyncio
async def test_list_models_on_error(provider: OllamaProvider) -> None:
    with patch.object(
        provider, "_get", new=AsyncMock(side_effect=Exception("refused"))
    ):
        assert await provider.list_models() == []


# ---------------------------------------------------------------------------
# lookup_table
# ---------------------------------------------------------------------------


def test_lookup_exact_hit() -> None:
    result = lookup_table.lookup("netflix.com")
    assert result is not None
    assert result["service_name"] == "netflix"
    assert result["confidence"] == 100


def test_lookup_subdomain_strips_leading_label() -> None:
    result = lookup_table.lookup("email.amazon.com")
    assert result is not None
    assert result["service_name"] == "amazon"


def test_lookup_case_insensitive() -> None:
    result = lookup_table.lookup("NETFLIX.COM")
    assert result is not None
    assert result["service_name"] == "netflix"


def test_lookup_trailing_dot_normalised() -> None:
    result = lookup_table.lookup("netflix.com.")
    assert result is not None
    assert result["service_name"] == "netflix"


def test_lookup_miss_returns_none() -> None:
    result = lookup_table.lookup("unknownxyz123-not-real.com")
    assert result is None


# ---------------------------------------------------------------------------
# _parse_batch_response
# ---------------------------------------------------------------------------


def test_parse_batch_all_valid() -> None:
    results = [
        {
            "index": 0,
            "service_name": "netflix",
            "display_name": "Netflix",
            "confidence": 90,
        },
        {
            "index": 1,
            "service_name": "spotify",
            "display_name": "Spotify",
            "confidence": 85,
        },
    ]
    raw = _make_raw(json.dumps({"results": results}))
    result = OllamaProvider._parse_batch_response(raw, expected_count=2)
    assert result["results"][0] is not None
    assert result["results"][0]["service_name"] == "netflix"
    assert result["results"][1] is not None
    assert result["results"][1]["service_name"] == "spotify"


def test_parse_batch_partial_valid_leaves_none() -> None:
    results = [
        {
            "index": 0,
            "service_name": "netflix",
            "display_name": "Netflix",
            "confidence": 90,
        },
        {
            "index": 1,
            "service_name": "bad name!",
            "display_name": "Bad",
            "confidence": 80,
        },
    ]
    raw = _make_raw(json.dumps({"results": results}))
    result = OllamaProvider._parse_batch_response(raw, expected_count=2)
    assert result["results"][0] is not None
    assert result["results"][1] is None


def test_parse_batch_empty_results() -> None:
    raw = _make_raw('{"results": []}')
    result = OllamaProvider._parse_batch_response(raw, expected_count=0)
    assert result["results"] == []


def test_parse_batch_missing_index_skipped() -> None:
    # Item without 'index' must be ignored — slot stays None.
    results = [{"service_name": "netflix", "display_name": "Netflix", "confidence": 90}]
    raw = _make_raw(json.dumps({"results": results}))
    result = OllamaProvider._parse_batch_response(raw, expected_count=1)
    assert result["results"][0] is None


def test_parse_batch_out_of_bounds_index_ignored() -> None:
    results = [
        {
            "index": 99,
            "service_name": "netflix",
            "display_name": "Netflix",
            "confidence": 90,
        }
    ]
    raw = _make_raw(json.dumps({"results": results}))
    result = OllamaProvider._parse_batch_response(raw, expected_count=2)
    assert result["results"][0] is None
    assert result["results"][1] is None


def test_parse_batch_boolean_index_rejected() -> None:
    # bool is a subclass of int; True == 1 would otherwise pass the isinstance check.
    results = [
        {
            "index": True,
            "service_name": "netflix",
            "display_name": "Netflix",
            "confidence": 90,
        }
    ]
    raw = _make_raw(json.dumps({"results": results}))
    result = OllamaProvider._parse_batch_response(raw, expected_count=1)
    assert result["results"][0] is None


# ---------------------------------------------------------------------------
# embeddings — graceful no-op when fastembed is absent
# ---------------------------------------------------------------------------


def test_query_embedding_returns_none_without_fastembed() -> None:
    """query_embedding must return None gracefully when fastembed is not installed."""
    from backend.app.providers.ai.ollama import embeddings

    saved_unavailable = embeddings._fastembed_unavailable
    saved_index = embeddings._index
    try:
        embeddings._fastembed_unavailable = False
        embeddings._index = None
        result = embeddings.query_embedding("netflix.com")
        # Either fastembed is absent (returns None) or the index was built — both valid.
        assert result is None or isinstance(result, dict)
    finally:
        embeddings._fastembed_unavailable = saved_unavailable
        embeddings._index = saved_index


def test_query_embedding_empty_domain_returns_none() -> None:
    from backend.app.providers.ai.ollama import embeddings

    result = embeddings.query_embedding("")
    assert result is None


def test_query_embedding_never_raises() -> None:
    """query_embedding must not propagate exceptions regardless of internal state."""
    from backend.app.providers.ai.ollama import embeddings

    with patch.object(embeddings, "_get_index", side_effect=RuntimeError("unexpected")):
        result = embeddings.query_embedding("netflix.com")
    assert result is None
