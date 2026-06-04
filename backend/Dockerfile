# FROM python:3.12-slim-bookworm

# WORKDIR /app

# RUN apt-get update && apt-get install -y --no-install-recommends \
#     libpq-dev gcc \
#     && rm -rf /var/lib/apt/lists/*

# COPY requirements.txt .
# RUN pip install --no-cache-dir -r requirements.txt

# COPY . .

# ENV PYTHONUNBUFFERED=1
# ENV PYTHONDONTWRITEBYTECODE=1
# ENV DJANGO_SETTINGS_MODULE=config.settings.dev

# EXPOSE 8000

# CMD python manage.py migrate --noinput && \
#     python manage.py collectstatic --noinput && \
#     daphne -b 0.0.0.0 -p ${PORT:-8000} config.asgi:application



FROM python:3.12-slim-bookworm
 
WORKDIR /app
 
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*
 
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
 
COPY . .
 
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV DJANGO_SETTINGS_MODULE=config.settings.prod
 
EXPOSE 8000
 
# Runs on every deploy: migrate → collectstatic → start Daphne (ASGI for WebSockets)
# Railway injects $PORT; falls back to 8000 for local docker-compose
CMD ["sh", "-c", "python manage.py migrate --noinput && python manage.py collectstatic --noinput && daphne -b 0.0.0.0 -p ${PORT:-8000} config.asgi:application"]