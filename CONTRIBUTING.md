# Contributing to P6-MCP

Thank you for considering contributing to P6-MCP! We welcome contributions from the community.

## Development Setup

1. **Fork and clone the repository**
   ```bash
   git clone https://github.com/your-username/P6-MCP.git
   cd P6-MCP
   ```

2. **Set up the development environment**
   We use [uv](https://docs.astral.sh/uv/) for dependency management:
   ```bash
   uv sync
   ```

3. **Install pre-commit hooks**
   ```bash
   uv run pre-commit install
   ```

4. **Run the test suite**
   ```bash
   uv run pytest
   ```

## Adding a New Tool

Follow these 5 steps to add a new MCP tool:

1. **Identify the service** - Determine which service module should contain the business logic (e.g., `services/analysis/` for analytics, `services/query/` for queries, `services/mutate/` for mutations)

2. **Implement the business logic** - Add the function to the appropriate service module, following existing patterns

3. **Create/update the MCP tool** - Add the tool to the appropriate module in `src/p6_mcp/mcp/tools/` (e.g., `activities.py`, `resources.py`)

4. **Register the tool** - Ensure the tool is registered in the module's `register()` function

5. **Add tests** - Write unit tests in unit tests in `tests/unit/` and integration tests in `tests/integration/`

## Coding Standards

- **Code formatting**: We use [ruff](https://docs.astral.sh/ruff/) for linting and formatting
- **Type hints**: All code must be fully type-annotated (`mypy --strict` clean)
- **Documentation**: Every public class/method must have a docstring
- **Module size**: No module > 600 lines
- **Function size**: No function > 60 lines
- **Naming**: Use descriptive, PEP-8 compliant names
- **Imports**: Group imports as standard library → third-party → local

## Git Workflow

1. Create a feature branch: `git checkout -b feature/your-feature-name`
2. Make your changes
3. Run tests: `uv run pytest`
4. Run linter: `uv run ruff check`
5. Format code: `uv run ruff format`
6. Commit with Conventional Commits: `git commit -m "feat: add new feature"`
7. Push to your fork: `git push origin feature/your-feature-name`
8. Open a Pull Request

## Commit Message Format

We use [Conventional Commits](https://www.conventionalcommits.org/):

- `feat:` - A new feature
- `fix:` - A bug fix
- `docs:` - Documentation changes
- `style:` - Formatting, missing semicolons, etc.
- `refactor:` - Code restructuring
- `perf:` - Performance improvements
- `test:` - Adding or correcting tests
- `chore:` - Build process or tooling changes

Examples:
- `feat: add get_activity_assignment_counts tool`
- `fix: resolve KeyError in critical path calculation`
- `docs: clarify EVM calculation methodology`
- `style: fix formatting in services/analysis/resources.py`
- `refactor: simplify WBS traversal logic`
- `perf: cache calendar working day calculations`
- `test: add unit tests for new cost analysis functions`
- `chore: update pre-commit hooks`

## Reporting Issues

Please use the GitHub issue tracker to report bugs or request features. Include:
- Clear description of the issue/feature request
- Steps to reproduce (for bugs)
- Expected vs actual behavior
- Relevant version information
- Any error messages or logs

## License

By contributing to P6-MCP, you agree that your contributions will be licensed under the MIT License.

## Questions?

Feel free to reach out via GitHub Issues or Discussions if you have any questions about contributing.