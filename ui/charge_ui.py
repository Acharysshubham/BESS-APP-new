"""UI for Section 11-19: Charging (DC Side, AC Side, Results) and RTE."""

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from calculations.models import ACEfficiencyChain, ChargeYearInput, ChargeSettings, TimeMode
from calculations import charge as C
from calculations import rte as R
from calculations.charge import CHARGE_EFFICIENCY_MAPPING_NOTE
from calculations.validation import collect_percentage_issues, require_percentage, ValidationError
from ui.styles import section_header_html, subsection_header_html, formula_box_html
from utils.helpers import fmt_energy, fmt_power, fmt_hours, fmt_pct


def _years_df_to_inputs(df: pd.DataFrame) -> list:
    year_inputs = []
    for _, row in df.iterrows():
        year_inputs.append(ChargeYearInput(
            year=int(row["Year"]),
            enclosures=int(row["Enclosures"]),
            availability_pct=float(row["Availability (%)"]),
            dc_charge_efficiency_pct=float(row["DC Charge Eff. (%)"]),
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
        "DC Charge Eff. (%)": yi.dc_charge_efficiency_pct,
        "SOH (%)": yi.soh_pct,
        "Calendar Degradation (%)": yi.calendar_degradation_pct,
        "DOD (%)": yi.dod_pct,
    } for yi in year_inputs])


def render_charge_dc_side():
    st.markdown(section_header_html("Charging \u2014 DC Side"), unsafe_allow_html=True)
    st.info(
        "\u2139\ufe0f Engineering note: charging-side calculations use **DC Charging Efficiency** "
        "(not discharge efficiency), per the specification's Section 13 instruction. See tooltip "
        "in the AC Side tab for full mapping details.",
        icon="\u2139\ufe0f",
    )
    st.caption(
        "Edit the table below to add years, remove years, or change year-specific parameters. "
        "Enclosure count typically mirrors the Discharging table but can be set independently."
    )

    df = _inputs_to_years_df(st.session_state.charge_years)

    edited = st.data_editor(
        df,
        num_rows="dynamic",
        use_container_width=True,
        key="charge_years_editor",
        column_config={
            "Year": st.column_config.NumberColumn("Year", min_value=1, step=1, format="%d"),
            "Enclosures": st.column_config.NumberColumn("Enclosures", min_value=1, step=1, format="%d"),
            "Availability (%)": st.column_config.NumberColumn("Availability (%)", min_value=0.0, max_value=100.0, step=0.1),
            "DC Charge Eff. (%)": st.column_config.NumberColumn("DC Charge Eff. (%)", min_value=0.0, max_value=100.0, step=0.1),
            "SOH (%)": st.column_config.NumberColumn("SOH (%)", min_value=0.0, max_value=100.0, step=0.1),
            "Calendar Degradation (%)": st.column_config.NumberColumn("Calendar Degradation (%)", min_value=0.0, max_value=100.0, step=0.1),
            "DOD (%)": st.column_config.NumberColumn("DOD (%)", min_value=0.0, max_value=100.0, step=0.1),
        },
    )

    if edited.empty:
        st.warning("At least one year is required. Add a row to continue.")
        return

    year_inputs = _years_df_to_inputs(edited)
    st.session_state.charge_years = year_inputs

    all_issues = []
    for yi in year_inputs:
        all_issues += collect_percentage_issues([
            (f"Year {yi.year} - Availability", yi.availability_pct),
            (f"Year {yi.year} - DC Charge Efficiency", yi.dc_charge_efficiency_pct),
            (f"Year {yi.year} - SOH", yi.soh_pct),
            (f"Year {yi.year} - Calendar Degradation", yi.calendar_degradation_pct),
            (f"Year {yi.year} - DOD", yi.dod_pct),
        ])
    for issue in all_issues:
        st.error(f"**{issue.field_name}** {issue.message}")


