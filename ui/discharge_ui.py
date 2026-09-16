"""UI for Section 5-10: Discharging (DC Side, AC Side, Results)."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from calculations.models import ACEfficiencyChain, DischargeYearInput, DischargeSettings, TimeMode
from calculations import discharge as D
from calculations.validation import collect_percentage_issues
from ui.styles import section_header_html, subsection_header_html, formula_box_html, calc_badge_html
from utils.helpers import fmt_energy, fmt_power, fmt_hours, fmt_pct, fmt_crate


def _years_df_to_inputs(df: pd.DataFrame) -> list:
    year_inputs = []
    for _, row in df.iterrows():
        year_inputs.append(DischargeYearInput(
            year=int(row["Year"]),
            enclosures=int(row["Enclosures"]),
            availability_pct=float(row["Availability (%)"]),
            dc_discharge_efficiency_pct=float(row["DC Discharge Eff. (%)"]),
            soh_pct=float(row["SOH (%)"]),
            calendar_degradation_pct=float(row["Calendar Degradation (%)"]),
            dod_pct=float(row["DOD (%)"]),
        ))
    return year_inputs


def _inputs_to_years_df(year_inputs: list) -> pd.DataFrame:
    return pd.DataFrame([{
        "Year": yi.year,
        "Enclosures": yi.enclosures,
        "Availability (%)": yi.availability_pct,
        "DC Discharge Eff. (%)": yi.dc_discharge_efficiency_pct,
        "SOH (%)": yi.soh_pct,
        "Calendar Degradation (%)": yi.calendar_degradation_pct,
        "DOD (%)": yi.dod_pct,
    } for yi in year_inputs])


def render_discharge_dc_side():
    st.markdown(section_header_html("Discharging \u2014 DC Side"), unsafe_allow_html=True)
    st.caption(
        "Edit the table below to add years, remove years, or change year-specific parameters. "
        "All dependent results recalculate immediately."
    )

    df = _inputs_to_years_df(st.session_state.discharge_years)

    edited = st.data_editor(
        df,
        num_rows="dynamic",
        use_container_width=True,
        key="discharge_years_editor",
        column_config={
            "Year": st.column_config.NumberColumn("Year", min_value=1, step=1, format="%d"),
            "Enclosures": st.column_config.NumberColumn("Enclosures", min_value=1, step=1, format="%d"),
            "Availability (%)": st.column_config.NumberColumn("Availability (%)", min_value=0.0, max_value=100.0, step=0.1),
            "DC Discharge Eff. (%)": st.column_config.NumberColumn("DC Discharge Eff. (%)", min_value=0.0, max_value=100.0, step=0.1),
            "SOH (%)": st.column_config.NumberColumn("SOH (%)", min_value=0.0, max_value=100.0, step=0.1),
            "Calendar Degradation (%)": st.column_config.NumberColumn("Calendar Degradation (%)", min_value=0.0, max_value=100.0, step=0.1),
            "DOD (%)": st.column_config.NumberColumn("DOD (%)", min_value=0.0, max_value=100.0, step=0.1),
        },
    )

    if edited.empty:
        st.warning("At least one year is required. Add a row to continue.")
        return

    year_inputs = _years_df_to_inputs(edited)
    st.session_state.discharge_years = year_inputs

    # Validation
    all_issues = []
    for yi in year_inputs:
        all_issues += collect_percentage_issues([
            (f"Year {yi.year} - Availability", yi.availability_pct),
            (f"Year {yi.year} - DC Discharge Efficiency", yi.dc_discharge_efficiency_pct),
            (f"Year {yi.year} - SOH", yi.soh_pct),
            (f"Year {yi.year} - Calendar Degradation", yi.calendar_degradation_pct),
            (f"Year {yi.year} - DOD", yi.dod_pct),
        ])
        if yi.enclosures <= 0:
            all_issues.append(type("I", (), {"field_name": f"Year {yi.year} - Enclosures",
                                               "message": "must be a positive integer."})())
    for issue in all_issues:
        st.error(f"**{issue.field_name}** {issue.message}")

    with st.expander("Calculation trace \u2014 DC Side (per year)", expanded=False):
        proj = st.session_state.project_inputs
        for yi in year_inputs:
            installed = D.installed_dc_capacity_mwh(proj.container_capacity_mwh, yi.enclosures)
            guarantee = D.guarantee_discharge_capacity_dc_mwh(
                installed, yi.availability_pct, yi.dc_discharge_efficiency_pct,
                yi.soh_pct, yi.calendar_degradation_pct, yi.dod_pct,
            )
            st.markdown(f"**Year {yi.year}**")
            st.markdown(formula_box_html(
                f"Installed DC Capacity = {proj.container_capacity_mwh:.3f} MWh x {yi.enclosures}\n"
                f"                        = {installed:,.2f} MWh\n\n"
                f"Guaranteed DC Discharge Capacity\n"
                f"  = {installed:,.2f} x {yi.availability_pct/100:.4f} x {yi.dc_discharge_efficiency_pct/100:.4f} "
                f"x {yi.soh_pct/100:.4f} x {yi.calendar_degradation_pct/100:.4f} x {yi.dod_pct/100:.4f}\n"
                f"  = {guarantee:,.3f} MWh"
            ), unsafe_allow_html=True)


def render_discharge_ac_side():
    st.markdown(section_header_html("Discharging \u2014 AC Side"), unsafe_allow_html=True)
    ac: ACEfficiencyChain = st.session_state.discharge_ac

    st.caption("Efficiency chain from DC side through to the Point of Interconnection (POI).")
    cols = st.columns(3)
    fields = [
        ("LV Cable / DC Cable Efficiency (%)", "lv_dc_cable_efficiency_pct"),
        ("PCS Efficiency (%)", "pcs_efficiency_pct"),
        ("PCS to IDT (LV) Cable Efficiency (%)", "pcs_to_idt_cable_efficiency_pct"),
        ("IDT Efficiency (%)", "idt_efficiency_pct"),
        ("DC DB Efficiency (%)", "dc_db_efficiency_pct"),
        ("MV Cable & MV Switchgear Efficiency (%)", "mv_cable_switchgear_efficiency_pct"),
        ("Main Power Transformer Efficiency (%)", "main_transformer_efficiency_pct"),
        ("11kV Cable / Interconnecting Point Eff. (%)", "interconnecting_efficiency_pct"),
        ("Measurement Accuracy (%)", "measurement_accuracy_pct"),
    ]
    for i, (label, attr) in enumerate(fields):
        with cols[i % 3]:
            val = st.number_input(
                label, min_value=0.0, max_value=100.0,
                value=float(getattr(ac, attr)), step=0.1, format="%.2f",
                key=f"disch_ac_{attr}",
            )
            setattr(ac, attr, val)

    st.session_state.discharge_ac = ac

    issues = collect_percentage_issues([(label, getattr(ac, attr)) for label, attr in fields])
    for issue in issues:
        st.error(f"**{issue.field_name}** {issue.message}")

    st.markdown(subsection_header_html("Discharge Duration"), unsafe_allow_html=True)
    settings: DischargeSettings = st.session_state.discharge_settings

    mode_label = st.radio(
        "Discharge duration mode",
        options=["Discharge Time (hours)", "C-rate"],
        index=0 if settings.time_mode == TimeMode.TIME else 1,
        horizontal=True,
        key="discharge_mode_radio",
    )
    settings.time_mode = TimeMode.TIME if mode_label.startswith("Discharge Time") else TimeMode.C_RATE

    c1, c2 = st.columns(2)
    with c1:
        if settings.time_mode == TimeMode.TIME:
            settings.discharge_time_hours = st.number_input(
                "Discharge Time (hours)", min_value=0.01, value=float(settings.discharge_time_hours),
                step=0.25, key="disch_time_input",
            )
        else:
            st.number_input(
                "Discharge Time (hours) \u2014 derived", value=round(1.0 / settings.discharge_c_rate, 4)
                if settings.discharge_c_rate else 0.0,
                disabled=True, key="disch_time_derived",
            )
    with c2:
        if settings.time_mode == TimeMode.C_RATE:
            settings.discharge_c_rate = st.number_input(
                "Discharge C-rate", min_value=0.001, value=float(settings.discharge_c_rate),
                step=0.05, format="%.3f", key="disch_crate_input",
            )
        else:
            derived_crate = 1.0 / settings.discharge_time_hours if settings.discharge_time_hours else 0.0
            st.number_input("Discharge C-rate \u2014 derived", value=round(derived_crate, 4),
                             disabled=True, key="disch_crate_derived")

    st.session_state.discharge_settings = settings

    resolved_time = D.discharge_time_from_settings(settings)
    resolved_crate = D.discharge_c_rate_from_settings(settings)
    st.markdown(formula_box_html(
        f"Active mode: {'C-rate -> Time' if settings.time_mode == TimeMode.C_RATE else 'Time entered directly'}\n"
        f"Discharge Time = {resolved_time:,.3f} h   |   Discharge C-rate = {resolved_crate:,.3f} C"
    ), unsafe_allow_html=True)


def render_discharge_results():
    st.markdown(section_header_html("Discharge Results"), unsafe_allow_html=True)

    proj = st.session_state.project_inputs
    ac = st.session_state.discharge_ac
    settings = st.session_state.discharge_settings
    year_inputs = st.session_state.discharge_years

    if not year_inputs:
        st.warning("Add at least one year in the DC Side tab to see results.")
        return []

    results = D.calculate_all_discharge_years(proj, year_inputs, ac, settings)
    st.session_state.discharge_results = results

    df = pd.DataFrame([{
        "Year": r.year,
        "Installed DC (MWh)": round(r.installed_dc_capacity_mwh, 2),
        "DC Usable Energy (MWh)": round(r.dc_usable_energy_mwh, 2),
        "Guaranteed DC Capacity (MWh)": round(r.guarantee_dc_capacity_mwh, 2),
        "Aux Load (MW)": round(r.aux_load_discharge_mw, 3),
        "Discharge Time (h)": round(r.discharge_time_hours, 2),
        "Aux Energy (MWh)": round(r.aux_energy_discharge_mwh, 3),
        "POI Excl. Aux (MWh)": round(r.poi_capacity_excl_aux_mwh, 2),
        "POI Incl. Aux (MWh)": round(r.poi_capacity_incl_aux_mwh, 2),
    } for r in results])

    st.dataframe(df, use_container_width=True, hide_index=True)

    if len(results) > 1:
        fig = go.Figure()
        years = [r.year for r in results]
        fig.add_trace(go.Scatter(x=years, y=[r.installed_dc_capacity_mwh for r in results],
                                  mode="lines+markers", name="Installed DC Capacity"))
        fig.add_trace(go.Scatter(x=years, y=[r.guarantee_dc_capacity_mwh for r in results],
                                  mode="lines+markers", name="Guaranteed DC Capacity"))
        fig.add_trace(go.Scatter(x=years, y=[r.poi_capacity_excl_aux_mwh for r in results],
                                  mode="lines+markers", name="POI Excl. Aux"))
        fig.add_trace(go.Scatter(x=years, y=[r.poi_capacity_incl_aux_mwh for r in results],
                                  mode="lines+markers", name="POI Incl. Aux"))
        fig.update_layout(
            title="Discharge Capacity vs Year", xaxis_title="Year", yaxis_title="Energy (MWh)",
            height=380, margin=dict(l=10, r=10, t=40, b=10), legend=dict(orientation="h", y=-0.2),
            template="plotly_white",
        )
        st.plotly_chart(fig, use_container_width=True)

    with st.expander("Calculation trace \u2014 POI (per year)", expanded=False):
        ac_product = D.ac_efficiency_product(ac)
        for r in results:
            st.markdown(f"**Year {r.year}**")
            st.markdown(formula_box_html(
                f"AC efficiency product = {ac_product:.5f}\n"
                f"POI Excl. Aux = {r.guarantee_dc_capacity_mwh:,.3f} MWh x {ac_product:.5f} = {r.poi_capacity_excl_aux_mwh:,.3f} MWh\n"
                f"Aux Energy   = {r.aux_load_discharge_mw:.4f} MW x {r.discharge_time_hours:.3f} h = {r.aux_energy_discharge_mwh:,.3f} MWh\n"
                f"POI Incl. Aux = {r.poi_capacity_excl_aux_mwh:,.3f} - {r.aux_energy_discharge_mwh:,.3f} = {r.poi_capacity_incl_aux_mwh:,.3f} MWh"
            ), unsafe_allow_html=True)

    return results
