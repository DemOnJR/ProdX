FROM python:3.14.5-slim

# Pick up the latest debian-slim package patches at build time. The
# python:3.12-slim base tracks debian-12-slim, which gets security backports
# faster than the python image is rebuilt. Without this `apt-get upgrade`,
# Trivy finds CRITICAL CVEs that already have fixed debian packages available.
RUN apt-get update \
    && apt-get upgrade -y --no-install-recommends \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
