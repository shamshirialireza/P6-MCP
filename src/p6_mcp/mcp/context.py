"""Shared plumbing for the MCP tool layer: app context, error envelopes,
and the resolve helpers every tool starts with."""

from __future__ import annotations

import functools
import inspect
import json
from collections.abc import Callable
from typing import Any, NoReturn, TypeVar

from mcp.server.mcpserver.exceptions import ToolError

from p6_mcp.config import Settings
from p6_mcp.domain.project import Project
from p6_mcp.domain.schedule import Schedule
from p6_mcp.exceptions import InvalidArgumentError, MutationDisabledError, P6McpError
from p6_mcp.mcp.limits import enforce
from p6_mcp.repository.loader import ScheduleLoader
from p6_mcp.repository.workspace import Workspace
from p6_mcp.services.query.activities import ActivityFilter
from p6_mcp.services.query.pagination import paginate
from p6_mcp.services.query.serialize import iso

T = TypeVar("T")


class AppContext:
    """Everything the tools need: settings, workspace guard, and schedule cache."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.workspace = Workspace(settings)
        self.loader = ScheduleLoader(settings, self.workspace)

    # -- resolution --------------------------------------------------------

    def schedule(self, file_path: str, encoding: str | None = None) -> Schedule:
        """Load by path or by a schedule_id handle from open_schedule."""
        return self.loader.load(file_path, encoding)

    def projects(
        self,
        sch: Schedule,
        project_id: int | None = None,
        project_short_name: str | None = None,
    ) -> list[Project]:
        """Selected projects, defaulting to every non-baseline project."""
        return sch.resolve_projects(project_id, project_short_name)

    def scope(
        self,
        file_path: str,
        project_id: int | None = None,
        project_short_name: str | None = None,
    ) -> tuple[Schedule, list[Project]]:
        """The common ``(schedule, projects)`` pair most tools open with."""
        sch = self.schedule(file_path)
        return sch, self.projects(sch, project_id, project_short_name)

    # -- limits ------------------------------------------------------------

    def clamp_limit(self, limit: int) -> int:
        return max(1, min(limit, self.settings.max_limit))

    def guard(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Apply the output-size budget."""
        return enforce(iso(payload), self.settings.max_output_bytes)

    def page(
        self,
        items: list[T],
        limit: int,
        offset: int,
        sort_by: str | None = None,
        sort_dir: str = "asc",
        key_of: Callable[[T, str], Any] | None = None,
        extra: dict[str, Any] | None = None,
        render: Callable[[T], Any] | None = None,
    ) -> dict[str, Any]:
        """Sort, slice, serialize, and wrap in the standard envelope."""
        sort_get = None
        if sort_by and key_of is not None:
            sort_get = functools.partial(_swap, key_of, sort_by)
        page, meta = paginate(
            items,
            limit=self.clamp_limit(limit),
            offset=offset,
            max_limit=self.settings.max_limit,
            sort_get=sort_get,
            sort_dir=sort_dir,
        )
        rendered = [render(x) for x in page] if render else list(page)
        return self.guard({**meta, **(extra or {}), "items": rendered})

    def require_mutation(self) -> None:
        if not self.settings.mutation_allowed():
            raise MutationDisabledError(
                "Write-back tools are disabled on this server",
                hint="Start the server with --enable-mutation (and without "
                "--read-only) to allow edits.",
            )


def _swap(key_of: Callable[[Any, str], Any], field: str, item: Any) -> Any:
    return key_of(item, field)


def fail(exc: P6McpError) -> NoReturn:
    """Convert a library error into an MCP tool error with a JSON envelope."""
    raise ToolError(json.dumps({"error": exc.to_dict()}, ensure_ascii=False)) from exc


def tool_errors(fn: Callable[..., Any]) -> Callable[..., Any]:
    """Wrap a tool so library errors become structured MCP errors, never
    stack traces. Works on both sync and async tool functions."""
    if inspect.iscoroutinefunction(fn):

        @functools.wraps(fn)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            try:
                return await fn(*args, **kwargs)
            except P6McpError as exc:
                fail(exc)
            except (ValueError, KeyError, TypeError) as exc:
                fail(InvalidArgumentError(str(exc), hint="Check the argument types."))

        return async_wrapper

    @functools.wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return fn(*args, **kwargs)
        except P6McpError as exc:
            fail(exc)
        except (ValueError, KeyError, TypeError) as exc:
            fail(InvalidArgumentError(str(exc), hint="Check the argument types."))

    return wrapper


def build_activity_filter(
    status: list[str] | None = None,
    task_type: list[str] | None = None,
    wbs_id: int | None = None,
    wbs_path_prefix: str | None = None,
    activity_code: dict[str, str] | None = None,
    udf: dict[str, Any] | None = None,
    calendar_id: int | None = None,
    resource_id: int | None = None,
    resource_name: str | None = None,
    role_id: int | None = None,
    name_contains: str | None = None,
    code_contains: str | None = None,
    code_regex: str | None = None,
    start_after: str | None = None,
    start_before: str | None = None,
    finish_after: str | None = None,
    finish_before: str | None = None,
    float_min_days: float | None = None,
    float_max_days: float | None = None,
    remaining_duration_min_days: float | None = None,
    remaining_duration_max_days: float | None = None,
    has_constraint: bool | None = None,
    constraint_type: str | None = None,
    is_critical: bool | None = None,
    on_longest_path: bool | None = None,
    has_no_predecessors: bool | None = None,
    has_no_successors: bool | None = None,
    is_behind_schedule: bool | None = None,
    has_actuals: bool | None = None,
) -> ActivityFilter:
    """Assemble an ActivityFilter from flat tool arguments."""
    from p6_mcp.parser.coercion import parse_date

    def rng(lo: str | None, hi: str | None) -> tuple[Any, Any] | None:
        if lo is None and hi is None:
            return None
        return (parse_date(lo) if lo else None, parse_date(hi) if hi else None)

    return ActivityFilter(
        status=status,
        task_type=task_type,
        wbs_id=wbs_id,
        wbs_path_prefix=wbs_path_prefix,
        activity_code=activity_code,
        udf=udf,
        calendar_id=calendar_id,
        resource_id=resource_id,
        resource_name=resource_name,
        role_id=role_id,
        name_contains=name_contains,
        code_contains=code_contains,
        code_regex=code_regex,
        start_between=rng(start_after, start_before),
        finish_between=rng(finish_after, finish_before),
        float_min_days=float_min_days,
        float_max_days=float_max_days,
        remaining_duration_min_days=remaining_duration_min_days,
        remaining_duration_max_days=remaining_duration_max_days,
        has_constraint=has_constraint,
        constraint_type=constraint_type,
        is_critical=is_critical,
        on_longest_path=on_longest_path,
        has_no_predecessors=has_no_predecessors,
        has_no_successors=has_no_successors,
        is_behind_schedule=is_behind_schedule,
        has_actuals=has_actuals,
    )
