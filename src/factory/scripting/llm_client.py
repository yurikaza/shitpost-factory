"""Provider-agnostic LLM wrapper. Swapping providers must be a config change only.

Default: MiMo (Xiaomi) via OpenAI-compatible API at https://api.xiaomimimo.com/v1.
Also supports: gemini, ollama (local), groq.
Only get MiMo keys from platform.xiaomimimo.com — the lookalike domains are not official.
See docs/research-2026.md section 7 for the full comparison.

Must support a fixture mode so the pipeline runs offline.
"""
from __future__ import annotations

import json
import logging
import os
from abc import ABC, abstractmethod

import httpx

log = logging.getLogger(__name__)


class LLMClient(ABC):
    @abstractmethod
    def complete(self, system: str, user: str, **kw) -> str:
        ...

    @abstractmethod
    def complete_json(self, system: str, user: str, schema: dict, **kw) -> dict:
        ...


# ---------------------------------------------------------------------------
# Fixture client — returns canned responses, no network
# ---------------------------------------------------------------------------

class FixtureLLMClient(LLMClient):
    """Returns predictable responses for offline testing."""

    def complete(self, system: str, user: str, **kw) -> str:
        return (
            "Did you know? Honey never spoils. Archaeologists found 3,000-year-old "
            "honey in Egyptian tombs that was still perfectly edible. The low moisture "
            "content and acidic pH create an environment where bacteria simply cannot survive."
        )

    def complete_json(self, system: str, user: str, schema: dict, **kw) -> dict:
        return {
            "hook": "Did you know?",
            "body": (
                "Honey never spoils. Archaeologists found 3,000-year-old honey in "
                "Egyptian tombs that was still perfectly edible."
            ),
            "title": "Honey Lasts Forever",
            "description": "3,000-year-old honey found in Egyptian tombs was still edible.",
            "hashtags": ["didyouknow", "honey", "facts", "history", "amazing"],
            "clip_queries": ["honey", "egyptian tomb", "ancient", "beekeeping", "food"],
        }


# ---------------------------------------------------------------------------
# OpenAI-compatible client (works for MiMo, Ollama, Groq)
# ---------------------------------------------------------------------------

class OpenAICompatClient(LLMClient):
    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        temperature: float = 0.9,
        max_tokens: int = 8000,
    ):
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._model = model
        self._temperature = temperature
        self._max_tokens = max_tokens

    def _chat(self, messages: list[dict], **kw) -> str:
        url = f"{self._base_url}/chat/completions"
        payload = {
            "model": self._model,
            "messages": messages,
            "temperature": kw.get("temperature", self._temperature),
            "max_tokens": kw.get("max_tokens", self._max_tokens),
        }
        headers = {"Authorization": f"Bearer {self._api_key}"}
        log.info("LLM request: %s model=%s", url, self._model)
        with httpx.Client(timeout=180) as client:
            resp = client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
        data = resp.json()
        msg = data["choices"][0]["message"]
        content = msg.get("content", "") or ""
        reasoning = msg.get("reasoning_content", "") or ""
        if not content and reasoning:
            log.warning("MiMo returned empty content but has reasoning (%d chars). "
                        "Reasoning preview: %s", len(reasoning), reasoning[:200])
        return content

    def complete(self, system: str, user: str, **kw) -> str:
        messages = [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]
        return self._chat(messages, **kw)

    def complete_json(self, system: str, user: str, schema: dict, **kw) -> dict:
        json_system = (
            f"{system}\n\n"
            "Respond with valid JSON only. No markdown fences, no explanation. "
            "Be concise — output the JSON directly, do not overthink. "
            f"Schema: {json.dumps(schema)}"
        )
        messages = [
            {"role": "system", "content": json_system},
            {"role": "user", "content": user},
        ]
        # Retry up to 2 times on empty/invalid responses
        for attempt in range(3):
            raw = self._chat(messages, **kw)
            if not raw.strip():
                log.warning("LLM returned empty response, attempt %d/3", attempt + 1)
                continue
            # Strip markdown fences if present
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1]
            if cleaned.endswith("```"):
                cleaned = cleaned.rsplit("```", 1)[0]
            cleaned = cleaned.strip()
            # Try to extract JSON from response (LLM sometimes adds extra text)
            try:
                return json.loads(cleaned)
            except json.JSONDecodeError:
                # Find first { ... } block
                start = cleaned.find("{")
                if start >= 0:
                    depth = 0
                    for i, ch in enumerate(cleaned[start:], start):
                        if ch == "{":
                            depth += 1
                        elif ch == "}":
                            depth -= 1
                            if depth == 0:
                                return json.loads(cleaned[start:i + 1])
                log.warning("LLM returned invalid JSON, attempt %d/3", attempt + 1)
        raise json.JSONDecodeError("LLM failed to return valid JSON after 3 attempts", "", 0)


