# services/keys.py
import os
import json
import requests
import streamlit as st
from dotenv import set_key, find_dotenv

SERPER_ENDPOINT = "https://google.serper.dev/search"   # endpoint tối giản để test

def get_serper_api_key() -> str | None:
    if st.session_state.get("SERPER_API_KEY"):
        return st.session_state["SERPER_API_KEY"]
    if os.getenv("SERPER_API_KEY"):
        return os.getenv("SERPER_API_KEY")
    if hasattr(st, "secrets") and "SERPER_API_KEY" in st.secrets:
        return st.secrets["SERPER_API_KEY"]
    return None

def set_serper_api_key(value: str, persist: bool = True) -> None:
    """Lưu mặc định: session + env; và GHI .env (persist=True luôn)."""
    val = (value or "").strip()
    if not val:
        return
    st.session_state["SERPER_API_KEY"] = val
    os.environ["SERPER_API_KEY"] = val
    # luôn ghi .env
    env_path = find_dotenv(usecwd=True) or ".env"
    try:
        open(env_path, "a", encoding="utf-8").close()
        set_key(env_path, "SERPER_API_KEY", val)
        st.session_state["SERPER_SAVED_PATH"] = env_path
    except Exception as e:
        st.session_state["SERPER_SAVE_ERROR"] = str(e)

def check_serper_key() -> dict:
    """
    Gửi 1 request nhẹ tới Serper để kiểm tra key.
    Trả về dict: { ok: bool, status: int|None, message: str, remaining: str|None }
    Lưu ý: Serper KHÔNG công bố API quota chính thức → remaining có thể None.
    """
    key = get_serper_api_key()
    if not key:
        return {"ok": False, "status": None, "message": "Chưa có SERPER_API_KEY.", "remaining": None}

    headers = {
        "X-API-KEY": key,
        "Content-Type": "application/json",
    }
    payload = {
        "q": "ping",  # truy vấn cực nhỏ
        "gl": "us",
        "hl": "en",
        "num": 1
    }
    try:
        r = requests.post(SERPER_ENDPOINT, headers=headers, data=json.dumps(payload), timeout=12)
        # Thử đoán thông tin quota từ header nếu có
        remaining = None
        for h in ("x-ratelimit-remaining", "x-remaining", "ratelimit-remaining"):
            if h in r.headers:
                remaining = r.headers[h]
                break

        if r.status_code == 200:
            return {"ok": True, "status": r.status_code, "message": "API key hợp lệ.", "remaining": remaining}

        # Một số khả năng thường gặp khi hết/quá hạn mức
        if r.status_code in (402, 429):
            # 402 Payment Required (hết credit) / 429 Too Many Requests (vượt rate)
            try:
                data = r.json()
                msg = data.get("message") or data.get("error") or str(data)
            except Exception:
                msg = r.text
            return {"ok": False, "status": r.status_code, "message": f"Hết hạn mức / quá giới hạn: {msg}", "remaining": remaining}

        # Các lỗi khác (401, 403…)
        try:
            data = r.json()
            msg = data.get("message") or data.get("error") or str(data)
        except Exception:
            msg = r.text
        return {"ok": False, "status": r.status_code, "message": msg, "remaining": remaining}

    except requests.RequestException as e:
        return {"ok": False, "status": None, "message": f"Lỗi kết nối: {e}", "remaining": None}
