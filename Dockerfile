# ================================================================
# FILE:        Dockerfile
# BƯỚC:        4/28
# MỤC ĐÍCH:    Build image FastAPI app (Python 3.11-slim), chạy non-root
# PHỤ THUỘC:   requirements.txt (01), .dockerignore (03b)
# BƯỚC TIẾP:   Bước 05: db/init.sql
# ================================================================

FROM python:3.11-slim

# gcc + libpq-dev: build psycopg2. (Có thể thay bằng psycopg2-binary để bỏ bước này)
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Tạo user non-root TRƯỚC, để COPY --chown một lần (không chown -R chậm)
RUN useradd -m -u 1000 appuser
WORKDIR /app

# Copy requirements trước để tận dụng cache layer
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source. .dockerignore chặn .env, pgdata, kms_keys, .git ... không lọt vào image
COPY --chown=appuser:appuser . .

# Thư mục KMS: chỉ owner truy cập (named volume sẽ thừa hưởng quyền này)
RUN mkdir -p /app/kms_keys && chown appuser:appuser /app/kms_keys && chmod 700 /app/kms_keys

USER appuser
EXPOSE 8000

# Production: KHÔNG --reload (dev dùng docker-compose.dev.yml)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]