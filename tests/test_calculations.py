"""
Automated tests for the BESS Sizing calculation engine (Section 30 of the spec).

Run with:
    pytest tests/test_calculations.py -v
"""

import sys
import os
import math
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from calculations.models import (
    ProjectInputs, ACEfficiencyChain, DischargeYearInput, ChargeYearInput,
    DischargeSettings, ChargeSettings, TimeMode,
)
from calculations import discharge as D
from calculations import charge as C
from calculations import rte as R
from calculations.validation import ValidationError, require_percentage, require_positive


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def project():
    return ProjectInputs(
        container_capacity_mwh=2.2,
        num_containers_initial=100,
        aux_consumption_discharge_mw=0.005,
        aux_consumption_charge_mw=0.006,
    )


@pytest.fixture
def flat_ac_chain():
    """An AC chain where every stage is 100% - isolates other calculations from AC losses."""
    return ACEfficiencyChain(
        lv_dc_cable_efficiency_pct=100.0,
        pcs_efficiency_pct=100.0,
        pcs_to_idt_cable_efficiency_pct=100.0,
        idt_efficiency_pct=100.0,
        dc_db_efficiency_pct=100.0,
        mv_cable_switchgear_efficiency_pct=100.0,
        main_transformer_efficiency_pct=100.0,
        interconnecting_efficiency_pct=100.0,
        measurement_accuracy_pct=100.0,
    )


# ---------------------------------------------------------------------------
# Installed DC Capacity
# ---------------------------------------------------------------------------

def test_installed_dc_capacity():
    assert D.installed_dc_capacity_mwh(2.2, 100) == pytest.approx(220.0)


def test_project_initial_installed_capacity(project):
    assert project.initial_installed_capacity_mwh == pytest.approx(220.0)


# ---------------------------------------------------------------------------
# DC Usable Energy
# ---------------------------------------------------------------------------

def test_dc_usable_energy_known_case():
    # 2.2 MWh x 100 x 0.90 x 0.98 x 1.00 x 1.00
    result = D.dc_usable_energy_mwh(
        container_capacity_mwh=2.2, enclosures=100, dod_pct=90.0,
        discharge_efficiency_pct=98.0, calendar_degradation_pct=100.0, soh_pct=100.0,
    )
    expected = 2.2 * 100 * 0.90 * 0.98 * 1.00 * 1.00
    assert result == pytest.approx(expected)


# ---------------------------------------------------------------------------
# Guaranteed DC Discharge Capacity
# ---------------------------------------------------------------------------

def test_guarantee_discharge_capacity_dc_known_case():
    installed = 220.0
    result = D.guarantee_discharge_capacity_dc_mwh(
        installed_dc_capacity=installed, availability_pct=98.0,
        dc_discharge_efficiency_pct=98.0, soh_pct=100.0,
        calendar_degradation_pct=100.0, dod_pct=90.0,
    )
    expected = 220.0 * 0.98 * 0.98 * 1.00 * 1.00 * 0.90
    assert result == pytest.approx(expected)


def test_guarantee_discharge_capacity_full_percent_equals_installed():
    """With all factors at 100%, guaranteed capacity should equal installed capacity."""
    result = D.guarantee_discharge_capacity_dc_mwh(
        installed_dc_capacity=220.0, availability_pct=100.0,
        dc_discharge_efficiency_pct=100.0, soh_pct=100.0,
        calendar_degradation_pct=100.0, dod_pct=100.0,
    )
    assert result == pytest.approx(220.0)


# ---------------------------------------------------------------------------
# Auxiliary Load / Energy - Discharge
# ---------------------------------------------------------------------------

def test_aux_load_discharge(project):
    result = D.aux_load_discharge_mw(project.num_containers_initial, project.aux_consumption_discharge_mw)
    assert result == pytest.approx(100 * 0.005)
    assert result == pytest.approx(0.5)


def test_aux_energy_discharge():
    result = D.aux_energy_discharge_mwh(aux_load_mw=0.5, discharge_time_hours=4.0)
    assert result == pytest.approx(2.0)


# ---------------------------------------------------------------------------
# C-rate / Time conversion
# ---------------------------------------------------------------------------

