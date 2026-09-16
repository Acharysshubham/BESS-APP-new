"""UI for Section 4: Project / Initial BESS Inputs."""

import streamlit as st

from calculations.models import ProjectInputs
from calculations.validation import collect_project_inputs_issues
from ui.styles import section_header_html, subsection_header_html, kpi_card_html, calc_badge_html


def render_initial_inputs() -> ProjectInputs:
    st.markdown(section_header_html("Project / Initial BESS Inputs"), unsafe_allow_html=True)

    proj: ProjectInputs = st.session_state.project_inputs

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(subsection_header_html("Container & Capacity"), unsafe_allow_html=True)
        proj.container_capacity_mwh = st.number_input(
            "DC Installed Capacity per Container (MWh)",
            min_value=0.0, value=float(proj.container_capacity_mwh), step=0.1, format="%.3f",
            help="Nameplate DC energy capacity of a single battery container/enclosure.",
            key="in_container_capacity",
        )
        proj.num_containers_initial = st.number_input(
            "Initial Number of Containers (Nos.)",
            min_value=1, value=int(proj.num_containers_initial), step=1,
            help="Total number of battery containers/enclosures installed at project start.",
            key="in_num_containers",
        )

        st.markdown(
            kpi_card_html(
                "Initial Installed Capacity " ,
                f"{proj.initial_installed_capacity_mwh:,.2f}",
                "MWh", accent="accent-cyan",
            ),
            unsafe_allow_html=True,
        )
        st.caption("Calculated = Container Capacity x Initial No. of Containers " + calc_badge_html(), unsafe_allow_html=True)

    with col2:
        st.markdown(subsection_header_html("Auxiliary Consumption per Container"), unsafe_allow_html=True)
        proj.aux_consumption_discharge_mw = st.number_input(
            "Auxiliary Consumption per Container - Discharge (MW)",
            min_value=0.0, value=float(proj.aux_consumption_discharge_mw), step=0.001, format="%.4f",
            help="Per-container auxiliary power draw while discharging (HVAC, controls, fans, etc.).",
            key="in_aux_disch",
        )
        proj.aux_consumption_charge_mw = st.number_input(
            "Auxiliary Consumption per Container - Charge (MW)",
            min_value=0.0, value=float(proj.aux_consumption_charge_mw), step=0.001, format="%.4f",
            help="Per-container auxiliary power draw while charging.",
            key="in_aux_charge",
        )

        st.markdown(
            kpi_card_html("Aux Load - Discharge (Project)",
                          f"{proj.num_containers_initial * proj.aux_consumption_discharge_mw:,.3f}",
                          "MW"),
            unsafe_allow_html=True,
        )
        st.markdown(
            kpi_card_html("Aux Load - Charge (Project)",
                          f"{proj.num_containers_initial * proj.aux_consumption_charge_mw:,.3f}",
                          "MW"),
            unsafe_allow_html=True,
        )

    issues = collect_project_inputs_issues(
        proj.container_capacity_mwh, proj.num_containers_initial,
        proj.aux_consumption_discharge_mw, proj.aux_consumption_charge_mw,
    )
    for issue in issues:
        st.error(f"**{issue.field_name}** {issue.message}")

    st.session_state.project_inputs = proj
    return proj
