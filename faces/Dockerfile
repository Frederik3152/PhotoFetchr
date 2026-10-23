FROM python:3.12-slim

# insightface compiles a small C++ extension when it is installed
RUN apt-get update && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /faces
RUN pip install --no-cache-dir uv==0.11.7
COPY pyproject.toml uv.lock ./
RUN UV_PYTHON_DOWNLOADS=never uv sync --frozen --no-install-project --python /usr/local/bin/python3

COPY *.py schema.sql calibration.json ./

ENV PATH="/faces/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

# The face model (~280 MB) is downloaded on first start into /root/.insightface;
# docker-compose keeps that directory on a volume.
EXPOSE 8901
CMD ["gunicorn", "-b", "0.0.0.0:8901", "-w", "1", "--threads", "2", "--timeout", "120", "service:app"]
