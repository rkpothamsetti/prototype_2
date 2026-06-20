FROM python:3.11-slim-bookworm

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Helmet YOLO weights (optional — app falls back if missing)
RUN mkdir -p data/models && \
    curl -fsSL -o data/models/helmet_yolo.pt \
    "https://huggingface.co/iam-tsr/yolov8n-helmet-detection/resolve/main/best.pt" \
    || echo "helmet model download skipped"

ENV PYTHONUNBUFFERED=1
ENV TV_WARMUP_ENABLED=true
ENV TV_WARMUP_BLOCKING=true

EXPOSE 10000

CMD uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-10000}
