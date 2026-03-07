"""
HTML Filler Module
===================
Reads template.html, replaces every {{key}} with the value from the DTC dict,
and writes the completed form. No LLM involved — pure string replacement.
"""

import os
from var_rules import VALID_CONDITIONS

TEMPLATE_PATH = os.path.join(os.path.dirname(__file__), "template.html")


def fill_template(dtc: dict, template_path: str = TEMPLATE_PATH) -> str:
    """
    Load the HTML template and replace every {{key}} placeholder
    with the matching value from the DTC dictionary.
    Returns the completed HTML string.
    """
    with open(template_path, "r", encoding="utf-8") as f:
        html = f.read()

    # Pre-build the highlighted condition list for section G)
    dtc["condition_list_html"] = _build_condition_list(dtc)

    # Replace placeholders
    for key, value in dtc.items():
        html = html.replace("{{" + key + "}}", str(value))

    return html


def save_html(html: str, output_path: str) -> None:
    """Write completed HTML to disk."""
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"  [FILE] Saved completed SNOWTAM → {output_path}")


# ── internal helper ────────────────────────────────────────────────
def _build_condition_list(dtc: dict) -> str:
    """
    Render the full ICAO condition list with any active conditions
    (those matching the three runway thirds) highlighted.
    """
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
