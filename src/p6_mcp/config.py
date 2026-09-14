"""Runtime settings for the p6-mcp server.

Settings come from (highest precedence first) CLI flags, environment variables
prefixed ``P6MCP_``, a ``.env`` file, and documented defaults.
"""

from __future__ import annotations

from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All server-wide knobs. See ``.env.example`` for documentation."""

    model_config = SettingsConfigDict(
        env_prefix="P6MCP_", env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    allowed_dirs: list[Path] = Field(
        default_factory=list,
        description="Directories .xer files may be read from (path-traversal guarded).",
    )
    output_dir: Path | None = Field(
        default=None,
        description="Directory exports and mutated XER files are written to. "
        "Defaults to the first allowed directory.",
    )
    cache_size: int = Field(
        default=1000, ge=1, description="Max parsed schedules kept in LRU cache."
    )
    max_output_bytes: int = Field(
        default=65536,
        ge=1_000,
        description="Serialized tool-output byte budget before truncation.",
    )
    default_encoding: str | None = Field(
        default=None, description="Force an encoding (cp1252/utf-8/...) instead of auto-detection."
    )
    log_level: str = Field(default="INFO")
    log_json: bool = Field(default=False)
    enable_mutation: bool = Field(
        default=True,
        description="Enable write-back tools. Forced off over HTTP unless explicitly set.",
    )
    read_only: bool = Field(
        default=False, description="Hard read-only mode: hides all mutation/export-write tools."
    )
    auth_token: str | None = Field(
        default=None, description="Bearer token required for HTTP transports when set."
    )
    default_limit: int = Field(default=100, ge=1, description="Default page size for list tools.")
    max_limit: int = Field(default=1000, ge=1, description="Maximum page size for list tools.")

    @field_validator("allowed_dirs", mode="before")
    @classmethod
    def _split_dirs(cls, v: object) -> object:
        if isinstance(v, str):
            return [p for p in v.split(":") if p]
        return v

    def resolved_allowed_dirs(self) -> list[Path]:
        """Absolute, resolved allowed directories."""
        if not self.allowed_dirs:
            return [Path.cwd().expanduser().resolve()]
        return [p.expanduser().resolve() for p in self.allowed_dirs]

    def resolved_output_dir(self) -> Path:
        """Absolute output directory (first allowed dir when unset)."""
        if self.output_dir is not None:
            base = self.output_dir
        else:
            base = self.resolved_allowed_dirs()[0]
        return base.expanduser().resolve()

    def mutation_allowed(self) -> bool:
        """Whether mutation tools may run."""
        return self.enable_mutation and not self.read_only
