"""Qt-free GO Factory section-mapping policy.

The GUI only displays available choices. This module enforces steel-only
alternatives and makes the preview uncertainty explicit.
"""
from __future__ import annotations

from .engineering_core import (
    CatalogError, STATUS_NOMINAL, nominal_section_properties, section_record,
)
from .sections import starter_sections


def choices_for_section(section_id):
    """Return label/payload options; never propose RC for a steel section."""
    try:
        nominal = section_record(section_id)["analysis_status"] == STATUS_NOMINAL
    except CatalogError:
        nominal = False
    choices = []
    if nominal:
        choices.extend((
            ("Nominal — STRONG axis (unverified)", {
                "mode": "go_core_nominal", "axis": "strong", "acknowledged": True,
            }),
            ("Nominal — WEAK axis (unverified)", {
                "mode": "go_core_nominal", "axis": "weak", "acknowledged": True,
            }),
        ))
    for item in starter_sections():
        if item.get("kind") == "Steel":
            choices.append((
                f"Manual steel: {item['id']} (not physically equivalent)",
                {"mode": "manual_starter", "section": item["id"],
                 "acknowledged": True},
            ))
    return choices


def preview_values(section_id, selection):
    """Return A, Iz and conspicuous source status for the review table.

    This calculates a display preview, NOT acceptance of an FEM model.
    The dialog requires explicit user consent before importing.
    """
    if not isinstance(selection, dict):
        raise CatalogError(f"{section_id}: invalid mapping")
    mode = selection.get("mode")
    if mode == "go_core_nominal":
        props = nominal_section_properties(
            section_id, axis=selection["axis"], acknowledge_unverified=True,
        )
        return (
            f"{props['A_m2']:.8g}",
            f"{props['Iz_m4']:.9g}",
            "NOMINAL / not manufacturer verified",
        )
    if mode == "manual_starter":
        target = selection.get("section")
        for s in starter_sections():
            if s.get("id") == target and s.get("kind") == "Steel":
                return (
                    f"{s['A']:.8g}",
                    f"{s['Iz']:.9g}",
                    "DEMO SUBSTITUTE — not same physical section",
                )
    raise CatalogError(f"Invalid steel mapping for {section_id}")
