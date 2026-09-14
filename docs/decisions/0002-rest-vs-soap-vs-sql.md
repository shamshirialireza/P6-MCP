# ADR 0002: REST vs SOAP vs SQL for Live P6 EPPM Backend

## Status
Accepted

## Context
We need to integrate with live Primavera P6 Enterprise Project Portfolio Management (P6 EPPM) systems to enable reading and writing schedule data. P6 EPPM provides multiple APIs for integration.

Options considered:
1. **REST API** (P6 Enterprise Project Portfolio Management Web Services)
2. **SOAP API** (Legacy P6 Web Services)
3. **Direct SQL** (Direct database access to P6 Oracle/SQL Server)

## Decision
We chose to use the **REST API** as the primary integration method, with SOAP as an optional fallback for missing objects.

## Rationale
### Why REST over SOAP:
1. **Modern Standard**: REST is the current direction for P6 EPPM, with ongoing investment and feature additions
2. **Simplicity**: JSON over HTTP is simpler to work with than SOAP/XML envelopes
3. **Performance**: Generally better performance due to less verbose payloads
4. **Future-Proof**: Oracle is actively developing the REST API while SOAP is legacy
5. **Standard Tooling**: Abundant HTTP client libraries and debugging tools

### Why not Direct SQL:
1. **Unsupported by Oracle**: Direct SQL write access is explicitly unsupported and can corrupt data
2. **Business Logic Bypass**: P6 business rules, validation, and triggers live in the application layer
3. **Version Fragility**: Database schema changes between P6 versions would break compatibility
4. **No Transaction Safety**: Missing P6's transaction management and rollback capabilities
5. **License Violation**: Likely violates P6 EPPM license terms

### Why REST with SOAP Fallback:
1. **Completeness**: Some older P6 EPPM releases or specific objects may lack REST endpoints
2. **Backward Compatibility**: SOAP provides access to objects not yet available in REST
3. **Graceful Degradation**: Clear documentation of gaps rather than pretending full compatibility
4. **Migration Path**: Enables gradual transition from SOAP to REST as coverage improves

## Consequences
### Positive
- Modern, maintainable integration approach
- Full read/write capability for supported objects
- Clear upgrade path as P6 enhances REST coverage
- No risk of database corruption from unsupported SQL access
- Leverages Oracle's current API investment

### Negative
- May require SOAP fallback for some objects in older releases
- Need to maintain two integration paths (primary REST, optional SOAP)
- Must document and handle gaps in REST coverage
- Slightly more complex implementation than single-method approach

## Implementation Plan
1. **Primary**: Implement full REST API integration in `src/p6_mcp.repository.p6eppm`
2. **Optional**: Implement SOAP adapter as fallback for missing objects (to be done if needed)
3. **Abstraction**: Use `ScheduleRepository` protocol so services remain backend-agnostic
4. **Documentation**: Clearly document any gaps in REST coverage per release
5. **Fallback Mechanism**: `P6EppmRepository` will attempt REST first, then SOAP if configured and object missing

## Field Mapping Strategy
- Maintain bidirectional mapping: REST field ↔ domain attribute ↔ XER column
- Handle PascalCase (REST) ↔ snake_case (domain) ↔ UPPER_CASE (XER) conversions
- Manage enum translations (e.g., REST "In Progress" ↔ XER "TK_Active")
- Store mapping definitions in `src/p6_mcp.repository.p6eppm.mapping.*`

## Related Decisions
- 0001: Own Parser vs Third-Party XER Libraries
- 0003: Changeset/snapshot safety model
- 0004: Decimal vs float for monetary values
- 0005: CPM recompute scope
- 0006: Mutation safety model
- 0007: Output-size guard design
- 0008: Transport/authentication choices

## References
- [Build Prompt Section 15](file:///Users/alireza/Downloads/P6-MCP-build-prompt.md#15-live-p6-eppm-backend---natural-language-changes-applied-directly-in-p6)
- Oracle Primavera P6 Enterprise Project Portfolio Management Web Services Guide