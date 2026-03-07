"""
Singleton holder for the wav2vec2 model and processor.
Loaded once at startup via the lifespan handler in main.py.
"""
import logging

import torch
from transformers import Wav2Vec2ForCTC

from app.config import settings

logger = logging.getLogger(__name__)

_model: Wav2Vec2ForCTC | None = None
_processor = None
_use_lm: bool = False


def preload_model() -> None:
    """Load model and processor into module-level singletons."""
    global _model, _processor, _use_lm

    logger.info("Loading wav2vec2 model: %s", settings.model_name)

    # Try LM-boosted processor first, fall back to plain processor
    try:
        from transformers import Wav2Vec2ProcessorWithLM

        _processor = Wav2Vec2ProcessorWithLM.from_pretrained(settings.model_name)
        _use_lm = True
        logger.info("Loaded processor with LM decoding")
    except (ImportError, OSError) as exc:
        from transformers import Wav2Vec2Processor

        logger.warning(
            "Could not load LM processor (%s), falling back to plain CTC decoding. "
            "Install pyctcdecode and kenlm for better accuracy.",
            exc,
        )
        _processor = Wav2Vec2Processor.from_pretrained(settings.model_name)
        _use_lm = False

    _model = Wav2Vec2ForCTC.from_pretrained(settings.model_name)
    _model.to(settings.device)
    _model.eval()

    logger.info("Model loaded successfully on device: %s", settings.device)


def get_model() -> Wav2Vec2ForCTC:
    if _model is None:
        raise RuntimeError("Model not loaded. Was preload_model() called?")
    return _model


def get_processor():
    if _processor is None:
        raise RuntimeError("Processor not loaded. Was preload_model() called?")
    return _processor


def uses_lm() -> bool:
    return _use_lm
