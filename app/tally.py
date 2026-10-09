"""
================================================================
FILE:        app/tally.py
BƯỚC:        16/28
MỤC ĐÍCH:    Tally Service: SELECT tất cả votes → KMS.unwrap → AES decrypt → cộng dồn → trả aggregate
PHỤ THUỘC:   app/models.py (bước 13), app/crypto_service.py (bước 10)
BƯỚC TIẾP:   Bước 17: app/seed_voters.py
================================================================
"""

