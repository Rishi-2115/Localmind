FROM python:3.11-slim

WORKDIR /app

# Copy requirements from services/api
COPY services/api/requirements.txt .
RUN pip install --no-cache-dir --retries 10 --timeout 120 -i https://pypi.org/simple/ -r requirements.txt

# Copy the ml module
COPY ml/ ./ml/

# Copy the api app
COPY services/api/app/ ./app/

# We also need to copy the api directory if it has __init__.py but app/ is enough
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
