# ADR 0001: Own Parser vs Third-Party XER Libraries

## Status
Accepted

## Context
We need to parse Primavera P6 XER (eXtensible Export Report) files to extract schedule data. XER is a tab-delimited format with specific header lines (%T for tables, %F for fields, %R for rows, %E for end) and encoding variations (CP1252, UTF-8, UTF-16).

Options considered:
1. Use a third-party XER parsing library
2. Build our own XER parser from scratch
3. Use a generic CSV/TSV parser with custom handling

## Decision
We chose to build our own XER parser from scratch.

## Rationale
1. **Completeness Requirement**: The build prompt requires parsing 100% of XER tables, including unknown/future tables. Third-party libraries typically only support a common subset of tables (TASK, PROJECT, RSRC, etc.) and drop unknown tables.

2. **Lossless Round-Trip**: We need byte-identical write-back capability for fixtures. Building our own parser gives us full control over formatting, encoding preservation, and field order.

3. **Performance Control**: Custom parser allows optimization for large schedules (50k+ activities) with lazy indexing and memory-conscious design.

4. **Encoding Handling**: Proper detection and handling of CP1252 (default), UTF-8, and UTF-16 with BOM requires specific logic that generic parsers may not handle correctly.

5. **Table/Field Registry**: We need to maintain a registry of known tables/fields with their types and P6 version quirks, which is easier to manage in a custom implementation.

6. **Calendar Data Parsing**: The CALENDAR.clndr_data blob requires specialized parsing into work week, holidays/exceptions, and shift blocks that is specific to P6's format.

## Consequences
### Positive
- Full control over parsing behavior and performance
- Ability to handle all XER tables including unknown ones
- Lossless round-trip capability
- Optimized for our specific use case
- No external dependencies for core parsing functionality

### Negative
- Increased development time initially
- Responsibility for maintaining and improving the parser
- Need to implement comprehensive tests for edge cases

## Implementation Plan
The parser will be implemented in `src/p6_mcp.parser` with modules for:
- tokenizer.py: Handle %T/%F/%R/%E lines, encoding detection
- schema.py: Known table/field registry and type definitions
- reader.py: Convert tokens to generic Table objects
- writer.py: Lossless XER writing with ERMHDR preservation
- coercion.py: Type conversion (dates, numbers, Y/N flags, enums)
- calendar_data.py: Parse clndr_data blob into workweek/exceptions

## Related Decisions
- 0002: REST vs SOAP vs SQL for live P6 EPPM backend
- 0003: Changeset/snapshot safety model
- 0004: Decimal vs float for monetary values
- 0005: CPM recompute scope
- 0006: Mutation safety model
- 0007: Output-size guard design
- 0008: Transport/authentication choices

## References
- [Build Prompt Section 4.3](file:///Users/alireza/Downloads/P6-MCP-build-prompt.md#43-known-tables-to-type-explicitly)
- Oracle Primavera P6 XER File Format Specification