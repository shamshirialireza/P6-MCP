# Security Policy

## Supported Versions

We provide security updates for the following versions of P6-MCP:

| Version | Supported          |
|---------|--------------------|
| >= 1.0  | ✅                 |
| < 1.0   | ❌                 |

## Reporting a Vulnerability

To report a security vulnerability, please use the
[GitHub Security Advisory](https://github.com/alireza/P6-MCP/security/advisories)
or email security@alireza.sh (preferred method).

Please include:
- Description of the vulnerability
- Steps to reproduce
- Potential impact
- Any suggested fixes (if known)

We will acknowledge receipt of your report within 48 hours and provide a
detailed response within 5 business days outlining our plan to address the
issue.

## Security Features

P6-MCP implements several security measures to protect users and their data:

### Path Traversal Prevention
- All file paths are validated against an allowed-directory allowlist
- Symlinks are resolved to prevent bypassing restrictions
- Directory traversal attacks (e.g., `../../etc/passwd`) are blocked

### Mutation Safety
- All modification tools require explicit `confirm=True` parameter
- Dry-run mode available for previewing changes before application
- Snapshots taken before live P6 EPPM mutations for rollback capability
- Optimistic concurrency checking prevents lost updates

### Transport Security
- Support for stdio, streamable-http, and sse transports
- Bearer token authentication available for HTTP transports
- CORS configuration options for HTTP servers
- No shell execution or arbitrary code execution capabilities

### Data Protection
- Credentials never stored in logs or error messages
- Sensitive data can be excluded from outputs via field selection
- Audit logging available for live P6 EPPM connections

## Best Practices for Users

1. **Use allowed directories** - Start the server with `--allowed-dir` to specify accessible locations
2. **Review mutation plans** - Always review dry-run output before confirming changes
3. **Keep dependencies updated** - Regularly update to receive security patches
4. **Monitor audit logs** - Review audit logs for live P6 EPPM connections
5. **Use least privilege** - Configure P6 EPPM connections with minimal required permissions

## Dependency Security

We monitor our dependencies for known vulnerabilities using:
- GitHub Dependabot
- Regular manual reviews
- Security scanning in CI/CD pipeline

Please report any dependency security concerns through the vulnerability reporting process above.

## Acknowledgments

We thank all security researchers and users who responsibly disclose
vulnerabilities to help make P6-MCP safer for everyone.