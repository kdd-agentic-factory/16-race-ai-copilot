FROM node:20.18.0-slim AS frontend-build

WORKDIR /app/frontend

COPY frontend/package.json ./
RUN npm install --legacy-peer-deps

COPY frontend/ .
RUN npm run build


FROM python:3.12.7-slim AS backend

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONPATH=/app/src

RUN apt-get update && apt-get install -y --no-install-recommends gcc && \
    apt-get clean && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

COPY backend/src ./src
COPY --from=frontend-build /app/frontend/dist ./static

RUN addgroup --system kdd && adduser --system --ingroup kdd --uid 1000 kdd \
    && chown -R kdd:kdd /app

USER kdd

EXPOSE 8160

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8160/health')" || exit 1

CMD ["uvicorn", "race_ai_copilot.main:app", "--host", "0.0.0.0", "--port", "8160"]
