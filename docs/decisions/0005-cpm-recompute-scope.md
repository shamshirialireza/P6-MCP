# ADR 0005: CPM Recompute Scope

## Status
Accepted

## Context
We need to implement Critical Path Method (CPM) recomputation for validating schedule logic and comparing against P6's native scheduling engine. The scope and limitations of our recomputation implementation need to be clearly defined.

Options considered:
1. Full P6-equivalent CPM engine (replicate all scheduling logic)
2. Subset CPM implementation focused on validation and comparison
3. External CPM engine integration (call out to specialized library)
4. No recomputation capability (rely solely on P6's native scheduling)

## Decision
We chose to implement a subset CPM implementation focused on validation and comparison with clear documentation of limitations.

## Rationale
### Why Subset CPM Implementation:
1. **Validation Focus**: Primary use case is comparing stored dates against recomputed dates to validate logic, not replacing P6's scheduler
2. **Transparency**: Clear documentation of what we do and don't support builds appropriate trust
3. **Development Effort**: Full P6-equivalent CPM would require replicating decades of scheduling sophistication
4. **Maintenance Burden**: Keeping up with P6's scheduling algorithm changes would be ongoing
5. **Sufficient for Analytics**: Our recomputation is adequate for float analysis, critical path validation, and schedule health assessments

### Why Not Full P6-Equivalent Engine:
1. **Unnecessary Complexity**: P6's scheduler includes many specialized cases we don't need to replicate
2. **Certification Gap**: We cannot and do not aim to be a "certified" scheduling engine
3. **Resource Investment**: Significant development effort for minimal additional user value
4. **Ongoing Maintenance**: Would require tracking P6's scheduling algorithm updates

### Why Not External Integration:
1. **Dependency Risk**: Introduces external dependency with its own licensing and maintenance
2. **Integration Complexity**: Adds failure points and data translation layers
3. **Limited Availability**: Few high-quality CPM engines are available as libraries with permissive licenses
4. **Performance Overhead**: Process marshalling and data conversion costs

### Why Not No Recomputation:
1. **Validation Blind Spot**: Cannot verify stored dates or detect data corruption
2. **Limited Analytics**: Would restrict float analysis, critical path assessment, and health scoring
3. **User Expectations**: Schedulers expect to validate logic and compare against baselines
4. **Build Prompt Requirement**: Section 5.6 explicitly requires CPM recompute functionality

## Consequences
### Positive
- Provides valuable schedule validation capabilities
- Enables float analysis and critical path verification
- Supports schedule health scoring and trend analysis
- Clear boundaries prevent overpromising capabilities
- Reasonable development and maintenance effort

### Negative
- Does not replicate all of P6's scheduling nuances
- May show small differences in complex scheduling scenarios
- Requires clear communication about limitations to users
- Not suitable for schedule optimization or what-if analysis

## Implementation Plan
Our CPM recomputation will implement:

### Supported Features
1. **Forward/Backward Pass**: Standard CPM calculation using activity durations and relationships
2. **Calendar Awareness**: Proper handling of activity-specific calendars and work hours
3. **Relationship Types**: FS, SS, FF, SF with lag/lead support
4. **Constraints**: Support for primary and secondary constraint types (MFO, MSO, SNET, FNET, SNLT, FNLT)
5. **Milestones and LOE**: Special handling for milestone and level of effort activities
6. **Actual Dates**: Integration of actual start/finish dates when available
7. **Delayed Activities**: Proper handling of delayed start/finish constraints
8. **WBS Summarization**: Respect for WBS summary activities (driven by children)

### Limitations and Exclusions
1. **Resource Leveling**: Does not perform resource leveling or overallocation resolution
2. **Advanced Calendars**: May not handle all calendar exceptions identically to P6
3. **Specific Constraint Interpretations**: Some edge-case constraint behaviors may differ
4. **Percent Complete Types**: May not handle all % complete type calculations identically
5. **Closed Loop Projects**: Special handling for projects with positive/negative float constraints
6. **Multiple Critical Paths**: May not identify all critical paths in complex networks identically
7. **Negative Float Handling**: May differ in how negative float is calculated and displayed
8. **Projection Scheduling**: Does not implement P6's projection scheduling mode
9. **Duration Type Variations**: May not handle all duration type variations identically

## Verification Approach
We will verify our implementation through:
1. **Unit Tests**: Individual component testing of CPM algorithm elements
2. **Golden Files**: Comparison against known good outputs from P6 for standard fixtures
3. **Property Tests**: Random schedule generation → P6 schedule → our recompute → compare within tolerance
4. **Analytics Validation**: Ensure derived metrics (total float, critical path, etc.) produce correct analytics
5. **Regression Testing**: Monitor changes against baseline P6 behavior

## Usage Guidelines
Appropriate uses of our CPM recomputation:
- Validating stored start/finish dates against calculated values
- Identifying driving path and float contributors
- Calculating total float and free float for analysis
- Determining critical path activities
- Validating schedule logic (open ends, dangling, etc.)
- Baseline variance analysis
- Schedule health scoring components

Inappropriate uses:
- Schedule optimization or resource leveling
- What-if scenario planning as primary scheduling engine
- Replacing P6's native scheduling for production schedules
- High-precision schedule calculations requiring bit-for-bit P6 match

## Related Components
- `services/analysis/cpm.py` - Core CPM recomputation engine
- `services/analysis/critical_path.py` - Critical path and float analysis
- `services/analysis/time_phasing.py` - Calendar-aware time phasing
- `services/analysis/constraints.py` - Constraint handling and validation
- `tools/critical.py` - MCP tools for critical path and float analysis
- `tests/unit/services/analysis/` - Unit tests for CPM implementation

## Related Decisions
- 0001: Own Parser vs Third-Party XER Libraries
- 0002: REST vs SOAP vs SQL for live P6 EPPM backend
- 0003: Changeset/snapshot safety model
- 0004: Decimal vs float for monetary values
- 0006: Mutation safety model
- 0007: Output-size guard design
- 0008: Transport/authentication choices

## References
- [Build Prompt Section 5.6](file:///Users/alireza/Downloads/P6-MCP-build-prompt.md#56-critical-path--float)
- [Build Prompt Section 10.3](file:///Users/alireza/Downloads/P6-MCP-build-prompt.md#103-analytics-correctness-tests) - "Analytics correctness tests with hand-computed expectations: CPM forward/backward pass"
- "Critical Path Method" by Kelley and Walker (1959)
- "Project Management: A Systems Approach to Planning, Scheduling, and Controlling" by Harold Kerzner
- Oracle Primavera P6 Scheduling Guide