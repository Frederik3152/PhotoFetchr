FROM python:3.12-slim

WORKDIR /app
RUN pip install --no-cache-dir uv==0.11.7
COPY pyproject.toml uv.lock ./

ENV UV_PROJECT_ENVIRONMENT=/opt/venv
RUN UV_PYTHON_DOWNLOADS=never uv sync --frozen --no-install-project --python /usr/local/bin/python3

COPY . .

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1

CMD ["python", "app.py"]
