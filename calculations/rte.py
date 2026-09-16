"""
RTE (Round-Trip Efficiency) calculation engine (Sections 14 & 19 of the specification).
"""

from __future__ import annotations

from typing import List

from .models import DischargeYearResult, ChargeYearResult, RTEYearResult
from .validation import require_positive


def ac_rte_excl_aux_pct(discharge_excl_aux_mwh: float, charge_excl_aux_mwh: float) -> float:
    """AC RTE (Excluding Aux) = Discharge Guarantee (Excl. Aux) / Charge Guarantee (Excl. Aux)."""
    require_positive(charge_excl_aux_mwh, "Charge Guarantee Capacity (Excl. Aux)")
    return (discharge_excl_aux_mwh / charge_excl_aux_mwh) * 100.0


def ac_rte_incl_aux_pct(discharge_incl_aux_mwh: float, charge_incl_aux_mwh: float) -> float:
    """AC RTE (Including Aux) = Discharge Guarantee (Incl. Aux) / Charge Guarantee (Incl. Aux)."""
    require_positive(charge_incl_aux_mwh, "Charge Guarantee Capacity (Incl. Aux)")
    return (discharge_incl_aux_mwh / charge_incl_aux_mwh) * 100.0


def calculate_rte_year(discharge_result: DischargeYearResult, charge_result: ChargeYearResult,
                        dc_dc_rte_pct: float) -> RTEYearResult:
    return RTEYearResult(
        year=discharge_result.year,
        dc_dc_rte_pct=dc_dc_rte_pct,
        ac_rte_excl_aux_pct=ac_rte_excl_aux_pct(
            discharge_result.poi_capacity_excl_aux_mwh, charge_result.charge_guarantee_excl_aux_mwh
        ),
        ac_rte_incl_aux_pct=ac_rte_incl_aux_pct(
            discharge_result.poi_capacity_incl_aux_mwh, charge_result.charge_guarantee_incl_aux_mwh
        ),
    )


def calculate_all_rte_years(
    discharge_results: List[DischargeYearResult],
    charge_results: List[ChargeYearResult],
    dc_dc_rte_pct: float,
) -> List[RTEYearResult]:
    """Pair discharge and charge results by year and compute RTE for each matched year."""
    charge_by_year = {r.year: r for r in charge_results}
    results = []
    for d in discharge_results:
        c = charge_by_year.get(d.year)
        if c is None:
            continue
        results.append(calculate_rte_year(d, c, dc_dc_rte_pct))
    return results
