# syntax=docker/dockerfile:1
FROM python:3.14-slim AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1
WORKDIR /workspace
RUN useradd --create-home --uid 10001 support \
    && mkdir -p /workspace/data/runtime \
    && chown -R support:support /workspace

FROM base AS api
RUN apt-get update && apt-get install --yes --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*
COPY requirements.txt requirements-transformers.txt requirements-api.txt ./
RUN python -m pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch==2.15.0 \
    && python -m pip install --no-cache-dir -r requirements-api.txt
COPY app ./app
COPY src ./src
COPY config ./config
USER support
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "app.api:app", "--host", "0.0.0.0", "--port", "8000"]

FROM base AS dashboard
COPY docker/requirements-ui.txt ./requirements-ui.txt
RUN python -m pip install --no-cache-dir -r requirements-ui.txt
COPY app ./app
COPY .streamlit ./.streamlit
USER support
EXPOSE 8501
CMD ["python", "-m", "streamlit", "run", "app/dashboard.py", "--server.address", "0.0.0.0", "--server.port", "8501", "--server.headless", "true"]
