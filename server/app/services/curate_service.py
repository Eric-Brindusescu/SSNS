"""
Service for curating text via a local LM Studio model.
Reformats raw transcription into structured aviation/runway condition reports.
"""
import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are an aviation operations specialist. Your task is to take raw, unstructured \
text (typically from speech-to-text transcription of runway condition reports) and \
reformat it into a clear, structured aviation runway condition report following \
ICAO standards.

Rules:
- Fix any obvious transcription errors or garbled words related to aviation terminology.
- Use standard aviation abbreviations where appropriate (RWY, TWY, APRON, FICON, etc.).
- Structure the output with clear sections: runway designation, surface condition, \
  contaminant type and depth, braking action, and any remarks.
- Preserve all factual data (numbers, measurements, runway identifiers) exactly as given.
- Use concise, professional aviation language.
- If the input mentions multiple runways or zones, organize them separately.
- Output in the same language as the input (typically Romanian).
- Do NOT add information that was not in the original text.
- Do NOT wrap the output in markdown code blocks.

Output format example:
---
RWY 07/25
  Suprafață: umedă
  Contaminant: apă, 2mm
  Acțiune de frânare: bună
  Observații: zona de touchdown - depuneri de cauciuc
---
"""


async def curate_text(text: str) -> str:
    """
    Send text to LM Studio for aviation report curation.
    Uses the OpenAI-compatible chat completions API.
    """
    url = f"{settings.lm_studio_base_url}/chat/completions"

    payload = {
        "model": settings.lm_studio_model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": text},
        ],
        "temperature": settings.lm_studio_temperature,
        "max_tokens": settings.lm_studio_max_tokens,
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            response = await client.post(url, json=payload)
            response.raise_for_status()
        except httpx.ConnectError:
            raise ConnectionError(
                f"Cannot connect to LM Studio at {settings.lm_studio_base_url}. "
                "Make sure LM Studio is running with a model loaded."
            )
        except httpx.HTTPStatusError as exc:
            raise RuntimeError(
                f"LM Studio returned {exc.response.status_code}: "
                f"{exc.response.text}"
            )

    data = response.json()
    return data["choices"][0]["message"]["content"].strip()
