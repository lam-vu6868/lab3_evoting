#!/bin/bash
# ================================================================
# FILE:        db/01_roles.sh
# BƯỚC:        5a/28
# MỤC ĐÍCH:    Tạo 3 role DB (app_user, admin_app, tally_user)
#              Password lấy từ biến môi trường → KHÔNG hard-code.
# PHỤ THUỘC:   Biến env APP_USER_PASSWORD, ADMIN_USER_PASSWORD,
#              TALLY_USER_PASSWORD từ docker-compose.yml
# BƯỚC TIẾP:   db/init.sql (chạy sau, tạo bảng + GRANT)
# ================================================================

set -e  # Dừng ngay nếu có lệnh lỗi

echo "🔧 [01_roles.sh] Bắt đầu tạo 3 role DB..."

# ---------- Kiểm tra biến môi trường ----------
if [ -z "$APP_USER_PASSWORD" ] || [ -z "$ADMIN_USER_PASSWORD" ] || [ -z "$TALLY_USER_PASSWORD" ]; then
    echo "❌ LỖI: Thiếu biến môi trường APP_USER_PASSWORD / ADMIN_USER_PASSWORD / TALLY_USER_PASSWORD"
    exit 1
fi

# ---------- Tạo role app_user ----------
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    DO \$\$
    BEGIN
        IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'app_user') THEN
            CREATE ROLE app_user LOGIN PASSWORD '${APP_USER_PASSWORD}';
            RAISE NOTICE 'Created role: app_user';
        ELSE
            RAISE NOTICE 'Role app_user đã tồn tại, bỏ qua';
        END IF;
    END
    \$\$;
EOSQL

# ---------- Tạo role admin_app ----------
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    DO \$\$
    BEGIN
        IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'admin_app') THEN
            CREATE ROLE admin_app LOGIN PASSWORD '${ADMIN_USER_PASSWORD}';
            RAISE NOTICE 'Created role: admin_app';
        ELSE
            RAISE NOTICE 'Role admin_app đã tồn tại, bỏ qua';
        END IF;
    END
    \$\$;
EOSQL

# ---------- Tạo role tally_user ----------
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    DO \$\$
    BEGIN
        IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'tally_user') THEN
            CREATE ROLE tally_user LOGIN PASSWORD '${TALLY_USER_PASSWORD}';
            RAISE NOTICE 'Created role: tally_user';
        ELSE
            RAISE NOTICE 'Role tally_user đã tồn tại, bỏ qua';
        END IF;
    END
    \$\$;
EOSQL

# ---------- Cấp USAGE trên schema public ----------
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    GRANT USAGE ON SCHEMA public TO app_user;
    GRANT USAGE ON SCHEMA public TO admin_app;
    GRANT USAGE ON SCHEMA public TO tally_user;
EOSQL

echo "✅ [01_roles.sh] Đã tạo xong 3 role + cấp USAGE schema"