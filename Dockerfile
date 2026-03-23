FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8420

WORKDIR /app

COPY pyproject.toml README.md ./
COPY src ./src

RUN pip install --no-cache-dir .

EXPOSE 8420

CMD ["sh", "-c", "gunicorn --workers ${WEB_CONCURRENCY:-2} --bind 0.0.0.0:${PORT:-8420} mnl_social_publisher.wsgi:app"]
