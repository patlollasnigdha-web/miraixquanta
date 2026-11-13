"""
Tests for MIRAI Ollama Client (M16)
Validates local LLM client connectivity, error handling, and offline behavior.
"""

import pytest
from unittest.mock import patch, MagicMock
from src.assistant.ollama_client import OllamaClient, OllamaServiceUnavailableError


def test_ollama_client_initialization():
    client = OllamaClient(host="http://localhost:11434", model="test-model", timeout_sec=5.0)
    assert client.host == "http://localhost:11434"
    assert client.model == "test-model"
    assert client.timeout == 5.0


def test_ollama_unreachable_host_raises_unavailable_error():
    # Dead host and port
    client = OllamaClient(host="http://127.0.0.1:59999", timeout_sec=0.5)
    assert client.is_available() is False
    assert client.list_models() == []

    with pytest.raises(OllamaServiceUnavailableError, match="Ollama server is unavailable"):
        client.chat(messages=[{"role": "user", "content": "Hello"}])


def test_ollama_mocked_chat_completion():
    client = OllamaClient()

    mock_response = MagicMock()
    mock_response.read.return_value = b'{"message": {"role": "assistant", "content": "Analysis completed."}}'
    mock_response.__enter__.return_value = mock_response

    with patch("urllib.request.urlopen", return_value=mock_response):
        res = client.chat(messages=[{"role": "user", "content": "Analyze TCS"}])
        assert res["message"]["content"] == "Analysis completed."
