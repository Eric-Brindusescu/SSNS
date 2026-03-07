"""
LLM Parser — Qwen3-8B via HuggingFace Inference API
=====================================================
Sends the input text + VaR dictionary to the model and gets back
a structured JSON dictionary (the DTC).

Requirements:
    pip install huggingface_hub
    Set the environment variable  HF_TOKEN  to your HuggingFace access token,
    or place it in a file called .hf_token in the project directory.

Model: Qwen/Qwen3-8B
Docs:  https://huggingface.co/Qwen/Qwen3-8B
"""

import json
import os
import re

try:
    from huggingface_hub import InferenceClient
except ImportError:
    InferenceClient = None   # handled at call time with a clear error

from var_rules import VAR, get_defaults

# ── Config ─────────────────────────────────────────────────────────
MODEL_ID = "Qwen/Qwen3-8B"


# ── Token loader ───────────────────────────────────────────────────
def _load_token() -> str:
    """Read HF token from env var or local .hf_token file."""
    token = os.environ.get("HF_TOKEN", "").strip()
    if token:
        return token
    token_file = os.path.join(os.path.dirname(__file__), ".hf_token")
    if os.path.isfile(token_file):
        with open(token_file) as f:
            return f.read().strip()
    raise RuntimeError(
        "No HuggingFace token found. "
        "Set the HF_TOKEN environment variable or create a .hf_token file."
    )


# ── Prompt builder ─────────────────────────────────────────────────
def _build_prompt(input_text: str, var_dict: dict) -> str:
    """
    Build the system + user prompt that instructs Qwen3-8B to return
    a JSON object whose keys match the VaR field names.
    """
    # Build a compact rules block from VaR
    rules_lines = []
    for field, meta in var_dict.items():
        valid = meta["valid_values"]
        if isinstance(valid, list) and len(valid) > 20:
            valid = f"see description"
        default = meta["default"]
        rules_lines.append(
            f'  "{field}": {{\n'
            f'    "description": "{meta["description"]}",\n'
            f'    "valid_values": {json.dumps(valid)},\n'
            f'    "default": {json.dumps(default)}\n'
            f'  }}'
        )
    rules_block = "{\n" + ",\n".join(rules_lines) + "\n}"

    prompt = f"""You are an aviation SNOWTAM data extraction assistant.

TASK:
Given a free-text description of runway conditions, extract the fields
defined in the RULES below and return ONLY a valid JSON object.

RULES (field name → description, valid values, default):
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

    return prompt


# ── LLM call ──────────────────────────────────────────────────────
def _call_qwen(prompt: str, token: str) -> str:
    """Send prompt to Qwen3-8B and return the raw text response."""
    if InferenceClient is None:
        raise RuntimeError(
            "huggingface_hub is not installed. "
            "Run: pip install huggingface_hub"
        )

    client = InferenceClient(
        model=MODEL_ID,
        token=token,
    )

    response = client.text_generation(
        prompt,
        max_new_tokens=600,
        temperature=0.1,          # low temp for structured output
        top_p=0.9,
        repetition_penalty=1.1,
        do_sample=True,
        return_full_text=False,
    )

    return response.strip()


# ── Response parser ───────────────────────────────────────────────
def _parse_response(raw: str) -> dict:
    """
    Parse the model's raw text output into a Python dict.
    Handles markdown fences, trailing text, etc.
    """
    # Strip markdown code fences if present
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw, flags=re.MULTILINE)
    cleaned = re.sub(r"\s*```$", "", cleaned, flags=re.MULTILINE)
    cleaned = cleaned.strip()

    # Find the first { ... } block
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1:
        raise ValueError(f"No JSON object found in model response:\n{raw}")

    json_str = cleaned[start : end + 1]
    return json.loads(json_str)


# ── Validation / defaults ────────────────────────────────────────
def _validate_and_fill(dtc: dict) -> dict:
    """Ensure every VaR key exists in dtc; fill missing with defaults."""
    defaults = get_defaults()
    for key, default_val in defaults.items():
        if key not in dtc or dtc[key] is None or dtc[key] == "":
            dtc[key] = default_val
    return dtc


# ── Public API ────────────────────────────────────────────────────
def llm_extract(input_text: str, var_dict: dict = VAR) -> dict:
    """
    Main entry point.
    Takes free text + VaR rules → calls Qwen3-8B → returns validated DTC dict.
    """
    # Handle empty / whitespace-only input immediately
    if not input_text.strip():
        print("  [LLM] Empty input — returning all defaults (no API call).")
        return get_defaults()

    token = _load_token()
    prompt = _build_prompt(input_text, var_dict)

    print(f"  [LLM] Sending prompt to {MODEL_ID} ...")
    raw_response = _call_qwen(prompt, token)
    print(f"  [LLM] Raw response:\n         {raw_response[:300]}")

    dtc = _parse_response(raw_response)
    dtc = _validate_and_fill(dtc)

    print(f"  [LLM] Parsed {len(dtc)} fields from model response.")
    return dtc
