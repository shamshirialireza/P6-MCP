# ADR 0006: Mutation Safety Model

## Status
Accepted

## Context
We need to ensure that modifications to schedule data (whether XER files or live P6 EPPM) are safe, predictable, and verifiable. Users must be able to review changes before they are applied and have confidence that what they intend to happen is what actually happens.

Options considered:
1. Direct modification with undo/redo
2. Transactional approach with commit/rollback
3. Changeset-based approach with planning, dry-run, and confirmation
4. Event sourcing with command replay
5. No modification capabilities (read-only only)

## Decision
We chose a changeset-based mutation safety model with explicit planning, dry-run preview, and user confirmation, as specified in build prompt Section 15.4.

## Rationale
### Why Changeset-Based Model with Dry-Run and Confirm:
1. **User Control**: Explicit confirmation step puts the user in charge of when changes are applied
2. **Preview Capability**: Dry-run allows users to see exactly what will change before any modification occurs
3. **Safety First**: Reduces risk of accidental or unintended modifications to critical schedule data
4. **Audit Trail**: Complete record of planned vs actual changes for compliance and troubleshooting
5. **Enterprise Appropriate**: Matches expectations for professional schedule management tools
6. **Build Prompt Compliance**: Directly implements the safety protocol specified in Section 15.4

### Why Not Direct Modification with Undo/Redo:
1. **Undo Limitations**: Undo may not be possible after certain operations or after other changes have been made
2. **False Sense of Security**: Users might rely on undo without realizing its limitations
3. **No Preview**: Users cannot see what will change before making the change
4. **Complex State Management**: Difficult to maintain accurate undo history for complex interconnected changes

### Why Not Transactional Commit/Rollback:
1. **No Direct DB Access**: Cannot use database transactions due to lack of direct SQL access (unsupported by Oracle)
2. **Application Layer**: Modifications happen through P6's application layer (REST API) or file system, not direct database
3. **Partial Commit Risk**: Risk of committing some changes but not others in interconnected modifications

### Why Not Event Sourcing:
1. **Over-Engineering**: Significantly more complex than needed for this use case
2. **Implementation Burden**: Would require redesigning around event sourcing principles
3. **Query Complexity**: Rebuilding state from events for every query would impact performance
4. **Unnecessary Features**: Provides capabilities (like temporal queries) that are not required

### Why Not Read-Only Only:
1. **Limited Utility**: Would prevent users from correcting errors or updating schedules
2. **Build Prompt Requirement**: Sections 5.15 and 15.5 explicitly require mutation capabilities
3. **User Expectations**: Professional schedulers need to update schedules based on actual progress

## Consequences
### Positive
- High confidence that changes match user intent
- Ability to review and approve changes before application
- Protection against accidental modifications
- Clear audit trail for regulatory and quality purposes
- Enterprise-grade change management appropriate for schedule data
- Ids
- Supports both XER file and live P6 EPPM backends consistently

### Negative
- Increased complexity in mutation tools
- Additional steps required for users to make changes
- Need to manage plan expiration and cleanup
- Storage overhead for snapshots and plans
- Slightly longer workflow due to planning/verification steps

## Implementation Plan
The mutation safety protocol implements all 10 steps from build prompt Section 15.4:

### 1. Guards (Pre-flight Checks)
- Connection not in read-only mode (`P6MCP_ENABLE_MUTATION` must be true)
- Project in configured `ALLOWED_PROJECTS` list (if specified)
- Project not checked out by another user (`CheckOutStatus` field)
- User has sufficient privileges (verified via privilege check or no-op PUT)
- User has explicitly opted into mutation capability

### 2. Plan Generation (ChangeSet Creation)
- `ScheduleEditor` analyzes requested changes
- Generates exact list of REST operations (service, verb, payload)
- Orders operations by dependency (WBS before activities before relationships before assignments)
- Creates human-readable diff showing before → after per field
- Calculates impact estimate (which successor activities/float may be affected)
- Returns `plan_id` for referencing this specific plan

### 3. Dry-Run Preview (Default for Live Sources)
- All mutation tools accept `dry_run=True` parameter
- For live P6 EPPM sources, `dry_run` defaults to `True`
- Returns only the plan without making any changes
- Allows user to review exactly what would happen
- Critical for building user trust in live modifications

