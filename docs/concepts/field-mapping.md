# P6 EPPM REST API Field Mapping

This document contains the mapping between P6 EPPM REST API field names, P6-MCP domain model attributes, and XER file column names. This mapping is used by the `P6EppmRepository` to translate between the live P6 EPPM data and the internal Schedule representation.

## How to Regenerate This Document

This document is generated from the field mapping tables in `src/p6_mcp/repository/p6eppm/mapping/`. To regenerate it:

```bash
python scripts/gen_field_mapping_docs.py
```

## Table Mappings

Below are the field mappings for each supported P6 EPPM REST service.

### PROJECT

| P6 REST Field | Domain Attribute | XER Column | Type | Description |
|---------------|------------------|------------|------|-------------|
| ObjectId | project_id | proj_id | Integer | Unique project identifier |
| Name | name | proj_short_name | String | Project short name |
| LongName | long_name | proj_name | String | Project long name |
| PlannedStartDate | plan_start_date | plan_start_date | DateTime | Planned start date |
| PlannedFinishDate | plan_end_date | plan_end_date | DateTime | Planned finish date |
| TargetStartDate | target_start_date | scd_end_date | DateTime | Target start date |
| TargetFinishDate | target_end_date | fcst_start_date | DateTime | Target finish date |
| ActualStartDate | actual_start_date | - | DateTime | Actual start date |
| ActualFinishDate | actual_finish_date | - | DateTime | Actual finish date |
| LastUpdateDate | last_update_date | last_recalc_date | DateTime | Last update timestamp |
| DataDate | data_date | next_data_date | DateTime | Data date for calculations |
| CriticalDuration | critical_duration | critical_drtn_hr_cnt | Float | Critical path duration |
| CriticalPathType | critical_path_type | critical_path_type | Enum | Type of critical path calculation |
| BaselineProjectId | baseline_project_id | sum_base_proj_id | Integer | Reference to baseline project |
| OriginalProjectId | original_project_id | orig_proj_id | Integer | Original project ID |
| SourceProjectId | source_project_id | source_proj_id | Integer | Source project for copied projects |
| BaselineTypeId | baseline_type_id | base_type_id | Integer | Type of baseline |
| LastBaselineUpdate | last_baseline_update | last_baseline_update_date | DateTime | Last baseline update |
| DefaultDurationType | default_duration_type | def_duration_type | Enum | Default duration type |
| DefaultPCTType | default_pct_type | def_complete_pct_type | Enum | Default % complete type |
| DefaultTaskType | default_task_type | def_task_type | Enum | Default task type |
| DefaultQtyType | default_qty_type | def_qty_type | Enum | Default quantity type |
| DefaultRateType | default_rate_type | def_rate_type | Enum | Default rate type |
| DefaultCostPerQty | default_cost_per_qty | def_cost_per_qty | Float | Default cost per quantity |
| TaskCodePrefix | task_code_prefix | task_code_prefix | String | Task code prefix |
| TaskCodeBase | task_code_base | task_code_base | Integer | Task code base |
| TaskCodeStep | task_code_step | task_code_step | Integer | Task code step |
| CalendarId | calendar_id | clndr_id | String | Calendar identifier |
| FiscalYearStart | fy_start_month | fy_start_month_num | Integer | Fiscal year start month |
| ProjectFlag | is_project | project_flag | Boolean | Indicates if this is a project vs baseline |
| PriorityNum | priority_num | priority_num | Integer | Priority number |
| StrategyPriorityNum | strategy_priority | strgy_priority_num | Integer | Strategic priority |
| AccountId | account_id | acct_id | Integer | Cost account identifier |
| LocationId | location_id | location_id | String | Location identifier |
| MultiAssignFlag | multi_assign | rsrc_multi_assign_flag | Boolean | Allow multiple resource assignments |
| AllowNegatives | allow_neg | allow_neg_act_flag | Boolean | Allow negative actuals |
| ApplyActualsDate | apply_actuals_date | apply_actuals_date | DateTime | Date to apply actuals to |
| AddActRemain | add_act_remain | add_act_remain_flag | Boolean | Add actuals to remaining |
| PctLink | pct_link | act_pct_link_flag | Boolean | Link % complete to duration/cost |
| CostRecalc | cost_recalc | cost_qty_recalc_flag | Boolean | Recalculate cost/quantity |
| RemTargetLink | rem_target_link | rem_target_link_flag | Boolean | Link remaining to target |
| ResetPlanned | reset_planned | reset_planned_flag | Boolean | Reset planned dates |
| StepComplete | step_complete | step_complete_flag | Boolean | Calculate % complete from steps |
| UseProjBaseline | use_proj_baseline | use_project_baseline_flag | Boolean | Use project baseline for calculations |
| MaxSumLevel | max_sum_level | wbs_max_sum_level | Integer | Maximum WBS summary level |
| SumAssignLevel | sum_assign_level | sum_assign_level | Integer | Level at which to summarize assignments |
| CheckoutFlag | checkout_flag | checkout_flag | Boolean | Project checkout status |
| Guid | guid | guid | String | Global unique identifier |

