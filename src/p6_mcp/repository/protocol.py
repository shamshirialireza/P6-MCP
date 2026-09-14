"""Repository protocols for XER and P6 EPPM backends."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Protocol, runtime_checkable

from p6_mcp.domain.activity import Activity
from p6_mcp.domain.baseline import BaselineProject
from p6_mcp.domain.calendar import Calendar
from p6_mcp.domain.expense import Expense
from p6_mcp.domain.notebook import Notebook
from p6_mcp.domain.project import Project
from p6_mcp.domain.resource import Resource
from p6_mcp.domain.role import Role
from p6_mcp.domain.step import Step
from p6_mcp.domain.udf import UdfType, UdfValue
from p6_mcp.domain.wbs import Wbs


@runtime_checkable
class ScheduleRepository(Protocol):
    """Read-only schedule repository protocol."""

    @abstractmethod
    def load(self, project_ref: str | int) -> dict[str, Any]:
        """Load a project and return the schedule aggregate."""
        ...

    @abstractmethod
    def load_scope(
        self,
        project_ref: str | int,
        load_activities: bool = True,
        load_relationships: bool = True,
        load_resources: bool = True,
        load_roles: bool = True,
        load_calendars: bool = True,
        load_wbs: bool = True,
        load_expenses: bool = True,
        load_uds: bool = True,
        load_steps: bool = True,
        load_notebooks: bool = True,
        load_baselines: bool = True,
    ) -> dict[str, Any]:
        """Load partial scope for analytics that don't need everything."""
        ...

    @abstractmethod
    def get_projects(self) -> list[Project]:
        """Get all projects/baselines in the loaded data."""
        ...

    @abstractmethod
    def get_project(self, project_id: int) -> Project:
        """Get a specific project by ID."""
        ...

    @abstractmethod
    def get_activities(self, project_id: int) -> list[Activity]:
        """Get all activities for a project."""
        ...

    @abstractmethod
    def get_activity(self, activity_id: int) -> Activity:
        """Get a specific activity by ID."""
        ...

    @abstractmethod
    def get_relationships(self, project_id: int) -> list[dict[str, Any]]:
        """Get all relationships (TASKPRED) for a project."""
        ...

    @abstractmethod
    def get_resources(self, project_id: int) -> list[Resource]:
        """Get all resources for a project."""
        ...

    @abstractmethod
    def get_resource(self, resource_id: int) -> Resource:
        """Get a specific resource by ID."""
        ...

    @abstractmethod
    def get_roles(self, project_id: int) -> list[Role]:
        """Get all roles for a project."""
        ...

    @abstractmethod
    def get_role(self, role_id: int) -> Role:
        """Get a specific role by ID."""
        ...

    @abstractmethod
    def get_wbs_nodes(self, project_id: int) -> list[Wbs]:
        """Get all WBS nodes for a project."""
        ...

    @abstractmethod
    def get_wbs_node(self, wbs_id: int) -> Wbs:
        """Get a specific WBS node by ID."""
        ...

    @abstractmethod
    def get_calendars(self, project_id: int) -> list[Calendar]:
        """Get all calendars referenced by a project."""
        ...

    @abstractmethod
    def get_calendar(self, calendar_id: int) -> Calendar:
        """Get a specific calendar by ID."""
        ...

    @abstractmethod
    def get_expenses(self, project_id: int) -> list[Expense]:
        """Get all expenses for a project."""
        ...

    @abstractmethod
    def get_expense(self, expense_id: int) -> Expense:
        """Get a specific expense by ID."""
        ...

    @abstractmethod
    def get_udf_types(self) -> list[UdfType]:
        """Get all UDF types."""
        ...

    @abstractmethod
    def get_udf_values(self, udf_type_id: int) -> list[UdfValue]:
        """Get all UDF values for a UDF type."""
        ...

    @abstractmethod
    def get_steps(self, project_id: int) -> list[Step]:
        """Get all steps for a project."""
        ...

    @abstractmethod
    def get_step(self, step_id: int) -> Step:
        """Get a specific step by ID."""
        ...

    @abstractmethod
    def get_notebooks(self, project_id: int) -> list[Notebook]:
        """Get all notebooks for a project."""
        ...

    @abstractmethod
    def get_notebook(self, notebook_id: int) -> Notebook:
        """Get a specific notebook by ID."""
        ...

    @abstractmethod
    def get_baselines(self) -> list[BaselineProject]:
        """Get all baseline projects."""
        ...

    @abstractmethod
    def get_baseline(self, baseline_id: int) -> BaselineProject:
        """Get a specific baseline by ID."""
        ...


@runtime_checkable
class MutableScheduleRepository(ScheduleRepository, Protocol):
    """Mutable schedule repository protocol with safety gates."""

    @abstractmethod
    def snapshot(self) -> str:
        """Take a snapshot and return the snapshot ID."""
        ...

    @abstractmethod
    def run_job(self, job_type: str, project_id: int, **kwargs) -> str:
        """Run a P6 job and return the job ID."""
        ...

    @abstractmethod
    def get_job_status(self, job_id: str) -> dict[str, Any]:
        """Get the status of a job."""
        ...

    @abstractmethod
    def get_job_log(self, job_id: str, lines: int = 100) -> list[str]:
        """Get the log output from a job."""
        ...

    @abstractmethod
    def cancel_job(self, job_id: str) -> bool:
        """Cancel a running job."""
        ...
from enum import Enum

class QueryMode(Enum):
    AUTODETECT = "autodetect"
    FAST = "fast"
    COMPLETE = "complete"
