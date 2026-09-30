# Backend container image. Build from the repository root:
#   docker build -t hobby-tracker-api .
#   docker run -p 8000:8000 --env-file .env hobby-tracker-api
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ backend/
COPY cloud/ cloud/
COPY analytics/ analytics/

EXPOSE 8000
CMD ["uvicorn", "backend.app:app", "--host", "0.0.0.0", "--port", "8000"]
