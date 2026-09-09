# Graph Report - P6-MCP  (2026-09-09)

## Corpus Check
- Corpus is ~26,774 words - fits in a single context window. You may not need a graph.

## Summary
- 730 nodes · 1499 edges · 45 communities (30 shown, 15 thin omitted)
- Extraction: 89% EXTRACTED · 11% INFERRED · 0% AMBIGUOUS · INFERRED: 172 edges (avg confidence: 0.94)
- Token cost: 17,000 input · 1,396 output

## Community Hubs (Navigation)
- Calendar Working-Time Math
- Cost and Earned Value
- XER Test Fixture Builder
- CPM Engine and DCMA
- Generic XER Table Model
- Error Hierarchy and Resolution
- Server Settings and Config
- XER Reader and Tokenizing
- Activity Status Classification
- Schedule Aggregate Indexes
- P6 Enum Labels
- Resource Assignment Quantities
- Activity Query Filters
- Health Score and Progress
- Workspace Path Security
- Value Type Coercion
- Network Logic Health
- Project and Baseline Identity
- Schedule Diff and Rollup
- Entity Base Accessors
- Relationship Logic Links
- XER Writer Round-Trip
- Critical Path Analysis
- Entity Serialization
- Activity Date Fields
- LRU Schedule Cache
- Structured Logging
- WBS Node Hierarchy
- Resource Definitions
- ERMHDR File Header
- Project Milestone Dates
- Lookahead Windows
- Float Distribution and Paths
- README Placeholder Docs
- Schedule Data Date
- Calendar Day Conversion
- Constraint Inventory
- Percent Complete Calculation
- WBS Path Building
- WBS Descendant Traversal
- Activity Code Index
- Package Version
- Module Entry Point
- Services Package Root
- Package Root Node

## God Nodes (most connected - your core abstractions)
1. `Schedule` - 142 edges
2. `Activity` - 94 edges
3. `Project` - 73 edges
4. `Calendar` - 43 edges
5. `Assignment` - 31 edges
6. `Relationship` - 22 edges
7. `Table` - 22 edges
8. `Entity` - 21 edges
9. `Resource` - 19 edges
10. `InvalidArgumentError` - 19 edges

## Surprising Connections (you probably didn't know these)
- `Workspace` --uses--> `Settings`  [INFERRED]
  src/p6_mcp/repository/workspace.py → src/p6_mcp/config.py
- `Schedule` --uses--> `Activity`  [INFERRED]
  src/p6_mcp/domain/schedule.py → src/p6_mcp/domain/activity.py
- `_baseline_pool()` --uses--> `Activity`  [INFERRED]
  src/p6_mcp/services/analysis/baseline_compare.py → src/p6_mcp/domain/activity.py
- `compare_to_baseline()` --uses--> `Activity`  [INFERRED]
  src/p6_mcp/services/analysis/baseline_compare.py → src/p6_mcp/domain/activity.py
- `activity_costs()` --uses--> `Activity`  [INFERRED]
  src/p6_mcp/services/analysis/cost.py → src/p6_mcp/domain/activity.py

## Import Cycles
- 3-file cycle: `src/p6_mcp/parser/__init__.py -> src/p6_mcp/parser/writer.py -> src/p6_mcp/parser/reader.py -> src/p6_mcp/parser/__init__.py`

## Communities (45 total, 15 thin omitted)

