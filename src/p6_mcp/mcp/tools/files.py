"""§5.1 File and workspace tools."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from mcp.server.mcpserver import MCPServer
from mcp.types import ToolAnnotations

from p6_mcp.exceptions import NotFoundError
from p6_mcp.mcp.context import AppContext, tool_errors
from p6_mcp.parser.reader import XerReader
from p6_mcp.services.export.datasets import build_dataset
from p6_mcp.services.mutate.validate import validate

READ_ONLY = ToolAnnotations(
    readOnlyHint=True, destructiveHint=False, idempotentHint=True, openWorldHint=False
)


def register(mcp: MCPServer, ctx: AppContext) -> None:
    """Register file and workspace tools."""

    @mcp.tool(title="List XER files", annotations=READ_ONLY)
    @tool_errors
    def list_xer_files(directory: str | None = None, recursive: bool = False) -> dict[str, Any]:
        """Discover .xer files in the server's allowed directories.

        Use this first when you don't know which schedule files are available.
        Returns each file's size, modification time, and a quick header peek
        (P6 version, export date, project count) without fully parsing it.
        """
        out: list[dict[str, Any]] = []
        for path in ctx.workspace.discover(directory, recursive):
            stat = path.stat()
            entry: dict[str, Any] = {
                "file_path": str(path),
                "name": path.name,
                "size_bytes": stat.st_size,
                "modified": datetime.fromtimestamp(stat.st_mtime),
            }
            try:
                head = path.read_bytes()[:4096]
                text = head.decode("cp1252", errors="replace")
                first = text.split("\n", 1)[0].split("\t")
                if first and first[0] == "ERMHDR":
                    entry["p6_version"] = first[1] if len(first) > 1 else None
                    entry["export_date"] = first[2] if len(first) > 2 else None
                    entry["currency"] = first[7] if len(first) > 7 else None
            except OSError as exc:
                entry["header_error"] = str(exc)
            out.append(entry)
        return ctx.guard(
            {
                "total": len(out),
                "directories": [str(d) for d in ctx.workspace.allowed],
                "items": out,
            }
        )

    @mcp.tool(title="Open schedule", annotations=READ_ONLY)
    @tool_errors
    def open_schedule(file_path: str, encoding: str | None = None) -> dict[str, Any]:
        """Parse and cache an XER file, returning a reusable schedule_id.

        Pass the returned schedule_id as `file_path` to any other tool to skip
        re-parsing. Use this when you plan several queries against one file.
        Encoding is auto-detected (cp1252/utf-8/utf-16) unless you override it.
        """
        sch = ctx.schedule(file_path, encoding)
        return ctx.guard(
            {
                "schedule_id": sch.schedule_id,
                "source_path": sch.doc.source_path,
                "encoding": sch.doc.encoding,
                "header": sch.doc.header.to_dict(),
                "tables": {t.name: len(t.rows) for t in sch.doc.tables.values()},
                "project_count": len(sch.projects),
                "activity_count": len(sch.activities),
                "parse_warnings": sch.doc.warnings,
            }
        )

    @mcp.tool(
        title="Close schedule",
        annotations=ToolAnnotations(
            readOnlyHint=False, destructiveHint=False, idempotentHint=True, openWorldHint=False
        ),
    )
    @tool_errors
    def close_schedule(schedule_id: str) -> dict[str, Any]:
        """Drop a cached schedule, freeing its memory. The file is untouched."""
        return {"schedule_id": schedule_id, "closed": ctx.loader.close(schedule_id)}

    @mcp.tool(
        title="Clear cache",
        annotations=ToolAnnotations(
            readOnlyHint=False, destructiveHint=False, idempotentHint=True, openWorldHint=False
        ),
    )
    @tool_errors
    def clear_cache() -> dict[str, Any]:
        """Drop every cached schedule. Files on disk are untouched."""
        return {"cleared": ctx.loader.clear()}

    @mcp.tool(title="Get file header", annotations=READ_ONLY)
    @tool_errors
    def get_file_header(file_path: str) -> dict[str, Any]:
        """Return the ERMHDR line: P6 version, export date, user, database, currency.

        Cheaper than open_schedule when you only need provenance.
        """
        sch = ctx.schedule(file_path)
        return ctx.guard(
            {
                "file_path": sch.doc.source_path,
                "encoding": sch.doc.encoding,
                **sch.doc.header.to_dict(),
            }
        )

    @mcp.tool(title="Get table inventory", annotations=READ_ONLY)
    @tool_errors
    def get_table_inventory(file_path: str) -> dict[str, Any]:
        """List every table in the file with row and field counts.

        Includes tables p6-mcp does not model explicitly (flagged known=false),
        which you can still read with get_raw_table.
        """
        sch = ctx.schedule(file_path)
        inv = sch.doc.inventory()
        return ctx.guard(
            {
                "table_count": len(inv),
                "total_rows": sum(t["rows"] for t in inv),
                "unknown_tables": [t["table"] for t in inv if not t["known"]],
                "items": sorted(inv, key=lambda t: str(t["table"])),
            }
        )

    @mcp.tool(title="Get raw table", annotations=READ_ONLY)
    @tool_errors
    def get_raw_table(
        file_path: str,
        table_name: str,
        limit: int = 100,
        offset: int = 0,
        fields: list[str] | None = None,
    ) -> dict[str, Any]:
        """Read raw rows from ANY table, including ones with no dedicated tool.

        This is the escape hatch: prefer the typed tools (get_activities,
        get_resources, ...) when one exists, because they decode enums, resolve
        names, and convert durations to days.
        """
        sch = ctx.schedule(file_path)
        table = sch.doc.table(table_name)
        if table is None:
            raise NotFoundError(
                f"No table {table_name!r} in this file",
                hint="Call get_table_inventory to list available tables.",
            )
        rows = build_dataset(sch, [], "raw_table", table_name=table_name)
        if fields:
            rows = [{k: v for k, v in r.items() if k in fields} for r in rows]
        return ctx.page(rows, limit, offset, extra={"table": table.name, "fields": table.fields})

    @mcp.tool(title="Validate XER", annotations=READ_ONLY)
    @tool_errors
    def validate_xer(file_path: str) -> dict[str, Any]:
        """Structurally validate a file: orphan references, duplicate keys,
        unknown tables, impossible dates, and calendar problems.

        Run this before trusting analytics on an unfamiliar file, and after any
        mutation. Never fails on bad data — problems come back as a report.
        """
        sch = ctx.schedule(file_path)
        return ctx.guard(validate(sch))

    @mcp.tool(title="Parse XER file", annotations=READ_ONLY)
    @tool_errors
    def parse_xer_file(file_path: str) -> dict[str, Any]:
        """One-call overview of a schedule file: header, table inventory,
        project list with status breakdowns, and totals.

        Good opening move on an unfamiliar file; follow with get_activities or
        get_schedule_summary for detail.
        """
        sch = ctx.schedule(file_path)
        projects = []
        for p in sch.projects:
            acts = [a for a in sch.activities if a.proj_id == p.proj_id]
            projects.append(
                {
                    "proj_id": p.proj_id,
                    "proj_short_name": p.short_name,
                    "is_baseline": p.is_baseline,
                    "data_date": p.data_date,
                    "activity_count": len(acts),
                    "status_counts": {
                        "completed": sum(1 for a in acts if a.is_completed),
                        "in_progress": sum(1 for a in acts if a.is_in_progress),
                        "not_started": sum(1 for a in acts if a.is_not_started),
                    },
                }
            )
        return ctx.guard(
            {
                "file_path": sch.doc.source_path,
                "schedule_id": sch.schedule_id,
                "encoding": sch.doc.encoding,
                "header": sch.doc.header.to_dict(),
                "tables": {t.name: len(t.rows) for t in sch.doc.tables.values()},
                "projects": projects,
                "totals": {
                    "projects": len(sch.projects),
                    "activities": len(sch.activities),
                    "relationships": len(sch.relationships),
                    "resources": len(sch.resources),
                    "assignments": len(sch.assignments),
                    "calendars": len(sch.calendars),
                    "wbs_nodes": len(sch.wbs_nodes),
                },
                "parse_warnings": sch.doc.warnings,
            }
        )

    _ = (
        list_xer_files,
        open_schedule,
        close_schedule,
        clear_cache,
        get_file_header,
        get_table_inventory,
        get_raw_table,
        validate_xer,
        parse_xer_file,
    )


def peek_header(path: str) -> dict[str, Any]:
    """Header fields without a full parse (used by the CLI)."""
    doc = XerReader().read_path(path)
    return doc.header.to_dict()
