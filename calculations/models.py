"""
Data models for the BESS Sizing calculation engine.

These models are pure Python dataclasses with no dependency on Streamlit or
any UI framework, so the calculation engine can be reused for Excel export,
automated testing, or a future API/web deployment.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional


class TimeMode(str, Enum):
    """Selects whether charge/discharge duration is defined directly or via C-rate."""
    TIME = "time"
    C_RATE = "c_rate"


@dataclass
class ProjectInputs:
    """Initial / project-level BESS inputs (Section 4 of the spec)."""

    # DC Installed Capacity per Container (MWh)
    container_capacity_mwh: float = 2.2
    # Initial Number of Containers (Nos.)
    num_containers_initial: int = 100
    # Auxiliary Consumption per Container - Discharge (MW)
    aux_consumption_discharge_mw: float = 0.005
    # Auxiliary Consumption per Container - Charge (MW)
    aux_consumption_charge_mw: float = 0.006

    @property
    def initial_installed_capacity_mwh(self) -> float:
        """Initial Installed Capacity = Container Capacity x Initial No. of Containers."""
        return self.container_capacity_mwh * self.num_containers_initial


@dataclass
class ACEfficiencyChain:
    """Shared AC-side efficiency chain used by both Discharging and Charging (Sections 6 & 12).

    All values are stored as PERCENTAGES (e.g. 98.5 means 98.5%).
    """

    lv_dc_cable_efficiency_pct: float = 99.5      # LV Cable Efficiency / DC Cable Efficiency
    pcs_efficiency_pct: float = 98.6               # PCS Efficiency
    pcs_to_idt_cable_efficiency_pct: float = 99.5   # PCS to IDT (LV) Cable Efficiency
    idt_efficiency_pct: float = 99.0                # IDT Efficiency
    dc_db_efficiency_pct: float = 99.8              # DC DB Efficiency
    mv_cable_switchgear_efficiency_pct: float = 99.5  # MV Cable and MV Switchgear Efficiency
    main_transformer_efficiency_pct: float = 99.0   # Main Power Transformer Efficiency
    interconnecting_efficiency_pct: float = 99.7    # 11kV Cable / Interconnecting Point Efficiency
    measurement_accuracy_pct: float = 99.5          # Measurement Accuracy

    def as_list(self):
        """Return (label, percentage) pairs in engineering order, DC side -> POI."""
        return [
            ("LV Cable / DC Cable Efficiency", self.lv_dc_cable_efficiency_pct),
            ("PCS Efficiency", self.pcs_efficiency_pct),
            ("PCS to IDT (LV) Cable Efficiency", self.pcs_to_idt_cable_efficiency_pct),
            ("IDT Efficiency", self.idt_efficiency_pct),
            ("DC DB Efficiency", self.dc_db_efficiency_pct),
            ("MV Cable & MV Switchgear Efficiency", self.mv_cable_switchgear_efficiency_pct),
            ("Main Power Transformer Efficiency", self.main_transformer_efficiency_pct),
            ("11kV Cable / Interconnecting Point Efficiency", self.interconnecting_efficiency_pct),
            ("Measurement Accuracy", self.measurement_accuracy_pct),
        ]


@dataclass
class DischargeYearInput:
    """Per-year Discharging DC-side user inputs (Section 5.1)."""

    year: int
    enclosures: int
    availability_pct: float = 98.0
    dc_discharge_efficiency_pct: float = 98.0
    soh_pct: float = 100.0
    calendar_degradation_pct: float = 100.0
    dod_pct: float = 90.0


@dataclass
class ChargeYearInput:
    """Per-year Charging DC-side user inputs (Section 11)."""

    year: int
    enclosures: int
    availability_pct: float = 98.0
    dc_charge_efficiency_pct: float = 98.0
    soh_pct: float = 100.0
    calendar_degradation_pct: float = 100.0
    dod_pct: float = 90.0


@dataclass
class DischargeSettings:
    """Global (non-year-specific) discharge settings: time/C-rate mode (Section 7)."""

    time_mode: TimeMode = TimeMode.C_RATE
    discharge_time_hours: float = 4.0
    discharge_c_rate: float = 0.25


@dataclass
class ChargeSettings:
    """Global (non-year-specific) charge settings: time/C-rate mode (Section 16) + DC-DC RTE (Section 14)."""

    time_mode: TimeMode = TimeMode.C_RATE
    charge_time_hours: float = 4.0
    charge_c_rate: float = 0.25
    dc_dc_rte_pct: float = 98.0


@dataclass
class DischargeYearResult:
    """Calculated (read-only) discharge results for a single year."""

    year: int
    installed_dc_capacity_mwh: float = 0.0
    dc_usable_energy_mwh: float = 0.0
    guarantee_dc_capacity_mwh: float = 0.0
    aux_load_discharge_mw: float = 0.0
    discharge_time_hours: float = 0.0
    aux_energy_discharge_mwh: float = 0.0
    poi_capacity_excl_aux_mwh: float = 0.0
    poi_capacity_incl_aux_mwh: float = 0.0
    ac_efficiency_product: float = 0.0


@dataclass
class ChargeYearResult:
    """Calculated (read-only) charge results for a single year."""

    year: int
    installed_dc_capacity_mwh: float = 0.0
    dc_usable_energy_mwh: float = 0.0
    aux_load_charge_mw: float = 0.0
    charge_time_hours: float = 0.0
    aux_energy_charge_mwh: float = 0.0
    charge_guarantee_excl_aux_mwh: float = 0.0
    charge_guarantee_incl_aux_mwh: float = 0.0
    ac_efficiency_product: float = 0.0


@dataclass
class RTEYearResult:
    """Calculated RTE results for a single year."""

    year: int
    dc_dc_rte_pct: float = 0.0
    ac_rte_excl_aux_pct: float = 0.0
    ac_rte_incl_aux_pct: float = 0.0


@dataclass
class ProjectCase:
    """The full editable state of a BESS sizing case (used for save/load as JSON)."""

    project_inputs: ProjectInputs = field(default_factory=ProjectInputs)
    discharge_ac: ACEfficiencyChain = field(default_factory=ACEfficiencyChain)
    charge_ac: ACEfficiencyChain = field(default_factory=ACEfficiencyChain)
    discharge_settings: DischargeSettings = field(default_factory=DischargeSettings)
    charge_settings: ChargeSettings = field(default_factory=ChargeSettings)
    discharge_years: List[DischargeYearInput] = field(default_factory=list)
    charge_years: List[ChargeYearInput] = field(default_factory=list)
    project_name: str = "Untitled BESS Case"
