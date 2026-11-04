# Multi-stage build; runtime is Chainguard distroless (no shell, no package manager, nonroot).
# The venv can't be copied as-is: its bin/python symlinks to the build image's
# /usr/local/bin/python, which Chainguard doesn't have — so copy site-packages into
# Chainguard's own site-packages and run via `python -m uvicorn`.
FROM python:3.15-slim AS build
COPY --from=ghcr.io/astral-sh/uv:0.13.6 /uv /bin/
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev

FROM cgr.dev/chainguard/python:latest
WORKDIR /app
# glob: the chainguard "latest" tag moves Python versions; don't hardcode 3.15
COPY --from=build /app/.venv/lib/python3.*/site-packages /app/sp/
ENV PYTHONPATH=/app/sp
COPY main.py qmenu_http.py ./
# chainguard python image already has ENTRYPOINT ["/usr/bin/python"]
CMD ["-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
