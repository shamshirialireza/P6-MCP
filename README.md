# P6-MCP

[![PyPI](https://img.shields.io/pypi/v/p6-mcp.svg)](https://pypi.org/project/p6-mcp/)
[![Python](https://img.shields.io/pypi/pyversions/p6-mcp.svg)](https://pypi.org/project/p6-mcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/alirezashamshiri/P6-MCP/blob/main/LICENSE)
[![CI](https://img.shields.io/github/actions/workflow/status/alirezashamshiri/P6-MCP/ci.yml/badge.svg?branch=main)](https://github.com/alirezashamshiri/P6-MCP/actions)
[![Smithery](https://img.shields.io/badge/Smithery-p6--mcp-brightgreen)](https://smithery.ai/@alirezashamshiri/p6-mcp)
[![Docker](https://img.shields.io/badge/Docker-ghcr.io-blue)](https://github.com/alirezashamshiri/P6-MCP/pkgs/container/p6-mcp)

## Primavera P6 MCP Server

An object-oriented, fully featured MCP server for Oracle Primavera P6 that works against two backends through one identical tool surface: (a) `.xer` schedule files on disk, and (b) a live P6 EPPM instance via the P6 EPPM REST API.

### 🚀 60-Second Quickstart

**Claude Desktop/Claude Code:**
```bash
# Install
uvx p6-mcp

# Configure (Claude Desktop)
# Add to claude_desktop_config.json:
# "p6-mcp": {
#   "command": "uvx",
#   "args": ["p6-mcp", "serve", "--transport", "stdio"]
# }

# Use
p6-mcp inspect tests/fixtures/xer/demo.xer
```

**Cursor/Windsurf/VS Code/Zed/Continue:**
See [client documentation](docs/clients/) for copy-paste configurations.

### 📊 Feature Matrix

| Tool Group | Capabilities |
|------------|--------------|
| **File & Workspace** | ✅ list_xer_files, open_schedule, validate_xer, get_file_header |
| **Projects & EPS** | ✅ get_projects, get_project_detail, get_project_codes |
| **WBS** | ✅ get_wbs, get_wbs_detail, get_wbs_rollup, get_wbs_budgets |
| **Activities** | ✅ get_activities, search_activities, get_activity_detail, get_milestones |
| **Relationships** | ✅ get_relationships, get_predecessors, get_successors, get_driving_path |
| **Critical Path** | ✅ get_critical_path, get_near_critical, get_float_paths, recompute_cpm |
| **Schedule Quality** | ✅ run_dcma_assessment, check_schedule_quality, get_schedule_health_score |
| **Progress** | ✅ get_progress_summary, get_behind_schedule_activities, get_lookahead |
| **Resources** | ✅ get_resources, get_resource_detail, get_resource_rates, analyze_resource_utilization |
| **Cost & EVM** | ✅ get_cost_summary, get_cash_flow, get_earned_value, get_financial_periods |
| **Calendars** | ✅ get_calendars, get_calendar_detail, calendar_working_days_between |
| **Baselines** | ✅ get_baselines, compare_to_baseline, diff_schedules, get_schedule_trend |
| **Reports** | ✅ generate_report, get_schedule_summary, parse_xer_file |
| **Export** | ✅ export_data, export_workbook, export_gantt_mermaid, export_filtered_xer |
| **Mutation** | ✅ update_activity, add/remove_relationship, add/delete_activity, assign_resource *(requires confirm=True)* |
| **Live P6 EPPM** | ✅ p6_list_connections, p6_open_project, p6_run_schedule_job, p6_create_baseline |

### 🔌 Capability Matrix (XER vs Live P6 EPPM)

| Tool Category | Tool | XER Backend | Live P6 EPPM Backend | Notes |
|---------------|------|-------------|----------------------|-------|
| **File & Workspace** | list_xer_files | ✅ | ❌ | Live backend only |
|  | open_schedule | ✅ | ✅ |  |
|  | validate_xer | ✅ | ❌ | Live backend only |
|  | get_file_header | ✅ | ❌ | Live backend only |
| **Projects & EPS** | get_projects | ✅ | ✅ |  |
|  | get_project_detail | ✅ | ✅ |  |
|  | get_project_codes | ✅ | ✅ |  |
| **WBS** | get_wbs | ✅ | ✅ |  |
|  | get_wbs_detail | ✅ | ✅ |  |
|  | get_wbs_rollup | ✅ | ✅ |  |
|  | get_wbs_budgets | ✅ | ✅ |  |
| **Activities** | get_activities | ✅ | ✅ |  |
|  | search_activities | ✅ | ✅ |  |
|  | get_activity_detail | ✅ | ✅ |  |
|  | get_milestones | ✅ | ✅ |  |
|  | get_activity_codes | ✅ | ✅ |  |
|  | get_activity_code_assignments | ✅ | ✅ |  |
|  | get_udfs | ✅ | ✅ |  |
|  | get_activity_steps | ✅ | ✅ |  |
|  | get_activity_notes | ✅ | ✅ |  |
|  | get_activity_documents | ✅ | ✅ |  |
|  | get_activity_feedback | ✅ | ✅ |  |
| **Relationships** | get_relationships | ✅ | ✅ |  |
|  | get_predecessors | ✅ | ✅ |  |
|  | get_successors | ✅ | ✅ |  |
|  | get_driving_path | ✅ | ✅ |  |
|  | get_relationship_type_summary | ✅ | ✅ |  |
|  | analyze_logic_health | ✅ | ✅ |  |
| **Critical Path** | get_critical_path | ✅ | ✅ |  |
|  | get_near_critical | ✅ | ✅ |  |
|  | get_float_paths | ✅ | ✅ |  |
|  | get_negative_float | ✅ | ✅ |  |
|  | get_float_distribution | ✅ | ✅ |  |
|  | recompute_cpm | ✅ | ✅ |  |
| **Schedule Quality** | run_dcma_assessment | ✅ | ✅ |  |
|  | check_schedule_quality | ✅ | ✅ |  |
|  | get_schedule_health_score | ✅ | ✅ |  |
|  | get_invalid_dates | ✅ | ✅ |  |
|  | get_out_of_sequence | ✅ | ✅ |  |
| **Progress** | get_progress_summary | ✅ | ✅ |  |
|  | get_behind_schedule_activities | ✅ | ✅ |  |
|  | get_lookahead | ✅ | ✅ |  |
|  | get_status_update_check | ✅ | ✅ |  |
|  | get_activity_variances | ✅ | ✅ |  |
| **Resources** | get_resources | ✅ | ✅ |  |
|  | get_resource_detail | ✅ | ✅ |  |
|  | get_resource_rates | ✅ | ✅ |  |
|  | get_resource_codes | ✅ | ✅ |  |
|  | get_resource_curves | ✅ | ✅ |  |
|  | analyze_resource_utilization | ✅ | ✅ |  |
|  | get_resource_histogram | ✅ | ✅ |  |
|  | get_resource_leveling_report | ✅ | ✅ |  |
| **Cost & EVM** | get_cost_summary | ✅ | ✅ |  |
|  | get_cash_flow | ✅ | ✅ |  |
|  | get_earned_value | ✅ | ✅ |  |
|  | get_earned_value_curve | ✅ | ✅ |  |
|  | get_financial_periods | ✅ | ✅ |  |
|  | get_past_period_actuals | ✅ | ✅ |  |
| **Calendars** | get_calendars | ✅ | ✅ |  |
|  | get_calendar_detail | ✅ | ✅ |  |
|  | calendar_working_days_between | ✅ | ✅ |  |
|  | calendar_add_working_days | ✅ | ✅ |  |
|  | is_working_day | ✅ | ✅ |  |
|  | compare_calendars | ✅ | ✅ |  |
| **Baselines** | get_baselines | ✅ | ✅ |  |
|  | compare_to_baseline | ✅ | ✅ |  |
|  | create_baseline_copy | ✅ | ✅ |  |
|  | assign_project_baseline | ✅ | ✅ |  |
| **Reports** | generate_report | ✅ | ✅ |  |
|  | get_schedule_summary | ✅ | ✅ |  |
|  | parse_xer_file | ✅ | ✅ |  |
| **Export** | export_data | ✅ | ✅ |  |
|  | export_workbook | ✅ | ✅ |  |
|  | export_gantt_mermaid | ✅ | ✅ |  |
|  | export_network_dot | ✅ | ✅ |  |
|  | export_ics_milestones | ✅ | ✅ |  |
|  | export_filtered_xer | ✅ | ✅ |  |
| **Mutation** | update_activity | ✅ | ✅ | Requires confirm=True |
|  | bulk_update_activities | ✅ | ✅ | Requires confirm=True |
|  | add_relationship | ✅ | ✅ | Requires confirm=True |
|  | remove_relationship | ✅ | ✅ | Requires confirm=True |
|  | update_relationship | ✅ | ✅ | Requires confirm=True |
|  | add_activity | ✅ | ✅ | Requires confirm=True |
|  | delete_activity | ✅ | ✅ | Requires confirm=True |
|  | update_project | ✅ | ✅ | Requires confirm=True |
|  | assign_resource | ✅ | ✅ | Requires confirm=True |
|  | remove_assignment | ✅ | ✅ | Requires confirm=True |
|  | update_assignment | ✅ | ✅ | Requires confirm=True |
|  | set_activity_code | ✅ | ✅ | Requires confirm=True |
|  | set_udf_value | ✅ | ✅ | Requires confirm=True |
|  | apply_progress | ✅ | ✅ | Requires confirm=True |
|  | create_baseline_copy | ✅ | ✅ | Requires confirm=True |
|  | merge_xer_files | ✅ | ✅ | Requires confirm=True |
|  | split_xer_by_project | ✅ | ✅ | Requires confirm=True |
|  | write_xer | ✅ | ❌ | Live backend only |
| **Live P6 EPPM Only** | p6_list_connections | ❌ | ✅ |  |
|  | p6_test_connection | ❌ | ✅ |  |
|  | p6_list_projects | ❌ | ✅ |  |
|  | p6_open_project | ❌ | ✅ |  |
|  | p6_refresh | ❌ | ✅ |  |
|  | p6_close | ❌ | ✅ |  |
|  | p6_get_fields | ❌ | ✅ |  |
|  | p6_raw_query | ❌ | ✅ |  |
|  | p6_run_schedule_job | ❌ | ✅ |  |
|  | p6_run_level_job | ❌ | ✅ |  |
|  | p6_run_summarize_job | ❌ | ✅ |  |
|  | p6_apply_actuals | ❌ | ✅ |  |
|  | p6_store_period_performance | ❌ | ✅ |  |
|  | p6_update_baseline_job | ❌ | ✅ |  |
|  | p6_schedule_check | ❌ | ✅ |  |
|  | p6_get_job_status | ❌ | ✅ |  |
|  | p6_get_job_log | ❌ | ✅ |  |
|  | p6_cancel_job | ❌ | ✅ |  |
|  | p6_list_jobs | ❌ | ✅ |  |
|  | p6_create_baseline | ⚠️ | ✅ |  |
|  | p6_assign_project_baseline | ⚠️ | ✅ |  |
|  | p6_export_project | ⚠️ | ✅ |  |
|  | p6_import_project | ⚠️ | ✅ |  |
|  | p6_update_project_data_date | ⚠️ | ✅ |  |
|  | p6_checkout_status | ⚠️ | ✅ |  |
|  | p6_global_change_preview | ⚠️ | ✅ |  |
|  | p6_compare_live_to_xer | ⚠️ | ✅ |  |
|  | p6_watch_project | ⚠️ | ✅ |  |

*Footnotes:*
- *Live P6 EPPM backend capabilities may vary depending on P6 EPPM release and configured permissions*
- *Some older P6 EPPM releases may not implement all REST endpoints (marked with ⚠️ in detailed documentation)*
- *Mutation tools require explicit `confirm=True` parameter for live P6 EPPM backend*
- *XER backend supports all tools unless specifically noted as "Live backend only"*
- *Live P6 EPPM backend supports all standard tools unless specifically noted as "Live P6 EPPM only"*

### 🏗️ Architecture