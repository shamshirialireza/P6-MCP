# ADR 0003: Changeset/Snapshot Safety Model

## Status
Accepted

## Context
We need to safely modify schedule data in live P6 EPPM environments. Direct modifications risk data corruption, unintended side effects, and make it difficult to verify changes were applied correctly.

Options considered:
1. Direct modification (read-modify-write without safeguards)
2. Changeset-based approach with planning and verification
3. Database transaction rollback (not applicable due to no direct DB access)
4. Event sourcing / command query responsibility segregation (CQRS)

## Decision
We chose a changeset-based safety model with snapshots, inspired by database migration patterns and software transactional memory.

## Rationale
### Why Changeset/Snapshot Model:
1. **Safety First**: Mandatory dry-run preview allows review before any changes
2. **Atomicity**: All-or-nothing application prevents partial updates
3. **Auditability**: Complete record of what was intended vs what was applied
4. **Rollback Capability**: Snapshots enable returning to known good state
5. **Concurrency Safety**: Optimistic locking prevents lost updates
6. **User Control**: Explicit confirmation step puts user in charge
7. **Compliance**: Matches requirements in build prompt Section 15.4

### Why Not Direct Modification:
- No safety net for mistakes
- Difficult to verify changes were applied correctly
- No audit trail
- Risk of partial failures leaving data in inconsistent state
- Cannot easily revert changes

### Why Not Database Transactions:
- No direct database access permitted (unsupported by Oracle)
- Would bypass P6 application layer business rules
- Not feasible given architecture constraints

### Why Not Pure Event Sourcing:
- Overly complex for this use case
- Would require significant re-architecture
- Changeset/snapshot provides sufficient safety with simpler implementation

## Consequences
### Positive
- Safe modification of live P6 EPPM data
- Clear audit trail of all changes
- Ability to review and approve changes before application
- Rollback capability via snapshots
- Protection against concurrent modification conflicts
- Matches enterprise expectations for change management

### Negative
- Increased complexity in mutation tools
- Additional storage required for snapshots
- Slightly longer execution time due to planning/verification steps
- Need to manage snapshot lifecycle and cleanup

## Implementation Plan
The safety protocol consists of 10 steps (build prompt Section 15.4):

1. **Guards** - Pre-flight checks:
   - Connection not read-only
   - Project in ALLOWED_PROJECTS (if configured)
   - Project not checked out by another user
   - User has sufficient privileges
   - P6MCP_ENABLE_MUTATION=true

2. **Plan** - Create ChangeSet:
   - ScheduleEditor computes exact list of REST operations
   - Operations ordered by dependency (WBS before activities, etc.)
   - Human-readable diff generated (before → after per field)
   - Impact estimate calculated (which successors/float may move)

3. **Dry-run** - Preview only:
   - Return plan without applying changes
   - Default `dry_run=True` for live sources
   - User reviews plan and impact

4. **Confirm** - Explicit approval:
   - Require `confirm=True` AND valid `plan_id`
   - Plan expires after N minutes or if touched objects changed
   - Optimistic concurrency via LastUpdateDate checking

5. **Snapshot** - Pre-change backup:
   - Take snapshot via P6 XML export or full REST read
   - Store under `P6MCP_OUTPUT_DIR/snapshots/<connection>/<project>/<timestamp>/`
   - Save ChangeSet JSON with snapshot

6. **Apply** - Execute changes:
   - Execute operations in dependency order with retries
   - Stop at first hard failure, report partial state
   - Never silently continue after errors

7. **Verify** - Post-application check:
   - Re-read touched objects
   - Diff against intended changes
   - Report any mismatches

8. **Post-actions** (Optional):
   - Automatically run `/job/schedule` (CPM/F9) if desired
   - Can trigger level, summarize, or other P6 jobs
   - Return post-schedule deltas showing what changed

9. **Audit** - Permanent record:
   - Append JSONL audit record to `P6MCP_OUTPUT_DIR/audit/`
   - Contains: who, when, connection, project, plan, result, job IDs

10. **Idempotency** - Safe re-application:
    - Re-applying already-applied plan is no-op
    - Clear message indicating no changes needed

## Related Components
- `services/mutate/editor.py` - ScheduleEditor computes ChangeSets
- `repository/p6eppm/changeset.py` - ChangeSet / ChangePlan implementations
- `repository/p6eppm/snapshots.py` - Snapshot creation and restoration
- `repository/p6eppm/jobs.py` - Job execution and monitoring
- `mcp/tools/mutations.py` - MCP tool implementations with safety protocols
- `p6_mcp.exceptions.MutationError` - Specific exception for mutation failures

## Related Decisions
- 0001: Own Parser vs Third-Party XER Libraries
- 0002: REST vs SOAP vs SQL for live P6 EPPM backend
- 0004: Decimal vs float for monetary values
- 0005: CPM recompute scope
- 0006: Mutation safety model (this decision focuses on the overall model)
- 0007: Output-size guard design
- 0008: Transport/authentication choices

## References
- [Build Prompt Section 15.4](file:///Users/alireza/Downloads/P6-MCP-build-prompt.md#154-live-mutation-safety-protocol-mandatory-for-every-write-against-p6)
- Database migration patterns (Flyway, Liquibase)
- Software Transactional Memory (STM) concepts
- ITIL Change Management practices