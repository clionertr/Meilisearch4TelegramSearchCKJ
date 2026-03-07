import json
import os
import secrets
from datetime import datetime, timedelta, timezone

TOKEN_STORE_FILE = "session/auth_tokens.json"
TOKEN_TTL_DAYS = 365

def generate_token(user_id: int, phone: str = "+8600000000000", username: str = "Admin"):
    """手动发布一个 Bearer Token 并保存到 session/auth_tokens.json"""
    
    # 生成随机 Token
    token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(days=TOKEN_TTL_DAYS)
    
    token_record = {
        "token": token,
        "user_id": user_id,
        "username": username,
        "first_name": "Manual",
        "last_name": "Generate",
        "phone_number": phone,
        "expires_at": expires_at.isoformat(),
        "created_at": now.isoformat()
    }
    
    # 确保目录存在
    os.makedirs(os.path.dirname(TOKEN_STORE_FILE), exist_ok=True)
    
    # 读取现有 Token
    data = {"version": 1, "tokens": []}
    if os.path.exists(TOKEN_STORE_FILE):
        try:
            with open(TOKEN_STORE_FILE, "r", encoding="utf-8") as f:
                content = json.load(f)
                if isinstance(content, dict) and "tokens" in content:
                    data = content
        except Exception as e:
            print(f"Warning: Failed to load existing tokens: {e}")

    # 添加新 Token
    data["tokens"].append(token_record)
    
    # 写入文件
    tmp_file = f"{TOKEN_STORE_FILE}.tmp"
    with open(tmp_file, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp_file, TOKEN_STORE_FILE)
    
    print(f"Token generated successfully!")
    print(f"Token: {token}")
    print(f"User ID: {user_id}")
    print(f"Expires at: {expires_at.isoformat()}")
    print(f"Saved to: {TOKEN_STORE_FILE}")
    return token

if __name__ == "__main__":
    import sys
    
    uid = 12345678
    if len(sys.argv) > 1:
        try:
            uid = int(sys.argv[1])
        except ValueError:
            print("Invalid User ID, using default.")
            
    generate_token(uid)
