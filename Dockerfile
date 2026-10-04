FROM node:22-alpine AS web
WORKDIR /build
COPY web/package*.json ./
RUN npm ci
COPY web/ ./
RUN npm run build

FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 AEGIS_HOST=0.0.0.0 AEGIS_DATA_DIR=/app/data AEGIS_WEB_DIR=/app/web/dist
WORKDIR /app
ARG AEGIS_INSTALL_POSTGRES=0
COPY pyproject.toml requirements.lock requirements-postgres.lock ./
COPY aegis/ aegis/
RUN pip install --no-cache-dir -r requirements.lock \
    && case "$AEGIS_INSTALL_POSTGRES" in 0) ;; 1) pip install --no-cache-dir -r requirements-postgres.lock ;; *) exit 2 ;; esac \
    && pip install --no-cache-dir --no-deps . \
    && pip check \
    && useradd --uid 10001 --create-home aegis
COPY --from=web /build/dist/ web/dist/
RUN mkdir -p /app/data && chown -R aegis:aegis /app
USER aegis
EXPOSE 8787
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s CMD ["python", "-m", "aegis.healthcheck"]
CMD ["python", "-m", "aegis"]
