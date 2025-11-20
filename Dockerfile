FROM ghcr.io/astral-sh/uv:python3.13-bookworm

WORKDIR /app

# Copy dependency manifests first to leverage Docker layer caching
ADD pyproject.toml uv.lock /app/

# Install dependencies (frozen to lockfile, skipping dev extras) into .venv
RUN uv sync --frozen --no-dev

# Now bring in the rest of the source
ADD . /app

ENV VIRTUAL_ENV=/app/.venv
ENV PATH="${VIRTUAL_ENV}/bin:${PATH}"
ENV PYTHONPATH /app

CMD ["python", "/app/src/main.py"]
