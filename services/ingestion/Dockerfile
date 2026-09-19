FROM python:3.11-slim

RUN apt-get update && apt-get install -y tesseract-ocr libtesseract-dev && apt-get clean

WORKDIR /app

COPY services/ingestion/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy ml module and ingestion code
COPY ml/ ./ml/
COPY services/ingestion/ ./ingestion/

WORKDIR /app/ingestion

CMD ["celery", "-A", "worker", "worker", "--loglevel=info"]
