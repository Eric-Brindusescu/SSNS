"""
Service for extracting SNOWTAM fields from curated text via local Qwen3 in LM Studio.
Adapts the FileFiller pipeline to work as an async service.
"""
import json
import logging
import re
from datetime import datetime, timezone

import httpx

from app.config import settings

logger = logging.getLogger(__name__)

# ── VaR field definitions (from FileFiller/var_rules.py) ──────────────

VALID_CONDITIONS = [
    "COMPACTED SNOW", "DRY", "DRY SNOW",
    "DRY SNOW ON TOP OF COMPACTED SNOW", "DRY SNOW ON TOP OF ICE",
    "FROST", "ICE", "SLIPPERY WET", "SLUSH",
    "SPECIALLY PREPARED WINTER RUNWAY", "STANDING WATER",
    "WATER ON TOP OF COMPACTED SNOW", "WET", "WET ICE", "WET SNOW",
    "WET SNOW ON TOP OF COMPACTED SNOW", "WET SNOW ON TOP OF ICE",
]

VAR = {
    "lower_runway_designation_number": {
        "description": "Lower runway designation number (two digits 01-36, optionally L/C/R).",
        "valid_values": [f"{i:02d}" for i in range(1, 37)],
        "default": "09",
    },
    "runway_condition_code_third_1": {
        "description": "RWYCC for the FIRST third (RCAM 0-6).",
        "valid_values": [0, 1, 2, 3, 4, 5, 6],
        "default": 5,
    },
    "runway_condition_code_third_2": {
        "description": "RWYCC for the SECOND third (RCAM 0-6).",
        "valid_values": [0, 1, 2, 3, 4, 5, 6],
        "default": 5,
    },
    "runway_condition_code_third_3": {
        "description": "RWYCC for the THIRD third (RCAM 0-6).",
        "valid_values": [0, 1, 2, 3, 4, 5, 6],
        "default": 5,
    },
    "percent_coverage_third_1": {
        "description": "Percent coverage of contaminant for the FIRST third.",
        "valid_values": ["NR", "0", "25", "50", "75", "100"],
        "default": "NR",
    },
    "percent_coverage_third_2": {
        "description": "Percent coverage for the SECOND third.",
        "valid_values": ["NR", "0", "25", "50", "75", "100"],
        "default": "NR",
    },
    "percent_coverage_third_3": {
        "description": "Percent coverage for the THIRD third.",
        "valid_values": ["NR", "0", "25", "50", "75", "100"],
        "default": "NR",
    },
    "depth_loose_contaminant_third_1": {
        "description": "Depth (mm) of loose contaminant for the FIRST third (0-999 or NR).",
        "valid_values": "integer 0-999 or NR",
        "default": "NR",
    },
    "depth_loose_contaminant_third_2": {
        "description": "Depth (mm) of loose contaminant for the SECOND third.",
        "valid_values": "integer 0-999 or NR",
        "default": "NR",
    },
    "depth_loose_contaminant_third_3": {
        "description": "Depth (mm) of loose contaminant for the THIRD third.",
        "valid_values": "integer 0-999 or NR",
        "default": "NR",
    },
    "condition_description_third_1": {
        "description": "Surface condition for the FIRST third (ICAO standard phrase).",
        "valid_values": VALID_CONDITIONS,
        "default": "DRY",
    },
    "condition_description_third_2": {
        "description": "Surface condition for the SECOND third.",
        "valid_values": VALID_CONDITIONS,
        "default": "DRY",
    },
    "condition_description_third_3": {
        "description": "Surface condition for the THIRD third.",
        "valid_values": VALID_CONDITIONS,
        "default": "DRY",
    },
}

DEFAULTS = {k: v["default"] for k, v in VAR.items()}

# ── Airport config ────────────────────────────────────────────────────
AIRPORT = "LROD"
LOGIN = "OPS01"
_serial_counter = 0


def _next_serial() -> str:
    global _serial_counter
    _serial_counter += 1
    return f"SW{AIRPORT}{_serial_counter:04d}"


# ── Prompt builder ────────────────────────────────────────────────────

