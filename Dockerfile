FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install -r requirements.txt

COPY backend/ .
RUN DATABASE_URL=postgresql://build:build@localhost/build \
    ROOMFINDER_DEBUG=False \
    SECRET_KEY=collect-static-build-key \
    python manage.py collectstatic --noinput

CMD ["sh", "-c", "python manage.py migrate --noinput && exec gunicorn config.wsgi:application --bind 0.0.0.0:${PORT:-8000}"]
