# P6-MCP Roadmap

## v1.0.0 (Current Target)

### Core Features
- [x] Complete XER parser (100% table support)
- [x] MCP server implementation (stdio, streamable-http, sse transports)
- [x] Core CLI tools: inspect, validate, dcma, evm, export
- [x] Professional schedule analytics: critical path, DCMA 14-point, EVM
- [x] Repository abstraction layer (XER and P6 EPPM backends)
- [x] Workspace security (allowed directory enforcement)
- [x] Mutation tools with safety protocols (confirm required)
- [x] Basic documentation

### In Progress
- [ ] Live P6 EPPM backend completion and testing
- [ ] Comprehensive test suite (≥90% coverage)
- [ ] Performance optimization for large schedules (50k+ activities)
- [ ] Complete documentation set
- [ ] Client integration examples and guides

## Future Releases

### v1.1.0
- Enhanced P6 EPPM support (additional REST endpoints)
- Additional export formats (PDF, HTML)
- Advanced analytics: resource leveling, what-if scenarios
- Improved MCP resource templates
- Performance benchmarks and optimizations

### v1.2.0
- Web-based schedule viewer (optional)
- Advanced reporting dashboard
- Baseline management enhancements
- Multi-project EPS navigation
- Integration with project management tools

### v1.3.0
- AI-powered schedule optimization suggestions
- Natural language interface enhancements
- Real-time collaboration features
- Advanced risk analysis integration
- Mobile companion app

## Ongoing Efforts
- Continuous security audits and improvements
- Regular dependency updates
- Performance monitoring and optimization
- Community feedback incorporation
- Documentation maintenance and expansion

## Release Process

We follow [Semantic Versioning](https://semver.org/):
- **MAJOR** version for incompatible API changes
- **MINOR** version for backwards-compatible functionality additions
- **PATCH** version for backwards-compatible bug fixes

Release candidates will be tagged and tested before final release.
All releases include changelog entries and are published to:
- PyPI (Python package)
- Docker Hub/GHCR (container images)
- GitHub Releases
- MCP Registry

## Contributing to the Roadmap

We welcome community input on the roadmap! Please:
1. Review upcoming features in the Issues tab
2. Suggest new features or improvements via GitHub Issues
3. Vote on existing feature requests with reactions
4. Participate in Discussions about future direction

See [CONTRIBUTING.md](CONTRIBUTING.md) for more details on how to contribute.