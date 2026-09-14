# P6-MCP

[![PyPI](https://img.shields.io/pypi/v/p6-mcp.svg)](https://pypi.org/project/p6-mcp/)
[![Python](https://img.shields.io/pypi/pyversions/p6-mcp.svg)](https://pypi.org/project/p6-mcp/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://github.com/alirezashamshiri/P6-MCP/blob/main/LICENSE)
[![CI](https://img.shields.io/github/actions/workflow/status/alirezashamshiri/P6-MCP/ci.yml/badge.svg?branch=main)](https://github.com/alirezashamshiri/P6-MCP/actions)
[![Smithery](https://img.shields.io/badge/Smithery-p6--mcp-brightgreen)](https://smithery.ai/@alirezashamshiri/p6-mcp)
[![Docker](https://img.shields.io/badge/Docker-ghcr.io-blue)](https://github.com/alirezashamshiri/P6-MCP/pkgs/container/p6-mcp)

## Primavera P6 MCP Server

A fully featured MCP server for Oracle Primavera P6. Point any MCP-compatible AI client at your XER files or a live P6 EPPM instance and start asking questions in plain language.

---

### ✨ Highlights

- **138 tools across one unified surface** — the same tool works against both XER files and live P6 EPPM with no changes to your prompt
- **Full XER parser** — lossless read and write of Oracle Primavera XER format including all tables, CP1252 encoding, and calendar data
- **DCMA 14-point schedule assessment** — automated compliance check with pass/fail per metric and actionable findings
- **Critical path & float analysis** — forward/backward pass, driving path, near-critical activities, negative float detection
- **Earned Value Management** — CPI, SPI, EAC, TCPI, S-curves, and period performance from XER or live P6
- **Resource utilization** — histogram, leveling report, overallocation detection across all assignments
- **Baseline comparison & schedule diff** — compare any two XER snapshots or XER vs live P6 project
- **Safe mutation by default** — write-back tools are disabled until you set `P6MCP_ENABLE_MUTATION=true`; all mutations require `confirm=True`
- **Three transports** — stdio for desktop clients, Streamable HTTP and SSE for remote/Docker deployments
- **Works with every major MCP client** — Claude Desktop, Cursor, Windsurf, VS Code, Zed, Continue, OpenAI Agents SDK

---

### 🚀 60-Second Quickstart

**Claude Desktop / Claude Code:**
```json
{
  "mcpServers": {
    "p6-mcp": {
      "command": "uvx",
      "args": ["p6-mcp", "serve", "--transport", "stdio"],
      "env": {
        "P6MCP_WORKSPACE_DIRS": "/path/to/your/xer/files"
      }
    }
  }
}
```

**Cursor / Windsurf / VS Code:**
```json
{
  "mcp": {
    "servers": {
      "p6-mcp": {
        "command": "uvx",
        "args": ["p6-mcp", "serve", "--transport", "stdio"],
        "env": { "P6MCP_WORKSPACE_DIRS": "/path/to/your/xer/files" }
      }
    }
  }
}
```

**Docker (HTTP transport):**
```bash
docker run -p 8000:8000 -v /path/to/xer:/data ghcr.io/alirezashamshiri/p6-mcp
```

**CLI:**
```bash
p6-mcp inspect schedule.xer       # table inventory and project list
p6-mcp dcma schedule.xer          # DCMA 14-point report
p6-mcp diff old.xer new.xer       # compare two schedules
p6-mcp export schedule.xer --format xlsx --output report.xlsx
```

---

### 📦 Installation

```bash
# Recommended — no install needed, always latest
uvx p6-mcp

# pip
pip install p6-mcp

# With optional extras (Excel export, charts, HTTP transport)
pip install "p6-mcp[excel,charts,http]"

# Docker
docker pull ghcr.io/alirezashamshiri/p6-mcp:latest
```

---

### 📊 Tool Groups

| Group | Tools |
|-------|-------|
| **File & Workspace** | list_xer_files, open_schedule, validate_xer, get_file_header, get_table_inventory, get_raw_table, clear_cache |
| **Projects & EPS** | get_projects, get_project_detail, get_project_codes, get_schedule_options, get_data_date |
| **WBS** | get_wbs, get_wbs_detail, get_wbs_rollup, get_wbs_budgets, get_wbs_notes, get_wbs_steps |
| **Activities** | get_activities, search_activities, get_activity_detail, get_milestones, get_constraints, get_udfs, get_expenses |
| **Relationships** | get_relationships, get_predecessors, get_successors, get_driving_path, analyze_logic_health |
| **Critical Path** | get_critical_path, get_near_critical, get_float_paths, get_negative_float, get_float_distribution, recompute_cpm |
| **Schedule Quality** | run_dcma_assessment, check_schedule_quality, get_schedule_health_score, get_invalid_dates, get_out_of_sequence |
| **Progress** | get_progress_summary, get_behind_schedule_activities, get_lookahead, get_activity_variances |
| **Resources & Roles** | get_resources, get_roles, get_resource_assignments, analyze_resource_utilization, get_resource_histogram |
| **Cost & EVM** | get_cost_summary, get_cash_flow, get_earned_value, get_earned_value_curve, get_past_period_actuals |
| **Calendars** | get_calendars, get_calendar_detail, calendar_working_days_between, is_working_day, compare_calendars |
| **Baselines** | get_baselines, compare_to_baseline, diff_schedules, get_schedule_trend |
| **Export** | export_data, export_workbook, export_gantt_mermaid, export_network_dot, export_ics_milestones |
| **Mutation** | update_activity, add/remove_relationship, add/delete_activity, assign_resource, write_xer *(opt-in)* |
| **Live P6 EPPM** | p6_list_connections, p6_open_project, p6_run_schedule_job, p6_apply_actuals, p6_create_baseline, +14 more |
| **Meta** | list_capabilities, explain_field, get_enum_values |

---

### 🔌 Backend Support

| Capability | XER Files | Live P6 EPPM |
|------------|:---------:|:------------:|
| Read schedule data | ✅ | ✅ |
| Critical path & float | ✅ | ✅ |
| DCMA 14-point assessment | ✅ | ✅ |
| Earned value & cost | ✅ | ✅ |
| Resource utilization | ✅ | ✅ |
| Baseline comparison | ✅ | ✅ |
| Export (xlsx, csv, Gantt) | ✅ | ✅ |
| Write back / mutate | ✅ | ✅ |
| Schedule & level jobs | ❌ | ✅ |
| Apply actuals | ❌ | ✅ |
| Store period performance | ❌ | ✅ |

---

### ⚙️ Configuration

| Environment Variable | Default | Description |
|---------------------|---------|-------------|
| `P6MCP_WORKSPACE_DIRS` | — | Colon-separated directories containing XER files |
| `P6MCP_OUTPUT_DIR` | `/tmp/p6mcp_output` | Where exports and reports are written |
| `P6MCP_ENABLE_MUTATION` | `false` | Enable write-back tools |
| `P6MCP_AUTH_TOKEN` | — | Bearer token for HTTP transport |
| `P6MCP_CACHE_SIZE` | `10` | Number of schedules to keep in memory |
| `P6MCP_LOG_JSON` | `false` | Emit structured JSON logs |

See `.env.example` for a full template including P6 EPPM connection setup.

---

### 🔒 Security

- XER file access restricted to `P6MCP_WORKSPACE_DIRS` — path traversal blocked
- Mutation disabled by default; requires `P6MCP_ENABLE_MUTATION=true` plus `confirm=True` per call
- HTTP transport supports bearer token auth via `P6MCP_AUTH_TOKEN`
- P6 EPPM credentials never logged

---

### 📄 License

MIT © [Alireza Shamshiri](https://github.com/alirezashamshiri)
