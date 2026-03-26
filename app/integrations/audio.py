"""Audio pipeline — Speech-to-Text (STT) and Text-to-Speech (TTS).

STT: faster-whisper (self-hosted) with Meta MMS fallback for African languages
TTS: Piper (fast) with fallback to edge-tts (Microsoft, no install needed)
"""

import asyncio
import io
import tempfile
import os
from pathlib import Path

import structlog

logger = structlog.get_logger()


# ── STT — Speech to Text ─────────────────────────────

class WhisperSTT:
    """faster-whisper based STT (self-hosted)."""

    def __init__(self):
        self._model = None

    def _get_model(self):
        if self._model is not None:
            return self._model
        try:
            from faster_whisper import WhisperModel
            # Use small model for speed on M4 16GB — upgrade to large-v3 for quality
            self._model = WhisperModel("small", device="cpu", compute_type="int8")
            logger.info("whisper_stt_loaded", model="small")
            return self._model
        except ImportError:
            logger.warning("faster_whisper_not_installed")
            return None

    async def transcribe(self, audio_data: bytes, language: str = "fr") -> str:
        """Transcribe audio bytes to text."""
        model = self._get_model()
        if model is None:
            raise RuntimeError("faster-whisper not installed")

        # Write to temp file — browser sends webm/opus from MediaRecorder
        # faster-whisper uses ffmpeg internally and can decode webm
        suffix = ".webm" if audio_data[:4] != b'RIFF' else ".wav"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as f:
            f.write(audio_data)
            tmp_path = f.name

        try:
            def _transcribe():
                segments, info = model.transcribe(
                    tmp_path,
                    language=language if language in ("fr", "en") else None,
                    beam_size=5,
                    vad_filter=True,
                )
                return " ".join(s.text for s in segments).strip()

            text = await asyncio.to_thread(_transcribe)
            logger.info("whisper_transcribed", length=len(text), language=language)
            return text
        finally:
            os.unlink(tmp_path)


class EdgeTTSFallbackSTT:
    """Fallback STT using browser Web Speech API (no server processing).
    Returns empty — the frontend handles STT via browser API.
    """
    async def transcribe(self, audio_data: bytes, language: str = "fr") -> str:
        return ""


# ── TTS — Text to Speech ─────────────────────────────

class PiperTTS:
    """Piper TTS — fast, lightweight, offline."""

    def __init__(self):
        self._available = None

    def _check_available(self) -> bool:
        if self._available is not None:
            return self._available
        try:
            import subprocess
            result = subprocess.run(["piper", "--version"], capture_output=True, timeout=5)
            self._available = result.returncode == 0
        except Exception:
            self._available = False
        logger.info("piper_tts_available", available=self._available)
        return self._available

    async def synthesize(self, text: str, language: str = "fr", voice: str = "fr_FR-siwis-medium") -> bytes:
        """Convert text to speech, return WAV bytes."""
        if not self._check_available():
            raise RuntimeError("Piper TTS not installed")

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as out_f:
            out_path = out_f.name

        try:
            def _synthesize():
                import subprocess
                process = subprocess.run(
                    ["piper", "--model", voice, "--output_file", out_path],
                    input=text.encode("utf-8"),
                    capture_output=True,
                    timeout=30,
                )
                if process.returncode != 0:
                    raise RuntimeError(f"Piper failed: {process.stderr.decode()[:200]}")
                with open(out_path, "rb") as f:
                    return f.read()

            audio = await asyncio.to_thread(_synthesize)
            logger.info("piper_tts_synthesized", text_length=len(text), audio_bytes=len(audio))
            return audio
        finally:
            if os.path.exists(out_path):
                os.unlink(out_path)


class EdgeTTS:
    """Microsoft Edge TTS — free, no API key, many voices, good quality.
    Uses the edge-tts library (pip install edge-tts).
    """

    VOICES = {
        "fr": "fr-FR-DeniseNeural",  # French female, natural
        "fr-male": "fr-FR-HenriNeural",
        "en": "en-US-JennyNeural",
        "en-male": "en-US-GuyNeural",
    }

    async def synthesize(self, text: str, language: str = "fr", voice: str | None = None) -> bytes:
        """Convert text to speech using Edge TTS."""
        try:
            import edge_tts

            voice_name = voice or self.VOICES.get(language, self.VOICES["fr"])

            communicate = edge_tts.Communicate(text, voice_name)

            # Collect audio chunks
            audio_chunks = []
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    audio_chunks.append(chunk["data"])

            audio = b"".join(audio_chunks)
            logger.info("edge_tts_synthesized", text_length=len(text), audio_bytes=len(audio), voice=voice_name)
            return audio

        except ImportError:
            logger.warning("edge_tts_not_installed")
            raise RuntimeError("edge-tts not installed. Run: pip install edge-tts")


# ── Router ────────────────────────────────────────────

class AudioRouter:
    """Routes STT/TTS requests to the best available provider."""

    def __init__(self):
        self._stt = None
        self._tts = None

    def _get_stt(self):
        if self._stt is None:
            stt = WhisperSTT()
            if stt._get_model() is not None:
                self._stt = stt
                logger.info("audio_stt_provider", provider="faster-whisper")
            else:
                self._stt = EdgeTTSFallbackSTT()
                logger.info("audio_stt_provider", provider="browser-fallback")
        return self._stt

    def _get_tts(self):
        if self._tts is None:
            # Try Piper first, then Edge TTS
            piper = PiperTTS()
            if piper._check_available():
                self._tts = piper
                logger.info("audio_tts_provider", provider="piper")
            else:
                self._tts = EdgeTTS()
                logger.info("audio_tts_provider", provider="edge-tts")
        return self._tts

    async def speech_to_text(self, audio_data: bytes, language: str = "fr") -> str:
        return await self._get_stt().transcribe(audio_data, language)

    async def text_to_speech(self, text: str, language: str = "fr", voice: str | None = None) -> bytes:
        return await self._get_tts().synthesize(text, language, voice)


_audio_router: AudioRouter | None = None


def get_audio_router() -> AudioRouter:
    global _audio_router
    if _audio_router is None:
        _audio_router = AudioRouter()
    return _audio_router
