"""
Charging calculation engine (Sections 11, 12, 13, 14, 15, 16, 17, 18 of the specification).

ENGINEERING AMBIGUITY FLAG (Section 36 compliance)
----------------------------------------------------
Section 15 of the specification writes the Charge Guarantee Capacity formula using the
generic term "Discharge Efficiency" inside the charging-side formula:

    Charge Guarantee Capacity (Excl. Aux) =
        (Battery Nameplate Energy x Qty x DOD x Discharge Efficiency x
         FAT-SAT Calendar Degradation x SOH) / (AC efficiencies) / DC-DC RTE

However, Section 13 explicitly instructs: "Where the charging calculation specifically
requires charging efficiency, use the charging-side efficiency consistently and
transparently. Do not silently substitute discharge efficiency for charging efficiency
where the engineering calculation requires the charging efficiency."

This module resolves the ambiguity by using the DC CHARGING EFFICIENCY (not discharge
efficiency) inside the charging-side DC Usable Energy / Charge Guarantee Capacity
formulas, per the explicit Section 13 instruction. This mapping is isolated in the
`CHARGE_EFFICIENCY_MAPPING_NOTE` constant below and in `dc_usable_energy_charge_mwh()`
so it can be easily changed later if the intended engineering methodology differs.

Similarly, Section 15's denominator lists only three efficiency terms ("DC/AC Cable
Efficiency x PCS Efficiency x Transformer Efficiency") but Section 15 also states:
"Where the detailed AC path contains multiple cable/switchgear/transformer efficiencies,
include all applicable efficiencies consistently. Do not hide or omit efficiency stages."
Since Section 12 defines the SAME detailed 9-stage AC efficiency chain for charging as
for discharging (Section 6), this module divides by the FULL 9-stage AC efficiency
product rather than only 3 generic terms, to avoid hiding efficiency stages.
"""

from __future__ import annotations

from typing import List

from .models import (
    ProjectInputs,
    ACEfficiencyChain,
    ChargeYearInput,
    ChargeSettings,
    ChargeYearResult,
    TimeMode,
)
from .validation import require_positive
from .discharge import pct_to_factor, installed_dc_capacity_mwh, ac_efficiency_product

CHARGE_EFFICIENCY_MAPPING_NOTE = (
    "Charging-side formulas use DC Charging Efficiency (not Discharge Efficiency) per "
    "Section 13 instruction, resolving the Section 15 formula's generic wording. "
    "The full 9-stage AC efficiency chain (Section 12) is used as the divisor per the "
    "'do not hide or omit efficiency stages' instruction in Section 15."
)


def dc_usable_energy_charge_mwh(container_capacity_mwh: float, enclosures: int,
                                 dod_pct: float, charging_efficiency_pct: float,
                                 calendar_degradation_pct: float, soh_pct: float) -> float:
    """DC Usable Energy (Charging side), using DC Charging Efficiency (see module note)."""
    return (
        container_capacity_mwh
        * enclosures
        * pct_to_factor(dod_pct)
        * pct_to_factor(charging_efficiency_pct)
        * pct_to_factor(calendar_degradation_pct)
        * pct_to_factor(soh_pct)
    )


def aux_load_charge_mw(num_containers_initial: int, aux_consumption_charge_mw: float) -> float:
    """Aux Load Charge = Initial No. of Containers x Aux Consumption per Container (Section 12)."""
    return num_containers_initial * aux_consumption_charge_mw


def charge_time_from_settings(settings: ChargeSettings) -> float:
    """Resolve Charge Time (hours) from either direct entry or C-rate (Section 16)."""
    if settings.time_mode == TimeMode.C_RATE:
        require_positive(settings.charge_c_rate, "Charge C-rate")
        return 1.0 / settings.charge_c_rate
    require_positive(settings.charge_time_hours, "Charge Time")
    return settings.charge_time_hours


def charge_c_rate_from_settings(settings: ChargeSettings) -> float:
    """Resolve the equivalent C-rate for display purposes, regardless of active mode."""
    if settings.time_mode == TimeMode.C_RATE:
        return settings.charge_c_rate
    require_positive(settings.charge_time_hours, "Charge Time")
    return 1.0 / settings.charge_time_hours


def charge_guarantee_excl_aux_mwh(dc_usable_energy: float, ac_chain: ACEfficiencyChain,
                                   dc_dc_rte_pct: float) -> float:
    """Charge Guarantee Capacity (Excluding Aux) (Section 15).

    = DC Usable Energy / (full AC efficiency product) / DC-DC RTE factor
    """
    require_positive(dc_dc_rte_pct, "DC-DC RTE")
    ac_product = ac_efficiency_product(ac_chain)
    rte_factor = pct_to_factor(dc_dc_rte_pct)
    return dc_usable_energy / ac_product / rte_factor


def aux_energy_charge_mwh(aux_load_mw: float, charge_time_hours: float) -> float:
    """Aux Energy Charge = Aux Load Charge x Charge Time (Section 17). MW x h = MWh."""
    return aux_load_mw * charge_time_hours


def charge_guarantee_incl_aux_mwh(guarantee_excl_aux: float, aux_energy: float) -> float:
    """Charge Guarantee Capacity (Including Aux) (Section 18)."""
    return guarantee_excl_aux + aux_energy


def calculate_charge_year(
    project: ProjectInputs,
    year_input: ChargeYearInput,
    ac_chain: ACEfficiencyChain,
    settings: ChargeSettings,
) -> ChargeYearResult:
    """Run the full charging calculation chain for a single year."""

    installed_dc = installed_dc_capacity_mwh(project.container_capacity_mwh, year_input.enclosures)

    usable_energy = dc_usable_energy_charge_mwh(
        project.container_capacity_mwh,
        year_input.enclosures,
        year_input.dod_pct,
        year_input.dc_charge_efficiency_pct,
        year_input.calendar_degradation_pct,
        year_input.soh_pct,
    )

    aux_load = aux_load_charge_mw(project.num_containers_initial, project.aux_consumption_charge_mw)
    charge_time = charge_time_from_settings(settings)

    guarantee_excl = charge_guarantee_excl_aux_mwh(usable_energy, ac_chain, settings.dc_dc_rte_pct)
    aux_energy = aux_energy_charge_mwh(aux_load, charge_time)
    guarantee_incl = charge_guarantee_incl_aux_mwh(guarantee_excl, aux_energy)

    return ChargeYearResult(
        year=year_input.year,
        installed_dc_capacity_mwh=installed_dc,
        dc_usable_energy_mwh=usable_energy,
        aux_load_charge_mw=aux_load,
        charge_time_hours=charge_time,
        aux_energy_charge_mwh=aux_energy,
        charge_guarantee_excl_aux_mwh=guarantee_excl,
        charge_guarantee_incl_aux_mwh=guarantee_incl,
        ac_efficiency_product=ac_efficiency_product(ac_chain),
    )


def calculate_all_charge_years(
    project: ProjectInputs,
    year_inputs: List[ChargeYearInput],
    ac_chain: ACEfficiencyChain,
    settings: ChargeSettings,
) -> List[ChargeYearResult]:
    return [calculate_charge_year(project, yi, ac_chain, settings) for yi in year_inputs]
