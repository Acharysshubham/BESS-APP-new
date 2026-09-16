"""UI for Section 24: Final Results Dashboard."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from ui.styles import section_header_html, subsection_header_html, kpi_card_html


def render_final_results():
    st.markdown(section_header_html("Final Results Dashboard"), unsafe_allow_html=True)

    proj = st.session_state.project_inputs
    discharge_results = st.session_state.get("discharge_results", [])
    charge_results = st.session_state.get("charge_results", [])
    rte_results = st.session_state.get("rte_results", [])

    if not discharge_results or not charge_results or not rte_results:
        st.warning("Complete the Discharging, Charging, and RTE sections first to view final results.")
        return

    # Use the first year as the headline "at commissioning" snapshot
    d0 = discharge_results[0]
    c0 = charge_results[0]
    r0 = rte_results[0]

    st.markdown(subsection_header_html("BESS"), unsafe_allow_html=True)
    cols = st.columns(4)
    with cols[0]:
        st.markdown(kpi_card_html("Number of Containers", f"{proj.num_containers_initial:,}", "Nos."), unsafe_allow_html=True)
    with cols[1]:
        st.markdown(kpi_card_html("Container Capacity", f"{proj.container_capacity_mwh:,.2f}", "MWh"), unsafe_allow_html=True)
    with cols[2]:
        st.markdown(kpi_card_html("Installed DC Capacity", f"{d0.installed_dc_capacity_mwh:,.2f}", "MWh"), unsafe_allow_html=True)
    with cols[3]:
        st.markdown(kpi_card_html("DC Usable Energy", f"{d0.dc_usable_energy_mwh:,.2f}", "MWh"), unsafe_allow_html=True)

    st.markdown(subsection_header_html(f"Discharge (Year {d0.year})"), unsafe_allow_html=True)
    cols = st.columns(4)
    with cols[0]:
        st.markdown(kpi_card_html("Guaranteed DC Discharge Capacity", f"{d0.guarantee_dc_capacity_mwh:,.2f}", "MWh"), unsafe_allow_html=True)
    with cols[1]:
        st.markdown(kpi_card_html("POI Capacity Excl. Aux", f"{d0.poi_capacity_excl_aux_mwh:,.2f}", "MWh", accent="accent-cyan"), unsafe_allow_html=True)
    with cols[2]:
        st.markdown(kpi_card_html("Aux Load Discharge", f"{d0.aux_load_discharge_mw:,.3f}", "MW"), unsafe_allow_html=True)
    with cols[3]:
        st.markdown(kpi_card_html("Aux Energy Discharge", f"{d0.aux_energy_discharge_mwh:,.3f}", "MWh"), unsafe_allow_html=True)
    cols2 = st.columns(4)
    with cols2[0]:
        st.markdown(kpi_card_html("POI Capacity Incl. Aux", f"{d0.poi_capacity_incl_aux_mwh:,.2f}", "MWh", accent="accent-success"), unsafe_allow_html=True)
    with cols2[1]:
        st.markdown(kpi_card_html("Discharge Time", f"{d0.discharge_time_hours:,.2f}", "h"), unsafe_allow_html=True)
    with cols2[2]:
        crate = 1.0 / d0.discharge_time_hours if d0.discharge_time_hours else 0.0
        st.markdown(kpi_card_html("Discharge C-rate", f"{crate:,.3f}", "C"), unsafe_allow_html=True)

    st.markdown(subsection_header_html(f"Charge (Year {c0.year})"), unsafe_allow_html=True)
    cols = st.columns(4)
    with cols[0]:
        st.markdown(kpi_card_html("Charge Guarantee Excl. Aux", f"{c0.charge_guarantee_excl_aux_mwh:,.2f}", "MWh"), unsafe_allow_html=True)
    with cols[1]:
        st.markdown(kpi_card_html("Aux Load Charge", f"{c0.aux_load_charge_mw:,.3f}", "MW"), unsafe_allow_html=True)
    with cols[2]:
        st.markdown(kpi_card_html("Aux Energy Charge", f"{c0.aux_energy_charge_mwh:,.3f}", "MWh"), unsafe_allow_html=True)
    with cols[3]:
        st.markdown(kpi_card_html("Charge Guarantee Incl. Aux", f"{c0.charge_guarantee_incl_aux_mwh:,.2f}", "MWh", accent="accent-success"), unsafe_allow_html=True)
    cols2 = st.columns(4)
    with cols2[0]:
        st.markdown(kpi_card_html("Charge Time", f"{c0.charge_time_hours:,.2f}", "h"), unsafe_allow_html=True)
    with cols2[1]:
        crate_c = 1.0 / c0.charge_time_hours if c0.charge_time_hours else 0.0
        st.markdown(kpi_card_html("Charge C-rate", f"{crate_c:,.3f}", "C"), unsafe_allow_html=True)

    st.markdown(subsection_header_html(f"Efficiency / RTE (Year {r0.year})"), unsafe_allow_html=True)
    cols = st.columns(3)
    with cols[0]:
        st.markdown(kpi_card_html("DC-DC RTE", f"{r0.dc_dc_rte_pct:,.2f}", "%"), unsafe_allow_html=True)
    with cols[1]:
        st.markdown(kpi_card_html("AC RTE Excl. Aux", f"{r0.ac_rte_excl_aux_pct:,.2f}", "%", accent="accent-cyan"), unsafe_allow_html=True)
    with cols[2]:
        st.markdown(kpi_card_html("AC RTE Incl. Aux", f"{r0.ac_rte_incl_aux_pct:,.2f}", "%", accent="accent-success"), unsafe_allow_html=True)

    if len(discharge_results) > 1:
        st.markdown(subsection_header_html("Year-wise Summary"), unsafe_allow_html=True)
        rte_by_year = {r.year: r for r in rte_results}
        charge_by_year = {r.year: r for r in charge_results}
        rows = []
        for d in discharge_results:
            c = charge_by_year.get(d.year)
            r = rte_by_year.get(d.year)
            rows.append({
                "Year": d.year,
                "Installed DC (MWh)": round(d.installed_dc_capacity_mwh, 2),
                "Guaranteed DC Discharge (MWh)": round(d.guarantee_dc_capacity_mwh, 2),
                "POI Excl. Aux (MWh)": round(d.poi_capacity_excl_aux_mwh, 2),
                "POI Incl. Aux (MWh)": round(d.poi_capacity_incl_aux_mwh, 2),
                "Charge Guarantee Excl. Aux (MWh)": round(c.charge_guarantee_excl_aux_mwh, 2) if c else None,
                "Charge Guarantee Incl. Aux (MWh)": round(c.charge_guarantee_incl_aux_mwh, 2) if c else None,
                "AC RTE Excl. Aux (%)": round(r.ac_rte_excl_aux_pct, 2) if r else None,
                "AC RTE Incl. Aux (%)": round(r.ac_rte_incl_aux_pct, 2) if r else None,
            })
        summary_df = pd.DataFrame(rows)
        st.dataframe(summary_df, use_container_width=True, hide_index=True)

        fig = go.Figure()
        years = [d.year for d in discharge_results]
        fig.add_trace(go.Bar(x=years, y=[d.poi_capacity_incl_aux_mwh for d in discharge_results], name="Discharge POI (Incl. Aux)"))
        fig.add_trace(go.Bar(x=years, y=[charge_by_year[y].charge_guarantee_incl_aux_mwh for y in years if y in charge_by_year], name="Charge Guarantee (Incl. Aux)"))
        fig.update_layout(
            barmode="group", title="Discharge vs Charge Capacity by Year",
            xaxis_title="Year", yaxis_title="Energy (MWh)", height=400,
            margin=dict(l=10, r=10, t=40, b=10), legend=dict(orientation="h", y=-0.2),
            template="plotly_white",
        )
        st.plotly_chart(fig, use_container_width=True)

    st.session_state.summary_ready = True
