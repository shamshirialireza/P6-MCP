"""Centralized analysis thresholds with documented DCMA defaults.

Every threshold is a parameter on the calling tool; these are the defaults.
DCMA 14-point defaults follow the DCMA-EA PAM 200.1 guide:

* missing logic ≤ 5% (i.e. ≥95% of incomplete tasks have preds AND succs)
* leads (negative lags) = 0
* lags ≤ 5% of relationships
* FS relationships ≥ 90%
* hard constraints ≤ 5%
* high float: > 44 working days, ≤ 5% of incomplete tasks
* negative float = 0
* high duration: > 44 working days remaining, ≤ 5%
* invalid dates = 0
* resources: every incomplete task with duration has a resource or cost
* missed tasks ≤ 5% of tasks that should have finished
* CPLI ≥ 0.95, BEI ≥ 0.95
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class DcmaThresholds:
    """Tunable DCMA 14-point thresholds (percentages are 0-100)."""

    missing_logic_pct_max: float = 5.0
    leads_max: int = 0
    lags_pct_max: float = 5.0
    fs_pct_min: float = 90.0
    hard_constraints_pct_max: float = 5.0
    high_float_days: float = 44.0
    high_float_pct_max: float = 5.0
    negative_float_max: int = 0
    high_duration_days: float = 44.0
    high_duration_pct_max: float = 5.0
    invalid_dates_max: int = 0
    missed_tasks_pct_max: float = 5.0
    cpli_min: float = 0.95
    bei_min: float = 0.95
    critical_path_test_delay_days: float = 120.0
    # Exemptions (all configurable; DCMA defaults)
    exempt_loe: bool = True
    exempt_wbs_summary: bool = True
    exempt_completed: bool = True
    exempt_milestones_from_duration_checks: bool = True
    exempt_milestones_from_resource_check: bool = True


NEAR_CRITICAL_DAYS_DEFAULT = 5.0
LONG_DURATION_DAYS_DEFAULT = 44.0
HIGH_FLOAT_DAYS_DEFAULT = 44.0
LOOKAHEAD_DAYS_DEFAULT = 28

#: Default weights for the composite health score (must sum to 100).
HEALTH_WEIGHTS_DEFAULT: dict[str, float] = {
    "logic": 20.0,
    "leads_lags": 10.0,
    "constraints": 10.0,
    "float": 15.0,
    "duration": 10.0,
    "invalid_dates": 15.0,
    "resources": 10.0,
    "progress": 10.0,
    "relationship_types": 5.0,
}
