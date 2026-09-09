"""Write-back editing. Every operation is applied to a deep copy of the parsed
document and written to a new file unless the caller explicitly overwrites."""

from p6_mcp.services.mutate.editor import ChangeSummary, ScheduleEditor

__all__ = ["ChangeSummary", "ScheduleEditor"]