### TASK

| P6 REST Field | Domain Attribute | XER Column | Type | Description |
|---------------|------------------|------------|------|-------------|
| ObjectId | task_id | task_id | Integer | Unique task identifier |
| ProjectId | project_id | proj_id | Integer | Parent project identifier |
| Name | name | task_name | String | Task name |
| LongName | long_name | - | String | Task long name |
| ShortName | short_name | task_code | String | Task short name/code |
| PlannedStartDate | planned_start_date | target_start_date | DateTime | Planned start date |
| PlannedFinishDate | planned_finish_date | target_end_date | DateTime | Planned finish date |
| ActualStartDate | actual_start_date | act_start_date | DateTime | Actual start date |
| ActualFinishDate | actual_finish_date | act_end_date | DateTime | Actual finish date |
| RemainingStartDate | rem_start_date | rem_late_start_date | DateTime | Remaining late start date |
| RemainingFinishDate | rem_finish_date | rem_late_end_date | DateTime | Remaining late finish date |
| EarlyStartDate | early_start_date | - | DateTime | Early start date |
| EarlyFinishDate | early_finish_date | - | DateTime | Early finish date |
| LateStartDate | late_start_date | - | DateTime | Late start date |
| LateFinishDate | late_finish_date | - | DateTime | Late finish date |
| TargetStartDate | target_start_date | target_start_date | DateTime | Target start date |
| TargetFinishDate | target_end_date | target_end_date | DateTime | Target finish date |
| BaselineStartDate | bl_start_date | - | DateTime | Baseline start date |
| BaselineFinishDate | bl_finish_date | - | DateTime | Baseline finish date |
| DurationType | duration_type | duration_type | Enum | Duration type |
| PCTType | pct_type | complete_pct_type | Enum | % complete type |
| PercentComplete | percent_complete | - | Float | % complete value |
| PhysicalPercent | physical_percent | - | Float | Physical % complete |
| BudgetedQty | budgeted_qty | target_work_qty | Float | Budgeted quantity |
| ActualQty | actual_qty | act_work_qty | Float | Actual quantity |
| RemainingQty | remaining_qty | remain_work_qty | Float | Remaining quantity |
| BudgetedCost | budgeted_cost | - | Float | Budgeted cost |
| ActualCost | actual_cost | - | Float | Actual cost |
| RemainingCost | remaining_cost | - | Float | Remaining cost |
| Duration | duration | target_drtn_hr_cnt | Float | Planned duration (hours) |
| ActualDuration | actual_duration | act_drtn_hr_cnt | Float | Actual duration (hours) |
| RemainingDuration | remaining_duration | remain_drtn_hr_cnt | Float | Remaining duration (hours) |
| TotalFloat | total_float | total_float_hr_cnt | Float | Total float (hours) |
| FreeFloat | free_float | free_float_hr_cnt | Float | Free float (hours) |
| DrivingPath | driving_path | driving_path_flag | Boolean | On driving path |
| Critical | is_critical | - | Boolean | On critical path |
| FloatPath | float_path | float_path | String | Float path identifier |
| FloatPathOrder | float_path_order | float_path_order | Integer | Float path order |
| ConstraintType | constraint_type | cstr_type | Enum | Primary constraint type |
| ConstraintDate | constraint_date | cstr_date | DateTime | Primary constraint date |
| ConstraintType2 | constraint_type2 | cstr_type2 | Enum | Secondary constraint type |
| ConstraintDate2 | constraint_date2 | cstr_date2 | DateTime | Secondary constraint date |
| Priority | priority | priority_type | Enum | Priority type |
| WBSId | wbs_id | wbs_id | Integer | WBS identifier |
| ActivityId | activity_id | - | String | Activity identifier (deprecated) |
| CalendarId | calendar_id | calendar_id | String | Calendar identifier |
| LocationId | location_id | location_id | String | Location identifier |
| ResourceId | primary_rsrc_id | rsrc_id | Integer | Primary resource identifier |
| Guid | guid | guid | String | Global unique identifier |
| CreateDate | create_date | create_date | DateTime | Creation timestamp |
| CreateUser | create_user | create_user | String | Creating user |
| UpdateDate | update_date | update_date | DateTime | Last update timestamp |
| UpdateUser | update_user | update_user | String | Last updating user |
| AutoComputeAct | auto_compute_act | auto_compute_act_flag | Boolean | Auto-compute actuals |
| RevFdbkFlag | rev_fdbk_flag | rev_fdbk_flag | Boolean | Review feedback flag |
| LockPlan | lock_plan | lock_plan_flag | Boolean | Lock planning |
| EstimatedWeight | est_wt | est_wt | Float | Estimated weight |

