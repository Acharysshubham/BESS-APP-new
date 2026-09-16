"""
Report generation utilities (text/markdown summary).

Kept separate from excel_export.py so that future report formats (PDF, DOCX,
HTML) can be added here without touching the Excel export logic, per the
Future Extensibility requirement (Section 31).
"""

from __future__ import annotations

from typing import List

from calculations.models import (
    ProjectInputs, DischargeYearResult, ChargeYearResult, RTEYearResult,
)


def build_text_summary(
    project_name: str,
    proj: ProjectInputs,
    discharge_results: List[DischargeYearResult],
    charge_results: List[ChargeYearResult],
    rte_results: List[RTEYearResult],
) -> str:
    """Build a plain-text calculation summary, suitable for clipboard/email/log use."""
    lines = [
        f"BESS Sizing Calculation Summary \u2014 {project_name}",
        "=" * 60,
        f"Container Capacity: {proj.container_capacity_mwh:.3f} MWh",
        f"Number of Containers: {proj.num_containers_initial}",
        f"Initial Installed Capacity: {proj.initial_installed_capacity_mwh:.2f} MWh",
        "",
    ]
    if discharge_results:
        d0 = discharge_results[0]
        lines += [
            f"Discharge (Year {d0.year}):",
            f"  Guaranteed DC Discharge Capacity: {d0.guarantee_dc_capacity_mwh:.2f} MWh",
            f"  POI Capacity Excl. Aux: {d0.poi_capacity_excl_aux_mwh:.2f} MWh",
            f"  POI Capacity Incl. Aux: {d0.poi_capacity_incl_aux_mwh:.2f} MWh",
            "",
        ]
    if charge_results:
        c0 = charge_results[0]
        lines += [
            f"Charge (Year {c0.year}):",
            f"  Charge Guarantee Excl. Aux: {c0.charge_guarantee_excl_aux_mwh:.2f} MWh",
            f"  Charge Guarantee Incl. Aux: {c0.charge_guarantee_incl_aux_mwh:.2f} MWh",
            "",
        ]
    if rte_results:
        r0 = rte_results[0]
        lines += [
            f"RTE (Year {r0.year}):",
            f"  DC-DC RTE: {r0.dc_dc_rte_pct:.2f}%",
            f"  AC RTE Excl. Aux: {r0.ac_rte_excl_aux_pct:.2f}%",
            f"  AC RTE Incl. Aux: {r0.ac_rte_incl_aux_pct:.2f}%",
        ]
    return "\n".join(lines)
