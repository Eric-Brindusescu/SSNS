#!/usr/bin/env python3
"""
SNOWTAM Form Completion — Main Pipeline
=========================================

Flow:
  ┌──────────┐     ┌───────────┐     ┌───────────────┐     ┌──────────────┐
  │  Input    │ ──► │  Qwen3-8B │ ──► │ Add standard  │ ──► │ Fill HTML    │
  │  string   │     │  + VaR    │     │ values (time,  │     │ template     │
  │           │     │  → DTC    │     │ serial, etc.)  │     │ → output.html│
  └──────────┘     └───────────┘     └───────────────┘     └──────────────┘

Usage:
  python main.py "Runway 09, code 5/5/3, wet snow, coverage 75%, depth 4mm"
  python main.py ""                 # empty → all standard defaults
  python main.py                    # interactive prompt

Requirements:
  pip install huggingface_hub
  export HF_TOKEN="hf_your_token"   # or create .hf_token file
"""

import sys
import os
import json

from var_rules import VAR
from llm_parser import llm_extract
from standard_values import add_standard_values
from html_filler import fill_template, save_html


def run(input_text: str, output_path: str = "snowtam_output.html") -> tuple[dict, str]:
    """
    Execute the full SNOWTAM pipeline.
    Returns (dtc_dict, html_string).
    """
    print("=" * 62)
    print("   SNOWTAM FORM COMPLETION  —  Qwen3-8B + VaR Pipeline")
    print("=" * 62)

    # ── 1. Show input ──────────────────────────────────────────────
    display = input_text if input_text.strip() else "(empty)"
    print(f"\n  INPUT : {display}")
    if not input_text.strip():
        print("  INFO  : Empty input → all fields will use standard defaults.\n")

    # ── 2. LLM extraction  (text + VaR → DTC) ─────────────────────
    print("  STEP 1 — LLM extraction via Qwen3-8B")
    print(f"           VaR has {len(VAR)} field definitions")
    dtc = llm_extract(input_text, VAR)

    print("           DTC (LLM-extracted):")
    for k, v in dtc.items():
        print(f"             {k}: {v}")

    # ── 3. Add standard computed values  (no LLM) ─────────────────
    print("\n  STEP 2 — Add standard values (serial, time, location)")
    dtc = add_standard_values(dtc)

    print("           DTC (complete):")
    for k, v in dtc.items():
        print(f"             {k}: {v}")

    # ── 4. Fill HTML template  (no LLM) ───────────────────────────
    print(f"\n  STEP 3 — Fill HTML template")
    html = fill_template(dtc)
    save_html(html, output_path)

    # ── 5. Also dump the DTC as JSON for traceability ─────────────
    json_path = output_path.replace(".html", "_dtc.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(dtc, f, indent=2, ensure_ascii=False)
    print(f"  [FILE] Saved DTC dictionary → {json_path}")

    print("\n" + "=" * 62)
    print("   DONE  — Open the .html in any browser to view the form.")
    print("=" * 62)
    return dtc, html


# ── CLI ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    if len(sys.argv) > 1:
        text = " ".join(sys.argv[1:])
    else:
        print("Enter runway condition description (or Enter for defaults):")
        text = input("> ").strip()

    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "snowtam_output.html")
    run(text, out)
