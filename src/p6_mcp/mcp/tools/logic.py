"""§5.5 Relationship and network-logic tools."""

from __future__ import annotations

from typing import Any

from mcp.server.mcpserver import MCPServer

from p6_mcp.mcp.context import AppContext, tool_errors
from p6_mcp.mcp.tools.files import READ_ONLY
from p6_mcp.services.analysis import logic_health as lh
from p6_mcp.services.analysis.critical_path import trace_driving_chain
from p6_mcp.services.query.serialize import activity_to_dict, iso, relationship_to_dict


def register(mcp: MCPServer, ctx: AppContext) -> None:
    """Register relationship and logic tools."""

    @mcp.tool(title="Get relationships", annotations=READ_ONLY)
    @tool_errors
    def get_relationships(
        file_path: str,
        project_id: int | None = None,
        project_short_name: str | None = None,
        task_code: str | None = None,
        pred_type: str | None = None,
        lag_min_hours: float | None = None,
        lag_max_hours: float | None = None,
        only_leads: bool = False,
        only_lags: bool = False,
        only_driving: bool = False,
        inter_project_only: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Query the relationship network (TASKPRED).

        `task_code` returns links on both sides of that activity. `pred_type`
        takes PR_FS / PR_SS / PR_FF / PR_SF. Leads are negative lags.
        """
        sch, projects = ctx.scope(file_path, project_id, project_short_name)
        proj_ids = {p.proj_id for p in projects}
        rels = [r for r in sch.relationships if r.proj_id in proj_ids or r.pred_proj_id in proj_ids]
        if task_code:
            act = sch.resolve_activity(task_code)
            rels = [r for r in rels if r.task_id == act.task_id or r.pred_task_id == act.task_id]
        if pred_type:
            rels = [r for r in rels if r.pred_type == pred_type]
        if lag_min_hours is not None:
            rels = [r for r in rels if r.lag_hours >= lag_min_hours]
        if lag_max_hours is not None:
            rels = [r for r in rels if r.lag_hours <= lag_max_hours]
        if only_leads:
            rels = [r for r in rels if r.is_lead]
        if only_lags:
            rels = [r for r in rels if r.is_lag]
        if inter_project_only:
            rels = [r for r in rels if r.crosses_projects]
        if only_driving:
            rels = [
                r
                for r in rels
                if (p := sch.activities_by_id.get(r.pred_task_id))
                and (s := sch.activities_by_id.get(r.task_id))
                and p.driving_path_flag
                and s.driving_path_flag
            ]
        rels.sort(key=lambda r: (r.pred_task_id, r.task_id))
        return ctx.page(
            rels,
            limit,
            offset,
            render=lambda r: {**relationship_to_dict(sch, r), "all_fields": iso(r.to_dict())},
        )

    @mcp.tool(title="Get predecessors", annotations=READ_ONLY)
    @tool_errors
    def get_predecessors(file_path: str, task_code: str, depth: int = 1) -> dict[str, Any]:
        """Predecessors of an activity, optionally walking back several levels.

        depth=1 is the direct predecessors; higher values walk the chain.
        """
        sch = ctx.schedule(file_path)
        return ctx.guard(_walk(sch, task_code, depth, backward=True))

    @mcp.tool(title="Get successors", annotations=READ_ONLY)
    @tool_errors
    def get_successors(file_path: str, task_code: str, depth: int = 1) -> dict[str, Any]:
        """Successors of an activity, optionally walking forward several levels."""
        sch = ctx.schedule(file_path)
        return ctx.guard(_walk(sch, task_code, depth, backward=False))

    def _walk(sch: Any, task_code: str, depth: int, backward: bool) -> dict[str, Any]:
        root = sch.resolve_activity(task_code)
        seen = {root.task_id}
        levels: list[list[dict[str, Any]]] = []
        frontier = [root.task_id]
        for _ in range(max(1, depth)):
            rows: list[dict[str, Any]] = []
            nxt: list[int] = []
            for tid in frontier:
                rels = (sch.predecessors_of if backward else sch.successors_of).get(tid, [])
                for r in rels:
                    other_id = r.pred_task_id if backward else r.task_id
                    other = sch.activities_by_id.get(other_id)
                    if other is None:
                        continue
                    anchor = sch.activities_by_id.get(tid)
                    rows.append(
                        {
                            "task_code": other.code,
                            "task_name": other.name,
                            "relative_to": anchor.code if anchor else tid,
                            "type": r.short_type,
                            "lag_hours": r.lag_hours,
                            "lag_days": sch.hours_to_days(other, r.lag_hours),
                            "driving": other.driving_path_flag,
                            "status": other.status_label,
                            "start": other.start,
                            "finish": other.finish,
                            "total_float_days": sch.hours_to_days(other, other.total_float_hours),
                        }
                    )
                    if other_id not in seen:
                        seen.add(other_id)
                        nxt.append(other_id)
            levels.append(sorted(rows, key=lambda d: str(d["task_code"])))
            frontier = nxt
            if not frontier:
                break
        key = "predecessors" if backward else "successors"
        return iso(
            {
                "task_code": root.code,
                "task_name": root.name,
                "depth": depth,
                key: levels[0] if levels else [],
                "by_level": {str(i + 1): rows for i, rows in enumerate(levels)},
                "total_reached": len(seen) - 1,
            }
        )

    @mcp.tool(title="Get driving path", annotations=READ_ONLY)
    @tool_errors
    def get_driving_path(
        file_path: str, task_code: str, direction: str = "backward"
    ) -> dict[str, Any]:
        """Trace the chain of driving relationships from an activity.

        `backward` walks to the project start (what is pushing this activity),
        `forward` walks to the finish (what this activity is pushing). Use this
        to explain *why* a date is where it is.
        """
        sch = ctx.schedule(file_path)
        act = sch.resolve_activity(task_code)
        chain = trace_driving_chain(sch, act, direction)
        return ctx.guard(
            {
                "task_code": act.code,
                "direction": direction,
                "chain_length": len(chain),
                "chain": [activity_to_dict(sch, a, "compact") for a in chain],
            }
        )

    @mcp.tool(title="Analyze logic health", annotations=READ_ONLY)
    @tool_errors
    def analyze_logic_health(
        file_path: str, project_id: int | None = None, project_short_name: str | None = None
    ) -> dict[str, Any]:
        """Full network-logic diagnostic: open ends, dangling starts/finishes,
        redundant links, circular logic, out-of-sequence progress, relationship
        type mix, and lead/lag distribution.

        Use before a DCMA run to understand *which* logic defects exist; use
        run_dcma_assessment for the formal pass/fail scoring.
        """
        sch, projects = ctx.scope(file_path, project_id, project_short_name)
        res = lh.analyze_logic_health(sch, projects)
        return ctx.guard(
            {
                "activity_count": res["activity_count"],
                "incomplete_count": res["incomplete_count"],
                "open_ends": {
                    "no_predecessors": [
                        activity_to_dict(sch, a, "compact")
                        for a in res["open_ends"]["no_predecessors"]
                    ],
                    "no_successors": [
                        activity_to_dict(sch, a, "compact")
                        for a in res["open_ends"]["no_successors"]
                    ],
                },
                "dangling": {
                    "finish_dangles_ss_only": [a.code for a in res["dangling"]["finish_dangles"]],
                    "start_dangles_ff_only": [a.code for a in res["dangling"]["start_dangles"]],
                },
                "redundant_relationships": res["redundant"],
                "circular_logic": res["circular"],
                "out_of_sequence": res["out_of_sequence"],
                "relationship_mix": res["relationship_mix"],
            }
        )

    @mcp.tool(title="Get relationship type summary", annotations=READ_ONLY)
    @tool_errors
    def get_relationship_type_summary(
        file_path: str, project_id: int | None = None, project_short_name: str | None = None
    ) -> dict[str, Any]:
        """Counts and percentages of FS/SS/FF/SF links, leads, lags, and
        cross-project links. DCMA expects FS >= 90%."""
        sch, projects = ctx.scope(file_path, project_id, project_short_name)
        return ctx.guard(lh.relationship_mix(sch, sch.activities_of(projects)))

    @mcp.tool(title="Get out of sequence", annotations=READ_ONLY)
    @tool_errors
    def get_out_of_sequence(
        file_path: str,
        project_id: int | None = None,
        project_short_name: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Activities that progressed before their predecessor logic allowed.

        Out-of-sequence progress makes remaining forecasts unreliable because
        P6's retained-logic pass no longer reflects how the work actually ran.
        """
        sch, projects = ctx.scope(file_path, project_id, project_short_name)
        rows = lh.out_of_sequence(sch, sch.activities_of(projects))
        return ctx.page(rows, limit, offset)

    _ = (
        get_relationships,
        get_predecessors,
        get_successors,
        get_driving_path,
        analyze_logic_health,
        get_relationship_type_summary,
        get_out_of_sequence,
    )
