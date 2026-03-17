FROM python:3.12-slim
# Pin to 3.12 (stable). Do not upgrade to 3.13+ without testing all deps (weasyprint, asyncpg, passlib).

# Install system dependencies for WeasyPrint
RUN apt-get update && apt-get install -y \
    libpango-1.0-0 \
    libharfbuzz0b \
    libpangoft2-1.0-0 \
    libgdk-pixbuf-xlib-2.0-0 \
    libgobject-2.0-0 \
    libglib2.0-0 \
    libcairo2 \
    postgresql-client \
    docker.io \
    docker-compose \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ./app /app/app
COPY ./alembic /app/alembic
COPY ./alembic.ini /app/alembic.ini

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