def test_discharge_time_from_c_rate():
    settings = DischargeSettings(time_mode=TimeMode.C_RATE, discharge_c_rate=0.25)
    assert D.discharge_time_from_settings(settings) == pytest.approx(4.0)


def test_discharge_time_from_direct_entry():
    settings = DischargeSettings(time_mode=TimeMode.TIME, discharge_time_hours=2.5)
    assert D.discharge_time_from_settings(settings) == pytest.approx(2.5)


def test_charge_time_from_c_rate():
    settings = ChargeSettings(time_mode=TimeMode.C_RATE, charge_c_rate=0.5)
    assert C.charge_time_from_settings(settings) == pytest.approx(2.0)


def test_c_rate_must_be_positive():
    settings = DischargeSettings(time_mode=TimeMode.C_RATE, discharge_c_rate=0.0)
    with pytest.raises(ValidationError):
        D.discharge_time_from_settings(settings)


def test_c_rate_negative_rejected():
    settings = DischargeSettings(time_mode=TimeMode.C_RATE, discharge_c_rate=-0.1)
    with pytest.raises(ValidationError):
        D.discharge_time_from_settings(settings)


# ---------------------------------------------------------------------------
# POI Discharge Capacity (excl / incl aux)
# ---------------------------------------------------------------------------

def test_poi_capacity_excl_aux_with_flat_chain(flat_ac_chain):
    # With all AC efficiencies at 100%, POI excl aux == guaranteed DC capacity
    result = D.poi_capacity_excl_aux_mwh(guarantee_dc_capacity=200.0, ac_chain=flat_ac_chain)
    assert result == pytest.approx(200.0)


def test_poi_capacity_excl_aux_with_losses():
    chain = ACEfficiencyChain(
        lv_dc_cable_efficiency_pct=99.0, pcs_efficiency_pct=98.0,
        pcs_to_idt_cable_efficiency_pct=99.0, idt_efficiency_pct=99.0,
        dc_db_efficiency_pct=99.0, mv_cable_switchgear_efficiency_pct=99.0,
        main_transformer_efficiency_pct=99.0, interconnecting_efficiency_pct=99.0,
        measurement_accuracy_pct=99.0,
    )
    product = D.ac_efficiency_product(chain)
    assert product == pytest.approx(0.99 * 0.98 * 0.99 * 0.99 * 0.99 * 0.99 * 0.99 * 0.99 * 0.99)
    result = D.poi_capacity_excl_aux_mwh(guarantee_dc_capacity=200.0, ac_chain=chain)
    assert result == pytest.approx(200.0 * product)


def test_poi_capacity_incl_aux():
    result = D.poi_capacity_incl_aux_mwh(poi_excl_aux=190.0, aux_energy=2.0)
    assert result == pytest.approx(188.0)


# ---------------------------------------------------------------------------
# Full year discharge calculation (integration)
# ---------------------------------------------------------------------------

def test_full_discharge_year_integration(project, flat_ac_chain):
    year_input = DischargeYearInput(
        year=1, enclosures=100, availability_pct=100.0, dc_discharge_efficiency_pct=100.0,
        soh_pct=100.0, calendar_degradation_pct=100.0, dod_pct=100.0,
    )
    settings = DischargeSettings(time_mode=TimeMode.C_RATE, discharge_c_rate=0.25)
    result = D.calculate_discharge_year(project, year_input, flat_ac_chain, settings)

    assert result.installed_dc_capacity_mwh == pytest.approx(220.0)
    assert result.guarantee_dc_capacity_mwh == pytest.approx(220.0)
    assert result.poi_capacity_excl_aux_mwh == pytest.approx(220.0)
    assert result.discharge_time_hours == pytest.approx(4.0)
    assert result.aux_load_discharge_mw == pytest.approx(0.5)
    assert result.aux_energy_discharge_mwh == pytest.approx(2.0)
    assert result.poi_capacity_incl_aux_mwh == pytest.approx(218.0)


# ---------------------------------------------------------------------------
# Charging engine
# ---------------------------------------------------------------------------

def test_aux_load_charge(project):
    result = C.aux_load_charge_mw(project.num_containers_initial, project.aux_consumption_charge_mw)
    assert result == pytest.approx(0.6)


