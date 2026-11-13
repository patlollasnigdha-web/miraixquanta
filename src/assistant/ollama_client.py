"""
MIRAI — Ollama Client (M16)
Low-level client for interacting with the local Ollama LLM runtime.
Gracefully handles offline states and API communication timeouts.
"""

import json
import os
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

from src.utils.logger import get_logger
from src.utils.config import get_config

logger = get_logger("OllamaClient")


class OllamaServiceUnavailableError(Exception):
    """Raised when the Ollama local runtime is unreachable or offline."""
    pass


class OllamaClient:
    """
    Communicates with local Ollama daemon for chat completions and generation.
    """

    def __init__(
        self,
        host: Optional[str] = None,
        model: Optional[str] = None,
        timeout_sec: Optional[float] = None,
    ):
        cfg = get_config()
        self.host = (
            host
            or os.getenv("OLLAMA_HOST")
            or cfg.get("assistant.ollama_host", "http://localhost:11434")
        ).rstrip("/")
        self.model = (
            model
            or os.getenv("OLLAMA_MODEL")
            or cfg.get("assistant.default_model", "qwen2.5-coder:7b")
        )
        self.timeout = float(
            timeout_sec
            if timeout_sec is not None
            else os.getenv("OLLAMA_TIMEOUT_SEC", cfg.get("assistant.timeout_sec", 30.0))
        )

    def is_available(self) -> bool:
        """Checks if Ollama service is reachable and responsive."""
        try:
            url = f"{self.host}/api/tags"
            req = urllib.request.Request(url, headers={"User-Agent": "MIRAI-Assistant/1.0"})
            with urllib.request.urlopen(req, timeout=2.0) as res:
                return res.status == 200
        except Exception:
            return False

    def list_models(self) -> List[str]:
        """Lists locally downloaded model tags in the Ollama instance."""
        try:
            url = f"{self.host}/api/tags"
            req = urllib.request.Request(url, headers={"User-Agent": "MIRAI-Assistant/1.0"})
            with urllib.request.urlopen(req, timeout=3.0) as res:
                data = json.loads(res.read().decode("utf-8"))
                return [m.get("name") for m in data.get("models", [])]
        except Exception as e:
            logger.warning("Failed to query Ollama model list: %s", e)
            return []

    def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        stream: bool = False,
        temperature: float = 0.1,
    ) -> Dict[str, Any]:
        """
        Sends chat completion request to /api/chat.
        """
        target_model = model or self.model
        url = f"{self.host}/api/chat"

        payload = {
            "model": target_model,
            "messages": messages,
            "stream": stream,
            "options": {
                "temperature": temperature,
            },
        }

        try:
            req_data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=req_data,
                headers={"Content-Type": "application/json", "User-Agent": "MIRAI-Assistant/1.0"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                body = response.read().decode("utf-8")
                return json.loads(body)
        except urllib.error.URLError as e:
            logger.error("Ollama connection error: %s", e)
            raise OllamaServiceUnavailableError(
                f"Ollama server is unavailable at {self.host}. Please ensure the Ollama service is running."
            ) from e
        except Exception as e:
            logger.error("Ollama invocation failed: %s", e)
            raise OllamaServiceUnavailableError(f"Ollama chat execution error: {str(e)}") from e

    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.3,
    ) -> str:
        """
        Sends completion generation request to /api/generate.
        """
        target_model = model or self.model
        url = f"{self.host}/api/generate"
        payload = {
            "model": target_model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
            },
        }
        try:
            req_data = json.dumps(payload).encode("utf-8")
            req = urllib.request.Request(
                url,
                data=req_data,
                headers={"Content-Type": "application/json", "User-Agent": "MIRAI-Assistant/1.0"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                body = json.loads(response.read().decode("utf-8"))
                return body.get("response", "")
        except Exception as e:
            logger.warning("Ollama generate failed or offline: %s", e)
            raise OllamaServiceUnavailableError(f"Ollama generation failed: {e}") from e