def _build_prompt(input_text: str) -> str:
    rules_lines = []
    for field, meta in VAR.items():
        valid = meta["valid_values"]
        if isinstance(valid, list) and len(valid) > 20:
            valid = "see description"
        default = meta["default"]
        rules_lines.append(
            f'  "{field}": {{\n'
            f'    "description": "{meta["description"]}",\n'
            f'    "valid_values": {json.dumps(valid)},\n'
            f'    "default": {json.dumps(default)}\n'
            f'  }}'
        )
    rules_block = "{\n" + ",\n".join(rules_lines) + "\n}"

    return f"""You are an aviation SNOWTAM data extraction assistant.

TASK:
Given a free-text description of runway conditions, extract the fields
defined in the RULES below and return ONLY a valid JSON object.

RULES (field name -> description, valid values, default):
{rules_block}

CRITICAL INSTRUCTIONS:
1. Return ONLY raw JSON — no markdown fences, no explanation, no extra text.
2. Every key from the RULES must appear in your output.
3. If the input text does not mention a field, use its default value.
4. For condition descriptions, use ONLY the exact ICAO phrases from valid_values.
5. If a single value is given for all three thirds, repeat it for each third.
6. The input may be in English or Romanian — handle both.

INPUT TEXT:
\"\"\"{input_text}\"\"\"

JSON output:"""


# ── LLM call via LM Studio ───────────────────────────────────────────

async def _call_lm_studio(prompt: str) -> str:
    url = f"{settings.lm_studio_base_url}/chat/completions"
    payload = {
        "model": settings.lm_studio_model,
        "messages": [
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.1,
        "max_tokens": settings.lm_studio_max_tokens,
        "no_think": True,
    }

    async with httpx.AsyncClient(timeout=120.0) as client:
        try:
            response = await client.post(url, json=payload)
            response.raise_for_status()
        except httpx.ConnectError:
            raise ConnectionError(
                f"Cannot connect to LM Studio at {settings.lm_studio_base_url}. "
                "Make sure LM Studio is running with Qwen3 loaded."
            )
        except httpx.HTTPStatusError as exc:
            raise RuntimeError(
                f"LM Studio returned {exc.response.status_code}: {exc.response.text}"
            )

    data = response.json()
    content = data["choices"][0]["message"]["content"]
    content = re.sub(r"<think>[\s\S]*?</think>", "", content)
    return content.strip()


# ── Response parser ───────────────────────────────────────────────────

def _parse_response(raw: str) -> dict:
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.MULTILINE)
    cleaned = re.sub(r"\s*```$", "", cleaned, flags=re.MULTILINE)
    cleaned = cleaned.strip()

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"No JSON object found in model response:\n{raw}")

    return json.loads(cleaned[start : end + 1])


def _validate_and_fill(dtc: dict) -> dict:
    for key, default_val in DEFAULTS.items():
        if key not in dtc or dtc[key] is None or dtc[key] == "":
            dtc[key] = default_val
    return dtc


def _add_standard_values(dtc: dict) -> dict:
    now = datetime.now(timezone.utc)
    dtc["serial_number"] = _next_serial()
    dtc["location_indicator"] = f"{AIRPORT} {now.strftime('%d%H%M')}"
    dtc["aerodrome_location_indicator"] = AIRPORT
    dtc["datetime_of_assessment"] = now.strftime("%m%d%H%MZ")
    dtc["datetime_of_assessment_readable"] = now.strftime("%Y-%m-%d %H:%M UTC")
    dtc["originator"] = f"{AIRPORT}/{LOGIN}"
    return dtc


def _build_condition_list_html(dtc: dict) -> str:
    active = {
        str(dtc.get(f"condition_description_third_{i}", "")).upper()
        for i in range(1, 4)
    }
    lines = []
    for cond in VALID_CONDITIONS:
        if cond.upper() in active:
            lines.append(f'<span class="active">{cond}</span>')
        else:
            lines.append(cond)
    return "<br>\n      ".join(lines)


def _fill_template(dtc: dict) -> str:
    import os
    template_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "template.html"
    )
    with open(template_path, "r", encoding="utf-8") as f:
        html = f.read()

    dtc["condition_list_html"] = _build_condition_list_html(dtc)

    for key, value in dtc.items():
        html = html.replace("{{ " + key + " }}", str(value))

    return html


# ── Public API ────────────────────────────────────────────────────────

async def extract_snowtam(text: str) -> dict:
    """
    Full SNOWTAM pipeline: text -> LLM extraction -> standard values -> DTC dict + HTML.
    """
    if not text.strip():
        dtc = dict(DEFAULTS)
    else:
        prompt = _build_prompt(text)
        logger.info("Sending SNOWTAM extraction prompt to LM Studio...")
        raw = await _call_lm_studio(prompt)
        logger.info("LM Studio raw response: %s", raw[:300])
        dtc = _parse_response(raw)
        dtc = _validate_and_fill(dtc)

    dtc = _add_standard_values(dtc)
    html = _fill_template(dtc)

    return {"dtc": dtc, "html": html}