def render_charge_ac_side():
    st.markdown(section_header_html("Charging \u2014 AC Side"), unsafe_allow_html=True)
    ac: ACEfficiencyChain = st.session_state.charge_ac

    st.caption("Efficiency chain from POI through to the DC side (same detailed stages as discharging).")
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
                key=f"charge_ac_{attr}",
            )
            setattr(ac, attr, val)

    st.session_state.charge_ac = ac

    issues = collect_percentage_issues([(label, getattr(ac, attr)) for label, attr in fields])
    for issue in issues:
        st.error(f"**{issue.field_name}** {issue.message}")

    with st.expander("Engineering mapping note (Section 13 / 15 ambiguity resolution)"):
        st.write(CHARGE_EFFICIENCY_MAPPING_NOTE)

    st.markdown(subsection_header_html("DC-DC RTE"), unsafe_allow_html=True)
    settings: ChargeSettings = st.session_state.charge_settings
    settings.dc_dc_rte_pct = st.number_input(
        "DC-DC RTE (%)", min_value=0.01, max_value=100.0, value=float(settings.dc_dc_rte_pct),
        step=0.1, help="Round-trip efficiency measured strictly at the DC-DC (battery) level.",
        key="dc_dc_rte_input",
    )
    try:
        require_percentage(settings.dc_dc_rte_pct, "DC-DC RTE")
    except ValidationError as e:
        st.error(f"**{e.field_name}** {e.message}")

    st.markdown(subsection_header_html("Charge Duration"), unsafe_allow_html=True)
    mode_label = st.radio(
        "Charge duration mode",
        options=["Charge Time (hours)", "C-rate"],
        index=0 if settings.time_mode == TimeMode.TIME else 1,
        horizontal=True,
        key="charge_mode_radio",
    )
    settings.time_mode = TimeMode.TIME if mode_label.startswith("Charge Time") else TimeMode.C_RATE

    c1, c2 = st.columns(2)
    with c1:
        if settings.time_mode == TimeMode.TIME:
            settings.charge_time_hours = st.number_input(
                "Charge Time (hours)", min_value=0.01, value=float(settings.charge_time_hours),
                step=0.25, key="charge_time_input",
            )
        else:
            st.number_input(
                "Charge Time (hours) \u2014 derived",
                value=round(1.0 / settings.charge_c_rate, 4) if settings.charge_c_rate else 0.0,
                disabled=True, key="charge_time_derived",
            )
    with c2:
        if settings.time_mode == TimeMode.C_RATE:
            settings.charge_c_rate = st.number_input(
                "Charge C-rate", min_value=0.001, value=float(settings.charge_c_rate),
                step=0.05, format="%.3f", key="charge_crate_input",
            )
        else:
            derived_crate = 1.0 / settings.charge_time_hours if settings.charge_time_hours else 0.0
            st.number_input("Charge C-rate \u2014 derived", value=round(derived_crate, 4),
                             disabled=True, key="charge_crate_derived")

    st.session_state.charge_settings = settings

    resolved_time = C.charge_time_from_settings(settings)
    resolved_crate = C.charge_c_rate_from_settings(settings)
    st.markdown(formula_box_html(
        f"Active mode: {'C-rate -> Time' if settings.time_mode == TimeMode.C_RATE else 'Time entered directly'}\n"
        f"Charge Time = {resolved_time:,.3f} h   |   Charge C-rate = {resolved_crate:,.3f} C"
    ), unsafe_allow_html=True)


def render_charge_results():
    st.markdown(section_header_html("Charge Results"), unsafe_allow_html=True)

    proj = st.session_state.project_inputs
    ac = st.session_state.charge_ac
    settings = st.session_state.charge_settings
    year_inputs = st.session_state.charge_years

    if not year_inputs:
        st.warning("Add at least one year in the DC Side tab to see results.")
        return []

    results = C.calculate_all_charge_years(proj, year_inputs, ac, settings)
    st.session_state.charge_results = results

    df = pd.DataFrame([{
        "Year": r.year,
        "Installed DC (MWh)": round(r.installed_dc_capacity_mwh, 2),
        "DC Usable Energy (MWh)": round(r.dc_usable_energy_mwh, 2),
        "Aux Load (MW)": round(r.aux_load_charge_mw, 3),
        "Charge Time (h)": round(r.charge_time_hours, 2),
        "Aux Energy (MWh)": round(r.aux_energy_charge_mwh, 3),
        "Guarantee Excl. Aux (MWh)": round(r.charge_guarantee_excl_aux_mwh, 2),
        "Guarantee Incl. Aux (MWh)": round(r.charge_guarantee_incl_aux_mwh, 2),
    } for r in results])

    st.dataframe(df, use_container_width=True, hide_index=True)

    if len(results) > 1:
        fig = go.Figure()
        years = [r.year for r in results]
        fig.add_trace(go.Scatter(x=years, y=[r.charge_guarantee_excl_aux_mwh for r in results],
                                  mode="lines+markers", name="Charge Guarantee Excl. Aux"))
        fig.add_trace(go.Scatter(x=years, y=[r.charge_guarantee_incl_aux_mwh for r in results],
                                  mode="lines+markers", name="Charge Guarantee Incl. Aux"))
        fig.update_layout(
            title="Charge Guarantee Capacity vs Year", xaxis_title="Year", yaxis_title="Energy (MWh)",
            height=380, margin=dict(l=10, r=10, t=40, b=10), legend=dict(orientation="h", y=-0.2),
            template="plotly_white",
        )
        st.plotly_chart(fig, use_container_width=True)

    with st.expander("Calculation trace \u2014 Charge Guarantee Capacity (per year)", expanded=False):
        ac_product = C.ac_efficiency_product(ac)
        for r in results:
            st.markdown(f"**Year {r.year}**")
            st.markdown(formula_box_html(
                f"AC efficiency product = {ac_product:.5f}   |   DC-DC RTE = {settings.dc_dc_rte_pct:.2f}%\n"
                f"Charge Guarantee Excl. Aux = {r.dc_usable_energy_mwh:,.3f} / {ac_product:.5f} / "
                f"{settings.dc_dc_rte_pct/100:.4f} = {r.charge_guarantee_excl_aux_mwh:,.3f} MWh\n"
                f"Aux Energy = {r.aux_load_charge_mw:.4f} MW x {r.charge_time_hours:.3f} h = {r.aux_energy_charge_mwh:,.3f} MWh\n"
                f"Charge Guarantee Incl. Aux = {r.charge_guarantee_excl_aux_mwh:,.3f} + {r.aux_energy_charge_mwh:,.3f} "
                f"= {r.charge_guarantee_incl_aux_mwh:,.3f} MWh"
            ), unsafe_allow_html=True)

    return results


