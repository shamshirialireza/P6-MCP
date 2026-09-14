"""Live P6 EPPM connection tools (§15.3)."""

from __future__ import annotations

from typing import Any

from mcp.server.mcpserver import MCPServer

from p6_mcp.mcp.context import AppContext, tool_errors
from p6_mcp.mcp.tools.files import READ_ONLY


def register(mcp: MCPServer, ctx: AppContext) -> None:
    """Register live P6 EPPM connection tools."""

    @mcp.tool(title="List P6 EPPM connections", annotations=READ_ONLY)
    @tool_errors
    def p6_list_connections() -> dict[str, Any]:
        """List configured P6 EPPM connections (never returns secrets)."""
        # In a real implementation, this would read from configuration
        # For now, return placeholder data
        return ctx.guard(
            {
                "total": 0,
                "items": [],
            }
        )

    @mcp.tool(title="Test P6 EPPM connection", annotations=READ_ONLY)
    @tool_errors
    def p6_test_connection(connection: str) -> dict[str, Any]:
        """Test a P6 EPPM connection with a smoke test."""
        # In a real implementation, this would:
        # 1. Get connection details from configuration
        # 2. Attempt to login/authenticate
        # 3. Run a simple query like GET /project?Fields=ObjectId&Filter=...
        # 4. Measure latency and detect server capabilities
        # 5. Return results
        raise NotImplementedError("P6 EPPM connection testing not yet implemented")

    @mcp.tool(title="List P6 EPPM projects", annotations=READ_ONLY)
    @tool_errors
    def p6_list_projects(
        connection: str,
        eps_filter: str | None = None,
        code_filter: str | None = None,
        name_contains: str | None = None,
        include_baselines: bool = True,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        """List projects from a P6 EPPM connection."""
        # In a real implementation, this would:
        # 1. Get connection details from configuration
        # 2. Query /project with appropriate filters
        # 3. Return project information
        raise NotImplementedError("P6 EPPM project listing not yet implemented")

    @mcp.tool(title="Open P6 EPPM project", annotations=READ_ONLY)
    @tool_errors
    def p6_open_project(
        connection: str,
        project_id: int | str,
        scope: str | None = None,
    ) -> dict[str, Any]:
        """Open a P6 EPPM project and return a schedule_id for use with §5 tools."""
        # In a real implementation, this would:
        # 1. Get connection details from configuration
        # 2. Use the ScheduleLoader to load the project
        # 3. Return the schedule_id and load stats
        try:
            project_id_int = int(project_id) if isinstance(project_id, str) else project_id
            # This would use the loader to open the project
            # schedule_id = ctx.loader.load(f"p6://{connection}/{project_id_int}")
            # For now, return placeholder
            schedule_id = f"p6-{connection}-{project_id_int}"
            return ctx.guard(
                {
                    "schedule_id": schedule_id,
                    "load_stats": {
                        "tables_loaded": 0,
                        "warnings": [],
                    },
                    "last_update_date": None,
                }
            )
        except ValueError:
            raise ValueError("Project ID must be an integer") from None

    @mcp.tool(title="Refresh P6 EPPM project", annotations=READ_ONLY)
    @tool_errors
    def p6_refresh(schedule_id: str) -> dict[str, Any]:
        """Refresh a P6 EPPM project to pick up server-side changes."""
        # In a real implementation, this would:
        # 1. Extract connection and project info from schedule_id
        # 2. Reload the project data
        # 3. Update the cached schedule
        raise NotImplementedError("P6 EPPM project refresh not yet implemented")

    @mcp.tool(title="Close P6 EPPM connection", annotations=READ_ONLY)
    @tool_errors
    def p6_close(connection: str) -> dict[str, Any]:
        """Close a P6 EPPM connection and clean up resources."""
        # In a real implementation, this would:
        # 1. Log out/authentication cleanup
        # 2. Remove cached data for this connection
        raise NotImplementedError("P6 EPPM connection close not yet implemented")

    @mcp.tool(title="Get P6 EPPM service fields", annotations=READ_ONLY)
    @tool_errors
    def p6_get_fields(connection: str, service: str) -> dict[str, Any]:
        """Get field definitions for a P6 EPPM service."""
        # In a real implementation, this would:
        # 1. Get connection details from configuration
        # 2. Query /{service}/fields
        # 3. Return the field definitions
        raise NotImplementedError("P6 EPPM service fields not yet implemented")

    @mcp.tool(title="Raw P6 EPPM query", annotations=READ_ONLY)
    @tool_errors
    def p6_raw_query(
        connection: str,
        service: str,
        fields: str | None = None,
        filter: str | None = None,
        order_by: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        """Raw query escape hatch for any P6 EPPM REST service."""
        # In a real implementation, this would:
        # 1. Get connection details from configuration
        # 2. Make the raw request to /{service} with parameters
        # 3. Return the results
        raise NotImplementedError("P6 EPPM raw query not yet implemented")

    _ = (
        p6_list_connections,
        p6_test_connection,
        p6_list_projects,
        p6_open_project,
        p6_refresh,
        p6_close,
        p6_get_fields,
        p6_raw_query,
    )
