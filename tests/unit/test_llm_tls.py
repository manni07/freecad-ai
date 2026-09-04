"""Security regressions for verified provider TLS setup."""

from unittest.mock import patch

import pytest

from freecad_ai.llm.client import LLMClient, LLMError


def _client(api_key="test-secret"):
    return LLMClient(
        provider_name="custom",
        base_url="https://provider.invalid/v1",
        api_key=api_key,
        model="test-model",
    )


def test_context_creation_failure_never_uses_an_unverified_fallback():
    """A broken trust store must not silently disable server authentication."""
    with patch(
        "freecad_ai.llm.client.ssl.create_default_context",
        side_effect=RuntimeError("trust store unavailable"),
    ), patch(
        "freecad_ai.llm.client.ssl._create_unverified_context"
    ) as unverified:
        client = _client()

    assert unverified.call_count == 0
    assert isinstance(getattr(client, "_ssl_context_error", None), RuntimeError)


def test_https_is_rejected_when_verified_context_creation_failed():
    """No HTTPS request may leave the process after trust setup failed."""
    with patch(
        "freecad_ai.llm.client.ssl.create_default_context",
        side_effect=RuntimeError("trust store unavailable"),
    ):
        client = _client(api_key="must-not-appear")

    with pytest.raises(LLMError) as caught:
        client._check_ssl("https://provider.invalid/v1?token=must-not-appear")

    message = str(caught.value)
    assert "must-not-appear" not in message
    assert "trust" in message.lower() or "certificate" in message.lower()


def test_local_http_remains_available_when_tls_context_creation_failed():
    """Fail-closed HTTPS must not disable an explicit local HTTP provider."""
    with patch(
        "freecad_ai.llm.client.ssl.create_default_context",
        side_effect=RuntimeError("trust store unavailable"),
    ):
        client = _client()

    assert client._check_ssl("http://127.0.0.1:11434/api/chat") is None


@pytest.mark.parametrize("edge", ["_http_post", "_http_stream"])
def test_https_edges_fail_before_urlopen_when_trust_setup_failed(edge):
    """Both network edges must stop before credentials can leave the process."""
    with patch(
        "freecad_ai.llm.client.ssl.create_default_context",
        side_effect=RuntimeError("trust store unavailable"),
    ):
        client = _client(api_key="authorization-secret")

    with patch(
        "freecad_ai.llm.client.urllib.request.urlopen"
    ) as urlopen, pytest.raises(LLMError) as caught:
        result = getattr(client, edge)(
            "https://provider.invalid/v1?query-secret",
            {"Authorization": "Bearer authorization-secret"},
            {"model": "test"},
        )
        if edge == "_http_stream":
            next(result)

    urlopen.assert_not_called()
    message = str(caught.value)
    assert "authorization-secret" not in message
    assert "query-secret" not in message
