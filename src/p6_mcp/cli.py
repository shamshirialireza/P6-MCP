"""Command-line interface: ``p6-mcp serve|inspect|dcma|diff|export|validate``.

Uses argparse (no extra dependency) so ``uvx p6-mcp`` stays a small install.
All human output goes to stdout *except* under ``serve --transport stdio``,
where stdout is reserved for the MCP protocol and logs go to stderr.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from p6_mcp import __version__
from p6_mcp.config import Settings
from p6_mcp.exceptions import P6McpError
from p6_mcp.logging import configure_logging


def _settings(args: argparse.Namespace) -> Settings:
    """Build Settings from CLI flags, falling back to env/.env defaults."""
    overrides: dict[str, Any] = {}
    dirs = getattr(args, "allowed_dir", None)
    if dirs:
        overrides["allowed_dirs"] = [Path(d) for d in dirs]
    elif getattr(args, "file", None):
        overrides["allowed_dirs"] = [Path(args.file).expanduser().resolve().parent]
    elif getattr(args, "files", None):
        overrides["allowed_dirs"] = list(
            {Path(f).expanduser().resolve().parent for f in args.files}
        )
    for flag, key in (
        ("output_dir", "output_dir"),
        ("cache_size", "cache_size"),
        ("max_output_bytes", "max_output_bytes"),
        ("log_level", "log_level"),
        ("log_json", "log_json"),
        ("encoding", "default_encoding"),
        ("read_only", "read_only"),
    ):
        value = getattr(args, flag, None)
        if value not in (None, False):
            overrides[key] = value
    if getattr(args, "enable_mutation", None) is not None:
        overrides["enable_mutation"] = args.enable_mutation
    return Settings(**overrides)


def _emit(payload: Any, as_json: bool, text: str | None = None) -> None:
    if as_json or text is None:
        print(json.dumps(payload, indent=2, ensure_ascii=False, default=str))
    else:
        print(text)


# ---------------------------------------------------------------------------
# commands
# ---------------------------------------------------------------------------


def cmd_serve(args: argparse.Namespace) -> int:
    """Run the MCP server on the requested transport."""
    settings = _settings(args)
    configure_logging(settings.log_level, settings.log_json)
    from p6_mcp.mcp.server import build_server

    if args.transport != "stdio" and args.enable_mutation is None:
        # Network transports are read-only unless mutation is asked for.
        settings = settings.model_copy(update={"enable_mutation": False})
    mcp = build_server(settings)
    if args.transport == "stdio":
        mcp.run("stdio")
        return 0
    from p6_mcp.transport import run_http

    run_http(
        mcp,
        settings,
        host=args.host,
        port=args.port,
        path=args.path,
        transport=args.transport,
        cors_origins=args.cors_origin,
    )
    return 0


def cmd_inspect(args: argparse.Namespace) -> int:
    """Print a summary of an XER file."""
    from p6_mcp.repository import ScheduleLoader, Workspace

    settings = _settings(args)
    sch = ScheduleLoader(settings, Workspace(settings)).load(args.file)
    from p6_mcp.services.analysis.progress import progress_summary

    projects = sch.active_projects or sch.projects
    prog = progress_summary(sch, projects)
    payload = {
        "file": sch.doc.source_path,
        "encoding": sch.doc.encoding,
        "header": sch.doc.header.to_dict(),
        "tables": {t.name: len(t.rows) for t in sch.doc.tables.values()},
        "projects": [
            {
                "proj_id": p.proj_id,
                "name": p.short_name,
                "baseline": p.is_baseline,
                "data_date": str(p.data_date),
            }
            for p in sch.projects
        ],
        "totals": {
            "activities": len(sch.activities),
            "relationships": len(sch.relationships),
            "resources": len(sch.resources),
            "calendars": len(sch.calendars),
        },
        "percent_complete_duration": prog["percent_complete"]["by_duration"],
        "forecast_finish": str(prog["forecast_finish"]),
        "warnings": sch.doc.warnings,
    }
    lines = [
        f"File:      {payload['file']}",
        f"Encoding:  {sch.doc.encoding}",
        f"P6 version {sch.doc.header.version}  exported {sch.doc.header.export_date}",
        "",
        f"Projects:      {len(sch.projects)} ({len(sch.baseline_projects)} baseline)",
        f"Activities:    {len(sch.activities)}",
        f"Relationships: {len(sch.relationships)}",
        f"Resources:     {len(sch.resources)}",
        f"Calendars:     {len(sch.calendars)}",
        f"Tables:        {len(sch.doc.tables)}",
        "",
        f"% complete (duration): {payload['percent_complete_duration']}%",
        f"Forecast finish:       {payload['forecast_finish']}",
    ]
    if sch.doc.warnings:
        lines += ["", f"Parse warnings: {len(sch.doc.warnings)}"]
        lines += [f"  - {w}" for w in sch.doc.warnings[:5]]
    _emit(payload, args.json, "\n".join(lines))
    return 0


def cmd_dcma(args: argparse.Namespace) -> int:
    """Run the DCMA 14-point assessment from the shell."""
    from p6_mcp.repository import ScheduleLoader, Workspace
    from p6_mcp.services.analysis.dcma import run_dcma_assessment

    settings = _settings(args)
    sch = ScheduleLoader(settings, Workspace(settings)).load(args.file)
    projects = sch.resolve_projects(project_short_name=args.project)
    res = run_dcma_assessment(sch, projects)
    lines = [
        f"DCMA 14-Point Assessment — {projects[0].short_name}",
        f"Data date: {res['data_date']}",
        "",
        f"{'#':>2}  {'Check':<26} {'Result':<7} {'Metric':>9}  Threshold",
        "-" * 72,
    ]
    for c in res["checks"]:
        metric = "-" if c["metric"] is None else f"{c['metric']:.2f}"
        lines.append(
            f"{c['check']:>2}  {c['name']:<26} "
            f"{'PASS' if c['passed'] else 'FAIL':<7} {metric:>9}  {c['threshold']}"
        )
    s = res["summary"]
    lines += ["-" * 72, f"Passed {s['passed']}/14  ({s['score_pct']}%)"]
    failed = [c for c in res["checks"] if not c["passed"]]
    if failed and not args.json:
        lines += ["", "Failures:"]
        for c in failed:
            offenders = ", ".join(map(str, c["offenders"][:6])) or "n/a"
            lines.append(f"  {c['check']}. {c['name']}: {offenders}")
    _emit(res, args.json, "\n".join(lines))
    return 0 if s["failed"] == 0 else 2


def cmd_diff(args: argparse.Namespace) -> int:
    """Compare two XER files."""
    from p6_mcp.repository import ScheduleLoader, Workspace
    from p6_mcp.services.analysis.schedule_diff import diff_schedules

    settings = _settings(args)
    loader = ScheduleLoader(settings, Workspace(settings))
    res = diff_schedules(loader.load(args.current), loader.load(args.previous), args.match)
    s = res["summary"]
    lines = [
        f"Diff: {Path(args.previous).name} -> {Path(args.current).name}",
        "",
        f"Activities added:    {s['activities_added']}",
        f"Activities deleted:  {s['activities_deleted']}",
        f"Activities changed:  {s['activities_changed']}",
        f"Activities progressed: {s['activities_progressed']}",
        f"Relationships added: {s['relationships_added']}",
        f"Relationships removed: {s['relationships_removed']}",
        "",
        f"Data date:  {s['data_date_previous']} -> {s['data_date_current']}",
        f"Finish:     {s['previous_finish']} -> {s['current_finish']}",
    ]
    _emit(res, args.json, "\n".join(lines))
    return 0


def cmd_validate(args: argparse.Namespace) -> int:
    """Structurally validate an XER file."""
    from p6_mcp.repository import ScheduleLoader, Workspace
    from p6_mcp.services.mutate.validate import validate

    settings = _settings(args)
    sch = ScheduleLoader(settings, Workspace(settings)).load(args.file)
    res = validate(sch)
    lines = [
        f"File:   {sch.doc.source_path}",
        f"Valid:  {'yes' if res['valid'] else 'NO'}",
        f"Tables: {res['table_count']}   Rows: {res['row_count']}",
        f"Errors: {res['error_count']}   Warnings: {res['warning_count']}",
    ]
    if res["unknown_tables"]:
        lines.append(f"Unknown tables: {', '.join(res['unknown_tables'])}")
    for kind, items in (("ERROR", res["errors"]), ("WARN", res["warnings"])):
        for item in items[:10]:
            lines.append(f"  [{kind}] {item['message']}")
    _emit(res, args.json, "\n".join(lines))
    return 0 if res["valid"] else 2


def cmd_evm(args: argparse.Namespace) -> int:
    """Calculate Earned Value Management metrics."""
    from datetime import datetime

    from p6_mcp.repository import ScheduleLoader, Workspace
    from p6_mcp.services.analysis.earned_value import earned_value

    settings = _settings(args)
    sch = ScheduleLoader(settings, Workspace(settings)).load(args.file)
    projects = sch.resolve_projects(project_short_name=args.project)

    # Parse as_of date if provided
    as_of = None
    if args.as_of:
        try:
            as_of = datetime.strptime(args.as_of, "%Y-%m-%d")
        except ValueError:
            print(f"error: Invalid date format '{args.as_of}'. Use YYYY-MM-DD.", file=sys.stderr)
            return 1

    res = earned_value(
        sch,
        projects,
        as_of=as_of,
        ev_method=args.ev_method,
        eac_method=args.eac_method,
        time_phased=args.time_phased,
    )
    _emit(res, args.json)
    return 0


def cmd_export(args: argparse.Namespace) -> int:
    """Export a dataset to CSV/JSON/XLSX/Markdown."""
    from p6_mcp.repository import ScheduleLoader, Workspace
    from p6_mcp.services.export.datasets import build_dataset
    from p6_mcp.services.export.tabular import (
        to_csv,
        to_excel,
        to_json_text,
        to_markdown,
    )

    settings = _settings(args)
    workspace = Workspace(settings)
    sch = ScheduleLoader(settings, workspace).load(args.file)
    projects = (
        sch.resolve_projects(project_short_name=args.project)
        if args.project
        else (sch.active_projects or sch.projects)
    )
    rows = build_dataset(sch, projects, args.dataset, table_name=args.table)
    fmt = args.format
    target = workspace.validate_write(
        args.output or f"{args.dataset}.{'md' if fmt == 'markdown' else fmt}"
    )
    if fmt == "xlsx":
        to_excel({args.dataset[:31]: rows}, target)
    else:
        text = {"csv": to_csv, "json": to_json_text, "markdown": to_markdown}[fmt](rows)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text, encoding="utf-8")
    _emit(
        {"output_path": str(target), "rows": len(rows), "format": fmt},
        args.json,
        f"Wrote {len(rows)} rows to {target}",
    )
    return 0


# ---------------------------------------------------------------------------
# parser
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    """The full CLI argument parser."""
    p = argparse.ArgumentParser(
        prog="P6-MCP",
        description="MCP server and CLI for Primavera P6 XER schedule files.",
    )
    p.add_argument("--version", action="version", version=f"p6-mcp {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    def common(sp: argparse.ArgumentParser) -> None:
        sp.add_argument(
            "--allowed-dir",
            action="append",
            help="Directory .xer files may be read from (repeatable).",
        )
        sp.add_argument("--output-dir", help="Directory exports are written to.")
        sp.add_argument("--encoding", help="Force an encoding (cp1252, utf-8, ...).")
        sp.add_argument(
            "--log-level",
            default="WARNING",
            choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        )
        sp.add_argument("--json", action="store_true", help="Emit JSON instead of text.")

    serve = sub.add_parser("serve", help="Run the MCP server.")
    serve.add_argument("--transport", default="stdio", choices=["stdio", "streamable-http", "sse"])
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8000)
    serve.add_argument("--path", default="/mcp", help="HTTP endpoint path.")
    serve.add_argument(
        "--allowed-dir", action="append", help="Directory .xer files may be read from (repeatable)."
    )
    serve.add_argument("--output-dir")
    serve.add_argument("--cache-size", type=int)
    serve.add_argument("--max-output-bytes", type=int)
    serve.add_argument("--encoding")
    serve.add_argument(
        "--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    )
    serve.add_argument("--log-json", action="store_true")
    serve.add_argument(
        "--cors-origin",
        action="append",
        help="Allowed CORS origin for HTTP transports (repeatable).",
    )
    mutation = serve.add_mutually_exclusive_group()
    mutation.add_argument(
        "--enable-mutation",
        dest="enable_mutation",
        action="store_true",
        default=None,
        help="Allow write-back tools (off by default over HTTP).",
    )
    mutation.add_argument(
        "--no-mutation",
        dest="enable_mutation",
        action="store_false",
        help="Disable write-back tools.",
    )
    serve.add_argument(
        "--read-only", action="store_true", help="Hide every tool that writes to disk."
    )
    serve.set_defaults(func=cmd_serve, json=False)

    inspect_p = sub.add_parser("inspect", help="Summarize an XER file.")
    inspect_p.add_argument("file")
    common(inspect_p)
    inspect_p.set_defaults(func=cmd_inspect)

    dcma = sub.add_parser("dcma", help="Run the DCMA 14-point assessment.")
    dcma.add_argument("file")
    dcma.add_argument("--project", help="Project short name to assess.")
    common(dcma)
    dcma.set_defaults(func=cmd_dcma)

    diff = sub.add_parser("diff", help="Compare two XER files.")
    diff.add_argument("current")
    diff.add_argument("previous")
    diff.add_argument("--match", default="short_name", choices=["short_name", "id", "guid"])
    common(diff)
    diff.set_defaults(func=cmd_diff, files=None)

    validate_p = sub.add_parser("validate", help="Validate an XER file.")
    validate_p.add_argument("file")
    common(validate_p)
    validate_p.set_defaults(func=cmd_validate)

    evm_p = sub.add_parser("evm", help="Calculate Earned Value Management metrics.")
    evm_p.add_argument("file")
    evm_p.add_argument("--project", help="Project short name to analyze.")
    evm_p.add_argument(
        "--as-of",
        help="Calculate EVM as of this date (YYYY-MM-DD). Defaults to schedule data date.",
    )
    evm_p.add_argument(
        "--ev-method",
        choices=["from_p6_settings", "physical", "duration", "units", "activity_pct"],
        default="from_p6_settings",
        help="Earned Value calculation method (default: from_p6_settings)",
    )
    evm_p.add_argument(
        "--eac-method",
        choices=["cpi", "spi_cpi", "remaining", "bac_ac_plus_etc"],
        default="cpi",
        help="Estimate at Completion calculation method (default: cpi)",
    )
    evm_p.add_argument(
        "--no-time-phased",
        dest="time_phased",
        action="store_false",
        help="Disable time-phased PV calculation",
    )
    common(evm_p)
    evm_p.set_defaults(func=cmd_evm)

    export = sub.add_parser("export", help="Export a dataset.")
    export.add_argument("file")
    export.add_argument("--dataset", default="activities")
    export.add_argument("--format", default="csv", choices=["csv", "json", "xlsx", "markdown"])
    export.add_argument("--output", help="Output file path.")
    export.add_argument("--project", help="Project short name.")
    export.add_argument("--table", help="Table name when dataset=raw_table.")
    common(export)
    export.set_defaults(func=cmd_export)
    return p


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)
    # `diff` takes two files; make both discoverable to _settings.
    if args.command == "diff":
        args.files = [args.current, args.previous]
    if args.command != "serve":
        configure_logging(getattr(args, "log_level", "WARNING"), False)
    try:
        return int(args.func(args))
    except P6McpError as exc:
        print(f"error: {exc.message}", file=sys.stderr)
        if exc.hint:
            print(f"hint:  {exc.hint}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:  # pragma: no cover
        return 130


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
