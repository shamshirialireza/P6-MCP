"""Relationship (TASKPRED row) entity."""

from __future__ import annotations

from p6_mcp.domain.base import PRED_TYPE, Entity, label_of


class Relationship(Entity):
    """One TASKPRED row: predecessor → successor with type and lag."""

    __slots__ = ()

    @property
    def rel_id(self) -> int:
        return int(self.num("task_pred_id"))

    @property
    def task_id(self) -> int:
        """Successor task id."""
        return int(self.num("task_id"))

    @property
    def pred_task_id(self) -> int:
        return int(self.num("pred_task_id"))

    @property
    def proj_id(self) -> int | None:
        v = self.f("proj_id")
        return int(v) if v is not None else None

    @property
    def pred_proj_id(self) -> int | None:
        v = self.f("pred_proj_id")
        return int(v) if v is not None else None

    @property
    def pred_type(self) -> str:
        return self.raw("pred_type") or "PR_FS"

    @property
    def type_label(self) -> str | None:
        return label_of(PRED_TYPE, self.pred_type)

    @property
    def short_type(self) -> str:
        """FS / SS / FF / SF."""
        return self.pred_type.removeprefix("PR_")

    @property
    def lag_hours(self) -> float:
        return self.num("lag_hr_cnt")

    @property
    def is_lead(self) -> bool:
        return self.lag_hours < 0

    @property
    def is_lag(self) -> bool:
        return self.lag_hours > 0

    @property
    def crosses_projects(self) -> bool:
        return (
            self.pred_proj_id is not None
            and self.proj_id is not None
            and self.pred_proj_id != self.proj_id
        )
