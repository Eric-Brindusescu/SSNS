"""
Speech-to-text service using the upb-nlp/ro-wav2vec2 model.
Handles audio loading, resampling to 16kHz, and CTC decoding.
"""
import io
import logging

import numpy as np
import torch

from app.config import settings
from app.dependencies import get_model, get_processor, uses_lm

logger = logging.getLogger(__name__)

TARGET_SR = 16_000


async def transcribe_audio(
    file_bytes: bytes,
    filename: str,
    *,
    alpha: float | None = None,
    beta: float | None = None,
    hotwords: list[str] | None = None,
) -> dict:
    """
    Transcribe audio bytes to text.

    1. Load audio from bytes (WAV, MP3, FLAC, OGG, etc.)
    2. Convert to mono if stereo
    3. Resample to 16kHz if needed
    4. Run through wav2vec2 model
    5. Decode with CTC (LM-boosted if available)

    Optional decoding parameters (LM mode only):
        alpha: LM weight (higher = trust LM more). Default from config.
        beta: Word insertion bonus (higher = favor more words). Default from config.
        hotwords: Domain-specific words to boost during decoding.
    """
    speech_array, sample_rate = _load_audio(file_bytes, filename)

    # Convert stereo to mono
    if speech_array.ndim > 1:
        speech_array = speech_array.mean(axis=0)

    # Resample to 16kHz
    if sample_rate != TARGET_SR:
        speech_array = _resample(speech_array, sample_rate, TARGET_SR)
        sample_rate = TARGET_SR

    duration_seconds = len(speech_array) / sample_rate

    if duration_seconds > settings.max_audio_duration_seconds:
        raise ValueError(
            f"Audio too long: {duration_seconds:.1f}s "
            f"(max {settings.max_audio_duration_seconds}s)"
        )

    if duration_seconds < 0.1:
        raise ValueError("Audio too short (minimum 0.1 seconds)")

    # Run inference
    processor = get_processor()
    model = get_model()

    inputs = processor(
        speech_array,
        sampling_rate=TARGET_SR,
        return_tensors="pt",
        padding=True,
    )

    input_values = inputs.input_values.to(settings.device)
    attention_mask = getattr(inputs, "attention_mask", None)
    if attention_mask is not None:
        attention_mask = attention_mask.to(settings.device)

    with torch.no_grad():
        logits = model(input_values, attention_mask=attention_mask).logits

    # Decode
    if uses_lm():
        decode_alpha = alpha if alpha is not None else settings.alpha
        decode_beta = beta if beta is not None else settings.beta
        decode_hotwords = hotwords if hotwords is not None else (settings.hotwords or None)

        decode_kwargs = {
            "beam_width": settings.beam_width,
            "alpha": decode_alpha,
            "beta": decode_beta,
        }
        if decode_hotwords:
            decode_kwargs["hotwords"] = decode_hotwords
            decode_kwargs["hotword_weight"] = settings.hotword_weight

        result = processor.batch_decode(logits.cpu().numpy(), **decode_kwargs)
        text = result.text[0] if hasattr(result, "text") else result[0]
    else:
        predicted_ids = torch.argmax(logits, dim=-1)
        text = processor.batch_decode(predicted_ids)[0]

    return {
        "text": text.strip(),
        "duration_seconds": round(duration_seconds, 2),
        "language": "ro",
    }


def _load_audio(file_bytes: bytes, filename: str) -> tuple[np.ndarray, int]:
    """Load audio from bytes. Try torchaudio first, fall back to librosa."""
    import torchaudio

    try:
        buffer = io.BytesIO(file_bytes)
        waveform, sr = torchaudio.load(buffer)
        return waveform.squeeze().numpy(), sr
    except Exception as exc:
        logger.warning("torchaudio failed (%s), falling back to librosa", exc)

    import librosa

    buffer = io.BytesIO(file_bytes)
    audio, sr = librosa.load(buffer, sr=None, mono=False)
    return audio, sr


def _resample(audio: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
    """Resample audio to target sample rate."""
    import torchaudio

    waveform = torch.tensor(audio).unsqueeze(0).float()
    resampler = torchaudio.transforms.Resample(
        orig_freq=orig_sr, new_freq=target_sr
    )
    resampled = resampler(waveform)
    return resampled.squeeze().numpy()
