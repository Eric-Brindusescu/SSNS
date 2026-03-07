"""
Standard Values Module
=======================
Adds the automatically computed fields to the DTC.
These are NOT extracted by the LLM — they come from the airport/login
variables and the current UTC clock.

Fields added:
  serial_number                 → from airport + login + counter
  location_indicator            → from airport + current UTC time
  aerodrome_location_indicator  → from airport
  datetime_of_assessment        → current UTC  (ICAO format MMDDHHmmZ)
  datetime_of_assessment_readable → human-readable version
  originator                    → airport/login
"""

from datetime import datetime, timezone

# ───────────────────────────────────────────────────────────────────
# Configuration — change these for each deployment / operator
# ───────────────────────────────────────────────────────────────────
airport = "LROD"      # ICAO aerodrome code (Oradea)
login   = "OPS01"     # Operator identifier

# Simple in-memory serial counter.
# In production replace with a persistent counter (file / DB).
_serial_counter = 0


def _next_serial() -> str:
    """Generate the next SNOWTAM serial number: SW<airport><0001…9999>."""
    global _serial_counter
    _serial_counter += 1
    return f"SW{airport}{_serial_counter:04d}"


def add_standard_values(dtc: dict) -> dict:
    """
    Enrich an existing DTC dict with the standard (computed) fields.
    Returns the same dict, mutated.
    """
    now = datetime.now(timezone.utc)

    # Serial number  (e.g. SWLROD0001)
    dtc["serial_number"] = _next_serial()

    # Location indicator + date-time group
    # ICAO format: <ICAO> DDHHmm   (day, hour, minute in UTC)
    dtc["location_indicator"] = f"{airport} {now.strftime('%d%H%M')}"

    # Aerodrome location indicator — just the ICAO code
    dtc["aerodrome_location_indicator"] = airport

    # Date / Time of assessment — ICAO DDHHmmZ
    dtc["datetime_of_assessment"] = now.strftime("%m%d%H%MZ")

    # Human-readable version (for the signature / DATA cell)
    dtc["datetime_of_assessment_readable"] = now.strftime("%Y-%m-%d %H:%M UTC")

    # Originator
    dtc["originator"] = f"{airport}/{login}"

    return dtc