### TASKPRED (Predecessors/Relationships)

| P6 REST Field | Domain Attribute | XER Column | Type | Description |
|---------------|------------------|------------|------|-------------|
| ObjectId | relation_id | - | Integer | Unique relation identifier |
| ProjectId | project_id | proj_id | Integer | Project identifier |
| PredecessorObjectId | predecessor_id | pred_proj_id | Integer | Predecessor project ID |
| SuccessorObjectId | successor_id | proj_id | Integer | Successor project ID (same as project) |
| PredObjectId | pred_task_id | pred_task_id | Integer | Predecessor task ID |
| SuccObjectId | succ_task_id | task_id | Integer | Successor task ID |
| Lag | lag | lag_hr_cnt | Float | Lag duration (hours) |
| LagUnit | lag_unit | - | String | Lag unit (always Hour) |
| PredType | pred_type | pred_type | Enum | Relationship type (FS, SS, FF, SF) |
| Comments | comments | comments | String | Relationship comments |
| DrivingPath | driving_path | - | Boolean | Is driving relationship |
| FloatPath | float_path | float_path | String | Float path |
| Aref | aref | aref | String | Absolute earliest start |
| Arls | arls | arls | String | Actual latest start |

### RSRC (Resources)

| P6 REST Field | Domain Attribute | XER Column | Type | Description |
|---------------|------------------|------------|------|-------------|
| ObjectId | resource_id | rsrc_id | Integer | Unique resource identifier |
| ProjectId | project_id | proj_id | Integer | Parent project identifier |
| ShortName | short_name | rsrc_short_name | String | Resource short name |
| LongName | long_name | rsrc_title_name | String | Resource long name/title |
| Notes | notes | rsrc_notes | String | Resource notes |
| Primary | is_primary | - | Boolean | Primary resource flag |
| Type | rsrc_type | rsrc_type | String | Resource type (Labor/Nonlabor/Material/Expense) |
| Id | id_num | - | String | Identifier number |
| Code | code | - | String | Resource code |
| CalendarId | calendar_id | clndr_id | String | Calendar identifier |
| RoleId | role_id | role_id | Integer | Role identifier |
| UnitId | unit_id | unit_id | String | Unit of measure identifier |
| CurrencyId | curr_id | curr_id | String | Currency identifier |
| ActiveFlag | active_flag | active_flag | Boolean | Active/inactive flag |
| CostQtyType | cost_qty_type | cost_qty_type | Enum | Cost quantity type |
| DefaultQtyPerHr | default_qty_per_hr | def_qty_per_hr | Float | Default quantity per hour |
| OTFactor | ot_factor | ot_factor | Float | Overtime factor |
| OTFlag | ot_flag | ot_flag | Boolean | Overtime flag |
| EmployeeCode | employee_code | employee_code | String | Employee code |
| Notes | notes | rsrc_notes | String | Resource notes |
| OfficePhone | office_phone | office_phone | String | Office phone number |
| OtherPhone | other_phone | other_phone | String | Other phone number |
| ShiftId | shift_id | shift_id | String | Shift identifier |
| PBSId | pobs_id | pobs_id | Integer | Organizational breakdown structure ID |
| UserId | user_id | user_id | Integer | User identifier |
| ParentId | parent_rsrc_id | parent_rsrc_id | Integer | Parent resource ID |
| SeqNum | rsrc_seq_num | rsrc_seq_num | Integer | Resource sequence number |
| LevelFlag | level_flag | level_flag | Boolean | Level flag |
| LoadTasksFlag | load_tasks | load_tasks_flag | Boolean | Load tasks flag |
| AutoComputeAct | auto_compute_act | auto_compute_act_flag | Boolean | Auto-compute actuals |
| DefaultCostQtyLink | default_cost_link | def_cost_qty_link_flag | Boolean | Default cost/quantity link |
| LocationId | location_id | location_id | String | Location identifier |
| Guid | guid | guid | String | Global unique identifier |
| CreateDate | create_date | create_date | DateTime | Creation timestamp |
| CreateUser | create_user | create_user | String | Creating user |
| UpdateDate | update_date | update_date | DateTime | Last update timestamp |
| UpdateUser | update_user | update_user | String | Last updating user |

