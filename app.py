"""
BESS Sizing Calculation Software
==================================
Professional, modular Battery Energy Storage System (BESS) sizing calculator
for engineering / EPC use. See README.md for full documentation.

Run with:
    streamlit run app.py
"""

import json
from datetime import datetime

import streamlit as st

from calculations.models import (
    ProjectInputs, ACEfficiencyChain, DischargeSettings, ChargeSettings,
    DischargeYearInput, ChargeYearInput, TimeMode,
)
from ui.styles import CUSTOM_CSS
from ui.inputs import render_initial_inputs
from ui.discharge_ui import render_discharge_dc_side, render_discharge_ac_side, render_discharge_results
from ui.charge_ui import render_charge_dc_side, render_charge_ac_side, render_charge_results, render_rte_section
from ui.results import render_final_results
from export.excel_export import build_excel_workbook
from utils.helpers import dataclass_to_dict

st.set_page_config(
    page_title="BESS Sizing Calculation Software",
    page_icon="\u26A1",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(CUSTOM_CSS, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Session state initialization
# ---------------------------------------------------------------------------

def init_default_years():
    """Create a sensible default multi-year table so the app is immediately usable."""
    discharge_years = []
    charge_years = []
    for y in range(1, 4):
        discharge_years.append(DischargeYearInput(
            year=y, enclosures=100,
            availability_pct=98.0, dc_discharge_efficiency_pct=98.0,
            soh_pct=max(80.0, 100.0 - (y - 1) * 2.0),
            calendar_degradation_pct=max(90.0, 100.0 - (y - 1) * 1.0),
            dod_pct=90.0,
        ))
        charge_years.append(ChargeYearInput(
            year=y, enclosures=100,
            availability_pct=98.0, dc_charge_efficiency_pct=98.0,
            soh_pct=max(80.0, 100.0 - (y - 1) * 2.0),
            calendar_degradation_pct=max(90.0, 100.0 - (y - 1) * 1.0),
            dod_pct=90.0,
        ))
    return discharge_years, charge_years


def init_session_state():
    if "initialized" in st.session_state:
        return
    st.session_state.project_name = "New BESS Sizing Case"
    st.session_state.project_inputs = ProjectInputs()
    st.session_state.discharge_ac = ACEfficiencyChain()
    st.session_state.charge_ac = ACEfficiencyChain()
    st.session_state.discharge_settings = DischargeSettings()
    st.session_state.charge_settings = ChargeSettings()
    dy, cy = init_default_years()
    st.session_state.discharge_years = dy
    st.session_state.charge_years = cy
    st.session_state.discharge_results = []
    st.session_state.charge_results = []
    st.session_state.rte_results = []
    st.session_state.initialized = True


def reset_all_inputs():
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    init_session_state()


init_session_state()


# ---------------------------------------------------------------------------
# Header
# ---------------------------------------------------------------------------

st.markdown(
    f"""
    <div class="bess-header">
        <h1>\u26A1 BESS Sizing Calculation Software</h1>
        <p>Engineering-grade Battery Energy Storage System sizing &amp; RTE calculation tool
        &nbsp;|&nbsp; Project: <b>{st.session_state.project_name}</b></p>
    </div>
    """,
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Sidebar: navigation + project tools
# ---------------------------------------------------------------------------

with st.sidebar:
    st.markdown("### BESS SIZING")
    st.session_state.project_name = st.text_input("Project Name", value=st.session_state.project_name)

    page = st.radio(
        "Navigate",
        options=[
            "Project / Initial Inputs",
            "Discharging",
            "Charging",
            "RTE",
            "Final Results",
            "Calculation Sheet / Export",
        ],
        key="nav_page",
    )

    st.markdown("---")
    st.markdown("#### Project Tools")

    if st.button("\U0001F504 Reset Inputs", use_container_width=True):
        reset_all_inputs()
        st.rerun()

    # Save current case as JSON
    case_dict = {
        "project_name": st.session_state.project_name,
        "project_inputs": dataclass_to_dict(st.session_state.project_inputs),
        "discharge_ac": dataclass_to_dict(st.session_state.discharge_ac),
        "charge_ac": dataclass_to_dict(st.session_state.charge_ac),
        "discharge_settings": dataclass_to_dict(st.session_state.discharge_settings),
        "charge_settings": dataclass_to_dict(st.session_state.charge_settings),
        "discharge_years": dataclass_to_dict(st.session_state.discharge_years),
        "charge_years": dataclass_to_dict(st.session_state.charge_years),
    }
    st.download_button(
        "\U0001F4BE Save Case (JSON)",
        data=json.dumps(case_dict, indent=2),
        file_name=f"bess_case_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        mime="application/json",
        use_container_width=True,
    )

    uploaded = st.file_uploader("\U0001F4C2 Load Case (JSON)", type=["json"], label_visibility="collapsed")
    if uploaded is not None:
        try:
            data = json.load(uploaded)
            st.session_state.project_name = data.get("project_name", "Loaded BESS Case")
            pi = data["project_inputs"]
            st.session_state.project_inputs = ProjectInputs(**pi)
            st.session_state.discharge_ac = ACEfficiencyChain(**data["discharge_ac"])
            st.session_state.charge_ac = ACEfficiencyChain(**data["charge_ac"])
            ds = data["discharge_settings"]
            ds["time_mode"] = TimeMode(ds["time_mode"])
            st.session_state.discharge_settings = DischargeSettings(**ds)
            cs = data["charge_settings"]
            cs["time_mode"] = TimeMode(cs["time_mode"])
            st.session_state.charge_settings = ChargeSettings(**cs)
            st.session_state.discharge_years = [DischargeYearInput(**yi) for yi in data["discharge_years"]]
            st.session_state.charge_years = [ChargeYearInput(**yi) for yi in data["charge_years"]]
            st.success("Case loaded successfully.")
            st.rerun()
        except Exception as e:
            st.error(f"Could not load case file: {e}")

    st.markdown("---")
    st.caption("BESS Sizing Calculation Software \u2014 v1.0")
    st.caption("Calculation engine is fully decoupled from the UI for auditability and reuse.")


# ---------------------------------------------------------------------------
# Page routing
# ---------------------------------------------------------------------------

if page == "Project / Initial Inputs":
    render_initial_inputs()

elif page == "Discharging":
    tab1, tab2, tab3 = st.tabs(["DC Side", "AC Side", "Discharge Results"])
    with tab1:
        render_discharge_dc_side()
    with tab2:
        render_discharge_ac_side()
    with tab3:
        render_discharge_results()

elif page == "Charging":
    tab1, tab2, tab3 = st.tabs(["DC Side", "AC Side", "Charge Results"])
    with tab1:
        render_charge_dc_side()
    with tab2:
        render_charge_ac_side()
    with tab3:
        render_charge_results()

elif page == "RTE":
    # Ensure discharge/charge results are computed before RTE (in case user jumped straight here)
    from calculations import discharge as D, charge as C
    proj = st.session_state.project_inputs
    if st.session_state.discharge_years:
        st.session_state.discharge_results = D.calculate_all_discharge_years(
            proj, st.session_state.discharge_years, st.session_state.discharge_ac, st.session_state.discharge_settings
        )
    if st.session_state.charge_years:
        st.session_state.charge_results = C.calculate_all_charge_years(
            proj, st.session_state.charge_years, st.session_state.charge_ac, st.session_state.charge_settings
        )
    render_rte_section()

elif page == "Final Results":
    from calculations import discharge as D, charge as C, rte as R
    proj = st.session_state.project_inputs
    if st.session_state.discharge_years:
        st.session_state.discharge_results = D.calculate_all_discharge_years(
            proj, st.session_state.discharge_years, st.session_state.discharge_ac, st.session_state.discharge_settings
        )
    if st.session_state.charge_years:
        st.session_state.charge_results = C.calculate_all_charge_years(
            proj, st.session_state.charge_years, st.session_state.charge_ac, st.session_state.charge_settings
        )
    if st.session_state.discharge_results and st.session_state.charge_results:
        st.session_state.rte_results = R.calculate_all_rte_years(
            st.session_state.discharge_results, st.session_state.charge_results,
            st.session_state.charge_settings.dc_dc_rte_pct,
        )
    render_final_results()

elif page == "Calculation Sheet / Export":
    st.markdown('<div class="section-header">Calculation Sheet / Export</div>', unsafe_allow_html=True)

    from calculations import discharge as D, charge as C, rte as R
    proj = st.session_state.project_inputs

    if not st.session_state.discharge_years or not st.session_state.charge_years:
        st.warning("Add at least one Discharging year and one Charging year before exporting.")
    else:
        discharge_results = D.calculate_all_discharge_years(
            proj, st.session_state.discharge_years, st.session_state.discharge_ac, st.session_state.discharge_settings
        )
        charge_results = C.calculate_all_charge_years(
            proj, st.session_state.charge_years, st.session_state.charge_ac, st.session_state.charge_settings
        )
        rte_results = R.calculate_all_rte_years(
            discharge_results, charge_results, st.session_state.charge_settings.dc_dc_rte_pct
        )
        st.session_state.discharge_results = discharge_results
        st.session_state.charge_results = charge_results
        st.session_state.rte_results = rte_results

        st.write(
            "The exported workbook contains 5 sheets: **Summary**, **Initial Inputs**, "
            "**Discharging Calculation**, **Charging Calculation**, and **RTE** \u2014 fully "
            "formatted with headers, units, number formatting, borders, and frozen panes."
        )

        excel_bytes = build_excel_workbook(
            project_name=st.session_state.project_name,
            proj=proj,
            discharge_ac=st.session_state.discharge_ac,
            charge_ac=st.session_state.charge_ac,
            discharge_settings=st.session_state.discharge_settings,
            charge_settings=st.session_state.charge_settings,
            discharge_years=st.session_state.discharge_years,
            charge_years=st.session_state.charge_years,
            discharge_results=discharge_results,
            charge_results=charge_results,
            rte_results=rte_results,
        )

        st.download_button(
            "\U0001F4E5 Export to Excel (.xlsx)",
            data=excel_bytes,
            file_name=f"BESS_Calculation_Sheet_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True,
        )

        st.markdown("---")
        st.caption("Preview \u2014 Discharge results included in export:")
        import pandas as pd
        st.dataframe(
            pd.DataFrame([{
                "Year": r.year,
                "Guaranteed DC Capacity (MWh)": round(r.guarantee_dc_capacity_mwh, 2),
                "POI Excl. Aux (MWh)": round(r.poi_capacity_excl_aux_mwh, 2),
                "POI Incl. Aux (MWh)": round(r.poi_capacity_incl_aux_mwh, 2),
            } for r in discharge_results]),
            use_container_width=True, hide_index=True,
        )

st.markdown(
    '<div class="footer-note">BESS Sizing Calculation Software &mdash; '
    'Calculation engine decoupled from UI for auditability, testing, and future extensibility.</div>',
    unsafe_allow_html=True,
)
