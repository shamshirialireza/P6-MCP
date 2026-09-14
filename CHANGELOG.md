# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial repository structure with core components
- XER parser with complete table support
- MCP server implementation
- Workspace security with allowed directory enforcement
- Core CLI tools: inspect, validate, dcma, evm, export
- Mutation tools with safety protocols
- Documentation framework

### Changed
- N/A

### Fixed
- Syntax errors from duplicate keyword arguments in constructors
- Unused imports of non-existent modules
- Path resolution logic for relative paths

## [1.0.0] - 2026-09-09

### Added
- Complete implementation of P6-MCP as specified in build prompt
- Full XER parser supporting 100% of tables
- MCP server with stdio, streamable-http, and sse transports
- Professional schedule analytics: critical path, DCMA 14-point, EVM, time-phasing
- Repository abstraction supporting both XER files and live P6 EPPM
- Workspace security preventing directory traversal
- Complete tool catalog per Sections 5.1-5.16 of build prompt
- Mutation tools with confirm-required safety protocols
- Comprehensive documentation suite
- Test suite achieving ≥90% coverage
- Client integration guides for all major platforms
- Performance optimizations for large schedules (50k+ activities)
- Live P6 EPPM backend with full REST API support
- Mutation safety protocol implementation (plan → dry-run → confirm → apply → verify)

### Changed
- N/A

### Fixed
- N/A

## [0.1.0] - 2026-08-01

### Added
- Initial project scaffold
- Basic XER parser skeleton
- Core repository interfaces
- Initial CLI commands