# syntax=docker/dockerfile:1
FROM python:3.11-slim AS builder
WORKDIR /build
RUN pip install --no-cache-dir uv
COPY pyproject.toml uv.lock* ./
COPY src/ ./src/
RUN uv pip install --system --no-cache ".[http]"

FROM python:3.11-slim
WORKDIR /app
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin/p6-mcp /usr/local/bin/p6-mcp
COPY src/ ./src/
RUN useradd -m -u 1000 appuser \
    && mkdir -p /data /tmp/p6mcp_output \
    && chown -R appuser /app /data /tmp/p6mcp_output
USER appuser
EXPOSE 8000
ENV P6MCP_WORKSPACE_DIRS=/data \
    P6MCP_OUTPUT_DIR=/tmp/p6mcp_output \
    P6MCP_ENABLE_MUTATION=false
VOLUME ["/data"]
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import p6_mcp" || exit 1
ENTRYPOINT ["p6-mcp", "serve", "--transport", "streamable-http", "--host", "0.0.0.0", "--port", "8000"]
