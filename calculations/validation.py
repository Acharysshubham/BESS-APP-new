"""
Engineering input validation for the BESS Sizing calculation engine.

All validators raise ValidationError with a clear, human-readable engineering
message. The UI layer catches these and displays them next to the offending
field; the calculation engine itself never silently accepts an invalid value.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


class ValidationError(Exception):
    """Raised when an input fails engineering validation."""

    def __init__(self, field_name: str, message: str):
        self.field_name = field_name
        self.message = message
        super().__init__(f"{field_name}: {message}")


@dataclass
class ValidationIssue:
    """A single validation problem, used to collect (not just raise-and-stop) issues in the UI."""
    field_name: str
    message: str
    severity: str = "error"  # "error" or "warning"


def require_positive(value: float, field_name: str) -> None:
    if value is None or value <= 0:
        raise ValidationError(field_name, "must be greater than zero.")


def require_positive_int(value: int, field_name: str) -> None:
    if value is None or not float(value).is_integer() or value <= 0:
        raise ValidationError(field_name, "must be a positive integer.")


def require_percentage(value: float, field_name: str, allow_zero: bool = False) -> None:
    """Validate a percentage value is within (0, 100] or [0, 100] if allow_zero."""
    if value is None:
        raise ValidationError(field_name, "is required.")
    lower_ok = value >= 0 if allow_zero else value > 0
    if not lower_ok or value > 100:
        bound = "[0, 100]%" if allow_zero else "greater than 0% and up to 100%"
        raise ValidationError(field_name, f"must be {bound}.")


def require_non_negative(value: float, field_name: str) -> None:
    if value is None or value < 0:
        raise ValidationError(field_name, "must not be negative.")


def validate_c_rate(value: float, field_name: str = "C-rate") -> None:
    require_positive(value, field_name)


def validate_time_hours(value: float, field_name: str = "Time") -> None:
    require_positive(value, field_name)


def collect_project_inputs_issues(container_capacity_mwh, num_containers,
                                   aux_disch_mw, aux_charge_mw) -> List[ValidationIssue]:
    issues: List[ValidationIssue] = []
    if container_capacity_mwh is None or container_capacity_mwh <= 0:
        issues.append(ValidationIssue("Container Capacity", "must be greater than zero (MWh)."))
    if num_containers is None or num_containers <= 0 or not float(num_containers).is_integer():
        issues.append(ValidationIssue("Number of Containers", "must be a positive integer."))
    if aux_disch_mw is None or aux_disch_mw < 0:
        issues.append(ValidationIssue("Aux Consumption (Discharge)", "must not be negative (MW)."))
    if aux_charge_mw is None or aux_charge_mw < 0:
        issues.append(ValidationIssue("Aux Consumption (Charge)", "must not be negative (MW)."))
    return issues


def collect_percentage_issues(named_values, allow_zero: bool = False) -> List[ValidationIssue]:
    """named_values: list of (field_name, value) tuples."""
    issues: List[ValidationIssue] = []
    for name, value in named_values:
        try:
            require_percentage(value, name, allow_zero=allow_zero)
        except ValidationError as e:
            issues.append(ValidationIssue(name, e.message))
    return issues


def validate_rte_result(rte_pct: float, field_name: str) -> Optional[ValidationIssue]:
    """RTE should be a physically meaningful value. Flag (warning) instead of silently accepting."""
    if rte_pct is None:
        return ValidationIssue(field_name, "could not be computed.", severity="error")
    if rte_pct <= 0:
        return ValidationIssue(field_name, "is zero or negative - check inputs.", severity="error")
    if rte_pct > 100:
        return ValidationIssue(
            field_name,
            f"is {rte_pct:.2f}%, which exceeds 100% and is not physically meaningful for RTE. "
            "Review DOD, efficiency, and RTE inputs.",
            severity="warning",
        )
    if rte_pct < 50:
        return ValidationIssue(
            field_name,
            f"is unusually low ({rte_pct:.2f}%). Verify efficiency chain and aux load inputs.",
            severity="warning",
        )
    return None
