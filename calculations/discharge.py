"""
Discharging calculation engine (Sections 5, 6, 7, 8, 9, 10 of the specification).

Pure functions only - no Streamlit / UI dependency, so this module can be
reused for Excel export, automated testing, or a future API.
"""

from __future__ import annotations

from typing import List

from .models import (
    ProjectInputs,
    ACEfficiencyChain,
    DischargeYearInput,
    DischargeSettings,
    DischargeYearResult,
    TimeMode,
)
from .validation import require_positive


def pct_to_factor(pct: float) -> float:
    """Convert a percentage value (e.g. 98.5) to a decimal factor (0.985)."""
    return pct / 100.0


def installed_dc_capacity_mwh(container_capacity_mwh: float, enclosures: int) -> float:
    """Installed DC Capacity = DC Installed Capacity per Container x No. of Enclosures."""
    return container_capacity_mwh * enclosures


def dc_usable_energy_mwh(container_capacity_mwh: float, enclosures: int,
                          dod_pct: float, discharge_efficiency_pct: float,
                          calendar_degradation_pct: float, soh_pct: float) -> float:
    """DC Usable Energy = Battery Nameplate Energy x Qty x DOD x Discharge Eff x
    FAT-SAT Calendar Degradation x SOH  (Section 13)."""
    return (
        container_capacity_mwh
        * enclosures
        * pct_to_factor(dod_pct)
        * pct_to_factor(discharge_efficiency_pct)
        * pct_to_factor(calendar_degradation_pct)
        * pct_to_factor(soh_pct)
    )


def guarantee_discharge_capacity_dc_mwh(installed_dc_capacity: float, availability_pct: float,
                                         dc_discharge_efficiency_pct: float, soh_pct: float,
                                         calendar_degradation_pct: float, dod_pct: float) -> float:
    """Guaranteed Discharge Capacity at DC Side (Section 5.1) - calculated, never a user input."""
    return (
        installed_dc_capacity
        * pct_to_factor(availability_pct)
        * pct_to_factor(dc_discharge_efficiency_pct)
        * pct_to_factor(soh_pct)
        * pct_to_factor(calendar_degradation_pct)
        * pct_to_factor(dod_pct)
    )


def aux_load_discharge_mw(num_containers_initial: int, aux_consumption_discharge_mw: float) -> float:
    """Aux Load Discharge = Initial No. of Containers x Aux Consumption per Container (Section 6)."""
    return num_containers_initial * aux_consumption_discharge_mw


def discharge_time_from_settings(settings: DischargeSettings) -> float:
    """Resolve Discharge Time (hours) from either direct entry or C-rate (Section 7)."""
    if settings.time_mode == TimeMode.C_RATE:
        require_positive(settings.discharge_c_rate, "Discharge C-rate")
        return 1.0 / settings.discharge_c_rate
    require_positive(settings.discharge_time_hours, "Discharge Time")
    return settings.discharge_time_hours


def discharge_c_rate_from_settings(settings: DischargeSettings) -> float:
    """Resolve the equivalent C-rate for display purposes, regardless of active mode."""
    if settings.time_mode == TimeMode.C_RATE:
        return settings.discharge_c_rate
    require_positive(settings.discharge_time_hours, "Discharge Time")
    return 1.0 / settings.discharge_time_hours


def ac_efficiency_product(ac_chain: ACEfficiencyChain) -> float:
    """Product of all AC-side efficiency factors, DC side -> POI."""
    product = 1.0
    for _label, pct in ac_chain.as_list():
        product *= pct_to_factor(pct)
    return product


def poi_capacity_excl_aux_mwh(guarantee_dc_capacity: float, ac_chain: ACEfficiencyChain) -> float:
    """Guaranteed Capacity at POI (Excluding Aux) (Section 8)."""
    return guarantee_dc_capacity * ac_efficiency_product(ac_chain)


def aux_energy_discharge_mwh(aux_load_mw: float, discharge_time_hours: float) -> float:
    """Aux Energy Discharge = Aux Load x Discharge Time (Section 9). MW x h = MWh."""
    return aux_load_mw * discharge_time_hours


def poi_capacity_incl_aux_mwh(poi_excl_aux: float, aux_energy: float) -> float:
    """Guaranteed Capacity at POI (Including Aux) (Section 10)."""
    return poi_excl_aux - aux_energy


def calculate_discharge_year(
    project: ProjectInputs,
    year_input: DischargeYearInput,
    ac_chain: ACEfficiencyChain,
    settings: DischargeSettings,
) -> DischargeYearResult:
    """Run the full discharging calculation chain for a single year."""

    installed_dc = installed_dc_capacity_mwh(project.container_capacity_mwh, year_input.enclosures)

    usable_energy = dc_usable_energy_mwh(
        project.container_capacity_mwh,
        year_input.enclosures,
        year_input.dod_pct,
        year_input.dc_discharge_efficiency_pct,
        year_input.calendar_degradation_pct,
        year_input.soh_pct,
    )

    guarantee_dc = guarantee_discharge_capacity_dc_mwh(
        installed_dc,
        year_input.availability_pct,
        year_input.dc_discharge_efficiency_pct,
        year_input.soh_pct,
        year_input.calendar_degradation_pct,
        year_input.dod_pct,
    )

    aux_load = aux_load_discharge_mw(project.num_containers_initial, project.aux_consumption_discharge_mw)
    disch_time = discharge_time_from_settings(settings)

    poi_excl = poi_capacity_excl_aux_mwh(guarantee_dc, ac_chain)
    aux_energy = aux_energy_discharge_mwh(aux_load, disch_time)
    poi_incl = poi_capacity_incl_aux_mwh(poi_excl, aux_energy)

    return DischargeYearResult(
        year=year_input.year,
        installed_dc_capacity_mwh=installed_dc,
        dc_usable_energy_mwh=usable_energy,
        guarantee_dc_capacity_mwh=guarantee_dc,
        aux_load_discharge_mw=aux_load,
        discharge_time_hours=disch_time,
        aux_energy_discharge_mwh=aux_energy,
        poi_capacity_excl_aux_mwh=poi_excl,
        poi_capacity_incl_aux_mwh=poi_incl,
        ac_efficiency_product=ac_efficiency_product(ac_chain),
    )


def calculate_all_discharge_years(
    project: ProjectInputs,
    year_inputs: List[DischargeYearInput],
    ac_chain: ACEfficiencyChain,
    settings: DischargeSettings,
) -> List[DischargeYearResult]:
    return [calculate_discharge_year(project, yi, ac_chain, settings) for yi in year_inputs]
