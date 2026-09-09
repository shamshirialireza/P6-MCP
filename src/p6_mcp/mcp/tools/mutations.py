"""§5.15 Write-back tools.

Every tool here requires ``confirm=True``, writes to a NEW file unless
``overwrite=True``, validates the result, and returns a change summary.
Disabled entirely when the server runs read-only.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations

from p6_mcp.domain.schedule import Schedule
from p6_mcp.exceptions import MutationError
from p6_mcp.mcp.context import AppContext, build_activity_filter, tool_errors
from p6_mcp.parser.writer import XerWriter
from p6_mcp.services.mutate.editor import ScheduleEditor
from p6_mcp.services.mutate.files import create_baseline_copy, merge_documents
from p6_mcp.services.mutate.files import split_by_project as split_service
from p6_mcp.services.mutate.validate import validate
from p6_mcp.services.query.activities import filter_activities

DESTRUCTIVE = ToolAnnotations(
    readOnlyHint=False, destructiveHint=True, idempotentHint=False, openWorldHint=False
)


def register(mcp: MCPServer, ctx: AppContext) -> None:
    """Register mutation tools."""

    def _require(confirm: bool) -> None:
        ctx.require_mutation()
        if not confirm:
            raise MutationError(
                "This tool modifies schedule data and needs confirm=True",
                hint="Re-call with confirm=True once you have reviewed the change.",
            )

    def _write(
        editor: ScheduleEditor, file_path: str, output_path: str | None, overwrite: bool
    ) -> dict[str, Any]:
        """Persist the edited document and validate the result."""
        if output_path:
            target = ctx.workspace.validate_write(output_path)
        elif overwrite:
            target = ctx.workspace.validate_read(file_path)
        else:
            src = Path(ctx.schedule(file_path).doc.source_path or "edited.xer")
            target = ctx.workspace.validate_write(f"{src.stem}-edited.xer")
        if target.exists() and not overwrite and output_path is None:
            raise MutationError(
                f"{target} already exists",
                hint="Pass output_path for a new name, or overwrite=True.",
            )
        XerWriter().write_path(editor.doc, target)
        report = validate(editor.schedule)
        return ctx.guard(
            {
                "output_path": str(target),
                "bytes": target.stat().st_size,
                "changes": editor.summary.to_dict(),
                "validation": {
                    "valid": report["valid"],
                    "errors": report["error_count"],
                    "warnings": report["warning_count"],
                    "error_details": report["errors"][:5],
                },
            }
        )

    @mcp.tool(title="Update activity", annotations=DESTRUCTIVE)
    @tool_errors
    def update_activity(
        file_path: str,
        task_code: str,
        changes: dict[str, Any],
        confirm: bool = False,
        output_path: str | None = None,
        overwrite: bool = False,
    ) -> dict[str, Any]:
        """Change fields on one activity and write a new XER.

        `changes` accepts friendly keys — name, status, task_type, wbs_id,
        calendar_id, duration_hours, remaining_duration_hours, actual_start,
        actual_finish, planned_start, planned_finish, constraint_type,
        constraint_date, physical_percent — or any raw TASK column name.
        Dates are 'YYYY-MM-DD HH:MM'.
        """
        _require(confirm)
        sch = ctx.schedule(file_path)
        editor = ScheduleEditor(sch)
        detail = editor.update_activity(task_code, changes)
        return {**_write(editor, file_path, output_path, overwrite), "detail": detail}

    @mcp.tool(title="Bulk update activities", annotations=DESTRUCTIVE)
    @tool_errors
    def bulk_update_activities(
        file_path: str,
        changes: dict[str, Any],
        confirm: bool = False,
        project_id: int | None = None,
        project_short_name: str | None = None,
        status: list[str] | None = None,
        task_type: list[str] | None = None,
        wbs_path_prefix: str | None = None,
        name_contains: str | None = None,
        code_regex: str | None = None,
        max_activities: int = 500,
        output_path: str | None = None,
        overwrite: bool = False,
    ) -> dict[str, Any]:
        """Apply the same field changes to every activity matching the filters.

        Refuses to run when the filter matches more than `max_activities`, so a
        missing filter cannot silently rewrite the whole schedule.
        """
        _require(confirm)
        sch, projects = ctx.scope(file_path, project_id, project_short_name)
        flt = build_activity_filter(
            status=status,
            task_type=task_type,
            wbs_path_prefix=wbs_path_prefix,
            name_contains=name_contains,
            code_regex=code_regex,
        )
        matches = filter_activities(sch, sch.activities_of(projects), flt)
        if not matches:
            raise MutationError(
                "No activities matched the filter",
                hint="Preview the selection with get_activities.",
            )
        if len(matches) > max_activities:
            raise MutationError(
                f"Filter matched {len(matches)} activities (limit {max_activities})",
                hint="Narrow the filter or raise max_activities deliberately.",
            )
        editor = ScheduleEditor(sch)
        for a in matches:
            editor.update_activity(a.code, changes)
        return {
            **_write(editor, file_path, output_path, overwrite),
            "updated": len(matches),
            "task_codes": sorted(a.code for a in matches)[:50],
        }

    @mcp.tool(title="Add relationship", annotations=DESTRUCTIVE)
    @tool_errors
    def add_relationship(
        file_path: str,
        predecessor: str,
        successor: str,
        pred_type: str = "PR_FS",
        lag_hours: float = 0.0,
        confirm: bool = False,
        output_path: str | None = None,
        overwrite: bool = False,
    ) -> dict[str, Any]:
        """Link two activities. pred_type is PR_FS, PR_SS, PR_FF, or PR_SF."""
        _require(confirm)
        editor = ScheduleEditor(ctx.schedule(file_path))
        detail = editor.add_relationship(predecessor, successor, pred_type, lag_hours)
        return {**_write(editor, file_path, output_path, overwrite), "detail": detail}

    @mcp.tool(title="Remove relationship", annotations=DESTRUCTIVE)
    @tool_errors
    def remove_relationship(
        file_path: str,
        predecessor: str,
        successor: str,
        confirm: bool = False,
        output_path: str | None = None,
        overwrite: bool = False,
    ) -> dict[str, Any]:
        """Delete the logic link between two activities."""
        _require(confirm)
        editor = ScheduleEditor(ctx.schedule(file_path))
        detail = editor.remove_relationship(predecessor, successor)
        return {**_write(editor, file_path, output_path, overwrite), "detail": detail}

    @mcp.tool(title="Update relationship", annotations=DESTRUCTIVE)
    @tool_errors
    def update_relationship(
        file_path: str,
        predecessor: str,
        successor: str,
        pred_type: str | None = None,
        lag_hours: float | None = None,
        confirm: bool = False,
        output_path: str | None = None,
        overwrite: bool = False,
    ) -> dict[str, Any]:
        """Change an existing link's type and/or lag."""
        _require(confirm)
        editor = ScheduleEditor(ctx.schedule(file_path))
        detail = editor.update_relationship(predecessor, successor, pred_type, lag_hours)
        return {**_write(editor, file_path, output_path, overwrite), "detail": detail}

    @mcp.tool(title="Add activity", annotations=DESTRUCTIVE)
    @tool_errors
    def add_activity(
        file_path: str,
        proj_id: int,
        wbs_id: int,
        task_code: str,
        task_name: str,
        duration_hours: float = 0.0,
        task_type: str = "TT_Task",
        calendar_id: int | None = None,
        confirm: bool = False,
        output_path: str | None = None,
        overwrite: bool = False,
    ) -> dict[str, Any]:
        """Create a new activity. The code must be unique and the WBS must exist.

        The new activity starts with no logic — add relationships next, or it
        will show up as an open end.
        """
        _require(confirm)
        editor = ScheduleEditor(ctx.schedule(file_path))
        detail = editor.add_activity(
            proj_id, wbs_id, task_code, task_name, duration_hours, task_type, calendar_id
        )
        return {**_write(editor, file_path, output_path, overwrite), "detail": detail}

    @mcp.tool(title="Delete activity", annotations=DESTRUCTIVE)
    @tool_errors
    def delete_activity(
        file_path: str,
        task_code: str,
        cascade: bool = True,
        confirm: bool = False,
        output_path: str | None = None,
        overwrite: bool = False,
    ) -> dict[str, Any]:
        """Delete an activity and, with cascade, its relationships, assignments,
        expenses, codes, notes, and steps.

        With cascade=False the call fails if the activity still has logic, so
        you cannot orphan the network by accident.
        """
        _require(confirm)
        editor = ScheduleEditor(ctx.schedule(file_path))
        detail = editor.delete_activity(task_code, cascade)
        return {**_write(editor, file_path, output_path, overwrite), "detail": detail}

    @mcp.tool(title="Update project", annotations=DESTRUCTIVE)
    @tool_errors
    def update_project(
        file_path: str,
        proj_id: int,
        changes: dict[str, Any],
        confirm: bool = False,
        output_path: str | None = None,
        overwrite: bool = False,
    ) -> dict[str, Any]:
        """Change project-level fields, e.g. {"data_date": "2024-03-04 08:00"}."""
        _require(confirm)
        editor = ScheduleEditor(ctx.schedule(file_path))
        detail = editor.update_project(proj_id, changes)
        return {**_write(editor, file_path, output_path, overwrite), "detail": detail}

    @mcp.tool(title="Assign resource", annotations=DESTRUCTIVE)
    @tool_errors
    def assign_resource(
        file_path: str,
        task_code: str,
        resource: str,
        budgeted_qty: float,
        cost_per_qty: float | None = None,
        confirm: bool = False,
        output_path: str | None = None,
        overwrite: bool = False,
    ) -> dict[str, Any]:
        """Assign a resource to an activity. The rate defaults to the resource's
        latest RSRCRATE price when not given."""
        _require(confirm)
        editor = ScheduleEditor(ctx.schedule(file_path))
        detail = editor.assign_resource(task_code, resource, budgeted_qty, cost_per_qty)
        return {**_write(editor, file_path, output_path, overwrite), "detail": detail}

    @mcp.tool(title="Remove assignment", annotations=DESTRUCTIVE)
    @tool_errors
    def remove_assignment(
        file_path: str,
        task_code: str,
        resource: str,
        confirm: bool = False,
        output_path: str | None = None,
        overwrite: bool = False,
    ) -> dict[str, Any]:
        """Remove a resource assignment from an activity."""
        _require(confirm)
        editor = ScheduleEditor(ctx.schedule(file_path))
        detail = editor.remove_assignment(task_code, resource)
        return {**_write(editor, file_path, output_path, overwrite), "detail": detail}

    @mcp.tool(title="Update assignment", annotations=DESTRUCTIVE)
    @tool_errors
    def update_assignment(
        file_path: str,
        task_code: str,
        resource: str,
        changes: dict[str, Any],
        confirm: bool = False,
        output_path: str | None = None,
        overwrite: bool = False,
    ) -> dict[str, Any]:
        """Change an assignment's quantities or costs (budgeted_qty,
        remaining_qty, budgeted_cost, remaining_cost, cost_per_qty,
        actual_qty, actual_cost)."""
        _require(confirm)
        editor = ScheduleEditor(ctx.schedule(file_path))
        detail = editor.update_assignment(task_code, resource, changes)
        return {**_write(editor, file_path, output_path, overwrite), "detail": detail}

    @mcp.tool(title="Set activity code", annotations=DESTRUCTIVE)
    @tool_errors
    def set_activity_code(
        file_path: str,
        task_code: str,
        code_type: str,
        code_value: str,
        confirm: bool = False,
        output_path: str | None = None,
        overwrite: bool = False,
    ) -> dict[str, Any]:
        """Assign an activity code value, replacing any existing value of that
        code type on the activity."""
        _require(confirm)
        editor = ScheduleEditor(ctx.schedule(file_path))
        detail = editor.set_activity_code(task_code, code_type, code_value)
        return {**_write(editor, file_path, output_path, overwrite), "detail": detail}

    @mcp.tool(title="Set UDF value", annotations=DESTRUCTIVE)
    @tool_errors
    def set_udf_value(
        file_path: str,
        entity_table: str,
        entity: str,
        udf_name: str,
        value: Any,
        confirm: bool = False,
        output_path: str | None = None,
        overwrite: bool = False,
    ) -> dict[str, Any]:
        """Set a user-defined field value. `entity_table` is usually TASK and
        `entity` the activity code; the UDF must already be defined in the file.
        """
        _require(confirm)
        editor = ScheduleEditor(ctx.schedule(file_path))
        detail = editor.set_udf_value(entity_table, entity, udf_name, value)
        return {**_write(editor, file_path, output_path, overwrite), "detail": detail}

    @mcp.tool(title="Apply progress", annotations=DESTRUCTIVE)
    @tool_errors
    def apply_progress(
        file_path: str,
        updates: list[dict[str, Any]],
        new_data_date: str | None = None,
        proj_id: int | None = None,
        confirm: bool = False,
        output_path: str | None = None,
        overwrite: bool = False,
    ) -> dict[str, Any]:
        """Status a batch of activities and advance the data date in one call.

        Each update is {"task_code": "A1030", "actual_start": "...",
        "actual_finish": "...", "remaining_duration": 40, "pct": 60}. Supplying
        an actual finish sets the status to Completed and zeroes the remaining
        duration; an actual start on an unstarted activity sets In Progress.

        This edits stored values only — it does not re-run CPM. Call
        recompute_cpm afterwards to see the resulting forecast.
        """
        _require(confirm)
        editor = ScheduleEditor(ctx.schedule(file_path))
        detail = editor.apply_progress(updates, new_data_date, proj_id)
        return {**_write(editor, file_path, output_path, overwrite), "detail": detail}

    @mcp.tool(name="create_baseline_copy", title="Create baseline copy", annotations=DESTRUCTIVE)
    @tool_errors
    def create_baseline_copy_tool(
        file_path: str, proj_id: int, output_path: str, confirm: bool = False
    ) -> dict[str, Any]:
        """Duplicate a project as a linked baseline inside a new XER file.

        IDs in the copy are offset so both live and baseline coexist, exactly as
        a P6 "save as baseline" export would. Afterwards compare_to_baseline and
        the DCMA baseline checks will work against this file.
        """
        _require(confirm)
        sch = ctx.schedule(file_path)
        doc, stats = create_baseline_copy(sch, proj_id)
        target = ctx.workspace.validate_write(output_path)
        XerWriter().write_path(doc, target)
        report = validate(Schedule(doc))
        return ctx.guard(
            {
                "output_path": str(target),
                "bytes": target.stat().st_size,
                **stats,
                "validation": {"valid": report["valid"], "errors": report["error_count"]},
            }
        )

    @mcp.tool(title="Merge XER files", annotations=DESTRUCTIVE)
    @tool_errors
    def merge_xer_files(
        file_paths: list[str], output_path: str, confirm: bool = False
    ) -> dict[str, Any]:
        """Merge several XER files into one.

        The first file wins any primary-key collision and the skip is reported —
        IDs are never renumbered, because that would break cross-table
        references. Merge files from different databases with care.
        """
        _require(confirm)
        if len(file_paths) < 2:
            raise MutationError("Provide at least two files to merge")
        schedules = [ctx.schedule(p) for p in file_paths]
        doc, stats = merge_documents(schedules)
        target = ctx.workspace.validate_write(output_path)
        XerWriter().write_path(doc, target)
        report = validate(Schedule(doc))
        return ctx.guard(
            {
                "output_path": str(target),
                "bytes": target.stat().st_size,
                **stats,
                "validation": {
                    "valid": report["valid"],
                    "errors": report["error_count"],
                    "warnings": report["warning_count"],
                },
            }
        )

    @mcp.tool(title="Split XER by project", annotations=DESTRUCTIVE)
    @tool_errors
    def split_xer_by_project(
        file_path: str, output_dir: str, confirm: bool = False
    ) -> dict[str, Any]:
        """Write one XER per project, each carrying its own baselines."""
        _require(confirm)
        sch = ctx.schedule(file_path)
        base = ctx.workspace.validate_write(output_dir)
        base.mkdir(parents=True, exist_ok=True)
        written = []
        for name, doc, stats in split_service(sch):
            target = ctx.workspace.validate_write(str(base / name))
            XerWriter().write_path(doc, target)
            written.append(
                {
                    "output_path": str(target),
                    "activities": stats["activities"],
                    "bytes": target.stat().st_size,
                }
            )
        return ctx.guard({"output_dir": str(base), "files": written})

    @mcp.tool(title="Write XER", annotations=DESTRUCTIVE)
    @tool_errors
    def write_xer(file_path: str, output_path: str, confirm: bool = False) -> dict[str, Any]:
        """Write a cached schedule back out to a new XER file unchanged.

        Useful for normalising or re-encoding a file; the round-trip is lossless.
        """
        _require(confirm)
        sch = ctx.schedule(file_path)
        target = ctx.workspace.validate_write(output_path)
        XerWriter().write_path(sch.doc, target)
        report = validate(sch)
        return ctx.guard(
            {
                "output_path": str(target),
                "bytes": target.stat().st_size,
                "validation": {"valid": report["valid"], "errors": report["error_count"]},
            }
        )

    _ = (
        update_activity,
        bulk_update_activities,
        add_relationship,
        remove_relationship,
        update_relationship,
        add_activity,
        delete_activity,
        update_project,
        assign_resource,
        remove_assignment,
        update_assignment,
        set_activity_code,
        set_udf_value,
        apply_progress,
        create_baseline_copy_tool,
        merge_xer_files,
        split_xer_by_project,
        write_xer,
    )
