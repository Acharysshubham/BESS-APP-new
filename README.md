# BESS Sizing Calculation Software

A professional, engineering-grade **Battery Energy Storage System (BESS) sizing calculator**
built for EPC / engineering use. It performs DC-side and AC-side discharge and charge
capacity calculations, computes DC-DC and AC round-trip efficiency (RTE), supports
multi-year degradation modeling, and exports a fully formatted, auditable Excel
calculation sheet.

---

## Features

- **Live, reactive calculations** — every dependent value recalculates immediately when
  any input changes; no "Calculate" button required.
- **Separated calculation engine** — `calculations/` has zero Streamlit dependency, so it
  can be reused for Excel export, automated tests, or a future API/web service.
- **Discharging & Charging sections** — DC side, AC side (9-stage efficiency chain), and
  results, each with full calculation traceability (formula + numbers shown).
- **DC-DC and AC RTE** (excluding and including auxiliary power), validated against
  physically meaningful ranges with warnings for unusual results.
- **Multi-year support** — add, remove, or edit year rows in an interactive table; SOH,
  calendar degradation, availability, and DOD can vary by year.
- **Professional Excel export** (OpenPyXL) — 5-sheet workbook (Summary, Initial Inputs,
  Discharging Calculation, Charging Calculation, RTE) with headers, units, percentage/
  number formatting, borders, frozen panes, and auto-fit columns.
- **Interactive Plotly charts** — capacity, degradation and RTE trends vs. year.
- **Save / Load case as JSON** — persist and reopen an engineering case.
- **Input validation** — engineering-sensible ranges (0–100% for efficiencies/SOH/DOD/
  availability, positive C-rate/time, etc.) with clear inline error messages.
- **Premium engineering dashboard UI** — navy/white theme, KPI cards, section headers,
  and clearly differentiated **Input** vs **Calculated** fields.

---

## Folder Structure

```
bess_sizing/
│
├── app.py                      # Streamlit entry point / page routing
├── calculations/                # Pure-Python calculation engine (no UI dependency)
│   ├── __init__.py
│   ├── models.py                 # Dataclasses: ProjectInputs, ACEfficiencyChain, Year inputs/results...
│   ├── discharge.py              # Discharging DC/AC-side formulas (Sections 5-10)
│   ├── charge.py                 # Charging DC/AC-side formulas (Sections 11-18)
│   ├── rte.py                    # DC-DC and AC RTE formulas (Sections 14, 19)
│   └── validation.py             # Engineering input validation
│
├── ui/
│   ├── inputs.py                 # Project / Initial Inputs page
│   ├── discharge_ui.py           # Discharging DC/AC side + results
│   ├── charge_ui.py              # Charging DC/AC side + results + RTE
│   ├── results.py                # Final Results dashboard
│   └── styles.py                 # Custom CSS + KPI card / section header helpers
│
├── export/
│   ├── excel_export.py           # Professional multi-sheet .xlsx export (OpenPyXL)
│   └── report.py                 # Plain-text summary (extensible to PDF/DOCX later)
│
├── utils/
│   └── helpers.py                # Formatting helpers, dataclass <-> JSON conversion
│
├── tests/
│   └── test_calculations.py      # Automated tests for the calculation engine
│
├── requirements.txt
└── README.md
```

---

## Installation

**Python version:** 3.9+

```bash
pip install -r requirements.txt
```

## Running the App

```bash
streamlit run app.py
```

Then open the URL Streamlit prints (typically `http://localhost:8501`).

## Running Tests

```bash
pip install pytest
pytest tests/test_calculations.py -v
```

The test suite covers: installed capacity, DC usable energy, guaranteed DC discharge
capacity, POI discharge capacity, auxiliary load/energy (charge & discharge), charge
capacity, DC-DC RTE, AC RTE, C-rate/time conversion, multi-year calculations, invalid
percentage handling, and zero/negative input rejection.

## Exporting to Excel

Navigate to **Calculation Sheet / Export** in the sidebar and click
**Export to Excel (.xlsx)**. The workbook contains:

| Sheet | Contents |
|---|---|
| Summary | Project inputs, key BESS parameters, final discharge/charge/RTE results |
| Initial Inputs | All initial user inputs and both AC efficiency chains |
| Discharging Calculation | Year-wise DC + AC side detail, aux load/energy, POI results |
| Charging Calculation | Year-wise DC + AC side detail, aux load/energy, guarantee results |
| RTE | DC-DC RTE, AC RTE (excl./incl. aux) per year |

---

## Calculation Methodology

All formulas are implemented exactly as specified in the engineering requirement,
without inventing additional methodology. Percentages are always converted to decimal
factors before multiplication (e.g. 98% → 0.98).

**Discharging (DC side):**
```
Installed DC Capacity = Container Capacity x No. of Enclosures
Guaranteed DC Discharge Capacity = Installed DC Capacity
    x Availability x DC Discharge Efficiency x SOH x Calendar Degradation x DOD
```

**Discharging (AC side / POI):**
```
POI Capacity (Excl. Aux) = Guaranteed DC Discharge Capacity x (product of 9 AC-side efficiencies)
Aux Load Discharge = Initial No. of Containers x Aux Consumption per Container (Discharge)
Aux Energy Discharge = Aux Load Discharge x Discharge Time
POI Capacity (Incl. Aux) = POI Capacity (Excl. Aux) - Aux Energy Discharge
```

**Charging:**
```
DC Usable Energy (Charge) = Container Capacity x Enclosures x DOD
    x DC Charging Efficiency x Calendar Degradation x SOH
Charge Guarantee (Excl. Aux) = DC Usable Energy / (product of 9 AC-side efficiencies) / DC-DC RTE
Aux Load Charge = Initial No. of Containers x Aux Consumption per Container (Charge)
Aux Energy Charge = Aux Load Charge x Charge Time
Charge Guarantee (Incl. Aux) = Charge Guarantee (Excl. Aux) + Aux Energy Charge
```

**RTE:**
```
AC RTE (Excl. Aux) = Discharge Guarantee (Excl. Aux) / Charge Guarantee (Excl. Aux) x 100%
AC RTE (Incl. Aux) = Discharge Guarantee (Incl. Aux) / Charge Guarantee (Incl. Aux) x 100%
```

### Engineering ambiguity resolution (documented, not silently changed)

The specification's Section 15 formula for Charge Guarantee Capacity uses the generic
term "Discharge Efficiency" inside a charging-side formula, while Section 13 explicitly
instructs that charging efficiency must be used where the charging calculation requires
it. This implementation uses **DC Charging Efficiency** in the charging-side formulas
(per the explicit Section 13 instruction) and uses the **full 9-stage AC efficiency
chain** as the divisor (per Section 15's "do not hide or omit efficiency stages"
instruction), rather than the 3 generic terms shown in Section 15's shorthand notation.
This mapping is isolated and documented in `calculations/charge.py`
(`CHARGE_EFFICIENCY_MAPPING_NOTE`) and surfaced in the app's Charging → AC Side tab, so
it can be revisited if the intended methodology differs.

---

## Future Expansion

The architecture is intentionally modular so additional BESS sizing modules can be
added without rewriting the existing application:

- Add a new file under `calculations/` (e.g. `pcs_sizing.py`, `transformer_sizing.py`)
  with pure functions/dataclasses, following the pattern in `discharge.py` / `charge.py`.
- Add a corresponding `ui/*_ui.py` module and register it as a new page in `app.py`'s
  sidebar navigation.
- Extend `export/excel_export.py` with a new sheet-builder function, or add a new file
  under `export/` (e.g. `pdf_report.py`) for a different output format.
- Because the calculation engine has no Streamlit dependency, the same modules can be
  wrapped in a REST API (FastAPI/Flask) for future web deployment without modification.

Potential future modules include: BESS block sizing, PCS sizing, transformer sizing,
C-rate sizing, DC/AC ratio, degradation modeling, cycle calculations, RTE at different
measurement points, POI sizing, grid connection calculations, cable sizing, auxiliary
power sizing, battery container selection, battery augmentation, 15/20-year degradation
analysis, tender-specific sizing requirements, multiple BESS blocks, cost estimation,
and sensitivity analysis.
