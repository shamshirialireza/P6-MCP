# Live P6 EPPM Integration

This document provides guidance on connecting P6-MCP to a live Primavera P6 Enterprise Project Portfolio Management (P6 EPPM) instance via the REST API.

## Prerequisites

Before connecting to a live P6 EPPM instance, ensure you have:

1. **P6 EPPM Web Services/REST deployed** - Version 8.2 or later recommended
2. **User with API access** - A P6 user account with Web Services access enabled
3. **Project privileges** - Appropriate permissions for the projects you wish to access
4. **Network access** - Ability to reach the P6 EPPM server from your client machine

## Connection Setup

### Environment Variables

Configure your connection using environment variables (one set per named connection):

```bash
# Basic connection info
export P6MCP_P6_PROD_BASE_URL="https://p6.example.com:8206/p6ws"
export P6MCP_P6_PROD_DATABASE="PROD"
export P6MCP_P6_PROD_AUTH_MODE="session"  # or "oauth"
export P6MCP_P6_PROD_USERNAME="your_username"
export P6MCP_P6_PROD_PASSWORD="your_password"  # or use keyring

# Optional settings
export P6MCP_P6_PROD_TOKEN_EXP_SECONDS="3600"
export P6MCP_P6_PROD_VERIFY_TLS="true"
export P6MCP_P6_PROD_READ_ONLY="false"
export P6MCP_P6_PROD_ALLOWED_PROJECTS="123,456,789"  # Comma-separated list
export P6MCP_P6_PROD_AUTO_SCHEDULE_AFTER_WRITE="false"
export P6MCP_P6_PROD_REQUIRE_SNAPSHOT="true"
```

### Using connections.yaml (Alternative)

Alternatively, create a `connections.yaml` file:

```yaml
connections:
  prod:
    base_url: "https://p6.example.com:8206/p6ws"
    database: "PROD"
    auth_mode: "session"
    username: "your_username"
    password: "your_password"  # or use: _password_keyring: true
    token_exp_seconds: 3600
    verify_tls: true
    read_only: false
    allowed_projects: [123, 456, 789]
    auto_schedule_after_write: false
    require_snapshot: true
```

## Authentication Modes

P6-MCP supports two authentication methods for P6 EPPM:

### 1. Session Login (On-Prem Default)

```
POST /p6ws/restapi/login?DatabaseName=<db>
Header: authToken: <base64(user:password)>
```

- Default for on-premises P6 EPPM installations
- Persists session cookie/token for subsequent calls
- Automatic re-login on 401 responses
- Requires username/password

### 2. OAuth Bearer (Cloud / Newer Releases)

```
POST /p6ws/oauth/token
Headers: 
  authToken: <base64(user:password)>
  token_exp: <seconds>
  return_json: true
```

Then send: `Authorization: Bearer <token>` on every request

- Used for Oracle Cloud P6 EPPM and newer on-prem releases
- Requires token refresh before expiry
- More suitable for stateless/cloud environments

## First Live Query

To test your connection and run your first query against a live P6 project:

```bash
# List available connections
p6-mcp p6_list_connections

# Test a specific connection
p6-mcp p6_test_connection --connection prod

# List projects in the connection
p6-mcp p6_list_projects --connection prod

# Open a project for analysis
p6-mcp p6_open_project --connection prod --project 123456
# Returns a schedule_id like "sched-abc123"

# Use the schedule_id with any §5 tool
p6-mcp inspect --source sched-abc123
p6-mcp dcma --source sched-abc123
p6-mcp evm --source sched-abc123
```

## First Live Change with Safety Protocol

The live mutation safety protocol ensures safe changes to your P6 EPPM data:

1. **Dry-run first** (default for live sources):
   ```bash
   p6-mcp update_activity --source p6://prod/123456 --task_code A1000 \
     --changes '{"name": "Updated Activity Name"}' --dry_run=true
   ```
   This returns a plan showing what would change without making any modifications.

2. **Review the plan** - Check the returned diff and impact estimate.

3. **Confirm with plan_id** - If satisfied, apply the changes:
   ```bash
   p6-mcp update_activity --source p6://prod/123456 --task_code A1000 \
     --changes '{"name": "Updated Activity Name"}' \
     --confirm=true --plan_id <plan_id_from_dry_run>
   ```

4. **Verify results** - The tool verifies the changes were applied correctly.

## Safety Protocol Details

The live mutation safety protocol (Section 15.4 of build prompt) includes:

### Guards
- Connection not in read-only mode
- Project in ALLOWED_PROJECTS list (if configured)
- Project not checked out by another user
- User has sufficient privileges (verified via no-op PUT or /project/fields)
- P6MCP_ENABLE_MUTATION environment variable set to true