### CALENDAR

| P6 REST Field | Domain Attribute | XER Column | Type | Description |
|---------------|------------------|------------|------|-------------|
| ObjectId | calendar_id | clndr_id | String | Unique calendar identifier |
| ProjectId | project_id | proj_id | Integer | Parent project identifier (null for global) |
| Name | name | - | String | Calendar name |
| BaseCalendarId | base_calendar_id | base_clndr_id | String | Base calendar identifier |
| DefaultFlag | is_default | default_flag | Boolean | Is default calendar |
| ProjectId | owning_project | proj_id | Integer | Owning project (null for global) |
| LastChangeDate | last_changed | last_chng_date | DateTime | Last changed timestamp |
| CalendarData | calendar_data | clndr_data | String | Encrypted calendar data (work hours + exceptions) |

*Note: CalendarData is parsed into standard work week (per weekday hours), holidays/exceptions (with hours), and shift blocks.*

### ROLE

| P6 REST Field | Domain Attribute | XER Column | Type | Description |
|---------------|------------------|------------|------|-------------|
| ObjectId | role_id | role_id | Integer | Unique role identifier |
| ProjectId | project_id | proj_id | Integer | Parent project identifier |
| ShortName | short_name | role_short_name | String | Role short name |
| LongName | long_name | role_name | String | Role long name |
| RateType | rate_type | rate_type | String | Rate type curve |
| LimitType | limit_type | - | String | Limit type |
| LimitValue | limit_value | - | Float | Limit value |
| DefaultRate | default_rate | - | Float | Default rate |
| IsLabor | is_labor | - | Boolean | Is labor role |
| Active | active | - | Boolean | Active/inactive flag |
| Guid | guid | guid | String | Global unique identifier |
| CreateDate | create_date | create_date | DateTime | Creation timestamp |
| CreateUser | create_user | create_user | String | Creating user |
| UpdateDate | update_date | update_date | DateTime | Last update timestamp |
| UpdateUser | update_user | update_user | String | Last updating user |

### UDFVALUE (User Defined Field Values)

| P6 REST Field | Domain Attribute | XER Column | Type | Description |
|---------------|------------------|------------|------|-------------|
| ObjectId | udf_value_id | - | Integer | Unique UDF value identifier |
| ProjectId | project_id | proj_id | Integer | Parent project identifier |
| UdfFieldId | udf_type_id | udf_type_id | Integer | UDF type identifier |
| ObjectId | object_id | - | Integer | Object ID (task, rsrc, etc.) |
| ObjectType | object_type | - | String | Object type (TASK, RSRC, etc.) |
| Value | value | - | String | UDF value (varies by type) |
| DateValue | date_value | - | DateTime | Date value (for DATE type UDFs) |
| NumberValue | number_value | - | Float | Number value (for NUMBER type UDFs) |
| Guid | guid | guid | String | Global unique identifier |
| CreateDate | create_date | create_date | DateTime | Creation timestamp |
| CreateUser | create_user | create_user | String | Creating user |
| UpdateDate | update_date | update_date | DateTime | Last update timestamp |
| UpdateUser | update_user | update_user | String | Last updating user |

### EXPENSE