def test_aux_energy_charge():
    assert C.aux_energy_charge_mwh(aux_load_mw=0.6, charge_time_hours=4.0) == pytest.approx(2.4)


def test_dc_usable_energy_charge_uses_charging_efficiency():
    """Confirms charging efficiency (not discharge efficiency) is used - Section 13 requirement."""
    result_charge_eff = C.dc_usable_energy_charge_mwh(
        container_capacity_mwh=2.2, enclosures=100, dod_pct=90.0,
        charging_efficiency_pct=95.0, calendar_degradation_pct=100.0, soh_pct=100.0,
    )
    expected = 2.2 * 100 * 0.90 * 0.95 * 1.00 * 1.00
    assert result_charge_eff == pytest.approx(expected)

    # Using a different discharge efficiency value should NOT affect this result
    result_other_eff = C.dc_usable_energy_charge_mwh(
        container_capacity_mwh=2.2, enclosures=100, dod_pct=90.0,
        charging_efficiency_pct=95.0, calendar_degradation_pct=100.0, soh_pct=100.0,
    )
    assert result_charge_eff == pytest.approx(result_other_eff)


def test_charge_guarantee_excl_aux_with_flat_chain(flat_ac_chain):
    result = C.charge_guarantee_excl_aux_mwh(
        dc_usable_energy=178.2, ac_chain=flat_ac_chain, dc_dc_rte_pct=100.0,
    )
    assert result == pytest.approx(178.2)


def test_charge_guarantee_excl_aux_with_rte_and_losses(flat_ac_chain):
    result = C.charge_guarantee_excl_aux_mwh(
        dc_usable_energy=178.2, ac_chain=flat_ac_chain, dc_dc_rte_pct=98.0,
    )
    assert result == pytest.approx(178.2 / 0.98)


def test_charge_guarantee_incl_aux():
    result = C.charge_guarantee_incl_aux_mwh(guarantee_excl_aux=180.0, aux_energy=2.4)
    assert result == pytest.approx(182.4)


def test_full_charge_year_integration(project, flat_ac_chain):
    year_input = ChargeYearInput(
        year=1, enclosures=100, availability_pct=100.0, dc_charge_efficiency_pct=100.0,
        soh_pct=100.0, calendar_degradation_pct=100.0, dod_pct=100.0,
    )
    settings = ChargeSettings(time_mode=TimeMode.C_RATE, charge_c_rate=0.25, dc_dc_rte_pct=100.0)
    result = C.calculate_charge_year(project, year_input, flat_ac_chain, settings)

    assert result.installed_dc_capacity_mwh == pytest.approx(220.0)
    assert result.dc_usable_energy_mwh == pytest.approx(220.0)
    assert result.charge_guarantee_excl_aux_mwh == pytest.approx(220.0)
    assert result.charge_time_hours == pytest.approx(4.0)
    assert result.aux_load_charge_mw == pytest.approx(0.6)
    assert result.aux_energy_charge_mwh == pytest.approx(2.4)
    assert result.charge_guarantee_incl_aux_mwh == pytest.approx(222.4)


# ---------------------------------------------------------------------------
# RTE
# ---------------------------------------------------------------------------

def test_ac_rte_excl_aux():
    result = R.ac_rte_excl_aux_pct(discharge_excl_aux_mwh=180.0, charge_excl_aux_mwh=200.0)
    assert result == pytest.approx(90.0)


def test_ac_rte_incl_aux():
    result = R.ac_rte_incl_aux_pct(discharge_incl_aux_mwh=176.0, charge_incl_aux_mwh=200.0)
    assert result == pytest.approx(88.0)


def test_ac_rte_zero_charge_capacity_raises():
    with pytest.raises(ValidationError):
        R.ac_rte_excl_aux_pct(discharge_excl_aux_mwh=100.0, charge_excl_aux_mwh=0.0)


