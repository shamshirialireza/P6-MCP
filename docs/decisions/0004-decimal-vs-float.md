# ADR 0004: Decimal vs Float for Monetary Values

## Status
Accepted

## Context
We need to represent monetary values (costs, budgets, actuals, etc.) in the P6-MCP domain model. Financial precision is critical for Earned Value Management and cost analysis.

Options considered:
1. Use Python's `float` type (IEEE 754 double-precision)
2. Use Python's `Decimal` type (exact decimal representation)
3. Use integers representing smallest currency unit (cents)

## Decision
We chose to use Python's `Decimal` type for all monetary values.

## Rationale
### Why Decimal over Float:
1. **Exact Representation**: Decimal can exactly represent decimal fractions like 0.1, 0.01, etc., which float cannot do accurately due to binary representation limitations
2. **Financial Accuracy**: Prevents rounding errors that accumulate in EVM calculations (CV, SV, CPI, SPI, EAC, etc.)
3. **Audit Trail Compatibility**: Matches P6's internal representation which uses fixed-point decimals
4. **Predictable Behavior**: No surprises from floating-point precision issues in equality comparisons or calculations
5. **Industry Standard**: Financial software commonly uses Decimal for monetary values

### Why Not Float:
1. **Representation Errors**: 0.1 + 0.2 ≠ 0.3 in floating-point arithmetic
2. **Accumulation Errors**: Small errors in individual calculations can accumulate significantly in EVM formulas
3. **Equality Problems**: Difficult to reliably compare financial values due to precision issues
4. **Reporting Inconsistencies**: May show values like 1234.9999999999 instead of 1235.00

### Why Not Integer Cents:
1. **Complexity**: Requires constant conversion between display values and stored values
2. **Division Complications**: Calculating rates, percentages, and averages requires careful handling
3. **Readability**: Makes code harder to read and understand (is 123456 $1,234.56 or 12,345.60?)
4. **Currency Assumptions**: Assumes all currencies use 1/100 subunits (not true for all currencies)
5. **Flexibility**: Less adaptable if P6 ever changes its precision model

## Consequences
### Positive
- Exact financial calculations with no precision loss
- Reliable equality and comparison operations
- Matches user expectations for financial software
- Clear semantics for monetary values throughout the codebase
- Compatible with P6's internal representation

### Negative
- Slightly higher memory usage per value (Decimal vs float)
- Marginally slower arithmetic operations
- Need to remember to convert from float when interacting with some libraries
- Slightly more verbose initialization (Decimal('10.50') vs 10.50)

## Implementation Plan
All monetary values in the domain model will use `Decimal`:
- Cost fields: budgeted_cost, actual_cost, remaining_cost
- Quantity fields: when representing monetary quantities
- EVM fields: BAC, PV, EV, AC, CV, SV, EAC, ETC, VAC
- Rate fields: cost per quantity, hourly rates
- Any field representing currency value

### Conversion Guidelines
1. **From String**: Use `Decimal(string_value)` to avoid float intermediate
   ```python
   cost = Decimal(raw_string)  # Correct
   cost = Decimal(float(raw_string))  # Incorrect - loses precision
   ```

2. **From Float**: Only when unavoidable, and prefer string conversion
   ```python
   # Only if you absolutely have a float and know its limitations
   cost = Decimal(str(float_value)) 
   ```

3. **To String for Display**: Use `str(decimal_value)` or formatting
   ```python
   display = f"{cost:.2f}"  # Always show 2 decimal places for currency
   ```

4. **Arithmetic Operations**: Safe to use standard operators
   ```python
   remaining = budget - actual  # Exact with Decimal
   variance = budget_actual - actual_actual
   ```

5. **Aggregation**: Use standard sum operations
   ```python
   total_cost = sum(task.cost for task in tasks)  # Exact
   ```

### Schema and Serialization
- In Pydantic models: Use `Decimal` type with appropriate validation
- JSON serialization: Convert to string to preserve precision
- XER writing: Convert to string with appropriate decimal places
- Database storage: Store as string or numeric depending on backend

## Related Decisions
- 0001: Own Parser vs Third-Party XER Libraries
- 0002: REST vs SOAP vs SQL for live P6 EPPM backend
- 0003: Changeset/snapshot safety model
- 0005: CPM recompute scope
- 0006: Mutation safety model
- 0007: Output-size guard design
- 0008: Transport/authentication choices

## References
- [Python Decimal Documentation](https://docs.python.org/3/library/decimal.html)
- [Build Prompt Section 13.7](file:///Users/alireza/Downloads/P6-MCP-build-prompt.md#137-coding-standards) - "All thresholds/constants centralized in `services/analysis/thresholds.py`"
- IEEE 754-2008 Standard for Floating-Point Arithmetic
- Martin Fowler's "Money" pattern analysis