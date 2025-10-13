# services/runner.py
import threading
from pathlib import Path
from typing import Optional
import time

import streamlit as st
from streamlit.runtime.scriptrunner import add_script_run_ctx, get_script_run_ctx

from core.crawler import crawl

# Trạng thái dùng chung, KHÔNG phụ thuộc UI
_STATE = {
    "running": False,
    "result_path": None,
    "last_error": None,
    "stop_event": None,
    "worker": None,
    "ctx": None,  # giữ ctx để enqueue_rerun ổn định
}
_LOCK = threading.Lock()

def _set(**kwargs):
    with _LOCK:
        _STATE.update(kwargs)

def _get(key, default=None):
    with _LOCK:
        return _STATE.get(key, default)

def _safe_rerun():
    """Yêu cầu rerun 1 lần. Ưu tiên ctx.enqueue_rerun(); fallback sang st.rerun()."""
    try:
        st.session_state["__last_finish__"] = time.time()
    except Exception:
        pass

    ctx = _get("ctx")
    # Ưu tiên enqueue_rerun
    try:
        if ctx is not None and hasattr(ctx, "enqueue_rerun"):
            ctx.enqueue_rerun()
            return
    except Exception:
        pass
    # Một số bản cũ có request_rerun
    try:
        if ctx is not None and hasattr(ctx, "request_rerun"):
            ctx.request_rerun()
            return
    except Exception:
        pass
    # Fallback cuối: st.rerun()
    try:
        st.rerun()
    except Exception:
        pass

def start_crawl_thread(query, location, num, gl, hl, extra_keywords_text, excel_path):
    if _get("running"):
        return False, "Đang có một phiên cào đang chạy."

    stop_ev = threading.Event()
    ctx = get_script_run_ctx()
    _set(running=True, result_path=None, last_error=None, stop_event=stop_ev, worker=None, ctx=ctx)

    def _job():
        try:
            df = crawl(
                query, location, num,
                gl=gl, hl=hl,
                extra_keywords_text=extra_keywords_text,
                stop_cb=stop_ev.is_set,    # để nút Dừng có tác dụng
            )
            if df is not None and not df.empty:
                # 🔑 Loại bỏ các cột không cần thiết trước khi xuất Excel
                cols_to_drop = ['lat', 'lng', 'reviews', 'type', 'open_hours', 'google_maps_link']
                df = df.drop(columns=[c for c in cols_to_drop if c in df.columns], errors='ignore')
                
                Path(excel_path).parent.mkdir(parents=True, exist_ok=True)
                df.to_excel(excel_path, index=False)
                _set(result_path=excel_path)
        except Exception as e:
            _set(last_error=str(e))
        finally:
            _set(running=False)
            _safe_rerun()  # 🔔 rerun 1 lần khi job KẾT THÚC

    t = threading.Thread(target=_job, daemon=True)
    _set(worker=t)
    # Gắn ctx để enqueue_rerun hoạt động từ thread
    if ctx is not None:
        add_script_run_ctx(t, ctx)
    t.start()
    return True, "OK"

def stop_crawl_thread():
    """Khi bấm 🛑 Dừng: gửi tín hiệu & ẩn spinner ngay."""
    ev: Optional[threading.Event] = _get("stop_event")
    if ev is not None:
        ev.set()
        _set(running=False)
        _safe_rerun()  # 🔔 rerun 1 lần để UI tắt "Đang cào…"
        return True
    return False

def is_running() -> bool:
    return bool(_get("running"))

def get_result_path():
    return _get("result_path")

def get_last_error():
    return _get("last_error")