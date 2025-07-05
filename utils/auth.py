# utils/auth.py
import hashlib

def hash_password(password):
    """パスワードをSHA256でハッシュ化します。"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(plain_password, hashed_password):
    """入力されたパスワードがハッシュ化されたパスワードと一致するか検証します。"""
    return hash_password(plain_password) == hashed_password