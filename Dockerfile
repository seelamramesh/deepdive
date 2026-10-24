FROM node:24-slim AS frontend
WORKDIR /ui
COPY frontend/package*.json ./
COPY frontend/.npmrc ./
RUN npm ci
COPY frontend/ ./
RUN npm run build
RUN npm test

FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
COPY --from=frontend /ui/dist ./frontend/dist

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
