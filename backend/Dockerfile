FROM python:3.12-slim AS python-base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    XDG_CACHE_HOME=/tmp/.cache

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    tini \
    libpango-1.0-0 \
    libharfbuzz0b \
    libpangoft2-1.0-0 \
    libgdk-pixbuf-xlib-2.0-0 \
    libgobject-2.0-0 \
    libglib2.0-0 \
    libcairo2 \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

FROM python-base AS deps-prod
COPY requirements/base.txt /tmp/requirements/base.txt
RUN pip install --no-cache-dir -r /tmp/requirements/base.txt

FROM python-base AS deps-dev
COPY requirements/base.txt /tmp/requirements/base.txt
COPY requirements/dev.txt /tmp/requirements/dev.txt
RUN pip install --no-cache-dir -r /tmp/requirements/dev.txt

FROM deps-dev AS dev
COPY ./app /app/app
COPY ./alembic /app/alembic
COPY ./alembic.ini /app/alembic.ini
COPY ./scripts /app/scripts
COPY ./tests /app/tests
RUN chmod +x /app/scripts/*.sh \
    && mkdir -p /var/lib/pmm/artifacts /var/lib/pmm/backups /var/log/pmm /tmp/.cache/fontconfig
EXPOSE 8000
ENTRYPOINT ["tini", "--"]
CMD ["/app/scripts/start-backend-dev.sh"]

FROM deps-prod AS prod
COPY ./app /app/app
COPY ./alembic /app/alembic
COPY ./alembic.ini /app/alembic.ini
COPY ./scripts /app/scripts
RUN addgroup --system --gid 10001 app && adduser --system --uid 10001 --ingroup app app \
    && chmod +x /app/scripts/*.sh \
    && mkdir -p /var/lib/pmm/artifacts /var/lib/pmm/backups /var/log/pmm /tmp/.cache/fontconfig \
    && chown -R app:app /app /var/lib/pmm /var/log/pmm /tmp/.cache
USER app
EXPOSE 8000
ENTRYPOINT ["tini", "--"]
CMD ["/app/scripts/start-backend-prod.sh"]