def render_rte_section():
    st.markdown(section_header_html("Round-Trip Efficiency (RTE)"), unsafe_allow_html=True)

    discharge_results = st.session_state.get("discharge_results", [])
    charge_results = st.session_state.get("charge_results", [])
    settings = st.session_state.charge_settings

    if not discharge_results or not charge_results:
        st.warning("Complete the Discharging and Charging sections first to see RTE results.")
        return []

    rte_results = R.calculate_all_rte_years(discharge_results, charge_results, settings.dc_dc_rte_pct)
    st.session_state.rte_results = rte_results

    if not rte_results:
        st.warning("No matching years found between Discharging and Charging tables. "
                    "Ensure both tables use the same Year values.")
        return []

    df = pd.DataFrame([{
        "Year": r.year,
        "DC-DC RTE (%)": round(r.dc_dc_rte_pct, 2),
        "AC RTE Excl. Aux (%)": round(r.ac_rte_excl_aux_pct, 2),
        "AC RTE Incl. Aux (%)": round(r.ac_rte_incl_aux_pct, 2),
    } for r in rte_results])
    st.dataframe(df, use_container_width=True, hide_index=True)

    from calculations.validation import validate_rte_result
    for r in rte_results:
        for label, val in [
            (f"Year {r.year} AC RTE (Excl. Aux)", r.ac_rte_excl_aux_pct),
            (f"Year {r.year} AC RTE (Incl. Aux)", r.ac_rte_incl_aux_pct),
        ]:
            issue = validate_rte_result(val, label)
            if issue:
                if issue.severity == "warning":
                    st.warning(f"**{issue.field_name}** {issue.message}")
                else:
                    st.error(f"**{issue.field_name}** {issue.message}")

    if len(rte_results) > 1:
        fig = go.Figure()
        years = [r.year for r in rte_results]
        fig.add_trace(go.Scatter(x=years, y=[r.ac_rte_excl_aux_pct for r in rte_results],
                                  mode="lines+markers", name="AC RTE Excl. Aux"))
        fig.add_trace(go.Scatter(x=years, y=[r.ac_rte_incl_aux_pct for r in rte_results],
                                  mode="lines+markers", name="AC RTE Incl. Aux"))
        fig.add_trace(go.Scatter(x=years, y=[r.dc_dc_rte_pct for r in rte_results],
                                  mode="lines", name="DC-DC RTE", line=dict(dash="dot")))
        fig.update_layout(
            title="RTE vs Year", xaxis_title="Year", yaxis_title="RTE (%)",
            height=380, margin=dict(l=10, r=10, t=40, b=10), legend=dict(orientation="h", y=-0.2),
            template="plotly_white",
        )
        st.plotly_chart(fig, use_container_width=True)

    with st.expander("Calculation trace \u2014 RTE (per year)", expanded=False):
        for r in rte_results:
            d = next(d for d in discharge_results if d.year == r.year)
            c = next(c for c in charge_results if c.year == r.year)
            st.markdown(f"**Year {r.year}**")
            st.markdown(formula_box_html(
                f"AC RTE Excl. Aux = {d.poi_capacity_excl_aux_mwh:,.3f} / {c.charge_guarantee_excl_aux_mwh:,.3f} "
                f"x 100 = {r.ac_rte_excl_aux_pct:,.2f}%\n"
                f"AC RTE Incl. Aux = {d.poi_capacity_incl_aux_mwh:,.3f} / {c.charge_guarantee_incl_aux_mwh:,.3f} "
                f"x 100 = {r.ac_rte_incl_aux_pct:,.2f}%"
            ), unsafe_allow_html=True)

    return rte_results
