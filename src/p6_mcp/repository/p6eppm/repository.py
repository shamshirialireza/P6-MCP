"""P6 EPPM repository implementation."""

from __future__ import annotations

import base64
import json
from datetime import datetime, timedelta
from typing import Any

import httpx

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
from p6_mcp.exceptions import P6McpError
from p6_mcp.repository.protocol import MutableScheduleRepository, ScheduleRepository


class P6EppmRepository(MutableScheduleRepository):
    """P6 EPPM repository that implements the ScheduleRepository protocol."""

    def __init__(
        self,
        base_url: str,
        database: str,
        auth_mode: str = "session",
        username: str | None = None,
        password: str | None = None,
        verify_tls: bool = True,
        timeout: int = 30,
    ):
        self.base_url = base_url.rstrip("/")
        self.database = database
        self.auth_mode = auth_mode.lower()
        self.username = username
        self.password = password
        self.verify_tls = verify_tls
        self.timeout = timeout
        self._client: httpx.Client | None = None
        self._session_token: str | None = None
        self._oauth_token: str | None = None
        self._oauth_expires: datetime | None = None
        self._field_cache: dict[str, list[dict[str, Any]]] = {}
        self._schedule_cache: dict[str, Any] = {}
        self._last_update_date: dict[int, datetime] = {}

    def _get_client(self) -> httpx.Client:
        """Get or create the HTTP client."""
        if self._client is None:
            self._client = httpx.Client(
                verify=self.verify_tls,
                timeout=self.timeout,
                follow_redirects=True,
            )
        return self._client

    def _ensure_authenticated(self) -> None:
        """Ensure we're authenticated with the P6 EPPM server."""
        if self.auth_mode == "session":
            self._ensure_session_auth()
        elif self.auth_mode == "oauth":
            self._ensure_oauth_auth()
        else:
            raise P6McpError(f"Unsupported auth mode: {self.auth_mode}")

    def _ensure_session_auth(self) -> None:
        """Ensure session authentication is valid."""
        # For now, we'll authenticate on each request - in production we'd cache
        # the session token and refresh when needed
        pass

    def _ensure_oauth_auth(self) -> None:
        """Ensure OAuth token is valid and refresh if needed."""
        if (
            self._oauth_token is None
            or self._oauth_expires is None
            or datetime.now() >= self._oauth_expires - timedelta(seconds=30)
        ):
            self._refresh_oauth_token()

    def _refresh_oauth_token(self) -> None:
        """Refresh the OAuth bearer token."""
        if not self.username or not self.password:
            raise P6McpError("Username and password required for OAuth auth")

        client = self._get_client()
        response = client.post(
            f"{self.base_url}/p6ws/oauth/token",
            headers={
                "authToken": base64.b64encode(
                    f"{self.username}:{self.password}".encode()
                ).decode(),
                "token_exp": "3600",  # 1 hour
                "return_json": "true",
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
        response.raise_for_status()
        token_data = response.json()
        self._oauth_token = token_data.get("access_token")
        expires_in = token_data.get("expires_in", 3600)
        self._oauth_expires = datetime.now() + timedelta(seconds=expires_in)

    def _get_auth_headers(self) -> dict[str, str]:
        """Get authentication headers for requests."""
        if self.auth_mode == "session":
            # Session auth would use cookies or a token in headers
            # This is a simplified implementation
            return {}
        elif self.auth_mode == "oauth":
            self._ensure_oauth_auth()
            if self._oauth_token is None:
                raise P6McpError("OAuth token not available")
            return {"Authorization": f"Bearer {self._oauth_token}"}
        else:
            raise P6McpError(f"Unsupported auth mode: {self.auth_mode}")

    def _make_request(
        self,
        method: str,
        service: str,
        *,
        fields: str | None = None,
        filter_expr: str | None = None,
        order_by: str | None = None,
        json_data: Any = None,
        params: dict[str, Any] | None = None,
    ) -> Any:
        """Make a request to the P6 EPPM REST API."""
        self._ensure_authenticated()
        client = self._get_client()

        # Build URL
        url = f"{self.base_url}/p6ws/restapi/{service}"

        # Build query parameters
        query_params: dict[str, str] = {}
        if fields:
            query_params["Fields"] = fields
        if filter_expr:
            query_params["Filter"] = filter_expr
        if order_by:
            query_params["OrderBy"] = order_by
        if params:
            query_params.update(params)

        # Make request
        if method.upper() == "GET":
            response = client.get(url, params=query_params, headers=self._get_auth_headers())
        elif method.upper() == "POST":
            response = client.post(
                url,
                params=query_params,
                headers={**self._get_auth_headers(), "Content-Type": "application/json"},
                json=json_data,
            )
        elif method.upper() == "PUT":
            response = client.put(
                url,
                params=query_params,
                headers={**self._get_auth_headers(), "Content-Type": "application/json"},
                json=json_data,
            )
        elif method.upper() == "DELETE":
            response = client.delete(
                url,
                params=query_params,
                headers=self._get_auth_headers(),
            )
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")

        response.raise_for_status()
        return response.json()

    def _get_fields(self, service: str) -> list[dict[str, Any]]:
        """Get field definitions for a service, cached."""
        if service not in self._field_cache:
            self._field_cache[service] = self._make_request("GET", f"{service}/fields")
        return self._field_cache[service]

    # Implementation of ScheduleRepository protocol

    def load(self, project_ref: str | int) -> dict[str, Any]:
        """Load a project and return the schedule aggregate."""
        # For now, return a basic structure - this would be expanded
        # to load all the necessary data and build the Schedule aggregate
        project_id = int(project_ref) if isinstance(project_ref, str) else project_ref
        return self.load_scope(project_id)

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
        project_id = int(project_ref) if isinstance(project_ref, str) else project_ref

        # Check cache
        cache_key = f"{project_id}:{load_activities}:{load_relationships}:{load_resources}:{load_roles}:{load_calendars}:{load_wbs}:{load_expenses}:{load_uds}:{load_steps}:{load_notebooks}:{load_baselines}"
        if cache_key in self._schedule_cache:
            cached = self._schedule_cache[cache_key]
            # In a real implementation, we'd check if the cache is still valid
            # based on LastUpdateDate watermarks
            return cached

        # Load the data - this is a simplified implementation
        result: dict[str, Any] = {}

        if load_baselines:
            result["baselines"] = self.get_baselines()

        # Get project info
        try:
            project = self.get_project(project_id)
            result["project"] = project
        except Exception:
            # Project might not exist or be accessible
            result["project"] = None

        if load_wbs and result["project"]:
            result["wbs_nodes"] = self.get_wbs_nodes(project_id)

        if load_activities and result["project"]:
            result["activities"] = self.get_activities(project_id)

        if load_relationships and result["project"]:
            result["relationships"] = self.get_relationships(project_id)

        if load_resources and result["project"]:
            result["resources"] = self.get_resources(project_id)

        if load_roles and result["project"]:
            result["roles"] = self.get_roles(project_id)

        if load_calendars and result["project"]:
            # Get calendars referenced by the project
            result["calendars"] = self.get_calendars(project_id)

        if load_expenses and result["project"]:
            result["expenses"] = self.get_expenses(project_id)

        if load_uds:
            result["udf_types"] = self.get_udf_types()
            # UDF values would be loaded per type as needed

        if load_steps and result["project"]:
            result["steps"] = self.get_steps(project_id)

        if load_notebooks and result["project"]:
            result["notebooks"] = self.get_notebooks(project_id)

        # Cache the result
        self._schedule_cache[cache_key] = result
        return result

    def get_projects(self) -> list[Project]:
        """Get all projects/baselines in the loaded data."""
        try:
            # Get projects from P6 EPPM
            data = self._make_request(
                "GET",
                "project",
                fields="ObjectId,Name,ShortName,ProjectId,DataDate,Status,CheckOutStatus,LastUpdateDate,ScheduledFinishDate,ProjectFlag",
                filter_expr="ProjectFlag IN(0,1)",  # 0=project, 1=baseline
            )
            projects = []
            for item in data:
                project = Project(
                    proj_id=int(item.get("ObjectId", 0)),
                    guid=item.get("ObjectId", ""),  # Using ObjectId as GUID for now
                    short_name=item.get("ShortName", ""),
                    name=item.get("Name", ""),
                )
                # Set additional properties
                project._data_date = item.get("DataDate")
                project._status = item.get("Status")
                projects.append(project)
            return projects
        except Exception as e:
            raise P6McpError(f"Failed to load projects: {e}")

    def get_project(self, project_id: int) -> Project:
        """Get a specific project by ID."""
        try:
            data = self._make_request(
                "GET",
                "project",
                fields="ObjectId,Name,ShortName,ProjectId,DataDate,Status,CheckOutStatus,LastUpdateDate,ScheduledFinishDate,ProjectFlag",
                filter_expr=f"ObjectId={project_id}",
            )
            if not data:
                raise P6McpError(f"Project {project_id} not found")
            item = data[0]
            project = Project(
                proj_id=int(item.get("ObjectId", 0)),
                guid=item.get("ObjectId", ""),
                short_name=item.get("ShortName", ""),
                name=item.get("Name", ""),
            )
            # Set additional properties
            project._data_date = item.get("DataDate")
            project._status = item.get("Status")
            return project
        except Exception as e:
            raise P6McpError(f"Failed to load project {project_id}: {e}")

    def get_activities(self, project_id: int) -> list[Activity]:
        """Get all activities for a project."""
        try:
            data = self._make_request(
                "GET",
                "activity",
                fields="ObjectId,TaskId,Name,ShortName,WBSObjectId,ProjectObjectId,PlannedStartDate,PlannedFinishDate,Status,PrimaryConstraintType,PrimaryConstraintDate,DurationType,PercentCompleteType,PercentComplete,RemainingDuration,ActualStartDate,ActualFinishDate,BudgetedCost,ActualCost,RemainingCost",
                filter_expr=f"ProjectObjectId={project_id}",
            )
            activities = []
            for item in data:
                activity = Activity(
                    task_id=int(item.get("ObjectId", 0)),
                    guid=item.get("ObjectId", ""),
                    code=item.get("ShortName", ""),
                    name=item.get("Name", ""),
                )
                # Set additional properties from the response
                activity._wbs_id = item.get("WBSObjectId")
                activity._proj_id = item.get("ProjectObjectId")
                activity._planned_start = item.get("PlannedStartDate")
                activity._planned_finish = item.get("PlannedFinishDate")
                activity._status = item.get("Status")
                activity._primary_constraint_type = item.get("PrimaryConstraintType")
                activity._primary_constraint_date = item.get("PrimaryConstraintDate")
                activity._duration_type = item.get("DurationType")
                activity._percent_complete_type = item.get("PercentCompleteType")
                activity._percent_complete = item.get("PercentComplete")
                activity._remaining_duration = item.get("RemainingDuration")
                activity._actual_start = item.get("ActualStartDate")
                activity._actual_finish = item.get("ActualFinishDate")
                activity._budgeted_cost = item.get("BudgetedCost")
                activity._actual_cost = item.get("ActualCost")
                activity._remaining_cost = item.get("RemainingCost")
                activities.append(activity)
            return activities
        except Exception as e:
            raise P6McpError(f"Failed to load activities for project {project_id}: {e}")

    def get_activity(self, activity_id: int) -> Activity:
        """Get a specific activity by ID."""
        try:
            data = self._make_request(
                "GET",
                "activity",
                fields="ObjectId,TaskId,Name,ShortName,WBSObjectId,ProjectObjectId,PlannedStartDate,PlannedFinishDate,Status,PrimaryConstraintType,PrimaryConstraintDate,DurationType,PercentCompleteType,PercentComplete,RemainingDuration,ActualStartDate,ActualFinishDate,BudgetedCost,ActualCost,RemainingCost",
                filter_expr=f"ObjectId={activity_id}",
            )
            if not data:
                raise P6McpError(f"Activity {activity_id} not found")
            item = data[0]
            activity = Activity(
                task_id=int(item.get("ObjectId", 0)),
                guid=item.get("ObjectId", ""),
                code=item.get("ShortName", ""),
                name=item.get("Name", ""),
            )
            # Set additional properties from the response
            activity._wbs_id = item.get("WBSObjectId")
            activity._proj_id = item.get("ProjectObjectId")
            activity._planned_start = item.get("PlannedStartDate")
            activity._planned_finish = item.get("PlannedFinishDate")
            activity._status = item.get("Status")
            activity._primary_constraint_type = item.get("PrimaryConstraintType")
            activity._primary_constraint_date = item.get("PrimaryConstraintDate")
            activity._duration_type = item.get("DurationType")
            activity._percent_complete_type = item.get("PercentCompleteType")
            activity._percent_complete = item.get("PercentComplete")
            activity._remaining_duration = item.get("RemainingDuration")
            activity._actual_start = item.get("ActualStartDate")
            activity._actual_finish = item.get("ActualFinishDate")
            activity._budgeted_cost = item.get("BudgetedCost")
            activity._actual_cost = item.get("ActualCost")
            activity._remaining_cost = item.get("RemainingCost")
            return activity
        except Exception as e:
            raise P6McpError(f"Failed to load activity {activity_id}: {e}")

    def get_relationships(self, project_id: int) -> list[dict[str, Any]]:
        """Get all relationships (TASKPRED) for a project."""
        try:
            data = self._make_request(
                "GET",
                "relationship",
                fields="ObjectId,PredecessorObjectId,SuccessorObjectId,RelationshipType,Lag,LagUnit,DrivingPathFlag",
                filter_expr=f"SuccessorObjectId IN (SELECT ObjectId FROM activity WHERE ProjectObjectId={project_id})",
            )
            return data
        except Exception as e:
            raise P6McpError(f"Failed to load relationships for project {project_id}: {e}")

    def get_resources(self, project_id: int) -> list[Resource]:
        """Get all resources for a project."""
        try:
            # Get resources assigned to activities in this project
            data = self._make_request(
                "GET",
                "resource",
                fields="ObjectId,ResourceId,Name,ShortName,ResourceType,UnitOfMeasure,StandardRate",
                filter_expr=f"ObjectId IN (SELECT ResourceId FROM resourceassignment WHERE TaskId IN (SELECT TaskId FROM activity WHERE ProjectObjectId={project_id}))",
            )
            resources = []
            for item in data:
                resource = Resource(
                    rsrc_id=int(item.get("ObjectId", 0)),
                    guid=item.get("ObjectId", ""),
                    name=item.get("Name", ""),
                    short_name=item.get("ShortName", ""),
                )
                # Set additional properties
                resource._resource_type = item.get("ResourceType")
                resource._unit_of_measure = item.get("UnitOfMeasure")
                resource._standard_rate = item.get("StandardRate")
                resources.append(resource)
            return resources
        except Exception as e:
            raise P6McpError(f"Failed to load resources for project {project_id}: {e}")

    def get_resource(self, resource_id: int) -> Resource:
        """Get a specific resource by ID."""
        try:
            data = self._make_request(
                "GET",
                "resource",
                fields="ObjectId,ResourceId,Name,ShortName,ResourceType,UnitOfMeasure,StandardRate",
                filter_expr=f"ObjectId={resource_id}",
            )
            if not data:
                raise P6McpError(f"Resource {resource_id} not found")
            item = data[0]
            resource = Resource(
                rsrc_id=int(item.get("ObjectId", 0)),
                guid=item.get("ObjectId", ""),
                name=item.get("Name", ""),
                short_name=item.get("ShortName", ""),
            )
            # Set additional properties
            resource._resource_type = item.get("ResourceType")
            resource._unit_of_measure = item.get("UnitOfMeasure")
            resource._standard_rate = item.get("StandardRate")
            return resource
        except Exception as e:
            raise P6McpError(f"Failed to load resource {resource_id}: {e}")

    def get_roles(self, project_id: int) -> list[Role]:
        """Get all roles for a project."""
        try:
            # Get roles used by assignments in this project
            data = self._make_request(
                "GET",
                "role",
                fields="ObjectId,RoleId,Name,ShortName",
                filter_expr=f"ObjectId IN (SELECT RoleId FROM resourceassignment WHERE TaskId IN (SELECT TaskId FROM activity WHERE ProjectObjectId={project_id}))",
            )
            roles = []
            for item in data:
                role = Role(
                    role_id=int(item.get("ObjectId", 0)),
                    guid=item.get("ObjectId", ""),
                    role_name=item.get("Name", ""),
                    role_short_name=item.get("ShortName", ""),
                )
                roles.append(role)
            return roles
        except Exception as e:
            raise P6McpError(f"Failed to load roles for project {project_id}: {e}")

    def get_role(self, role_id: int) -> Role:
        """Get a specific role by ID."""
        try:
            data = self._make_request(
                "GET",
                "role",
                fields="ObjectId,RoleId,Name,ShortName",
                filter_expr=f"ObjectId={role_id}",
            )
            if not data:
                raise P6McpError(f"Role {role_id} not found")
            item = data[0]
            role = Role(
                role_id=int(item.get("ObjectId", 0)),
                guid=item.get("ObjectId", ""),
                role_name=item.get("Name", ""),
                role_short_name=item.get("ShortName", ""),
            )
            return role
        except Exception as e:
            raise P6McpError(f"Failed to load role {role_id}: {e}")

    def get_wbs_nodes(self, project_id: int) -> list[Wbs]:
        """Get all WBS nodes for a project."""
        try:
            data = self._make_request(
                "GET",
                "wbs",
                fields="ObjectId,WBSID,Name,ShortName,ProjectObjectId",
                filter_expr=f"ProjectObjectId={project_id}",
            )
            wbs_nodes = []
            for item in data:
                wbs = Wbs(
                    wbs_id=int(item.get("ObjectId", 0)),
                    guid=item.get("ObjectId", ""),
                    name=item.get("Name", ""),
                    short_name=item.get("ShortName", ""),
                )
                wbs_nodes.append(wbs)
            return wbs_nodes
        except Exception as e:
            raise P6McpError(f"Failed to load WBS nodes for project {project_id}: {e}")

    def get_wbs_node(self, wbs_id: int) -> Wbs:
        """Get a specific WBS node by ID."""
        try:
            data = self._make_request(
                "GET",
                "wbs",
                fields="ObjectId,WBSID,Name,ShortName,ProjectObjectId",
                filter_expr=f"ObjectId={wbs_id}",
            )
            if not data:
                raise P6McpError(f"WBS node {wbs_id} not found")
            item = data[0]
            wbs = Wbs(
                wbs_id=int(item.get("ObjectId", 0)),
                guid=item.get("ObjectId", ""),
                name=item.get("Name", ""),
                short_name=item.get("ShortName", ""),
            )
            return wbs
        except Exception as e:
            raise P6McpError(f"Failed to load WBS node {wbs_id}: {e}")

    def get_calendars(self, project_id: int) -> list[Calendar]:
        """Get all calendars referenced by a project."""
        try:
            # Get calendars used by activities in this project
            data = self._make_request(
                "GET",
                "calendar",
                fields="ObjectId,CalendarID,Name,Description",
                filter_expr=f"ObjectId IN (SELECT CalendarObjectId FROM activity WHERE ProjectObjectId={project_id})",
            )
            calendars = []
            for item in data:
                calendar = Calendar(
                    clndr_id=int(item.get("ObjectId", 0)),
                    guid=item.get("ObjectId", ""),
                    name=item.get("Name", ""),
                    description=item.get("Description", ""),
                )
                calendars.append(calendar)
            return calendars
        except Exception as e:
            raise P6McpError(f"Failed to load calendars for project {project_id}: {e}")

    def get_calendar(self, calendar_id: int) -> Calendar:
        """Get a specific calendar by ID."""
        try:
            data = self._make_request(
                "GET",
                "calendar",
                fields="ObjectId,CalendarID,Name,Description",
                filter_expr=f"ObjectId={calendar_id}",
            )
            if not data:
                raise P6McpError(f"Calendar {calendar_id} not found")
            item = data[0]
            calendar = Calendar(
                clndr_id=int(item.get("ObjectId", 0)),
                guid=item.get("ObjectId", ""),
                name=item.get("Name", ""),
                description=item.get("Description", ""),
            )
            return calendar
        except Exception as e:
            raise P6McpError(f"Failed to load calendar {calendar_id}: {e}")

    def get_expenses(self, project_id: int) -> list[Expense]:
        """Get all expenses for a project."""
        try:
            data = self._make_request(
                "GET",
                "activityexpense",
                fields="ObjectId,TaskID,CostAccountObjectId,TargetCost,ActualCost,RemainingCost",
                filter_expr=f"TaskID IN (SELECT TaskId FROM activity WHERE ProjectObjectId={project_id})",
            )
            expenses = []
            for item in data:
                expense = Expense(
                    guid=item.get("ObjectId", ""),
                    task_id=int(item.get("TaskID", 0)),
                    acct_id=int(item.get("CostAccountObjectId", 0)) if item.get("CostAccountObjectId") else None,
                    budgeted_cost=float(item.get("TargetCost", 0)),
                    actual_cost=float(item.get("ActualCost", 0)),
                    remaining_cost=float(item.get("RemainingCost", 0)),
                )
                expenses.append(expense)
            return expenses
        except Exception as e:
            raise P6McpError(f"Failed to load expenses for project {project_id}: {e}")

    def get_expense(self, expense_id: int) -> Expense:
        """Get a specific expense by ID."""
        try:
            data = self._make_request(
                "GET",
                "activityexpense",
                fields="ObjectId,TaskID,CostAccountObjectId,TargetCost,ActualCost,RemainingCost",
                filter_expr=f"ObjectId={expense_id}",
            )
            if not data:
                raise P6McpError(f"Expense {expense_id} not found")
            item = data[0]
            expense = Expense(
                guid=item.get("ObjectId", ""),
                task_id=int(item.get("TaskID", 0)),
                acct_id=int(item.get("CostAccountObjectId", 0)) if item.get("CostAccountObjectId") else None,
                budgeted_cost=float(item.get("TargetCost", 0)),
                actual_cost=float(item.get("ActualCost", 0)),
                remaining_cost=float(item.get("RemainingCost", 0)),
            )
            return expense
        except Exception as e:
            raise P6McpError(f"Failed to load expense {expense_id}: {e}")

    def get_udf_types(self) -> list[UdfType]:
        """Get all UDF types."""
        try:
            data = self._make_request(
                "GET",
                "udfvalue",
                fields="ObjectId,FieldName,TableName,DataType",
                filter_expr="FieldName IS NOT NULL",  # Get UDF type definitions
            )
            udf_types = []
            for item in data:
                udf_type = UdfType(
                    guid=item.get("ObjectId", ""),
                    name=item.get("FieldName", ""),
                    table_name=item.get("TableName", ""),
                    data_type=item.get("DataType", ""),
                )
                udf_types.append(udf_type)
            return udf_types
        except Exception as e:
            raise P6McpError(f"Failed to load UDF types: {e}")

    def get_udf_values(self, udf_type_id: int) -> list[UdfValue]:
        """Get all UDF values for a UDF type."""
        try:
            data = self._make_request(
                "GET",
                "udfvalue",
                fields="ObjectId,FieldValue,TableName",
                filter_expr=f"FieldName IN (SELECT FieldName FROM udfvalue WHERE ObjectId={udf_type_id})",
            )
            udf_values = []
            for item in data:
                udf_value = UdfValue(
                    guid=item.get("ObjectId", ""),
                    udf_type_guid="",  # Would need to look this up
                    value=item.get("FieldValue", ""),
                )
                udf_values.append(udf_value)
            return udf_values
        except Exception as e:
            raise P6McpError(f"Failed to load UDF values for type {udf_type_id}: {e}")

    def get_steps(self, project_id: int) -> list[Step]:
        """Get all steps for a project."""
        try:
            data = self._make_request(
                "GET",
                "activitystep",
                fields="ObjectId,StepID,Description",
                filter_expr=f"ObjectId IN (SELECT StepId FROM activity WHERE ProjectObjectId={project_id})",
            )
            steps = []
            for item in data:
                step = Step(
                    guid=item.get("ObjectId", ""),
                    step_id=item.get("StepID", ""),
                    description=item.get("Description", ""),
                )
                steps.append(step)
            return steps
        except Exception as e:
            raise P6McpError(f"Failed to load steps for project {project_id}: {e}")

    def get_step(self, step_id: int) -> Step:
        """Get a specific step by ID."""
        try:
            data = self._make_request(
                "GET",
                "activitystep",
                fields="ObjectId,StepID,Description",
                filter_expr=f"ObjectId={step_id}",
            )
            if not data:
                raise P6McpError(f"Step {step_id} not found")
            item = data[0]
            step = Step(
                guid=item.get("ObjectId", ""),
                step_id=item.get("StepID", ""),
                description=item.get("Description", ""),
            )
            return step
        except Exception as e:
            raise P6McpError(f"Failed to load step {step_id}: {e}")

    def get_notebooks(self, project_id: int) -> list[Notebook]:
        """Get all notebooks for a project."""
        try:
            data = self._make_request(
                "GET",
                "activitynote",
                fields="ObjectId,TaskID,NoteText",
                filter_expr=f"TaskID IN (SELECT TaskId FROM activity WHERE ProjectObjectId={project_id})",
            )
            notebooks = []
            for item in data:
                notebook = Notebook(
                    guid=item.get("ObjectId", ""),
                    task_id=int(item.get("TaskID", 0)),
                    note=item.get("NoteText", ""),
                )
                notebooks.append(notebook)
            return notebooks
        except Exception as e:
            raise P6McpError(f"Failed to load notebooks for project {project_id}: {e}")

    def get_notebook(self, notebook_id: int) -> Notebook:
        """Get a specific notebook by ID."""
        try:
            data = self._make_request(
                "GET",
                "activitynote",
                fields="ObjectId,TaskID,NoteText",
                filter_expr=f"ObjectId={notebook_id}",
            )
            if not data:
                raise P6McpError(f"Notebook {notebook_id} not found")
            item = data[0]
            notebook = Notebook(
                guid=item.get("ObjectId", ""),
                task_id=int(item.get("TaskID", 0)),
                note=item.get("NoteText", ""),
            )
            return notebook
        except Exception as e:
            raise P6McpError(f"Failed to load notebook {notebook_id}: {e}")

    def get_baselines(self) -> list[BaselineProject]:
        """Get all baseline projects."""
        try:
            data = self._make_request(
                "GET",
                "project",
                fields="ObjectId,Name,ShortName,ProjectFlag,OrigProjId,SumBaseProjId",
                filter_expr="ProjectFlag=1",  # Baseline projects
            )
            baselines = []
            for item in data:
                baseline = BaselineProject(
                    proj_id=int(item.get("ObjectId", 0)),
                    guid=item.get("ObjectId", ""),
                    short_name=item.get("ShortName", ""),
                    name=item.get("Name", ""),
                )
                # Set baseline-specific fields
                baseline._orig_proj_id = item.get("OrigProjId")
                baseline._sum_base_proj_id = item.get("SumBaseProjId")
                baselines.append(baseline)
            return baselines
        except Exception as e:
            raise P6McpError(f"Failed to load baselines: {e}")

    def get_baseline(self, baseline_id: int) -> BaselineProject:
        """Get a specific baseline by ID."""
        try:
            data = self._make_request(
                "GET",
                "project",
                fields="ObjectId,Name,ShortName,ProjectFlag,OrigProjId,SumBaseProjId",
                filter_expr=f"ObjectId={baseline_id} AND ProjectFlag=1",
            )
            if not data:
                raise P6McpError(f"Baseline {baseline_id} not found")
            item = data[0]
            baseline = BaselineProject(
                proj_id=int(item.get("ObjectId", 0)),
                guid=item.get("ObjectId", ""),
                short_name=item.get("ShortName", ""),
                name=item.get("Name", ""),
            )
            # Set baseline-specific fields
            baseline._orig_proj_id = item.get("OrigProjId")
            baseline._sum_base_proj_id = item.get("SumBaseProjId")
            return baseline
        except Exception as e:
            raise P6McpError(f"Failed to load baseline {baseline_id}: {e}")

    # Implementation of MutableScheduleRepository protocol

    def snapshot(self) -> str:
        """Take a snapshot and return the snapshot ID."""
        # In a real implementation, this would:
        # 1. Call the P6 export service to get XML
        # 2. Store it in the output directory
        # 3. Return a snapshot ID
        raise P6McpError("Snapshot functionality not yet implemented")

    def run_job(self, job_type: str, project_id: int, **kwargs) -> str:
        """Run a P6 job and return the job ID."""
        # In a real implementation, this would:
        # 1. Call /job/{job_type} with appropriate parameters
        # 2. Return the job ID
        raise P6McpError("Job execution not yet implemented")

    def get_job_status(self, job_id: str) -> dict[str, Any]:
        """Get the status of a job."""
        # In a real implementation, this would:
        # 1. Call /job/readJobStatus with the job ID
        # 2. Return the status
        raise P6McpError("Job status not yet implemented")

    def get_job_log(self, job_id: str, lines: int = 100) -> list[str]:
        """Get the log output from a job."""
        # In a real implementation, this would:
        # 1. Call /job/readJobLog with the job ID
        # 2. Return the log lines
        raise P6McpError("Job log not yet implemented")

    def cancel_job(self, job_id: str) -> bool:
        """Cancel a running job."""
        # In a real implementation, this would:
        # 1. Call /job/cancelJob with the job ID
        # 2. Return success/failure
        raise P6McpError("Job cancellation not yet implemented")