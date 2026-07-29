# Multi-stage build. The models are fetched in the builder so the runtime
# image needs no network access, and the final stage runs as a non-root user
# with no build toolchain present.
#
# No `# syntax=` directive on purpose: pinning an external frontend image makes
# the build depend on resolving docker/dockerfile at build time, which fails in
# networks that reach the registry only through a proxy. Everything used here
# (cache mounts, multi-stage, --chown) is supported by BuildKit's built-in
# frontend.

# --------------------------------------------------------------------------
# Stage 1: dependencies + models
# --------------------------------------------------------------------------
FROM python:3.13-slim AS builder

COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /usr/local/bin/uv

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# Dependencies are resolved before the source is copied, so editing a router
# does not invalidate the (slow) dependency layer.
COPY pyproject.toml ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv venv /opt/venv && \
    VIRTUAL_ENV=/opt/venv uv pip install -r pyproject.toml

# Fetch and verify the ONNX models. Digests are pinned in the script; a
# mismatch fails the build rather than shipping an unverified model.
COPY scripts/ ./scripts/
RUN /opt/venv/bin/python scripts/fetch_models.py --dest /opt/models

# --------------------------------------------------------------------------
# Stage 2: test
#
# A separate target so the runtime image carries neither pytest nor the test
# suite. Run it with:  docker compose run --rm tests
# --------------------------------------------------------------------------
FROM builder AS test

RUN --mount=type=cache,target=/root/.cache/uv \
    VIRTUAL_ENV=/opt/venv uv pip install -r pyproject.toml --extra dev

COPY src/ ./src/
COPY tests/ ./tests/

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH=/app/src \
    PYTHONUNBUFFERED=1 \
    FZIP_MODEL_DIR=/opt/models

CMD ["pytest", "tests", "-q"]

# --------------------------------------------------------------------------
# Stage 3: runtime
# --------------------------------------------------------------------------
FROM python:3.13-slim AS runtime

# opencv-python-headless still needs libGL's ABI companions for its imgcodecs
# path. Headless spares us the full X11 stack that plain opencv-python drags in.
RUN apt-get update && \
    apt-get install -y --no-install-recommends libglib2.0-0 curl && \
    rm -rf /var/lib/apt/lists/*

# Unprivileged. A container process that does not need root should not have it:
# it turns a container escape from a full host compromise into a limited one.
RUN groupadd --system --gid 1001 fzip && \
    useradd --system --uid 1001 --gid fzip --no-create-home fzip

COPY --from=builder /opt/venv /opt/venv
COPY --from=builder --chown=fzip:fzip /opt/models /app/models

WORKDIR /app
COPY --chown=fzip:fzip src/ ./src/
COPY --chown=fzip:fzip scripts/ ./scripts/
COPY --chown=fzip:fzip pyproject.toml ./

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH=/app/src \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    FZIP_MODEL_DIR=/app/models

USER fzip
EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=40s --retries=5 \
    CMD curl -fsS http://localhost:8000/healthz || exit 1

CMD ["uvicorn", "fzip_server.main:app", \
     "--host", "0.0.0.0", "--port", "8000", \
     "--proxy-headers", "--forwarded-allow-ips", "*"]
