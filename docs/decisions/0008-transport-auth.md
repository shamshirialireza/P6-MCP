# ADR 0008: Transport and Authentication Choices

## Status
Accepted

## Context
We need to support multiple transport mechanisms for MCP communication and provide flexible authentication options for different deployment scenarios. The build prompt requires support for stdio, streamable-http, and sse transports, as well as authentication for HTTP transports.

Options considered for transports:
1. Standard IO (stdio) only
2. Standard IO + WebSocket
3. Standard IO + HTTP (Streamable HTTP and SSE)
4. Multiple transport abstraction layer
5. Remote procedure call (gRPC, Thrift, etc.)

Options considered for authentication:
1. No authentication (trusted environments only)
2. API keys / bearer tokens
3. OAuth 2.0
4. Mutual TLS (mTLS)
5. Custom authentication schemes

## Decision
We chose to support **stdio, streamable-http, and sse transports** with **bearer token authentication** for HTTP transports.

## Rationale
### Why These Transports:
1. **stdio** - Required for MCP standard integration with Claude Desktop, Claude Code, and other local clients
   - Simplest deployment: no network configuration needed
   - Works with uvx/pipx installations
   - Standard MCP interface for local tool usage
   - Required by build prompt Section 8

2. **Streamable HTTP** - Modern HTTP-based MCP transport
   - Enables remote access over HTTP/S
   - Supports proxying, load balancing, and standard HTTP infrastructure
   - Better firewall compatibility than custom ports
   - Aligns with MCP specification evolution
   - Required by build prompt Section 8

3. **SSE (Server-Sent Events)** - Legacy HTTP transport for MCP
   - Backward compatibility with older MCP clients
   - Simpler than WebSockets for server-to-client streaming
   - Widely supported in HTTP infrastructure
   - Required by build prompt Section 8 for completeness

### Why Not Other Transports:
- **WebSocket**: More complex than needed; Streamable HTTP and SSE cover HTTP-based requirements
- **gRPC/Thrift**: Would require custom MCP adapter layers; deviates from standard MCP
- **Custom TCP/UDP**: Increases attack surface and complicates firewall configuration
- **Only stdio**: Would prevent remote deployment and enterprise use cases

### Why Bearer Token Authentication:
1. **Simplicity**: Easy to understand, implement, and use
2. **Standards Alignment**: Widely used in APIs (GitHub, Google Cloud, etc.)
3. **Flexibility**: Works with various token sources (static, dynamic, keyring, etc.)
4. **HTTP Standard**: Fits naturally with HTTP Authorization headers
5. **Build Prompt Compliance**: Section 8 mentions `P6MCP_AUTH_TOKEN` (bearer for HTTP)
6. **Sufficient Security**: When combined with HTTPS/TLS, provides adequate protection

### Why Not Other Authentication Schemes:
- **No Authentication**: Insecure for any network-exposed deployment
- **API Keys**: Less flexible than bearer tokens (can't easily integrate with OAuth, SSO, etc.)
- **OAuth 2.0**: Overly complex for many use cases; bearer tokens can carry OAuth tokens
- **mTLS**: Excellent security but significantly increases complexity and deployment friction
- **Custom Schemes**: Non-standard, harder to integrate with existing infrastructure

## Consequences
### Positive
- Supports all required transport mechanisms from build prompt
- Flexible authentication suitable for various deployment scenarios
- stdio enables simple local usage with tools like uvx
- HTTP transports enable remote access and enterprise deployment
- Bearer tokens work well with HTTPS/TLS for secure communication
- Aligns with MCP ecosystem standards
- Clear separation of concerns: transport vs authentication

### Negative
- Multiple transports increase implementation complexity slightly
- Need to ensure consistent behavior across transports
- Bearer tokens require careful secret management
- HTTP transports introduce additional attack surface vs stdio-only
- SSE legacy support adds maintenance overhead

## Implementation Plan
### Transport Layer
- `src/p6_mcp.mcp.server.build_server()` - Creates MCP server instance
- `src/p6_mcp.transport` - Handles stdio, streamable-http, and sse transport running
- CLI argument `--transport stdio|streamable-http|sse` (default: stdio)
- Environment variable `P6MCP_TRANSPORT` for configuration

### Authentication for HTTP Transports
- Bearer token support via `Authorization: Bearer <token>` header
- Token sourced from:
  1. `P6MCP_AUTH_TOKEN` environment variable (highest priority)
  2. `_password_keyring=true` configuration for keyring retrieval
  3. Future: support for token refresh scripts
- Automatic WWW-Authenticate challenge on 401 responses
- Works with both streamable-http and sse transports
- Disabled for stdio transport (not applicable)

### Implementation Components
- `src/p6_mcp.mcp.server` - Server creation and transport integration
- `src/p6_mcp.transport` - Transport runners for stdio, HTTP, SSE
- `src/p6_mcp.mcp.server.py` - Authentication middleware for HTTP transports
- `src/p6_mcp.config.Settings` - Configuration for transports and auth
- `src/p6_mcp.cli.py` --transport flag and related options

### Security Considerations
- All HTTP transports should be used with HTTPS/TLS in production
- Bearer tokens treated as secrets - never logged or exposed
- Consider short-lived tokens for high-security environments
- Token revocation strategy important for compromised tokens
- HTTP transports enable standard infrastructure security (WAF, IDS, etc.)

## Related Decisions
- 0001: Own Parser vs Third-Party XER Libraries
- 0002: REST vs SOAP vs SQL for live P6 EPPM backend
- 0003: Changeset/snapshot safety model
- 0004: Decimal vs float for monetary values
- 0005: CPM recompute scope
- 0006: Mutation safety model
- 0007: Output-size guard design

## References
- [Build Prompt Section 8](file:///Users/alireza/Downloads/P6-MCP-build-prompt.md#8-transports-configuration-security) - "CLI: `p6-mcp serve --transport stdio|streamable-http|sse --host --port --path /mcp --allowed-dir DIR (repeatable) --output-dir DIR --cache-size N --max-output-bytes N --log-level --log-json`"
- [Build Prompt Section 8](file:///Users/alireza/Downloads/P6-MCP-build-prompt.md#8-transports-configuration-security) - "Env vars: `P6MCP_AUTH_TOKEN` (bearer for HTTP)"
- [Build Prompt Section 8.4](file:///Users/alireza/Downloads/P6-MCP-build-prompt.md#84-mcp-protocol-compliance) - "MCP protocol compliance: capabilities negotiation, tool annotations, progress notifications..."
- MCP Specification: Transport Mechanisms
- RFC 6750: Bearer Token Usage in OAuth 2.0
- Server-Sent Events W3C Recommendation