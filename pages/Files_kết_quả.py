import hashlib
from pathlib import Path
import streamlit as st
from services.state import init_state, bump_sel_ver
from services.file_manager import list_output_files

st.set_page_config(page_title="📂 Files", layout="wide")
init_state()

#Ẩn thanh Streamlit "Deploy" (nếu có)
st.markdown("""
<style>
a[data-testid="stDeployButton"] { display: none !important; }
button[title="Deploy this app"] { display: none !important; }
button[aria-label="Deploy this app"] { display: none !important; }
[data-testid="stToolbar"] { display: none !important; }   /* đã bật */
</style>
""", unsafe_allow_html=True)

st.title("📂 File đã tạo trước đó")

ver = st.session_state.get("sel_ver", 0)

# Xử lý danh sách file
file_items = list_output_files()

def _k(prefix: str, path: str) -> str:
    return f"{prefix}_{ver}_" + hashlib.sha1(path.encode("utf-8","ignore")).hexdigest()[:16]

# Nút thao tác
colA, colB, colC, colD = st.columns([0.2, 0.2, 0.2, 0.4])
btn_all  = colA.button("Chọn tất cả")
btn_none = colB.button("Bỏ chọn")

# Nút xoá hàng loạt (đặt lên đầu)
btn_delete_selected = colC.button("🗑️ Xóa đã chọn", type="primary")

# Áp trạng thái chọn tất cả/bỏ chọn trước khi render
if btn_all or btn_none:
    for it in file_items:
        st.session_state[_k("sel", it["path"])] = bool(btn_all)

# Xử lý xóa hàng loạt
if btn_delete_selected:
    deleted_any, errs = False, []
    for it in file_items:
        if st.session_state.get(_k("sel", it["path"]), False):
            try:
                Path(it["path"]).unlink(missing_ok=True)
                deleted_any = True
            except Exception as e:
                errs.append((it["name"], str(e)))
    if deleted_any:
        bump_sel_ver()
        st.toast("Đã xóa file đã chọn", icon="✅")
        st.rerun()
    elif not errs:
        st.info("Chưa chọn file nào.")
    if errs:
        st.warning("Một số file không xóa được:")
        for name, msg in errs:
            st.text(f"- {name}: {msg}")

# Bảng danh sách
box = st.container()
if not file_items:
    box.info("Chưa có file nào trong thư mục outputs.")
else:
    for it in file_items:
        c1, c2, c3, c4 = box.columns([0.07, 0.53, 0.20, 0.20])
        c1.checkbox("", key=_k("sel", it["path"]))
        c2.markdown(f"**{it['name']}**\n\n_{it['ts_str']}_")
        try:
            with open(it["path"], "rb") as f:
                data = f.read()
            mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" if it["suffix"]==".xlsx" else \
                   ("text/csv" if it["suffix"]==".csv" else "application/octet-stream")
            c3.download_button("Tải xuống", data, file_name=it["name"], mime=mime, key=_k("dl", it["path"]))
        except FileNotFoundError:
            c3.error("File không còn tồn tại")

        # Nút xoá từng file
        if c4.button("Xóa", key=_k("del1", it["path"])):
            try:
                Path(it["path"]).unlink(missing_ok=True)
                st.toast(f"Đã xóa {it['name']}", icon="✅")
                bump_sel_ver()
                st.rerun()
            except Exception as e:
                st.warning(f"Không xóa được {it['name']}: {e}")