### Community 0 - "Calendar Working-Time Math"
Cohesion: 0.05
Nodes (37): Calendar, _p6_weekday(), date, datetime, Calendar entity with working-time arithmetic. All schedule math (CPM, time-…, Date after consuming ``days`` full working days (0 -> next working day)., Count of working days in [start, end] inclusive (negative if reversed)., Working hours in [start, end); negative when end < start. (+29 more)

### Community 1 - "Cost and Earned Value"
Cohesion: 0.08
Nodes (46): InvalidArgumentError, A tool argument failed validation beyond what the JSON schema covers., cash_flow(), cost_summary(), _group_keys(), Any, Cost summaries and time-phased cash flow., Budget/actual/remaining/at-completion grouped by the requested dimension. Note:… (+38 more)

### Community 2 - "XER Test Fixture Builder"
Cohesion: 0.10
Nodes (23): add_workdays(), after(), _assemble(), build_demo_xer(), build_large_xer(), DemoSchedule, _dt(), fmt() (+15 more)

### Community 3 - "CPM Engine and DCMA"
Cohesion: 0.10
Nodes (28): compare_to_stored(), compute_cpm(), CpmResult, _fallback_calendar(), Any, datetime, Independent CPM forward/backward pass over the parsed network. Purpose:…, Computed dates/float per task_id plus a comparison to stored values. (+20 more)

### Community 4 - "Generic XER Table Model"
Cohesion: 0.08
Nodes (16): Enum, Any, Write a typed value back into a row's raw storage., One row as a field→value mapping., Rows whose raw field equals ``value``., Table name → row/field counts, flagging unknown tables., One XER table: ordered field names + raw string rows., Raw string value for a field ('' when missing). (+8 more)

### Community 5 - "Error Hierarchy and Resolution"
Cohesion: 0.09
Nodes (24): Exception, Find one activity by task_code or numeric task_id., Find a resource by rsrc_id, short name, or name (case-insensitive)., AmbiguousMatchError, ExportError, MutationDisabledError, MutationError, NotFoundError (+16 more)

### Community 6 - "Server Settings and Config"
Cohesion: 0.08
Nodes (16): BaseSettings, field_validator, Path, Runtime settings for the p6-mcp server. Settings come from (highest precedence…, All server-wide knobs. See ``.env.example`` for documentation., Absolute, resolved allowed directories., Absolute output directory (first allowed dir when unset)., Whether mutation tools may run. (+8 more)

### Community 7 - "XER Reader and Tokenizing"
Cohesion: 0.12
Nodes (23): The file could not be tokenized/parsed as an XER document., The file's byte encoding could not be determined or decoded., XerEncodingError, XerParseError, Path, XER document model and reader. The reader is lossless: every table (known or…, Parses XER bytes/files into :class:`XerDocument` (never raises on content)., Read and parse a file from disk. (+15 more)

### Community 9 - "Schedule Aggregate Indexes"
Cohesion: 0.13
Nodes (5): Any, Typed, indexed view over one parsed XER document., task_id → [{code_type, code_value, short_name}]., (table_name, fk_id) → [{name, label, type, value}]., Schedule

### Community 10 - "P6 Enum Labels"
Cohesion: 0.12
Nodes (10): Activity (TASK row) entity., label_of(), Entity base class and P6 enum vocabulary with human-readable labels. Enum…, Human label for a P6 code; unknown codes pass through verbatim., Typed domain models over the generic parser tables., Project (PROJECT row) and WBS (PROJWBS row) entities., Relationship (TASKPRED row) entity., Resource (RSRC) and assignment (TASKRSRC) entities. (+2 more)

### Community 11 - "Resource Assignment Quantities"
Cohesion: 0.09
Nodes (3): Assignment, datetime, One TASKRSRC row: a resource/role assignment on an activity.

### Community 12 - "Activity Query Filters"
Cohesion: 0.14
Nodes (19): ActivityFilter, _code_match(), filter_activities(), normalize_status(), Any, Activity filtering with the full §5.4 predicate set., Apply every supplied predicate; order-preserving., All optional predicates; only supplied ones are applied (AND semantics). (+11 more)

### Community 13 - "Health Score and Progress"
Cohesion: 0.16
Nodes (16): check_schedule_quality(), health_score(), Any, Composite schedule health score and the quick quality check., Weighted 0-100 score with per-component breakdown and recommendations., Quick quality sweep: every common defect with offending activity codes., Schedule analytics: critical path, DCMA, EVM, time-phasing, comparison., activity_variances() (+8 more)

### Community 14 - "Workspace Path Security"
Cohesion: 0.20
Nodes (12): FileAccessError, The path does not exist, is not a file, or cannot be read., The path is outside the allowed workspace directories., WorkspaceError, Loading, caching, and workspace path validation., Path, Allowed-directory enforcement and .xer file discovery., Validates every read/write path against the allowed-directory allowlist. (+4 more)

### Community 15 - "Value Type Coercion"
Cohesion: 0.13
Nodes (17): format_bool(), format_date(), format_number(), parse_bool(), parse_date(), parse_float(), parse_int(), date (+9 more)

### Community 16 - "Network Logic Health"
Cohesion: 0.18
Nodes (17): analyze_logic_health(), circular_logic(), dangling(), _eligible(), open_ends(), out_of_sequence(), Any, Network logic health: open ends, dangling, redundancy, circularity, out-of-… (+9 more)

### Community 17 - "Project and Baseline Identity"
Cohesion: 0.12
Nodes (3): Project, One PROJECT row. ``project_flag='N'`` rows are baselines., Projects matching the selector; all non-baseline projects by default.

### Community 18 - "Schedule Diff and Rollup"
Cohesion: 0.17
Nodes (14): activity_costs(), budgeted/actual/remaining cost of one activity (assignments + expenses), with…, progress_summary(), diff_schedules(), _match_projects(), Any, XER-vs-XER update comparison and multi-update trend., Key metrics across a series of updates (ordered as given). (+6 more)

### Community 19 - "Entity Base Accessors"
Cohesion: 0.18
Nodes (8): Entity, Any, datetime, A typed view over one raw table row (raw strings stay authoritative)., Typed field value (None when blank/absent)., Raw string value ('' when blank/absent)., Write a value back into raw storage (used by the mutation layer)., Serialize (all or selected) fields with typed values.

### Community 21 - "XER Writer Round-Trip"
Cohesion: 0.21
Nodes (10): XER file-format layer: tokenizer, schema registry, reader, writer. No business…, A parsed XER file: header + ordered tables + physical-format facts., XerDocument, Path, Lossless XER writer. Writes an :class:`XerDocument` back to bytes preserving…, Serializes an XerDocument back to XER format., Render the document to a single string with its original line ending., Render the document to bytes in its original encoding. (+2 more)

### Community 22 - "Critical Path Analysis"
Cohesion: 0.19
Nodes (14): critical_by_longest_path(), critical_by_total_float(), get_critical_path(), get_near_critical(), get_negative_float(), _incomplete(), Critical path, near-critical, float paths, and float distribution. Two methods…, Working-hour slack across a relationship (0 ⇒ driving). (+6 more)

### Community 23 - "Entity Serialization"
Cohesion: 0.31
Nodes (14): activity_to_dict(), assignment_to_dict(), calendar_to_dict(), iso(), project_to_dict(), Any, Entity → dict serializers with verbosity levels and field selection. Durations…, Recursively make a value JSON-serializable. (+6 more)

### Community 24 - "Activity Date Fields"
Cohesion: 0.14
Nodes (3): datetime, Current start: actual if started, else early/planned., Current finish: actual if complete, else early/planned.

### Community 25 - "LRU Schedule Cache"
Cohesion: 0.22
Nodes (5): K, LruCache, LRU cache for parsed schedules, keyed by (path, mtime, size)., A small ordered-dict LRU (thread safety not required: MCP servers are single-…, V

### Community 26 - "Structured Logging"
Cohesion: 0.20
Nodes (9): Logger, LogRecord, configure_logging(), get_logger(), JsonFormatter, Logging setup: stderr only (stdio transport needs a clean stdout)., One JSON object per line, suitable for log shippers., Configure the root ``p6_mcp`` logger to write to stderr only. (+1 more)

### Community 30 - "Project Milestone Dates"
Cohesion: 0.29
Nodes (3): datetime, P6's current data date is last_recalc_date., Scheduled (must-finish-by driven) end date.

### Community 31 - "Lookahead Windows"
Cohesion: 0.40
Nodes (5): lookahead(), Any, datetime, Lookahead windows: what starts, finishes, or is in progress soon., Activities starting/finishing/in-progress within the window from the data date…

### Community 32 - "Float Distribution and Paths"
Cohesion: 0.40
Nodes (5): get_float_distribution(), get_float_paths(), Any, Group by P6 multiple-float-path fields, else bucket by float value., Histogram of total float in days over incomplete activities.

### Community 33 - "README Placeholder Docs"
Cohesion: 1.00
Nodes (3): P6-MCP, Phase 11, Placeholder README (Phase 11 regeneration)

### Community 36 - "Constraint Inventory"
Cohesion: 0.67
Nodes (3): constraints(), Any, All constrained activities with hard/soft classification and constraints dated…

## Knowledge Gaps
- **1 isolated node(s):** `p6-mcp`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 340 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **15 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `Schedule` connect `Schedule Aggregate Indexes` to `Calendar Working-Time Math`, `Cost and Earned Value`, `CPM Engine and DCMA`, `Generic XER Table Model`, `Error Hierarchy and Resolution`, `Server Settings and Config`, `Activity Status Classification`, `P6 Enum Labels`, `Resource Assignment Quantities`, `Activity Query Filters`, `Health Score and Progress`, `Network Logic Health`, `Project and Baseline Identity`, `Schedule Diff and Rollup`, `Relationship Logic Links`, `XER Writer Round-Trip`, `Critical Path Analysis`, `Entity Serialization`, `WBS Node Hierarchy`, `Resource Definitions`, `Lookahead Windows`, `Float Distribution and Paths`, `Schedule Data Date`, `Calendar Day Conversion`, `Constraint Inventory`, `WBS Path Building`, `WBS Descendant Traversal`, `Activity Code Index`?**
  _High betweenness centrality (0.427) - this node is a cross-community bridge._
- **Why does `Calendar` connect `Calendar Working-Time Math` to `Cost and Earned Value`, `CPM Engine and DCMA`, `Calendar Day Conversion`, `Schedule Aggregate Indexes`, `P6 Enum Labels`, `Entity Base Accessors`, `Entity Serialization`?**
  _High betweenness centrality (0.222) - this node is a cross-community bridge._
- **Why does `Activity` connect `Activity Status Classification` to `Float Distribution and Paths`, `Cost and Earned Value`, `Calendar Day Conversion`, `CPM Engine and DCMA`, `Percent Complete Calculation`, `Error Hierarchy and Resolution`, `Schedule Aggregate Indexes`, `P6 Enum Labels`, `Activity Query Filters`, `Health Score and Progress`, `Network Logic Health`, `Project and Baseline Identity`, `Schedule Diff and Rollup`, `Entity Base Accessors`, `Critical Path Analysis`, `Entity Serialization`, `Activity Date Fields`?**
  _High betweenness centrality (0.134) - this node is a cross-community bridge._
- **Are the 72 inferred relationships involving `Schedule` (e.g. with `Activity` and `Calendar`) actually correct?**
  _`Schedule` has 72 INFERRED edges - model-reasoned connections that need verification._
- **Are the 32 inferred relationships involving `Activity` (e.g. with `Schedule` and `_baseline_pool()`) actually correct?**
  _`Activity` has 32 INFERRED edges - model-reasoned connections that need verification._
- **Are the 33 inferred relationships involving `Project` (e.g. with `Schedule` and `_baseline_pool()`) actually correct?**
  _`Project` has 33 INFERRED edges - model-reasoned connections that need verification._
- **Are the 7 inferred relationships involving `Calendar` (e.g. with `ParsedCalendar` and `WorkShift`) actually correct?**
  _`Calendar` has 7 INFERRED edges - model-reasoned connections that need verification._