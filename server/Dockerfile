# Created: 2026-09-16
# Last Edited: 2026-09-16 18:31 CT (America/Chicago)
# Path: server/Dockerfile
# Purpose: Build the AetherVault zero-knowledge sync relay image.

FROM python:3.12-slim

WORKDIR /app
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    AETHERVAULT_DATA_DIR=/data \
    AETHERVAULT_HOST=0.0.0.0 \
    AETHERVAULT_PORT=8787

COPY server/requirements.txt ./server/requirements.txt
RUN pip install --no-cache-dir -r server/requirements.txt

COPY server ./server

RUN useradd --system --uid 10001 relay \
    && mkdir -p /data \
    && chown -R relay:relay /data /app
USER relay

EXPOSE 8787
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s \
    CMD python -c "import os,urllib.request; h=os.environ.get('AETHERVAULT_HOST','127.0.0.1'); h='127.0.0.1' if h in ('0.0.0.0','::') else h; urllib.request.urlopen('http://'+h+':'+os.environ.get('AETHERVAULT_PORT','8787')+'/healthz')" || exit 1

CMD ["/bin/sh", "-c", "uvicorn server.app:create_app --factory --host \"${AETHERVAULT_HOST}\" --port \"${AETHERVAULT_PORT}\""]
