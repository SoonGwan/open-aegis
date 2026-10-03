FROM node:22-alpine AS web
WORKDIR /build
COPY web/package*.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 AEGIS_HOST=0.0.0.0 AEGIS_DATA_DIR=/app/data AEGIS_WEB_DIR=/app/web/dist
WORKDIR /app
COPY pyproject.toml requirements.lock ./
COPY aegis/ aegis/
RUN pip install --no-cache-dir -r requirements.lock && pip install --no-cache-dir --no-deps . && useradd --uid 10001 --create-home aegis
COPY --from=web /build/dist/ web/dist/
RUN mkdir -p /app/data && chown -R aegis:aegis /app
USER aegis
EXPOSE 8787
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8787/api/health',timeout=3)"
CMD ["python", "-m", "aegis"]
