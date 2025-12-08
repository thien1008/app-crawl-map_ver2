# pages/1_Crawl.py
import os
import time as _t
from pathlib import Path

import pandas as pd
import streamlit as st
from dotenv import load_dotenv

# ── services & core
from services.keys import get_serper_api_key, set_serper_api_key, check_serper_key
from services.file_manager import next_nonconflict_path
from services.runner import (
    start_crawl_thread,
    stop_crawl_thread,
    is_running,
    get_result_path,
    get_last_error,
)

load_dotenv()
st.set_page_config(page_title="🗺️ Crawl", layout="wide")
st.title("🗺️ Cào địa điểm từ Google Maps")

# ─────────────────────────────────────────────────────────
# Sidebar: SERPER API Key + nút Dừng
# ─────────────────────────────────────────────────────────

# Kiểm tra xem có chạy trên Streamlit Cloud không
def is_streamlit_cloud():
    """Detect nếu app đang chạy trên Streamlit Cloud"""
    try:
        return hasattr(st, "secrets") and len(st.secrets) > 0
    except:
        return False

is_cloud = is_streamlit_cloud()
current_key = get_serper_api_key()

# Nếu đang trên Cloud và đã có key trong secrets → ẩn phần nhập key
if is_cloud and current_key:
    with st.sidebar:
        st.success("🔐 API Key đã được cấu hình")
        if st.button("🔎 Kiểm tra API Key", use_container_width=True):
            info = check_serper_key()
            if info["ok"]:
                st.success(f"✅ API key hợp lệ. Remaining: {info.get('remaining') or '—'}")
            else:
                st.error(f"❌ Key KHÔNG dùng được\n\n{info['status'] or 'N/A'} — {info['message']}")
else:
    # Local hoặc chưa có key → hiện đầy đủ form nhập
    with st.sidebar.expander("🔐 SERPER API Key", expanded=(get_serper_api_key() is None)):
        current_key = get_serper_api_key() or ""
        api_in = st.text_input(
            "Nhập SERPER_API_KEY",
            value=current_key,
            type="password",
            placeholder="Dán API key tại đây",
            key="inp_serper_key_page",
        )
        colk1, colk2 = st.columns([1, 1])
        if colk1.button("💾 Lưu", use_container_width=True, key="btn_save_serper_page"):
            if not api_in.strip():
                st.warning("Vui lòng nhập SERPER_API_KEY trước khi lưu.")
            else:
                set_serper_api_key(api_in.strip(), persist=True)
                if "SERPER_SAVE_ERROR" in st.session_state:
                    st.error(f"Không lưu được vào .env: {st.session_state['SERPER_SAVE_ERROR']}")
                else:
                    st.success("Đã lưu SERPER_API_KEY (.env).")
        if colk2.button("🔎 Kiểm tra", use_container_width=True, key="btn_check_serper_page"):
            info = check_serper_key()
            if info["ok"]:
                st.success(f"API key hợp lệ. Remaining: {info.get('remaining') or '—'}")
            else:
                st.error(f"Key KHÔNG dùng được. {info['status'] or 'N/A'} — {info['message']}")

# Nút DỪNG ở sidebar
if st.sidebar.button("🛑 Dừng cào", use_container_width=True, key="btn_stop_sidebar"):
    if stop_crawl_thread():
        st.rerun()

# ─────────────────────────────────────────────────────────
# Khu nhập thông tin tìm kiếm (không form để sidebar tự do callback)
# ─────────────────────────────────────────────────────────
st.subheader("🔎 Thông tin tìm kiếm")
c1, c2 = st.columns([1, 1])
query = c1.text_input("Từ khóa (search_query)", value="thi công bảng hiệu")
location = c2.text_input("Khu vực (location)", value="Thành phố Hồ Chí Minh, Việt Nam")

related = st.text_area(
    "Thêm từ khóa liên quan (mỗi dòng hoặc ngăn cách bằng dấu phẩy)",
    value="",
    help="Hệ thống sẽ thêm các từ khóa này vào danh sách tìm kiếm để mở rộng phạm vi thu thập.",
)

num = st.slider("Số kết quả mong muốn (tối đa 100)", 10, 100, 100, 10)
save_unique = st.checkbox("Không ghi đè file trùng tên, luôn tạo file mới", value=True)

running_now = is_running()

# Cò giật rerun 1 lần khi trạng thái chuyển True -> False (phòng khi runner không rerun được)
_prev = st.session_state.get("_was_running", False)
if _prev and not running_now:
    st.session_state["_was_running"] = running_now
    st.rerun()  # rerun 1 phát để tắt spinner & hiện nút
else:
    st.session_state["_was_running"] = running_now

# ─────────────────────────────────────────────────────────
# Nút CHẠY (ẩn khi đang chạy) + Spinner tối giản khi đang chạy
# ─────────────────────────────────────────────────────────
if not running_now:
    if st.button("▶️ Chạy", type="primary", use_container_width=True, key="btn_run"):
        if not get_serper_api_key():
            st.error("Chưa có SERPER_API_KEY. Vào sidebar → '🔐 SERPER API Key' để nhập và lưu.")
        else:
            safe_q = "".join([c if c.isalnum() else "_" for c in query])[:40] or "export"
            excel_path = (
                next_nonconflict_path(f"export_{safe_q}", ".xlsx")
                if save_unique else f"outputs/export_{safe_q}.xlsx"
            )
            ok, _ = start_crawl_thread(
                query,
                location.strip(),
                num,
                gl="vn",
                hl="vi",
                extra_keywords_text=related,
                excel_path=excel_path,
            )
            st.rerun()
else:
    # Spinner tối giản
    st.markdown(
        """
        <style>
        .mini-spinner{display:flex;align-items:center;gap:10px;margin:8px 0 2px 0;}
        .mini-spinner .dot{
          width:14px;height:14px;border:2px solid #ccc;border-top-color:#3a86ff;border-radius:50%;
          animation: spin 0.9s linear infinite;
        }
        @keyframes spin { to { transform: rotate(360deg); } }
        </style>
        <div class="mini-spinner">
          <div class="dot"></div>
          <div>Đang cào…</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    
    # 🔑 QUAN TRỌNG: Auto-refresh mỗi 2 giây để kiểm tra trạng thái
    _t.sleep(2)
    st.rerun()

# ─────────────────────────────────────────────────────────
# Sau khi hoàn tất: hiện lỗi (nếu có) / cho tải file
# ─────────────────────────────────────────────────────────
err = get_last_error()
if err:
    st.error(f"Lỗi khi cào: {err}")

path = get_result_path()
if path and Path(path).exists():
    # Hiển thị thông báo thành công
    st.success("✅ Cào dữ liệu hoàn tất!")
    
    # Hiển thị thông tin file
    file_size = Path(path).stat().st_size / 1024  # KB
    st.info(f"📁 File: **{Path(path).name}** ({file_size:.1f} KB)")
    
    with open(path, "rb") as f:
        data = f.read()
    st.download_button(
        "⬇️ Tải Excel",
        data,
        file_name=Path(path).name,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True,
    )

