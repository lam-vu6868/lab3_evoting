#!/bin/bash
# FILE: db/01_roles.sh
# MỤC ĐÍCH: Tạo app_user, admin_app, tally_user trước init.sql; đã có script.
# CÁCH DÙNG / VIỆC CẦN LÀM:
# 1. PostgreSQL entrypoint gọi script; nhận password qua biến môi trường Docker.
# 2. Tạo role và USAGE schema, không tạo bảng ở đây.
# 3. Trước dùng thật, thay nội suy password trực tiếp trong SQL bằng cơ chế quote literal
#    an toàn của psql; kiểm tra password có dấu nháy không làm hỏng câu lệnh.
# 4. Không echo password; chạy lại không âm thầm thay password role cũ; file dùng LF.
# ĐỌC KÈM: docs/STRUCTURE.md

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