# ---------------------------------------------------------------------------
# Gemini client (Google AI Studio free tier)
# ---------------------------------------------------------------------------

class GeminiClient(LLMClient):
    def __init__(self, api_key: str, model: str = "gemini-2.0-flash", **kw):
        self._api_key = api_key
        self._model = model
        self._temperature = kw.get("temperature", 0.9)
        self._max_tokens = kw.get("max_tokens", 3000)

    def _generate(self, contents: list[dict]) -> str:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/"
            f"models/{self._model}:generateContent?key={self._api_key}"
        )
        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": self._temperature,
                "maxOutputTokens": self._max_tokens,
            },
        }
        log.info("LLM request: gemini model=%s", self._model)
        with httpx.Client(timeout=180) as client:
            resp = client.post(url, json=payload)
            resp.raise_for_status()
        data = resp.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]

    def complete(self, system: str, user: str, **kw) -> str:
        contents = [
            {"role": "user", "parts": [{"text": f"{system}\n\n{user}"}]},
        ]
        return self._generate(contents, **kw)

    def complete_json(self, system: str, user: str, schema: dict, **kw) -> dict:
        json_system = (
            f"{system}\n\n"
            "Respond with valid JSON only. No markdown fences, no explanation. "
            f"Schema: {json.dumps(schema)}"
        )
        raw = self.complete(json_system, user, **kw)
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("\n", 1)[1]
        if cleaned.endswith("```"):
            cleaned = cleaned.rsplit("```", 1)[0]
        cleaned = cleaned.strip()
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            start = cleaned.find("{")
            if start >= 0:
                depth = 0
                for i, ch in enumerate(cleaned[start:], start):
                    if ch == "{":
                        depth += 1
                    elif ch == "}":
                        depth -= 1
                        if depth == 0:
                            return json.loads(cleaned[start:i + 1])
            raise


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def build_client(provider: str | None = None, dry_run: bool = False) -> LLMClient:
    """Build an LLM client. If dry_run, returns FixtureLLMClient."""
    if dry_run:
        log.info("Using fixture LLM client (dry run)")
        return FixtureLLMClient()

    prov = provider or os.getenv("LLM_PROVIDER", "mimo")
    log.info("Building LLM client: provider=%s", prov)

    if prov == "fixture":
        return FixtureLLMClient()

    if prov in ("mimo", "ollama", "groq"):
        env_map = {
            "mimo": ("MIMO_BASE_URL", "MIMO_API_KEY", "MIMO_MODEL"),
            "ollama": ("OLLAMA_HOST", "_", "_"),
            "groq": ("https://api.groq.com/openai/v1", "GROQ_API_KEY", "llama-3.1-8b-instant"),
        }
        base_url_key, api_key_key, model_key = env_map[prov]
        base_url = os.getenv(base_url_key, base_url_key)
        api_key = os.getenv(api_key_key, "") if api_key_key != "_" else "ollama"
        model = os.getenv(model_key, model_key) if model_key != "_" else "llama3.1"
        return OpenAICompatClient(
            base_url=base_url,
            api_key=api_key,
            model=model,
            temperature=float(os.getenv("LLM_TEMPERATURE", "0.9")),
            max_tokens=int(os.getenv("LLM_MAX_TOKENS", "8000")),
        )

    if prov == "gemini":
        return GeminiClient(
            api_key=os.getenv("GEMINI_API_KEY", ""),
            model=os.getenv("GEMINI_MODEL", "gemini-2.0-flash"),
            temperature=float(os.getenv("LLM_TEMPERATURE", "0.9")),
            max_tokens=int(os.getenv("LLM_MAX_TOKENS", "8000")),
        )

    raise ValueError(f"Unknown LLM provider: {prov}")
