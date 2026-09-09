"""§5.14 Export tools. All writes land inside the configured output directory."""

from __future__ import annotations

from typing import Any

from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations

from p6_mcp.exceptions import ExportError, InvalidArgumentError
from p6_mcp.mcp.context import AppContext, build_activity_filter, tool_errors
from p6_mcp.mcp.tools.files import READ_ONLY
from p6_mcp.parser.writer import XerWriter
from p6_mcp.services.export.datasets import DATASETS, build_dataset
from p6_mcp.services.export.diagrams import gantt_mermaid, milestones_ics, network_dot
from p6_mcp.services.export.tabular import to_csv, to_excel, to_json_text, to_markdown
from p6_mcp.services.export.xer_subset import build_subset
from p6_mcp.services.mutate.validate import validate

WRITES = ToolAnnotations(
    readOnlyHint=False, destructiveHint=False, idempotentHint=True, openWorldHint=False
)


def register(mcp: MCPServer, ctx: AppContext) -> None:
    """Register export tools."""

    @mcp.tool(title="Export data", annotations=WRITES)
    @tool_errors
    def export_data(
        file_path: str,
        dataset: str = "activities",
        export_format: str = "csv",
        output_path: str | None = None,
        project_id: int | None = None,
        project_short_name: str | None = None,
        table_name: str | None = None,
        name_contains: str | None = None,
        status: list[str] | None = None,
        wbs_path_prefix: str | None = None,
        verbosity: str = "standard",
        preview_rows: int = 5,
    ) -> dict[str, Any]:
        """Write a dataset to a file and return the path plus a small preview.

        dataset: activities, relationships, assignments, wbs, resources,
        calendars, codes, udfs, expenses, projects, or raw_table (with
        `table_name`). export_format: csv, json, xlsx, or markdown.

        Omit `output_path` to auto-name the file inside the server's output
        directory. Basic activity filters are available; for the full filter set
        run get_activities first and export from there.
        """
        sch, projects = ctx.scope(file_path, project_id, project_short_name)
        if dataset not in DATASETS:
            raise InvalidArgumentError(
                f"Unknown dataset {dataset!r}", hint=f"Use one of {DATASETS}"
            )
        flt = None
        if dataset == "activities" and (name_contains or status or wbs_path_prefix):
            flt = build_activity_filter(
                status=status, name_contains=name_contains, wbs_path_prefix=wbs_path_prefix
            )
        rows = build_dataset(sch, projects, dataset, flt, table_name, verbosity)
        suffix = {"csv": "csv", "json": "json", "xlsx": "xlsx", "markdown": "md"}.get(export_format)
        if suffix is None:
            raise InvalidArgumentError(
                f"Unknown export_format {export_format!r}",
                hint="Use csv, json, xlsx, or markdown.",
            )
        target = ctx.workspace.validate_write(output_path or f"{dataset}.{suffix}")
        if export_format == "xlsx":
            to_excel({dataset[:31]: rows}, target)
        else:
            text = {
                "csv": lambda: to_csv(rows),
                "json": lambda: to_json_text(rows),
                "markdown": lambda: to_markdown(rows),
            }[export_format]()
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8")
        return ctx.guard(
            {
                "output_path": str(target),
                "dataset": dataset,
                "format": export_format,
                "rows": len(rows),
                "bytes": target.stat().st_size,
                "preview": rows[:preview_rows],
            }
        )

    @mcp.tool(title="Export workbook", annotations=WRITES)
    @tool_errors
    def export_workbook(
        file_path: str,
        output_path: str | None = None,
        sheets: list[str] | None = None,
        project_id: int | None = None,
        project_short_name: str | None = None,
    ) -> dict[str, Any]:
        """Write a multi-sheet Excel workbook, one sheet per dataset.

        Defaults to activities, relationships, assignments, wbs, and resources.
        Requires the `excel` extra (pip install 'p6-mcp[excel]').
        """
        sch, projects = ctx.scope(file_path, project_id, project_short_name)
        wanted = sheets or ["activities", "relationships", "assignments", "wbs", "resources"]
        data = {}
        for name in wanted:
            if name not in DATASETS:
                raise InvalidArgumentError(
                    f"Unknown dataset {name!r}", hint=f"Use any of {DATASETS}"
                )
            data[name] = build_dataset(sch, projects, name)
        target = ctx.workspace.validate_write(output_path or "schedule.xlsx")
        to_excel(data, target)
        return ctx.guard(
            {
                "output_path": str(target),
                "sheets": {k: len(v) for k, v in data.items()},
                "bytes": target.stat().st_size,
            }
        )

    @mcp.tool(title="Export Gantt (Mermaid)", annotations=READ_ONLY)
    @tool_errors
    def export_gantt_mermaid(
        file_path: str,
        project_id: int | None = None,
        project_short_name: str | None = None,
        max_rows: int = 60,
        group_by_wbs: bool = True,
        wbs_path_prefix: str | None = None,
        status: list[str] | None = None,
        output_path: str | None = None,
    ) -> dict[str, Any]:
        """Render the schedule as a Mermaid gantt diagram.

        Returns the diagram text (renderable in Markdown that supports Mermaid);
        also writes it to a file when `output_path` is given. Critical
        activities carry the `crit` tag, completed `done`, in-progress `active`.
        """
        sch, projects = ctx.scope(file_path, project_id, project_short_name)
        flt = (
            build_activity_filter(status=status, wbs_path_prefix=wbs_path_prefix)
            if (status or wbs_path_prefix)
            else None
        )
        text = gantt_mermaid(sch, projects, flt, max_rows, group_by_wbs)
        out: dict[str, Any] = {"mermaid": text, "lines": len(text.splitlines())}
        if output_path:
            target = ctx.workspace.validate_write(output_path)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8")
            out["output_path"] = str(target)
        return ctx.guard(out)

    @mcp.tool(title="Export network (DOT)", annotations=READ_ONLY)
    @tool_errors
    def export_network_dot(
        file_path: str,
        project_id: int | None = None,
        project_short_name: str | None = None,
        max_nodes: int = 200,
        wbs_path_prefix: str | None = None,
        is_critical: bool | None = None,
        output_path: str | None = None,
    ) -> dict[str, Any]:
        """Render the activity network as Graphviz DOT.

        Feed the result to `dot -Tpng` (or any Graphviz renderer). Nodes are
        coloured by status, critical work is red, milestones are diamonds, and
        non-FS relationships are dashed.
        """
        sch, projects = ctx.scope(file_path, project_id, project_short_name)
        flt = (
            build_activity_filter(wbs_path_prefix=wbs_path_prefix, is_critical=is_critical)
            if (wbs_path_prefix or is_critical is not None)
            else None
        )
        text = network_dot(sch, projects, flt, max_nodes)
        out: dict[str, Any] = {"dot": text}
        if output_path:
            target = ctx.workspace.validate_write(output_path)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8")
            out["output_path"] = str(target)
        return ctx.guard(out)

    @mcp.tool(title="Export milestones (ICS)", annotations=READ_ONLY)
    @tool_errors
    def export_ics_milestones(
        file_path: str,
        project_id: int | None = None,
        project_short_name: str | None = None,
        output_path: str | None = None,
    ) -> dict[str, Any]:
        """Export milestones as an iCalendar feed for Outlook/Google Calendar."""
        sch, projects = ctx.scope(file_path, project_id, project_short_name)
        text = milestones_ics(sch, projects)
        out: dict[str, Any] = {"ics": text, "events": text.count("BEGIN:VEVENT")}
        if output_path:
            target = ctx.workspace.validate_write(output_path)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(text, encoding="utf-8", newline="")
            out["output_path"] = str(target)
        return ctx.guard(out)

    @mcp.tool(title="Export filtered XER", annotations=WRITES)
    @tool_errors
    def export_filtered_xer(
        file_path: str,
        output_path: str,
        project_ids: list[int] | None = None,
        project_short_names: list[str] | None = None,
        wbs_ids: list[int] | None = None,
        include_baselines: bool = True,
    ) -> dict[str, Any]:
        """Write a valid subset XER containing only the selected projects (and
        optionally only some WBS branches).

        Rows that reference dropped activities are removed too, so the result
        imports into P6 cleanly rather than dangling. The output is validated
        before the path is returned.
        """
        sch = ctx.schedule(file_path)
        ids: set[int] = set(project_ids or [])
        for name in project_short_names or []:
            ids.update(p.proj_id for p in sch.resolve_projects(project_short_name=name))
        if not ids:
            ids = {p.proj_id for p in sch.active_projects}
        if include_baselines:
            for b in sch.baseline_projects:
                if b.orig_proj_id in ids:
                    ids.add(b.proj_id)
                if any(
                    sch.projects_by_id[i].sum_base_proj_id == b.proj_id
                    for i in ids
                    if i in sch.projects_by_id
                ):
                    ids.add(b.proj_id)
        task_ids: set[int] | None = None
        if wbs_ids:
            keep: set[int] = set()
            for wid in wbs_ids:
                keep |= sch.wbs_descendant_ids(wid)
            task_ids = {a.task_id for a in sch.activities if a.wbs_id in keep}
        doc, stats = build_subset(sch, ids, task_ids)
        target = ctx.workspace.validate_write(output_path)
        if target.suffix.lower() != ".xer":
            raise ExportError(
                f"{target.name} does not end in .xer",
                hint="Give the output file a .xer extension.",
            )
        XerWriter().write_path(doc, target)
        from p6_mcp.domain.schedule import Schedule

        report = validate(Schedule(doc))
        return ctx.guard(
            {
                "output_path": str(target),
                "bytes": target.stat().st_size,
                "projects": sorted(ids),
                "activities": stats["activities"],
                "tables_filtered": stats["tables"],
                "validation": {
                    "valid": report["valid"],
                    "errors": report["error_count"],
                    "warnings": report["warning_count"],
                },
            }
        )

    _ = (
        export_data,
        export_workbook,
        export_gantt_mermaid,
        export_network_dot,
        export_ics_milestones,
        export_filtered_xer,
    )
