#!/bin/bash
# FILE: db/01_roles.sh
# MỤC ĐÍCH: Tạo app_user, admin_app, tally_user trước init.sql; đã có script.
# CÁCH DÙNG / VIỆC CẦN LÀM:
# 1. PostgreSQL entrypoint gọi script; nhận password qua biến môi trường Docker.
# 2. Tạo role và USAGE schema, không tạo bảng ở đây.
# 3. psql đọc password từ env bằng \getenv; :'variable' và format %L quote SQL literal.
#    Heredoc có dấu nháy để shell không thay biến bên trong SQL; không truyền secret qua argv.
# 4. Không echo password; chạy lại không âm thầm thay password role cũ; file dùng LF.
# ĐỌC KÈM: docs/STRUCTURE.md

set -e  # Dừng ngay nếu có lệnh lỗi

echo "🔧 [01_roles.sh] Bắt đầu tạo 3 role DB..."

# ---------- Kiểm tra biến môi trường ----------
if [ -z "$APP_USER_PASSWORD" ] || [ -z "$ADMIN_USER_PASSWORD" ] || [ -z "$TALLY_USER_PASSWORD" ]; then
    echo "❌ LỖI: Thiếu biến môi trường APP_USER_PASSWORD / ADMIN_USER_PASSWORD / TALLY_USER_PASSWORD"
    exit 1
fi

# ---------- Đọc secret trong psql, tạo role còn thiếu và cấp USAGE ----------
# \gexec thực thi các câu CREATE ROLE do SELECT tạo ra; không trả câu SQL ra console.
# Role đã tồn tại không được đổi password khi chạy lại.
psql -X -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<'EOSQL'
\getenv app_password APP_USER_PASSWORD
\getenv admin_password ADMIN_USER_PASSWORD
\getenv tally_password TALLY_USER_PASSWORD

SELECT format('CREATE ROLE %I LOGIN PASSWORD %L', 'app_user', :'app_password')
WHERE NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'app_user')
\gexec

SELECT format('CREATE ROLE %I LOGIN PASSWORD %L', 'admin_app', :'admin_password')
WHERE NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'admin_app')
\gexec

SELECT format('CREATE ROLE %I LOGIN PASSWORD %L', 'tally_user', :'tally_password')
WHERE NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'tally_user')
\gexec

GRANT USAGE ON SCHEMA public TO app_user, admin_app, tally_user;
EOSQL

echo "✅ [01_roles.sh] Đã tạo xong 3 role + cấp USAGE schema"