### Plan
- ChangeSet generated in dependency order (WBS before activities, etc.)
- Human-readable diff showing before → after per field
- Impact estimate showing which successors/float may be affected

### Snapshot
- Pre-change snapshot taken via P6 XML export or full REST read
- Stored under `P6MCP_OUTPUT_DIR/snapshots/<connection>/<project>/<timestamp>/`
- Includes ChangeSet JSON for reference

### Apply
- Operations executed in order with retries on transient errors
- Stops at first hard failure and reports partial state
- No silent continuation after failures

### Verify
- Re-read touched objects and diff against intended changes
- Reports any mismatches for manual review

### Post-actions (Optional)
- Automatically run `/job/schedule` (CPM/F9) after successful apply
- Can also trigger level, summarize, or other P6 jobs
- Returns post-schedule deltas showing what actually changed

### Audit
- JSONL audit record appended to `P6MCP_OUTPUT_DIR/audit/`
- Contains: who, when, connection, project, plan, result, job IDs

## Snapshots and Rollback

### Listing Snapshots
```bash
p6-mcp p6_list_snapshots --connection prod --project 123456
```

### Restoring from Snapshot
```bash
p6-mcp p6_restore_snapshot --snapshot_id <snapshot_id> --confirm=true
```
Restores using the inverse ChangeSet via REST (what cannot be undocumented is documented).

## Troubleshooting

### Common Issues

#### 401/403 Authentication Errors
- Verify username/password are correct
- Check that the user has Web Services access enabled in P6
- For OAuth, verify token endpoint is accessible
- Ensure proper domain/user format if required (e.g., "DOMAIN\\username")

#### Checked-out Projects
- Error: "Project is checked out by another user"
- Solution: Have the checking-out user check in the project, or wait for checkout to expire

#### Insufficient Privileges
- Error: "Insufficient privileges for operation"
- Solution: Verify the user has appropriate rights for the target project and objects

#### Connection Timeouts
- Increase timeout settings in your client
- Verify network connectivity to P6 EPPM server
- Check if P6 EPPM Web Services are responsive

#### TLS/SSL Certificate Issues
- Set `P6MCP_P6_<NAME>_VERIFY_TLS=false` for testing (not recommended for production)
- Properly configure certificate trust store

#### Missing REST Endpoints
- Some older P6 EPPM releases may not implement all REST endpoints
- Check release notes for your P6 version
- Fallback to SOAP adapter may be needed for missing objects (documented gap)

## Job Management

P6-MCP provides tools for managing P6 EPPM asynchronous jobs:

### Running Jobs
```bash
# Schedule job (CPM/F9)
p6-mcp p6_run_schedule_job --connection prod --project 123456

# Leveling job
p6-mcp p6_run_level_job --connection prod --project 123456

# Summarize project
p6-mcp p6_run_summarize_job --connection prod --project 123456

# Apply actuals
p6-mcp p6_apply_actuals --connection prod --project 123456 --new_data_date "2026-09-01"

# Store period performance
p6-mcp p6_store_period_performance --connection prod --project 123456 --financial_period "2026-09"
```

### Monitoring Jobs
```bash
# Check job status
p6-mcp p6_get_job_status --connection prod --job_id <job_id>

# Get job log
p6-mcp p6_get_job_log --connection prod --job_id <job_id> --lines 100

# Cancel job
p6-mcp p6_cancel_job --connection prod --job_id <job_id>

# List current jobs
p6-mcp p6_list_jobs --connection prod
```

## Best Practices

1. **Always use dry_run=True first** for live mutations to preview changes
2. **Review snapshots** before making significant changes to critical projects
3. **Monitor audit logs** regularly for live P6 EPPM connections
4. **Keep connections minimal** - only configure connections you actively use
5. **Use least privilege** - configure P6 users with minimum required permissions
6. **Test in non-production** first before connecting to production P6 instances
7. **Monitor job execution** - long-running jobs can affect P6 performance
8. **Backup regularly** - while snapshots help, maintain regular P6 database backups

## Release Notes and Compatibility

P6-MCP aims to maintain compatibility with P6 EPPM versions 8.2 through 22.x. Some features may have limitations in older releases:

| Feature | Min P6 Version | Notes |
|---------|----------------|-------|
| Basic REST connectivity | 8.2 | Core read/write operations |
| OAuth authentication | 18.x | Newer releases only |
| All mutation endpoints | 15.x | Some older releases missing endpoints |
| Job service endpoints | 8.2 | Standard across supported releases |
| Field-level security | 12.x | Respects P6 security profiles |

Consult `docs/concepts/p6-rest-api-notes.md` for detailed release-specific information.