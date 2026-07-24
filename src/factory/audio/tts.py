"""Stage 3a. Narration.

Default engine: edge-tts (free, no key, good quality, runs on cpu).
Alternatives: piper (fully offline), MiMo TTS.

Note on disclosure: synthetic narration over non-realistic footage does not
require an AI label on any of the three platforms. Cloning a real person's voice
does. Do not clone voices.
"""
from __future__ import annotations

import asyncio
import logging
import os
import wave
from abc import ABC, abstractmethod
from pathlib import Path

log = logging.getLogger(__name__)

_DEFAULT_VOICE = "en-US-AndrewNeural"


class TTSEngine(ABC):
    @abstractmethod
    def synthesize(self, text: str, output_path: Path) -> Path:
        """Synthesize text to an audio file. Returns the output path."""
        ...


# ---------------------------------------------------------------------------
# Fixture — silent WAV, no network
# ---------------------------------------------------------------------------

class FixtureTTS(TTSEngine):
    """Generates a short silent WAV file for offline testing."""

    def synthesize(self, text: str, output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        # Generate ~3 seconds of silence at 16kHz mono
        sample_rate = 16000
        duration_s = max(1.0, len(text.split()) * 0.3)  # rough estimate
        n_samples = int(sample_rate * duration_s)
        with wave.open(str(output_path), "w") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(b"\x00\x00" * n_samples)
        log.info("Fixture TTS: wrote %s (%.1fs silence)", output_path, duration_s)
        return output_path


# ---------------------------------------------------------------------------
# Edge-TTS — free, no API key, good quality
# ---------------------------------------------------------------------------

class EdgeTTS(TTSEngine):
    """Microsoft Edge TTS via edge-tts package."""

    def __init__(self, voice: str | None = None):
        self._voice = voice or os.getenv("TTS_VOICE", _DEFAULT_VOICE)

    def synthesize(self, text: str, output_path: Path) -> Path:
        import edge_tts

        output_path.parent.mkdir(parents=True, exist_ok=True)
        log.info("Edge TTS: voice=%s -> %s", self._voice, output_path)

        communicate = edge_tts.Communicate(text, self._voice)
        asyncio.run(communicate.save(str(output_path)))
        return output_path


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def build_tts(provider: str | None = None, dry_run: bool = False) -> TTSEngine:
    """Build a TTS engine. If dry_run, returns FixtureTTS."""
    if dry_run:
        log.info("Using fixture TTS (dry run)")
        return FixtureTTS()

    prov = provider or os.getenv("TTS_PROVIDER", "edge")
    log.info("Building TTS engine: provider=%s", prov)

    if prov == "fixture":
        return FixtureTTS()
    if prov == "edge":
        return EdgeTTS()
    # piper and mimo would go here
    raise ValueError(f"Unknown TTS provider: {prov}")
