"""Formatting and small shared helpers used across the UI and export layers."""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from typing import Any


def fmt_energy(value: float, decimals: int = 2) -> str:
    """Format an energy value with MWh unit."""
    if value is None:
        return "-"
    return f"{value:,.{decimals}f} MWh"


def fmt_power(value: float, decimals: int = 3) -> str:
    """Format a power value with MW unit."""
    if value is None:
        return "-"
    return f"{value:,.{decimals}f} MW"


def fmt_hours(value: float, decimals: int = 2) -> str:
    if value is None:
        return "-"
    return f"{value:,.{decimals}f} h"


def fmt_pct(value: float, decimals: int = 2) -> str:
    if value is None:
        return "-"
    return f"{value:,.{decimals}f}%"


def fmt_crate(value: float, decimals: int = 3) -> str:
    if value is None:
        return "-"
    return f"{value:,.{decimals}f}C"


def dataclass_to_dict(obj: Any) -> Any:
    """Recursively convert dataclasses (including Enums) into JSON-serializable dicts."""
    if is_dataclass(obj):
        result = {}
        for k, v in asdict(obj).items():
            result[k] = dataclass_to_dict(v)
        return result
    if isinstance(obj, list):
        return [dataclass_to_dict(v) for v in obj]
    if hasattr(obj, "value"):  # Enum
        return obj.value
    return obj


def project_case_to_json(case) -> str:
    return json.dumps(dataclass_to_dict(case), indent=2)
