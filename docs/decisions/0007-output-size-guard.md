# ADR 0007: Output Size Guard Design

## Status
Accepted

## Context
We need to prevent MCP tool outputs from exceeding model context windows, which could cause failures or degraded performance when used with LLMs. The build prompt requires output size guards to truncate responses when they exceed a configurable byte budget.

Options considered:
1. No size limits (return full results)
2. Hard truncation at fixed limit
3. Configurable byte budget with continuation tokens
4. Streaming responses for large result sets
5. Pagination with offset/limit parameters

## Decision
We chose to implement a configurable byte budget with continuation tokens and truncation flags, combined with standard pagination.

## Rationale
### Why Configurable Byte Budget with Continuation Tokens:
1. **LLM Safety**: Prevents overwhelming model context windows with excessively large responses
2. **User Control**: Administrators can tune limits based on their specific LLM configurations
3. **Transparency**: Clear indication when truncation occurs via `truncated: true` flag
4. **Continuation Support**: Continuation tokens allow users to retrieve remaining results
5. **Standards Alignment**: Matches MCP specification for pagination cursors and structured content
6. **Build Prompt Compliance**: Directly implements requirement from Section 5.7: "Output-size guard: if serialized output exceeds a configurable byte budget, truncate `items`, set `truncated: true`, and include `next_offset`."

### Why Not Hard Truncation at Fixed Limit:
1. **Inflexibility**: Different LLMs have different context window sizes
2. **Deployment Variability**: Users may deploy with different LLM backends (Claude, GPT, local models, etc.)
3. **Use Case Differences**: Some users may prioritize completeness over safety in controlled environments

### Why Not Streaming Responses:
1. **MCP Limitations**: Current MCP specification doesn't fully support streaming for tool responses
2. **Complexity**: Significantly increases implementation complexity on both client and server sides
3. **Buffering Issues**: Middleware/proxies may not handle streaming correctly
4. **Partial Failure Handling**: Difficult to handle errors part-way through a stream

### Why Not Pagination Alone:
1. **Still Risky**: Even with pagination, a single page could be too large for context windows
2. **No Size Awareness**: Offset/limit doesn't prevent oversized pages
3. **Requires Two Mechanisms**: Need both pagination (for navigation) and size guards (for safety)

## Consequences
### Positive
- Protects LLM context windows from overload
- Provides clear indication when data is incomplete
- Allows retrieval of complete dataset through continuation
- Configurable to match deployment requirements
- Aligns with MCP specification and best practices

### Negative
- Increased complexity in response handling
- Need to manage continuation token lifecycle
- Slightly more complex client logic to handle continuation
- Edge cases around token expiration and validity

## Implementation Plan
The output size guard will be implemented in `src/p6_mcp.mcp.limits` with the following behavior:

### Configuration
- `--max-output-bytes N` CLI flag (default: 65536 bytes / 64KB)
- `P6MCP_MAX_OUTPUT_BYTES` environment variable
- Configurable per server instance

### Response Structure
All list-type tool responses will follow this envelope:
```json
{
  "total": 150,           // Total number of items available
  "offset": 0,            // Current offset in the result set
  "limit": 100,           // Maximum number of items requested
  "returned": 100,        // Number of items actually returned in this response
  "truncated": false,     // True if items were truncated due to size limits
  "next_offset": 100,     // Offset for next page (if not truncated, offset + returned)
  "items": [              // Array of result items
    { /* item 1 */ },
    { /* item 2 */ },
    // ...
  ]
}
```

### Size Calculation
1. Serialize the complete response to JSON
2. Measure byte length of UTF-8 encoded JSON
3. If length ≤ budget: return complete response
4. If length > budget: 
   - Truncate `items` array to fit within budget
   - Set `truncated: true`
   - Calculate `next_offset` based on how many items were included
   - Include continuation information

### Truncation Strategy
1. **Preserve Structure**: Keep all response fields except truncate `items` array
2. **Maintain Order**: Return items in original sort order
3. **Consistent Offsets**: `next_offset` correctly points to next item after truncated set
4. **Empty Pages**: If even the first item exceeds budget, return empty items array with `truncated: true`

### Special Considerations
1. **Large Individual Items**: If a single item would exceed the budget:
   - Return empty items array
   - Set `truncated: true`
   - Set `next_offset` to 0 (indicating need to handle large item separately)
   - Consider implementing item-level truncation for specific data types in future

2. **Continuation Tokens**: For now using offset-based continuation; may evolve to opaque tokens
   - Current: `next_offset` is numeric offset for next page
   - Future: Could implement opaque continuation tokens for more flexible paging

3. **Different Formats**: Apply size guard to JSON, CSV, and Markdown outputs
   - For CSV/Markdown: Calculate size of formatted output
   - Truncate rows rather than fields when necessary

### Implementation Components
- `src/p6_mcp.mcp.limits` - Core size checking and truncation logic
- `src/p6_mcp.mcp.tools.*` - Individual tools use limits helpers
- `src/p6_mcp.mcp.tools.exports` - Export tools with size considerations
- `src/p6_mcp.mcp.content` - Content emission helpers that respect limits
- `src/p6_mcp.mcp.schemas` - Pydantic models that define response structure

## Related Decisions
- 0001: Own Parser vs Third-Party XER Libraries
- 0002: REST vs SOAP vs SQL for live P6 EPPM backend
- 0003: Changeset/snapshot safety model
- 0004: Decimal vs float for monetary values
- 0005: CPM recompute scope
- 0006: Mutation safety model
- 0008: Transport/authentication choices

## References
- [Build Prompt Section 5.7](file:///Users/alireza/Downloads/P6-MCP-build-prompt.md#57-output-size-guard-if-serialized-output-exceeds-a-configurable-byte-budget-truncate-items-set-truncated-true-and-include-next_offset)
- [Build Prompt Section 8.4](file:///Users/alireza/Downloads/P6-MCP-build-prompt.md#84-mcp-protocol-compliance) - "pagination cursors for `tools/list`/`resources/list` if large"
- MCP Specification: Pagination and Resource Navigation
- HTTP Range Requests (RFC 7233) for inspiration on continuation patterns
- GitHub GraphQL API pagination implementation