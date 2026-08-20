# Root Dockerfile — delegates to umbrella-core-CURRENT.
# Render builds from the repo root, so we need this here.
FROM python:3.12-slim

WORKDIR /app

COPY umbrella-core-CURRENT/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY umbrella-core-CURRENT/ .

EXPOSE 8765

CMD ["python", "main.py"]