### 4. Explicit Confirmation
- User must provide both `confirm=True` AND valid `plan_id`
- Plans expire after configurable time period (default: 20 minutes)
- Plans automatically invalidated if `LastUpdateDate` of any touched object changes
- Implements optimistic concurrency checking to prevent lost updates
- Clear error message if confirmation fails: "Review the plan and re-call with confirm=True"

### 5. Snapshot Creation (Pre-Change Backup)
- Before applying changes, take a snapshot of all touched objects
- For P6 EPPM: Use `/export/exportProject` for P6 XML or full REST read
- For XER: Copy the original file or record original state
- Store snapshot under `P6MCP_OUTPUT_DIR/snapshots/<connection>/<project>/<timestamp>/`
- Save the ChangeSet JSON with the snapshot for reference
- Provides rollback capability via `p6_restore_snapshot` tool

### 6. Ordered Application with Error Handling
- Execute operations in precisely determined dependency order
- WBS → Activities → Relationships → Assignments → etc.
- Delete operations performed in reverse order (assignments last)
- Retry mechanism for transient errors (network timeouts, etc.)
- Stop at first hard failure and report partial state precisely
- Never silently continue after errors
- Return detailed information about what was successfully applied

### 7. Post-Application Verification
- Re-read all objects that were intended to be modified
- Compare actual state against intended changes
- Report any mismatches between plan and result
- Provide detailed information about what succeeded vs failed
- Enable user to determine if manual correction is needed

### 8. Optional Post-Actions
- Automatically run `/job/schedule` (CPM/F9) after successful apply if desired
- Can optionally trigger `/job/level`, `/job/summarizeProject`, etc.
- Poll until completion with progress reporting
- Return post-schedule deltas showing what actually changed
- Activities whose dates/float changed, new critical path count, etc.

### 9. Audit Logging
- Append JSONL audit record to `P6MCP_OUTPUT_DIR/audit/`
- Record includes:
  - Who (user identifier)
  - When (timestamp)
  - Connection and project identifiers
  - Plan ID and ChangeSet summary
  - Result (success/partial failure/failure)
  - Associated job IDs (if post-actions were run)
- Enables compliance reporting and forensic analysis

### 10. Idempotency Guarantee
- Re-applying an already-applied plan is a safe no-op
- System detects that the plan has already been applied
- Returns clear message: "This plan has already been applied"
- Prevents duplicate changes and user confusion
- Important for recovery scenarios and retry logic

## Related Components
- `services/mutate/editor.py` - ScheduleEditor computes ChangeSets and applies them
- `repository/p6eppm/changeset.py` - ChangeSet / ChangePlan data structures and logic
- `repository/p6eppm/snapshots.py` - Snapshot creation and restoration logic
- `repository/p6eppm/jobs.py` - Job execution, monitoring, and post-action handling
- `mcp/tools/mutations.py` - All mutation tool implementations with safety protocols
- `p6_mcp.exceptions` - MutationError, PlanExpiredError, ConcurrentModificationError, etc.
- `p6_mcp.mcp.context.AppContext` - Provides `require_mutation()` and other safety checks

## Related Decisions
- 0001: Own Parser vs Third-Party XER Libraries
- 0002: REST vs SOAP vs SQL for live P6 EPPM backend
- 0003: Changeset/snapshot safety model (closely related - this focuses on mutation specifics)
- 0004: Decimal vs float for monetary values
- 0005: CPM recompute scope
- 0007: Output-size guard design
- 0008: Transport/authentication choices

## References
- [Build Prompt Section 15.4](file:///Users/alireza/Downloads/P6-MCP-build-prompt.md#154-live-mutation-safety-protocol-mandatory-for-every-write-against-p6)
- [Build Prompt Section 5.15](file:///Users/alireza/Downloads/P6-MCP-build-prompt.md#515-mutation-write-back-destructivehinttrue-require-confirmtrue)
- Database transaction patterns (ACID properties)
- Software change management best practices (ITIL, ISO 20000)
- Optimistic concurrency control patterns