| P6 REST Field | Domain Attribute | XER Column | Type | Description |
|---------------|------------------|------------|------|-------------|
| ObjectId | expense_id | - | Integer | Unique expense identifier |
| ProjectId | project_id | proj_id | Integer | Parent project identifier |
| TaskId | task_id | task_id | Integer | Associated task ID |
| CostAccountId | acct_id | acct_id | Integer | Cost account identifier |
| ExpenseType | expense_type | - | String | Expense type |
| Amount | amount | - | Float | Expense amount |
| CurrencyId | curr_id | curr_id | String | Currency identifier |
| DateIncurred | date_incurred | - | DateTime | Date expense incurred |
| Guid | guid | guid | String | Global unique identifier |
| CreateDate | create_date | create_date | DateTime | Creation timestamp |
| CreateUser | create_user | create_user | String | Creating user |
| UpdateDate | update_date | update_date | DateTime | Last update timestamp |
| UpdateUser | update_user | update_user | String | Last updating user |

### ACTIVITYCODE

| P6 REST Field | Domain Attribute | XER Column | Type | Description |
|---------------|------------------|------------|------|-------------|
| ObjectId | activity_code_id | - | Integer | Unique activity code identifier |
| ProjectId | project_id | proj_id | Integer | Parent project identifier |
| CodeType | code_type | - | String | Activity code type |
| Value | value | - | String | Activity code value |
| Description | description | - | String | Activity code description |
| Guid | guid | guid | String | Global unique identifier |
| CreateDate | create_date | create_date | DateTime | Creation timestamp |
| CreateUser | create_user | create_user | String | Creating user |
| UpdateDate | update_date | update_date | DateTime | Last update timestamp |
| UpdateUser | update_user | update_user | String | Last updating user |

## Enum Mappings

### Constraint Types (CstrType)

| P6 REST Value | Domain Enum | XER Value | Description |
|---------------|-------------|-----------|-------------|
| Must Finish On | MFOST | MSLF | Must finish on |
| Must Start On | MSOT | MSEL | Must start on |
| Start No Earlier Than | SNET | SNET | Start no earlier than |
| Finish No Earlier Than | FNET | FNET | Finish no earlier than |
| Start No Later Than | SNLT | SNLT | Start no later than |
| Finish No Later Than | FNLT | FNLT | Finish no later than |
| As Soon As Possible | ASAP | ASAP | As soon as possible |
| As Late As Possible | ALAP | ALAP | As late as possible |

### Relationship Types (PredType)

| P6 REST Value | Domain Enum | XER Value | Description |
|---------------|-------------|-----------|-------------|
| Finish to Start | FS | FS | Finish to Start |
| Start to Start | SS | SS | Start to Start |
| Finish to Finish | FF | FF | Finish to Finish |
| Start to Finish | SF | SF | Start to Finish |

### Duration Types

| P6 REST Value | Domain Enum | XER Value | Description |
|---------------|-------------|-----------|-------------|
| Hours | HR | HR | Hours |
| Days | DY | DAYS | Days |
| Weeks | WK | WEEKS | Weeks |
| Months | MO | MONTHS | Months |
| Years | YR | YEARS | Years |

### Percent Complete Types

| P6 REST Value | Domain Enum | XER Value | Description |
|---------------|-------------|-----------|-------------|
| Physical | PHYSICAL | PHYSICAL | Physical % complete |
| Duration | DURATION | DURATION | Duration % complete |
| Units | UNITS | UNITS | Units % complete |
| Effort | EFFORT | EFFORT | Effort % complete |

### Resource Types

| P6 REST Value | Domain Enum | XER Value | Description |
|---------------|-------------|-----------|-------------|
| Labor | LABOR | L | Labor |
| Nonlabor | NONLABOR | M | Material |
| Material | MATERIAL | M | Material |
| Expense | EXPENSE | E | Expense |

### Cost Quantity Types

| P6 REST Value | Domain Enum | XER Value | Description |
|---------------|-------------|-----------|-------------|
| Quantity | QTY | Q | Quantity-based |
| Cost | COST | C | Cost-based |

## Usage

This mapping is used automatically by the `P6EppmRepository` when:
1. Reading data from P6 EPPM via REST API
2. Writing data to P6 EPPM via REST API
3. Converting between P6 EPPM data and internal Schedule representation

Developers generally do not need to interact with this mapping directly unless extending support for additional P6 EPPM fields or services.