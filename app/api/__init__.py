"""
FILE: app/api/__init__.py
MỤC ĐÍCH: Đánh dấu package api. Hợp đồng JSON request/response; main.py ở gốc app điều phối HTTP.
CÁCH TRIỂN KHAI: Giữ file chỉ có docstring; viết nghiệp vụ trong module cùng thư mục.
IMPORT: Dùng đường dẫn đầy đủ đến module, xem docs/STRUCTURE.md.
Không tự import main, kết nối DB hoặc sinh khóa tại đây.
TỰ KIỂM TRA: Import package không gây tác dụng phụ.
"""
