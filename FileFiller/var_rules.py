"""
VaR — Variable and Rules Dictionary
====================================
Each key is a SNOWTAM field the LLM must extract from the input text.
Each value contains:
  - description : what the field means (sent to the LLM as context)
  - type        : expected data type
  - valid_values: list or range the LLM must pick from
  - default     : fallback when the input text says nothing about this field
"""

VAR = {

    # ── C) Lower Runway Designation Number ──────────────────────────
    "lower_runway_designation_number": {
        "description": (
            "The lower runway designation number, as painted on the threshold. "
            "Two digits from 01 to 36, optionally followed by L, C, or R."
        ),
        "type": "string",
        "valid_values": (
            [f"{i:02d}" for i in range(1, 37)]
            + [f"{i:02d}L" for i in range(1, 37)]
            + [f"{i:02d}C" for i in range(1, 37)]
            + [f"{i:02d}R" for i in range(1, 37)]
        ),
        "default": "09",
    },

    # ── D) Runway Condition Code per third (RCAM 0-6) ──────────────
    "runway_condition_code_third_1": {
        "description": (
            "Runway Condition Code (RWYCC) for the FIRST third of the runway, "
            "from the Runway Condition Assessment Matrix (RCAM). Integer 0 to 6."
        ),
        "type": "integer",
        "valid_values": [0, 1, 2, 3, 4, 5, 6],
        "default": 5,
    },
    "runway_condition_code_third_2": {
        "description": (
            "Runway Condition Code (RWYCC) for the SECOND (middle) third. "
            "Integer 0 to 6."
        ),
        "type": "integer",
        "valid_values": [0, 1, 2, 3, 4, 5, 6],
        "default": 5,
    },
    "runway_condition_code_third_3": {
        "description": (
            "Runway Condition Code (RWYCC) for the THIRD (last) third. "
            "Integer 0 to 6."
        ),
        "type": "integer",
        "valid_values": [0, 1, 2, 3, 4, 5, 6],
        "default": 5,
    },

    # ── E) Percent coverage per third ──────────────────────────────
    "percent_coverage_third_1": {
        "description": (
            "Percent coverage of contaminant for the FIRST runway third. "
            "One of: NR, 0, 25, 50, 75, 100."
        ),
        "type": "string",
        "valid_values": ["NR", "0", "25", "50", "75", "100"],
        "default": "NR",
    },
    "percent_coverage_third_2": {
        "description": "Percent coverage of contaminant for the SECOND third.",
        "type": "string",
        "valid_values": ["NR", "0", "25", "50", "75", "100"],
        "default": "NR",
    },
    "percent_coverage_third_3": {
        "description": "Percent coverage of contaminant for the THIRD third.",
        "type": "string",
        "valid_values": ["NR", "0", "25", "50", "75", "100"],
        "default": "NR",
    },

    # ── F) Depth (mm) of loose contaminant per third ───────────────
    "depth_loose_contaminant_third_1": {
        "description": (
            "Depth in millimetres of loose contaminant for the FIRST runway third. "
            "An integer 0-999, or 'NR' if not reported."
        ),
        "type": "string",
        "valid_values": "integer 0-999 or the string NR",
        "default": "NR",
    },
    "depth_loose_contaminant_third_2": {
        "description": "Depth (mm) of loose contaminant for the SECOND third.",
        "type": "string",
        "valid_values": "integer 0-999 or the string NR",
        "default": "NR",
    },
    "depth_loose_contaminant_third_3": {
        "description": "Depth (mm) of loose contaminant for the THIRD third.",
        "type": "string",
        "valid_values": "integer 0-999 or the string NR",
        "default": "NR",
    },

    # ── G) Condition description per third ─────────────────────────
    "condition_description_third_1": {
        "description": (
            "Surface condition description for the FIRST runway third. "
            "Must be EXACTLY one of the ICAO standard phrases listed in valid_values."
        ),
        "type": "string",
        "valid_values": [
            "COMPACTED SNOW",
            "DRY",
            "DRY SNOW",
            "DRY SNOW ON TOP OF COMPACTED SNOW",
            "DRY SNOW ON TOP OF ICE",
            "FROST",
            "ICE",
            "SLIPPERY WET",
            "SLUSH",
            "SPECIALLY PREPARED WINTER RUNWAY",
            "STANDING WATER",
            "WATER ON TOP OF COMPACTED SNOW",
            "WET",
            "WET ICE",
            "WET SNOW",
            "WET SNOW ON TOP OF COMPACTED SNOW",
            "WET SNOW ON TOP OF ICE",
        ],
        "default": "DRY",
    },
    "condition_description_third_2": {
        "description": "Surface condition description for the SECOND third.",
        "type": "string",
        "valid_values": "same list as condition_description_third_1",
        "default": "DRY",
    },
    "condition_description_third_3": {
        "description": "Surface condition description for the THIRD third.",
        "type": "string",
        "valid_values": "same list as condition_description_third_1",
        "default": "DRY",
    },
}


# ── Helper accessors ───────────────────────────────────────────────
VALID_CONDITIONS = VAR["condition_description_third_1"]["valid_values"]


def get_defaults() -> dict:
    """Return a dict of {field: default_value} for every VaR field."""
    return {k: v["default"] for k, v in VAR.items()}
