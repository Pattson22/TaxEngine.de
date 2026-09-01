# Multi-stage build for the FastAPI web process AND the eric-submitter
# worker -- the same image serves both (docker-compose.yml overrides the
# CMD for the worker service). This image must NEVER load the real ERiC
# library at web-process startup (see app/eric/native_bindings.py's
# module docstring): the ERiC SDK itself is never baked in here either
# way. The worker gets it via a bind-mounted volume + ERIC_SDK_PATH at
# container runtime, exactly like local development.

FROM python:3.12-slim AS builder

WORKDIR /app

# gcc/libffi-dev are only needed to build cffi/argon2-cffi from source
# on platforms without a prebuilt wheel (e.g. arm64) -- discarded after
# this stage so they don't bloat the runtime image.
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libffi-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

FROM python:3.12-slim AS runtime

WORKDIR /app

COPY --from=builder /install /usr/local
COPY app ./app
COPY alembic ./alembic
COPY alembic.ini .

RUN useradd --create-home --uid 1000 taxengine
USER taxengine

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
