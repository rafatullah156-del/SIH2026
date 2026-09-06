FROM python:3.11-slim

WORKDIR /code

ENV PYTHONPATH=/code
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# OpenCV / onnxruntime system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 libglib2.0-0 libsm6 libxext6 libxrender1 libgomp1 \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir --upgrade pip

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Build-time sanity check: OCR engine + bundled models load correctly
RUN python -c "from rapidocr_onnxruntime import RapidOCR; RapidOCR(); print('OCR engine OK')"

COPY app ./app

EXPOSE 8000
# Render start script
COPY start_render.sh ./start_render.sh
RUN chmod +x /code/start_render.sh
