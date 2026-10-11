FROM python:3.11-slim
RUN apt-get update && apt-get install -y --no-install-recommends build-essential cmake ninja-build git && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
COPY templates ./templates
ENV PYTHONUNBUFFERED=1
EXPOSE 10000
CMD ["sh", "-c", "gunicorn -w 1 --threads 2 --timeout 600 -b 0.0.0.0:${PORT:-10000} app:app"]
