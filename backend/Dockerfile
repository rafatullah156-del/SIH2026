FROM python:3.11-slim

WORKDIR /code

ENV PYTHONPATH=/code
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# System deps: OpenCV + Tesseract OCR
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 libsm6 libxext6 libxrender1 libgomp1 \
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-hin \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --upgrade pip

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

EXPOSE 8000
COPY start_render.sh ./start_render.sh
RUN chmod +x /code/start_render.sh

# Start the API (and the Celery worker) when the container runs.
# Without this, the image inherits python:3.11-slim's default CMD ["python3"],
# which exits straight away, so the container starts and stops doing nothing.
CMD ["./start_render.sh"]