def test_calculate_all_rte_years_matches_by_year(project, flat_ac_chain):
    d_inputs = [
        DischargeYearInput(year=1, enclosures=100, availability_pct=100, dc_discharge_efficiency_pct=100,
                            soh_pct=100, calendar_degradation_pct=100, dod_pct=100),
        DischargeYearInput(year=2, enclosures=100, availability_pct=98, dc_discharge_efficiency_pct=98,
                            soh_pct=99, calendar_degradation_pct=99, dod_pct=90),
    ]
    c_inputs = [
        ChargeYearInput(year=1, enclosures=100, availability_pct=100, dc_charge_efficiency_pct=100,
                         soh_pct=100, calendar_degradation_pct=100, dod_pct=100),
        ChargeYearInput(year=2, enclosures=100, availability_pct=98, dc_charge_efficiency_pct=98,
                         soh_pct=99, calendar_degradation_pct=99, dod_pct=90),
    ]
    d_settings = DischargeSettings(time_mode=TimeMode.C_RATE, discharge_c_rate=0.25)
    c_settings = ChargeSettings(time_mode=TimeMode.C_RATE, charge_c_rate=0.25, dc_dc_rte_pct=98.0)

    d_results = D.calculate_all_discharge_years(project, d_inputs, flat_ac_chain, d_settings)
    c_results = C.calculate_all_charge_years(project, c_inputs, flat_ac_chain, c_settings)

    rte_results = R.calculate_all_rte_years(d_results, c_results, dc_dc_rte_pct=98.0)

    assert len(rte_results) == 2
    assert rte_results[0].year == 1
    assert rte_results[1].year == 2
    for r in rte_results:
        assert 0 < r.ac_rte_excl_aux_pct <= 150  # sanity bound, not a hard engineering limit
        assert 0 < r.ac_rte_incl_aux_pct <= 150


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def test_require_percentage_rejects_zero_by_default():
    with pytest.raises(ValidationError):
        require_percentage(0.0, "SOH")


def test_require_percentage_rejects_above_100():
    with pytest.raises(ValidationError):
        require_percentage(101.0, "Availability")


def test_require_percentage_accepts_valid_range():
    require_percentage(50.0, "DOD")  # should not raise
    require_percentage(100.0, "SOH")  # should not raise


def test_require_positive_rejects_negative_and_zero():
    with pytest.raises(ValidationError):
        require_positive(0.0, "Capacity")
    with pytest.raises(ValidationError):
        require_positive(-5.0, "Capacity")


# ---------------------------------------------------------------------------
# Multi-year regression: increasing enclosures/degradation should move results sensibly
# ---------------------------------------------------------------------------

def test_multi_year_degradation_reduces_guaranteed_capacity(project, flat_ac_chain):
    settings = DischargeSettings(time_mode=TimeMode.C_RATE, discharge_c_rate=0.25)
    year1 = DischargeYearInput(year=1, enclosures=100, availability_pct=100, dc_discharge_efficiency_pct=100,
                                soh_pct=100, calendar_degradation_pct=100, dod_pct=100)
    year5 = DischargeYearInput(year=5, enclosures=100, availability_pct=100, dc_discharge_efficiency_pct=100,
                                soh_pct=92, calendar_degradation_pct=97, dod_pct=100)

    r1 = D.calculate_discharge_year(project, year1, flat_ac_chain, settings)
    r5 = D.calculate_discharge_year(project, year5, flat_ac_chain, settings)

    assert r5.guarantee_dc_capacity_mwh < r1.guarantee_dc_capacity_mwh


def test_live_recalculation_on_container_capacity_change(project, flat_ac_chain):
    """Simulates Section 21: changing container capacity must propagate through the chain."""
    year_input = DischargeYearInput(year=1, enclosures=100, availability_pct=100,
                                     dc_discharge_efficiency_pct=100, soh_pct=100,
                                     calendar_degradation_pct=100, dod_pct=100)
    settings = DischargeSettings(time_mode=TimeMode.C_RATE, discharge_c_rate=0.25)

    project.container_capacity_mwh = 2.2
    r_before = D.calculate_discharge_year(project, year_input, flat_ac_chain, settings)

    project.container_capacity_mwh = 2.5
    r_after = D.calculate_discharge_year(project, year_input, flat_ac_chain, settings)

    assert r_after.installed_dc_capacity_mwh > r_before.installed_dc_capacity_mwh
    assert r_after.guarantee_dc_capacity_mwh > r_before.guarantee_dc_capacity_mwh
    assert r_after.poi_capacity_excl_aux_mwh > r_before.poi_capacity_excl_aux_mwh


if __name__ == "__main__":
    sys.exit(pytest.main([__file__, "-v"]))
